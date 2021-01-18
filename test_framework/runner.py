import concurrent.futures
import logging
import traceback
import sys

from test_framework.discovery import discover_suites
from test_framework.enums import Status, RunMode
from test_framework import exceptions
from test_framework.logger import SuiteLogManager
from test_framework.popo import (
    Result,
    TestMethod,
    TestMethodResult,
    TestModule,
    TestModuleResult,
    TestSuiteResult,
)


def create_test_suite_instance(suite_paths: list, stop_on_first_failure: bool = False, test_parameters_func=None,
                               log_manager: SuiteLogManager = None) -> tuple:
    log_manager_ = log_manager or SuiteLogManager(run_logger_name='suite_run')
    sequential_modules, parallel_modules, ignored_modules, failed_imports = discover_suites(suite_paths)
    sequential_module_runs = tuple(
        TestModuleRun(x, stop_run=stop_on_first_failure, test_parameters_func=test_parameters_func, log_manager=log_manager_)
        for x in sequential_modules
    )
    parallel_module_runs = tuple(
        TestModuleRun(x, stop_run=stop_on_first_failure, test_parameters_func=test_parameters_func, log_manager=log_manager_)
        for x in parallel_modules
    )
    return (TestSuiteRun(' '.join(suite_paths), sequential_module_runs, parallel_module_runs, log_manager_),
            ignored_modules, failed_imports)


class Run:
    def __init__(self, test_parameters_func=None, logger=None):
        self.test_parameters_func = test_parameters_func or Run._create_default_parameters
        self.logger = logger or logging.getLogger()

    def run_func(self, func, ResultClass, logger=None) -> Result:
        logger_ = logger or self.logger
        result = None
        if func:
            args, kwargs = self.test_parameters_func(logger_)
            result = ResultClass(func.__name__, status=Status.FAILED)
            try:
                func(*args, **kwargs)
                result.status = Status.PASSED
            except AssertionError as ae:
                _, _, tb = sys.exc_info()
                tb_info = traceback.extract_tb(tb)
                filename, line, func, error_text = tb_info[-1]
                error_text_ = str(ae) if str(ae) else error_text
                logger_.error(error_text_)
                result.message = error_text_
            except exceptions.SkipTestException as ste:
                logger_.info(ste.message)
                result.message = ste.message
                result.status = Status.SKIPPED
            except Exception as e:
                logger_.debug(traceback.format_exc())
                result.message = f'Encountered an exception: {e}'
                logger_.error(result.message)
            result.end()
        return result

    @staticmethod
    def _create_default_parameters(logger) -> tuple:
        return (logger,), {}


class TestSuiteRun:
    def __init__(self, name: str, sequential_modules: tuple, parallel_modules: tuple, log_manager: SuiteLogManager = None):
        self.name = name
        self.sequential_modules = sequential_modules
        self.parallel_modules = parallel_modules
        self.suite_result = None
        self.log_manager = log_manager or SuiteLogManager()

    def execute(self, parallel: bool) -> TestSuiteResult:
        self.suite_result = TestSuiteResult(self.name)
        self.log_manager.on_suite_start(self.name)
        try:
            if parallel:
                for module in self.sequential_modules:
                    self.suite_result.append(module.execute(parallel=False))
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    future_results = {executor.submit(module.execute, parallel): module for module in self.parallel_modules}
                    for future_result in concurrent.futures.as_completed(future_results):
                        try:
                            test_module_result = future_result.result()
                            if test_module_result:
                                self.suite_result.append(test_module_result)
                        except exceptions.StopTestRunException:
                            raise
                        except Exception:
                            self.log_manager.logger.error(traceback.format_exc())
            else:
                for module in self.sequential_modules + self.parallel_modules:
                    self.suite_result.append(module.execute(parallel=False))
        except exceptions.StopTestRunException as stre:
            self.log_manager.logger.error(stre)
        except Exception:
            self.log_manager.logger.error(traceback.format_exc())
        self.suite_result.end()
        self.log_manager.on_suite_stop(self.suite_result)
        return self.suite_result


