import asyncio
import concurrent.futures
import inspect
import traceback
import sys
from typing import Tuple

from src import exceptions
from src.discovery import discover_suite
from src.enums import Status, RunMode
from src.fixtures import metadata, teardown
from src.logger import SuiteLogManager
from src.models.result import (
    Result,
    TestMethodResult,
    TestModuleResult,
    TestSuiteResult,
)
from src.models.test_popo import TestModule
from src.resource_profile import create_last_run_rc


def default_test_parameters(logger, package_object):
    return (logger,), {}


def create_test_run(args, test_parameters_func=default_test_parameters) -> tuple:
    sequential_modules, parallel_modules, failed_imports = discover_suite(args.suite.modules)
    suite_run = SuiteRun(args, test_parameters_func, sequential_modules, parallel_modules)
    return suite_run, failed_imports


def start_test_run(args, test_parameters_func=default_test_parameters) -> Tuple[TestSuiteResult, tuple]:
    suite_run, failed_imports = create_test_run(args, test_parameters_func)
    print(suite_run.run(args.suite.modules, test_parameters_func))
    return suite_run.results, failed_imports


class SuiteRun:
    def __init__(self, args, test_parameters_func, sequential_modules: tuple, parallel_modules: tuple, log_manager: SuiteLogManager = None):
        self.args = args
        self.test_parameters_func = test_parameters_func
        if self.args.no_concurrency:
            self.sequential_modules = sequential_modules + parallel_modules
            self.parallel_modules = tuple()
        else:
            self.sequential_modules = sequential_modules
            self.parallel_modules = parallel_modules
        self.allow_concurrency = not self.args.no_concurrency
        self.name = 'suite_run'
        self.results = None
        self.log_manager = log_manager or SuiteLogManager(run_logger_name='suite_run', max_folders=self.args.max_log_folders)
        self.logger = self.log_manager.logger

    def run(self, paths: list, test_parameters_func) -> tuple:
        self.log_manager.on_suite_start(self.name)
        self.results = TestSuiteResult(self.name)
        try:
            for test_module in self.sequential_modules:
                module_run = TestModuleRun(test_parameters_func, test_module, self.log_manager, self.args.stop_on_fail)
                self.results.append(module_run.run())

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.max_workers) as executor:
                futures = [
                    executor.submit(
                        TestModuleRun(test_parameters_func, test_module, self.log_manager, self.args.stop_on_fail, executor).run)
                    for test_module in self.parallel_modules
                ]
                for future in futures:
                    self.results.append(future.result())
        except exceptions.StopTestRunException as stre:
            self.logger.critical(stre)
        self.results.end()
        self.log_manager.on_suite_stop(self.results)
        create_last_run_rc(self.results)
        return self.results


