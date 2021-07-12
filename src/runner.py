import asyncio
import concurrent.futures
import inspect
import logging
from src.resource_profile import create_last_run_rc
import traceback
import sys

sys.path.insert(0, 'C:\\Users\\jon.wesneski\\repos\\test_framework')
from src import exceptions
from src.discovery import discover_suite, discover_module
from src.enums import Status, RunMode
from src.fixtures import metadata
from src.logger import SuiteLogManager
from src.popo import (
    Result,
    TestMethod,
    TestMethodResult,
    TestModule,
    TestModuleResult,
    TestSuiteResult,
)


_empty_logger = logging.getLogger('EMPTY')
_empty_logger.propagate = False
_empty_logger.disabled = True


def default_test_parameters(logger_):
    return (logger_,), {}


def start_test_run(args, test_parameters_func=default_test_parameters) -> tuple:
    suite_run = SuiteRun()
    print(suite_run.run(args.suite.modules, test_parameters_func, not args.no_concurrency, args.stop_on_fail))
    return suite_run.results


class SuiteRun:
    def __init__(self, log_manager: SuiteLogManager = None):
        self.results = []
        self.failed_imports = []
        self.ignored_paths = []
        self.log_manager = log_manager or SuiteLogManager(run_logger_name='suite_run')
        self.logger = self.log_manager.logger

    def run(self, paths, test_parameters_func, allow_concurrency=True, stop_on_fail=False) -> tuple:
        iter_modules = discover_suite(paths)
        self.results, failed_imports = [], set()
        for test_module, failed_import in iter_modules:
            if test_module:
                self.log_manager.on_module_start(test_module.name)
                module_result = TestModuleResult(test_module)
                args, kwargs = test_parameters_func(self.logger)
                module_result.setup_result = run_test_func(self.logger, test_module.setup_func, *args, **kwargs)
                module_result.test_results = self._run_tests(test_parameters_func,
                                                              test_module.tests, 
                                                              allow_concurrency and test_module.run_mode is RunMode.PARALLEL,
                                                              stop_on_fail)
                args, kwargs = test_parameters_func(self.logger)
                module_result.setup_result = run_test_func(self.logger, test_module.teardown_func, *args, **kwargs)
                module_result.end()
                self.results.append(module_result)
                self.log_manager.on_module_done(module_result)
            else:
                failed_imports.add(failed_import)
        self.failed_imports = list(failed_imports)
        self.log_manager.on_suite_stop(self.results)
        create_last_run_rc(self.results)
        return self.results, self.failed_imports, self.ignored_paths

    def _run_tests(self, tests_parameters_func, tests, is_concurrent=True, stop_on_fail=False):
        def intialize_args_and_run(test_method):
            args, kwargs = tests_parameters_func(self.logger)
            return run_test_func(self.logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)

        async def intialize_args_and_run_async(test_method):
            args, kwargs = tests_parameters_func(self.logger)
            return await run_async_test_func(self.logger, test_method.func, *(args + test_method.parameterized_tuple), **kwargs)
        
        async def as_completed(coroutines_, results_, stop_on_first_fail_):
            for fs in coroutines_:
                result = await fs
                results_.append(result)
                if result.status == Status.FAILED and stop_on_first_fail_:
                    [f.cancel() for f in coroutines_]
        
        routines, coroutines = [], []
        for k, test in tests.items():
            if inspect.iscoroutinefunction(test):
                coroutines.append(test)
            else:
                routines.append(test)
        results = []
        loop = asyncio.get_event_loop()
        if is_concurrent:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_results = [
                    executor.submit(intialize_args_and_run, test)
                    for test in routines
                ]
                try:
                    for future_result in concurrent.futures.as_completed(future_results):
                        result = future_result.result()
                        results.append(result)
                        if stop_on_fail and result.status is Status.FAILED:
                            raise exceptions.StopTestRunException(result.message)
                except exceptions.StopTestRunException as stre:
                    self.logger.critical(stre)
                except:
                    self.logger.error(traceback.format_exc())
            loop.run_until_complete(as_completed(coroutines, results, stop_on_fail))
        else:
            try:
                for test in routines:
                    results.append(intialize_args_and_run(test))
                    if stop_on_fail and results[-1].status is Status.FAILED:
                        raise exceptions.StopTestRunException(results[-1].message)
                for test in coroutines:
                    results.append(loop.run_until_complete(intialize_args_and_run_async(test)))
                    if stop_on_fail and results[-1].status is Status.FAILED:
                        raise exceptions.StopTestRunException(results[-1].message)
            except exceptions.StopTestRunException as stre:
                self.logger.critical(stre)
            except:
                self.logger.error(traceback.format_exc())
        return results

    def _run_tests2(self, funcs, stop_on_first_fail: bool = True, sequential: bool = False):
        def handle_awaited_result(result, coroutines_, results_, stop_on_first_fail_):
            results_.append(result)
            if result.status == Status.FAILED and stop_on_first_fail_:
                [f.cancel() for f in coroutines_]

        async def as_completed(coroutines_, results_, stop_on_first_fail_):
            for fs in coroutines_:
                handle_awaited_result(await fs, coroutines_, results_, stop_on_first_fail_)
    
        coroutines = []
        results = []
        loop = asyncio.get_event_loop()
        for func in funcs:
            if inspect.iscoroutinefunction(func):
                coroutines.append(loop.create_task(run_async_test_func(logging.getLogger(), func)))
            else:
                results.append(run_test_func(logging.getLogger(), func))

        if coroutines:
            if sequential:
                for fs in coroutines:
                    handle_awaited_result(loop.run_until_complete(fs), coroutines, results, stop_on_first_fail)
            else:          
                loop.run_until_complete(as_completed(coroutines, results, stop_on_first_fail))


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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