class TestModuleRun(Run):
    def __init__(self, test_module: TestModule, stop_run: bool, test_parameters_func=None, log_manager: SuiteLogManager = None):
        super().__init__(test_parameters_func)
        self.test_module = test_module
        self.stop_run = stop_run
        self.log_manager = log_manager

    def execute(self, parallel: bool) -> TestModuleResult:
        self.log_manager.on_module_start(self.test_module.name)
        setup = self.setup()
        if setup is None or setup.status is Status.PASSED:
            test_module_result = self.run(parallel and self.test_module.module.__run_mode__==RunMode.PARALLEL_TEST)
        else:
            test_results = [
                TestMethodResult(test.name, status=Status.SKIPPED, message=f'Setup Failed: {setup.message}') for test in self.test_module.tests.values()
            ]
            test_module_result = TestModuleResult(self.test_module.name, test_results=test_results, status=Status.SKIPPED)
        test_module_result.setup = setup
        test_module_result.teardown = self.teardown()
        test_module_result.end()
        self.log_manager.on_module_done(test_module_result)
        return test_module_result

    def setup(self) -> Result:
        result = None
        if self.test_module.setup:
            result = self.run_func(self.test_module.setup, Result, self.log_manager.get_setup_logger(self.test_module.name))
            self.log_manager.on_setup_module_done(self.test_module.name, result)
        return result

    def run(self, parallel: bool) -> TestModuleResult:
        test_module_result = TestModuleResult(self.test_module.name)
        if parallel:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_results = {
                    executor.submit(TestMethodRun(self.test_module.name, test, self.stop_run, self.test_parameters_func, self.log_manager).execute): test
                    for test in self.test_module.tests.values()
                }
                for future_result in concurrent.futures.as_completed(future_results):
                    try:
                        test_result, parameterized_results = future_result.result()
                        test_module_result.append(test_result)
                        test_module_result.extend(parameterized_results)
                        if self.stop_run and test_module_result.test_results[-1].status is Status.FAILED:
                            raise exceptions.StopTestRunException(test_module_result.test_results[-1].message)
                    except exceptions.StopTestRunException:
                        raise
                    except Exception:
                        self.logger.error(traceback.format_exc())
        else:
            for test in self.test_module.tests.values():
                test_result, parameterized_results = \
                TestMethodRun(self.test_module.name, test, self.stop_run, self.test_parameters_func, self.log_manager).execute()
                test_module_result.append(test_result)
                test_module_result.extend(parameterized_results)
                if self.stop_run and test_module_result.test_results[-1].status is Status.FAILED:
                    raise exceptions.StopTestRunException(test_module_result.test_results[-1].message)
        return test_module_result

    def teardown(self) -> Result:
        result= None
        if self.test_module.teardown:
            result = self.run_func(self.test_module.teardown, Result, self.log_manager.get_teardown_logger(self.test_module.name))
            self.log_manager.on_teardown_module_done(self.test_module.name, result)
        return result


class TestMethodRun(Run):
    def __init__(self, module_name: str, test_method: TestMethod, stop_run: bool, test_parameters_func, log_manager: SuiteLogManager):
        super().__init__(test_parameters_func, None)
        self.module_name = module_name
        self.test_method = test_method
        self.log_manager = log_manager
        self.stop_run = stop_run

    def execute(self) -> TestMethodResult:
        setup = self.setup()
        if setup is None or setup.status is Status.PASSED:
            result, parameterized_results = self.run()
        else:
            result = TestMethodResult(self.test_method.name, setup, status=Status.SKIPPED, message=f'Setup Test Failed: {setup.message}')
            parameterized_results = []
            if hasattr(self.test_method.func, 'parameterized_list'):
                for i in range(len(self.test_method.func.parameterized_list)):
                    parameterized_results.append(TestModuleResult(f'{self.test_method.name}[{i}]', status=Status.SKIPPED))
        teardown = self.teardown()
        if result:
            result.setup = setup
            result.teardown = teardown
            self.log_manager.on_test_execution_done(self.module_name, result)
        for i in range(len(parameterized_results)):
            parameterized_results[i].setup = setup
            parameterized_results[i].teardown = teardown
        return result, parameterized_results

    def setup(self) -> Result:
        result = None
        if self.test_method.setup_func:
            result = self.run_func(self.test_method.setup_func, Result, self.log_manager.get_setup_test_logger(self.module_name, self.test_method.name))
            self.log_manager.on_setup_test_done(self.module_name, self.test_method.name, result)
        return result

    def run(self) -> TestMethodResult:
        result = None
        parameter_results = []
        if hasattr(self.test_method.func, 'parameterized_list'):
            if self.test_method.func.is_parallel:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    def execute(i, parameters_list):
                        def parameters_func(logger):
                            args, kwargs = self.test_parameters_func(logger)
                            return args+parameters_list[i], kwargs
                        parameter_run = Run(parameters_func, self.log_manager.get_test_logger(self.module_name, self.test_method.func.names[i]))
                        parameter_result = parameter_run.run_func(self.test_method.func, TestMethodResult)
                        parameter_result.name = self.test_method.func.names[i]
                        self.log_manager.on_parameterized_test_done(self.module_name, parameter_result)
                        return parameter_result
                    future_results = {
                        executor.submit(execute, i, self.test_method.func.parameterized_list): i
                        for i in self.test_method.func.range
                    }
                    for future_result in concurrent.futures.as_completed(future_results):
                        try:
                            parameter_result = future_result.result()
                            if parameter_result:
                                parameter_results.append(parameter_result)
                                if self.stop_run and parameter_result.status is Status.FAILED:
                                    raise exceptions.StopTestRunException(parameter_result.message)
                        except exceptions.StopTestRunException:
                            raise
                        except Exception:
                            self.logger.error(traceback.format_exc())
            else:
                for i in self.test_method.func.range:
                    def parameters_func(logger):
                        args, kwargs = self.test_parameters_func(logger)
                        return args+self.test_method.func.parameterized_list[i], kwargs
                    parameter_run = Run(parameters_func, self.log_manager.get_test_logger(self.module_name, self.test_method.func.names[i]))
                    parameter_result = parameter_run.run_func(self.test_method.func, TestMethodResult)
                    parameter_result.name = self.test_method.func.names[i]
                    self.log_manager.on_parameterized_test_done(self.module_name, parameter_result)
                    parameter_results.append(parameter_result)
        else:
            result = TestMethodResult(self.test_method.name)
            logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
            result = self.run_func(self.test_method.func, TestMethodResult, logger)
            self.log_manager.on_test_done(self.module_name, result)
        return result, parameter_results

    def teardown(self) -> Result:
        result = None
        if self.test_method.teardown_func:
            result = self.run_func(self.test_method.teardown_func, Result, self.log_manager.get_teardown_test_logger(self.module_name, self.test_method.name))
            self.log_manager.on_teardown_test_done(self.module_name, self.test_method.name, result)
        return result
