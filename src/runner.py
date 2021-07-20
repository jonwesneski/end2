import asyncio
import concurrent.futures
import inspect
import traceback
import sys

from src import exceptions
from src.discovery import discover_suite, discover_module
from src.enums import Status, RunMode
from src.fixtures import metadata, teardown
from src.logger import SuiteLogManager
from src.popo import (
    Result,
    TestMethod,
    TestMethodResult,
    TestModule,
    TestModuleResult,
    TestSuiteResult,
)
from src.resource_profile import create_last_run_rc


def default_test_parameters(logger_):
    return (logger_,), {}


def start_test_run(args, test_parameters_func=default_test_parameters) -> tuple:
    suite_run = SuiteRun(args)
    print(suite_run.run(args.suite.modules, test_parameters_func))
    return suite_run.results


class SuiteRun:
    def __init__(self, args, log_manager: SuiteLogManager = None):
        self.args = args
        self.allow_concurrency = not self.args.no_concurrency
        self.name = 'suite_run'
        self.results = None
        self.failed_imports = tuple()
        self.ignored_paths = tuple()
        self.log_manager = log_manager or SuiteLogManager(run_logger_name='suite_run', max_folders=self.args.max_log_folders)
        self.logger = self.log_manager.logger

    def run(self, paths: list, test_parameters_func) -> tuple:
        sequential_modules, parallel_modules, self.failed_imports = discover_suite(paths)
        self.log_manager.on_suite_start(self.name)
        self.results = TestSuiteResult(self.name)
        concurrent_executor = None
        sequential_modules_ = sequential_modules + parallel_modules
        if self.allow_concurrency:
            concurrent_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.args.max_workers)
            sequential_modules_ = sequential_modules
        try:
            for test_module in sequential_modules_:
                module_run = TestModuleRun(test_parameters_func, test_module, self.log_manager, self.args.stop_on_fail)
                self.results.append(module_run.run())
            if concurrent_executor:
                for test_module in parallel_modules:
                    module_run = TestModuleRun(test_parameters_func, test_module, self.log_manager, self.args.stop_on_fail, concurrent_executor)
                    self.results.append(module_run.run())
        except exceptions.StopTestRunException as stre:
            self.logger.critical(stre)
        if concurrent_executor:
            concurrent_executor.shutdown(True)
        self.results.end()
        self.log_manager.on_suite_stop(self.results)
        create_last_run_rc(self.results)
        return self.results, self.failed_imports, self.ignored_paths


class TestModuleRun:
    def __init__(self, test_parameters_func, module, log_manager: SuiteLogManager, stop_on_fail: bool, concurrent_executor: concurrent.futures.ThreadPoolExecutor = None):
        self.test_parameters_func = test_parameters_func
        self.module = module
        self.log_manager = log_manager
        self.stop_on_fail = stop_on_fail
        self.concurrent_executor = concurrent_executor

    def run(self) -> TestModuleResult:
        setup_result = self.setup()
        result = TestModuleResult(self.module, setup_result)
        result.test_results = self.run_tests()
        result.teardown = self.teardown()
        result.end()
        self.log_manager.on_module_done(result)
        return result

    def setup(self) -> Result:
        setup_logger = self.log_manager.get_setup_logger(self.module.name)
        args, kwargs = self.test_parameters_func(setup_logger)
        result = run_test_func(setup_logger, self.module.setup_func, *args, **kwargs)
        self.log_manager.on_setup_module_done(self.module.name, result)
        return result

    def run_tests(self) -> list:
        def intialize_args_and_run(test_method):
            logger = self.log_manager.get_test_logger(self.module.name, test_method.name)
            args, kwargs = self.test_parameters_func(logger)
            return run_test_func(logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)

        async def intialize_args_and_run_async(test_method):
            logger = self.log_manager.get_test_logger(self.module.name, test_method.name)
            args, kwargs = self.test_parameters_func(logger)
            return await run_async_test_func(logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)
        
        async def as_completed(coroutines_, results_, stop_on_first_fail_):
            for fs in coroutines_:
                result = await fs
                results_.append(result)
                if result.status is Status.FAILED and stop_on_first_fail_:
                    [f.cancel() for f in coroutines_]
        
        routines, coroutines = [], []
        for k, test in self.module.tests.items():
            if inspect.iscoroutinefunction(test):
                coroutines.append(test)
            else:
                routines.append(test)
        results = []
        loop = asyncio.get_event_loop()
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
        args, kwargs = self.test_parameters_func(teardown_logger)
        result = run_test_func(teardown_logger, self.module.setup_func, *args, **kwargs)
        self.log_manager.on_teardown_module_done(self.module.name, result)
        return result


def run_test_func(logger, func, *args, **kwargs) -> TestMethodResult:
    """
    >>> def test_1():
    ...     assert True
    >>> result = run_test_func(_empty_logger, test_1)
    >>> result.status == Status.PASSED and result.message == "" and result.end_time is not None
    True
    >>> def test_2(a):
    ...     assert False
    >>> result = run_test_func(_empty_logger, test_2, 1)
    >>> result.status == Status.FAILED and result.message != "" and result.end_time is not None
    True
    >>> def test_3(a, b):
    ...     raise exceptions.SkipTestException("I skip")
    >>> result = run_test_func(_empty_logger, test_3, a=1, b=2)
    >>> result.status == Status.SKIPPED and result.message == "I skip" and result.end_time is not None
    True
    >>> def test_4(a, b, c):
    ...     raise Exception("Error")
    >>> result = run_test_func(_empty_logger, test_4, 1, 2, 3)
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


async def run_async_test_func(logger, func, *args, **kwargs) -> TestMethodResult:
    """
    >>> import asyncio
    >>> loop = asyncio.get_event_loop()
    >>> async def test_1():
    ...     assert True
    >>> result = loop.run_until_complete(run_async_test_func(_empty_logger, test_1))
    >>> result.status == Status.PASSED and result.message == "" and result.end_time is not None
    True
    >>> def test_2(a):
    ...     assert False
    >>> result = loop.run_until_complete(run_async_test_func(_empty_logger, test_2, 1))
    >>> result.status == Status.FAILED and result.message != "" and result.end_time is not None
    True
    >>> def test_3(a, b):
    ...     raise exceptions.SkipTestException("I skip")
    >>> result = loop.run_until_complete(run_async_test_func(_empty_logger, test_3, a=1, b=2))
    >>> result.status == Status.SKIPPED and result.message == "I skip" and result.end_time is not None
    True
    >>> def test_4(a, b, c):
    ...     raise Exception("Error")
    >>> result = loop.run_until_complete(run_async_test_func(_empty_logger, test_4, 1, 2, 3))
    >>> result.status == Status.FAILED and "Encountered an exception" in result.message and result.end_time is not None
    True
    """
    result = TestMethodResult(func.__name__, status=Status.FAILED, metadata=getattr(func, 'metadata', None))
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
