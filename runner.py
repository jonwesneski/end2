import concurrent.futures
from datetime import datetime
import logging

from test_framework.discovery import discover_suites
from test_framework.enums import Status, RunMode
from test_framework.logger import LogManager
from test_framework.popo import (
    Result,
    StopTestRunException,
    TestMethod,
    TestMethodResult,
    TestModule,
    TestModuleResult
)


def create_test_suite_instance(suite_paths: list, logger=None):
    log_manager = LogManager()
    sequential_modules, parallel_modules, ignored_modules, failed_imports = discover_suites(suite_paths)
    sequential_module_runs = tuple(TestModuleRun(x, stop_run=False, log_manager=log_manager) for x in sequential_modules)
    parallel_module_runs = tuple(TestModuleRun(x, stop_run=False, log_manager=log_manager) for x in parallel_modules)
    return TestSuiteRun(sequential_module_runs, parallel_module_runs, logger), ignored_modules, failed_imports



class Run:
    def __init__(self, test_parameters_func=None, logger=None):
        self.test_parameters_func = test_parameters_func or Run._create_default_parameters
        self.default_logger = logging.getLogger()
        self.logger = logger or self.default_logger

    def run_func(self, func, logger=None) -> Result:
        result = None
        if func:
            args, kwargs = self.test_parameters_func(logger or self.logger)
            result = Result(func.__name__, Status.FAILED)
            try:
                func(*args, **kwargs)
                result.status = Status.PASSED
            except AssertionError as ae:
                result.message = ae
                self.logger.error(ae)
            except Exception as e:
                result.message = e
                self.logger.error(e)
            result.end()
        return result

    @staticmethod
    def _create_default_parameters(logger):
        return [logger], {}


class TestMethodRun(Run):
    def __init__(self, test_method: TestMethod, test_parameters_func=None, logger=None):
        super().__init__(test_parameters_func, logger)
        self.test_method = test_method

    def execute(self) -> TestMethodResult:
        setup = self.setup()
        if setup is None or setup.status == Status.PASSED:
            result = self.run()
        else:
            result = TestMethodResult(self.test_method.name, setup, Status.SKIPPED)
            self.logger.critical(result.setup.message)
        result.end()
        self.logger.info(result.status)
        result.setup = setup
        result.teardown = self.teardown()
        if result.teardown and result.teardown.status != Status.PASSED:
            self.logger.critical(result.teardown.message)
        return result

    def setup(self) -> Result:
        return self.run_func(self.test_method.setup_func)

    def run(self) -> TestMethodResult:
        args, kwargs = self.test_parameters_func(self.logger)
        result = TestMethodResult(self.test_method.name)
        try:
            if hasattr(self.test_method.func, 'parameterized_list'):
                for i, parameters in enumerate(self.test_method.func.parameterized_list):
                    def parameters_func(logger):
                        args, kwargs = self.test_parameters_func(self.logger)
                        return args+list(parameters), kwargs
                    parameter_run = Run(parameters_func, self.logger)
                    parameter_result = parameter_run.run_func(self.test_method.func)
                    parameter_result.name = str(i)
                    result.parameterized_results.append(parameter_result)
            else:
                args, kwargs = self.test_parameters_func(self.logger)
                self.test_method.func(*args, **kwargs)
            result.status = Status.PASSED
        except AssertionError as ae:
            result.message = ae
            result.status = Status.FAILED
        except Exception as e:
            result.message = e
            result.status = Status.FAILED
            self.logger.error(e)
        return result.end()

    def teardown(self) -> Result:
        return self.run_func(self.test_method.teardown_func)


class TestModuleRun(Run):
    def __init__(self, test_module: TestModule, stop_run: bool, log_manager: LogManager, test_parameters_func=None):
        super().__init__(test_parameters_func)
        self.test_module = test_module
        self.stop_run = stop_run
        self.log_manager = log_manager

    def execute(self, threads: bool) -> TestModuleResult:
        setup = self.setup()
        test_module_result = self.run(threads and self.test_module.module.__run_mode__==RunMode.PARALLEL_TEST)
        test_module_result.setup = setup
        test_module_result.teardown = self.teardown()
        return test_module_result.end()

    def setup(self) -> Result:
        logger = self.default_logger if not self.test_module.setup else self.log_manager.get_setup_logger(self.test_module.name)
        return self.run_func(self.test_module.setup, logger)

    def run(self, threads: bool) -> TestModuleResult:
        test_module_result = TestModuleResult(self.test_module.name)
        if test_module_result.setup is None or test_module_result.setup.status == Status.PASSED:
            if threads:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    future_results = {executor.submit(TestMethodRun(test, None, self.log_manager.get_test_logger(self.test_module.name, test.name)).execute): test for test in self.test_module.tests}
                    for future_result in concurrent.futures.as_completed(future_results):
                        try:
                            test_result = future_result.result()
                            if test_result:
                                test_module_result.test_results.append(test_result)
                                if self.stop_run and test_module_result.test_results[-1].status == Status.FAILED:
                                    raise StopTestRunException(test_module_result.test_results[-1].message)
                        except Exception as exc:
                            if isinstance(exc, StopTestRunException):
                                raise
                            self.logger.error(t)
            else:
                for test in self.test_module.tests:
                    # self.logger.warning('START')
                    # self.logger.warning(test.name)
                    # self.logger.warning('END')
                    #self.log_manager.get_test_logger(self.test_module.name, test.name)
                    test_module_result.test_results.append(TestMethodRun(test, None, self.log_manager.get_test_logger(self.test_module.name, test.name)).execute())
                    if self.stop_run and test_module_result.test_results[-1].status == Status.FAILED:
                        raise StopTestRunException(test_module_result.test_results[-1].message)
        return test_module_result.end()

    def teardown(self) -> Result:
        logger = self.default_logger if not self.test_module.teardown else self.log_manager.get_teardown_logger(self.test_module.name)
        return self.run_func(self.test_module.teardown, logger)


class TestSuiteRun:
    def __init__(self, sequential_modules: tuple, parallel_modules: tuple, logger=None):
        self.sequential_modules = sequential_modules
        self.parallel_modules = parallel_modules
        self.module_results = []
        self.logger = logger or logging.getLogger()

    def execute(self, threads: bool):
        self.module_results = []
        try:
            if threads:
                for s in self.sequential_modules:
                    self.module_results.append(s.execute(threads=False))
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    future_results = {executor.submit(module.execute, threads): module for module in self.parallel_modules}
                    for future_result in concurrent.futures.as_completed(future_results):
                        try:
                            test_module_result = future_result.result()
                            if test_module_result:
                                self.module_results.append(test_module_result)
                        except Exception as exc:
                            self.logger.error(exc)
            else:
                for s in self.sequential_modules + self.parallel_modules:
                    self.module_results.append(s.execute(threads=False))
        except StopTestRunException as stre:
            pass
        except Exception as e:
            self.logger.error(e)
        return self.module_results