class TestModuleRun:
    def __init__(self, test_parameters_func, module: TestModule, log_manager: SuiteLogManager, stop_on_fail: bool, concurrent_executor: concurrent.futures.ThreadPoolExecutor = None):
        self.test_parameters_func = test_parameters_func
        self.module = module
        self.log_manager = log_manager
        self.stop_on_fail = stop_on_fail
        self.concurrent_executor = concurrent_executor

    def run(self) -> TestModuleResult:
        self.module.test_package_list.setup()
        setup_result = self.setup()
        result = TestModuleResult(self.module, setup_result)
        result.test_results = self.run_tests()
        result.teardown = self.teardown()
        result.end()
        self.log_manager.on_module_done(result)
        self.module.test_package_list.teardown()
        return result

    def setup(self) -> Result:
        setup_logger = self.log_manager.get_setup_logger(self.module.name)
        args, kwargs = self.test_parameters_func(setup_logger, self.module.test_package_list.package_object)
        result = run_test_func(setup_logger, self.module.setup_func, *args, **kwargs)
        self.log_manager.on_setup_module_done(self.module.name, result.to_base())
        return result

    def run_tests(self) -> list:
        def intialize_args_and_run(test_method):
            logger = self.log_manager.get_test_logger(self.module.name, test_method.name)
            args, kwargs = self.test_parameters_func(logger, self.module.test_package_list.package_object)
            b = 2
            result = run_test_func(logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)
            self.log_manager.on_test_done(self.module.name, result)
            return result

        async def intialize_args_and_run_async(test_method):
            logger = self.log_manager.get_test_logger(self.module.name, test_method.name)
            args, kwargs = self.test_parameters_func(logger, self.module.test_package_list.package_object)
            result = await run_async_test_func(logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)
            self.log_manager.on_test_done(self.module.name, result)
            return result
        
        async def as_completed(coroutines_, results_, stop_on_first_fail_):
            for fs in coroutines_:
                result = await intialize_args_and_run_async(fs)
                results_.append(result)
                if result.status is Status.FAILED and stop_on_first_fail_:
                    [f.cancel() for f in coroutines_]
        
        routines, coroutines = [], []
        for k, test in self.module.tests.items():
            if inspect.iscoroutinefunction(test.func):
                coroutines.append(test)
            else:
                routines.append(test)
        results = []
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if self.concurrent_executor:
            future_results = [
                self.concurrent_executor.submit(intialize_args_and_run, test)
                for test in routines
            ]
            try:
                for future_result in concurrent.futures.as_completed(future_results):
                    result = future_result.result()
                    results.append(result)
                    if self.stop_on_fail and result.status is Status.FAILED:
                        raise exceptions.StopTestRunException(result.message)
            except exceptions.StopTestRunException as stre:
                raise
            except:
                self.log_manager.logger.error(traceback.format_exc())
            loop.run_until_complete(as_completed(coroutines, results, self.stop_on_fail))
        else:
            try:
                for test in routines:
                    results.append(intialize_args_and_run(test))
                    if self.stop_on_fail and results[-1].status is Status.FAILED:
                        raise exceptions.StopTestRunException(results[-1].message)
                for test in coroutines:
                    results.append(loop.run_until_complete(intialize_args_and_run_async(test)))
                    if self.stop_on_fail and results[-1].status is Status.FAILED:
                        raise exceptions.StopTestRunException(results[-1].message)
            except exceptions.StopTestRunException as stre:
                raise
            except:
                self.log_manager.logger.error(traceback.format_exc())
        return results

    def teardown(self) -> Result:
        teardown_logger = self.log_manager.get_teardown_logger(self.module.name)
        args, kwargs = self.test_parameters_func(teardown_logger, self.module.test_package_list.package_object)
        result = run_test_func(teardown_logger, self.module.teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_module_done(self.module.name, result.to_base())
        return result


def run_test_func(logger, func, *args, **kwargs) -> TestMethodResult:
    """
    >>> from src.logger import empty_logger
    >>> def test_1():
    ...     assert True
    >>> result = run_test_func(empty_logger, test_1)
    >>> result.status == Status.PASSED and result.message == "" and result.end_time is not None
    True
    >>> def test_2(a):
    ...     assert False
    >>> result = run_test_func(empty_logger, test_2, 1)
    >>> result.status == Status.FAILED and result.message != "" and result.end_time is not None
    True
    >>> def test_3(a, b):
    ...     raise exceptions.SkipTestException("I skip")
    >>> result = run_test_func(empty_logger, test_3, a=1, b=2)
    >>> result.status == Status.SKIPPED and result.message == "I skip" and result.end_time is not None
    True
    >>> def test_4(a, b, c):
    ...     raise Exception("Error")
    >>> result = run_test_func(empty_logger, test_4, 1, 2, 3)
    >>> result.status == Status.FAILED and "Encountered an exception" in result.message and result.end_time is not None
    True
    """
    result = TestMethodResult(func.__name__, status=Status.FAILED, metadata=getattr(func, 'metadata', None))
    try:
        func(*args, **kwargs)
        result.status = Status.PASSED
    except AssertionError as ae:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, error_text = tb_info[-1]
        result.message = str(ae) if str(ae) else error_text
        logger.error(result.message)
    except exceptions.SkipTestException as ste:
        logger.info(ste.message)
        result.message = ste.message
        result.status = Status.SKIPPED
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.message = f'Encountered an exception: {e}'
        logger.error(result.message)
    result.end()
    return result


async def run_async_test_func(logger, func, result_class: Result, *args, **kwargs) -> Result:
    """
    >>> from src.logger import empty_logger
    >>> import asyncio
    >>> loop = asyncio.get_event_loop()
    >>> async def test_1():
    ...     assert True
    >>> result = loop.run_until_complete(run_async_test_func(empty_logger, test_1))
    >>> result.status == Status.PASSED and result.message == "" and result.end_time is not None
    True
    >>> def test_2(a):
    ...     assert False
    >>> result = loop.run_until_complete(run_async_test_func(empty_logger, test_2, 1))
    >>> result.status == Status.FAILED and result.message != "" and result.end_time is not None
    True
    >>> def test_3(a, b):
    ...     raise exceptions.SkipTestException("I skip")
    >>> result = loop.run_until_complete(run_async_test_func(empty_logger, test_3, a=1, b=2))
    >>> result.status == Status.SKIPPED and result.message == "I skip" and result.end_time is not None
    True
    >>> def test_4(a, b, c):
    ...     raise Exception("Error")
    >>> result = loop.run_until_complete(run_async_test_func(empty_logger, test_4, 1, 2, 3))
    >>> result.status == Status.FAILED and "Encountered an exception" in result.message and result.end_time is not None
    True
    """
    result = result_class(func.__name__, status=Status.FAILED, metadata=getattr(func, 'metadata', None))
    try:
        await func(*args, **kwargs)
        result.status = Status.PASSED
    except AssertionError as ae:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, error_text = tb_info[-1]
        result.message = str(ae) if str(ae) else error_text
        logger.error(result.message)
    except exceptions.SkipTestException as ste:
        logger.info(ste.message)
        result.message = ste.message
        result.status = Status.SKIPPED
    except asyncio.CancelledError:
        result.message = 'I got cancelled'
        result.status = Status.SKIPPED
        logger.info(result.message)
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.message = f'Encountered an exception: {e}'
        logger.error(result.message)
    result.end()
    return result
