from argparse import Namespace
import asyncio
import concurrent.futures
import inspect
from logging import Logger
import traceback
import sys
from typing import (
    List,
    Tuple
)

from end2 import exceptions
from end2.discovery import discover_suite
from end2.constants import Status
from end2.logger import SuiteLogManager
from end2.models.result import (
    Result,
    TestMethodResult,
    TestModuleResult,
    TestSuiteResult,
)
from end2.models.testing_containers import (
    DynamicMroMixin,
    TestGroups,
    TestMethod,
    TestModule,
    TestPackageTree
)
from end2.resource_profile import create_last_run_rc


def default_test_parameters(logger, package_object) -> Tuple[tuple, dict]:
    return (logger,), {}


def create_test_run(parsed_args: Namespace, test_parameters_func=default_test_parameters
                    , log_manager: SuiteLogManager = None) -> Tuple[TestSuiteResult, Tuple[str]]:
    test_packages, failed_imports = discover_suite(parsed_args.suite.modules)
    suite_run = SuiteRun(parsed_args, test_parameters_func, test_packages, log_manager)
    return suite_run, failed_imports


def start_test_run(parsed_args: Namespace, test_parameters_func=default_test_parameters
                   , log_manager: SuiteLogManager = None) -> Tuple[TestSuiteResult, Tuple[str]]:
    suite_run, failed_imports = create_test_run(parsed_args, test_parameters_func, log_manager)
    return suite_run.run(), failed_imports


class SuiteRun:
    def __init__(self, parsed_args: Namespace, test_parameters_func, test_packages: Tuple[TestPackageTree], log_manager: SuiteLogManager = None) -> None:
        self.parsed_args = parsed_args
        self.test_parameters_func = test_parameters_func
        self.test_packages = test_packages
        self.allow_concurrency = not self.parsed_args.no_concurrency
        self.name = 'suite_run'
        self.results = None
        self.log_manager = log_manager or SuiteLogManager(run_logger_name=self.name, max_folders=self.parsed_args.max_log_folders)
        self.logger = self.log_manager.logger

    def run(self) -> TestSuiteResult:
        self.log_manager.on_suite_start(self.name)
        self.results = TestSuiteResult(self.name)
        try:
            for package in self.test_packages:
                test_parameters_func = package.package_test_parameters_func or self.test_parameters_func 
                package.setup()
                if self.allow_concurrency:
                    sequential_modules = package.sequential_modules
                    parallel_modules = package.parallel_modules
                else:
                    sequential_modules = sequential_modules + parallel_modules
                    parallel_modules = tuple()
                for test_module in sequential_modules:
                    module_run = TestModuleRun(test_parameters_func, test_module, self.log_manager, package.package_object, self.parsed_args.stop_on_fail)
                    self.results.append(module_run.run())

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.parsed_args.max_workers) as executor:
                    futures = [
                        executor.submit(
                            TestModuleRun(test_parameters_func, test_module, self.log_manager, package.package_object, self.parsed_args.stop_on_fail, executor).run)
                        for test_module in parallel_modules
                    ]
                    for future in futures:
                        self.results.append(future.result())
                package.teardown()
        except exceptions.StopTestRunException as stre:
            self.logger.critical(stre)
        self.results.end()
        self.log_manager.on_suite_stop(self.results)
        create_last_run_rc(self.results)
        return self.results


class TestModuleRun:
    def __init__(self, test_parameters_func, module: TestModule, log_manager: SuiteLogManager
                 , package_object: DynamicMroMixin, stop_on_fail: bool
                 , concurrent_executor: concurrent.futures.ThreadPoolExecutor = None) -> None:
        self.test_parameters_func = test_parameters_func
        self.module = module
        self.log_manager = log_manager
        self.package_object = package_object
        self.stop_on_fail = stop_on_fail
        self.concurrent_executor = concurrent_executor

    def run(self) -> TestModuleResult:
        result = TestModuleResult(self.module)
        setup_results, test_results, teardown_results = self.run_group(self.module.groups)
        result.setups = setup_results
        result.test_results = test_results
        result.teardowns = teardown_results
        result.end()
        self.log_manager.on_module_done(result)
        return result

    def run_group(self, group: TestGroups) -> Tuple[List[Result], List[TestMethodResult], List[Result]]:
        setup_results = [self.setup(group.setup_func)]
        teardown_results = []
        if setup_results[0].status is Status.FAILED:
            test_results = self.create_skipped_results(group, setup_results[0].message)
        else:
            test_results = self.run_tests(group)
            for group_ in group.children:
                sr, tr, trr = self.run_group(group_)
                setup_results.extend(sr)
                test_results.extend(tr)
                teardown_results.extend(trr)
            teardown_results.append(self.teardown(group.teardown_func))
        return setup_results, test_results, teardown_results

    def create_skipped_results(self, group: TestGroups, message: str) -> List[TestMethodResult]:
        test_results = [
            TestMethodResult(v.name, status=Status.SKIPPED, message=message, description=v.__doc__, metadata=v.metadata)
            for _, v in group.tests.items()
        ]
        for g in group.children:
            test_results.extend(self.create_skipped_results(g, message))
        return test_results

    def setup(self, setup_func) -> Result:
        setup_logger = self.log_manager.get_setup_logger(self.module.name)
        args, kwargs = self.test_parameters_func(setup_logger, self.package_object)
        if inspect.iscoroutinefunction(setup_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async_test_func(setup_logger, setup_func, *args, **kwargs))
            loop.close()
        else:
            result = run_test_func(setup_logger, setup_func, *args, **kwargs)
        self.log_manager.on_setup_module_done(self.module.name, result.to_base())
        return result

    def run_tests(self, group: TestGroups) -> List[TestMethodResult]:        
        async def as_completed(coroutines_, results_, stop_on_first_fail_):
            for fs in coroutines_:
                try:
                    result = await fs.run_async()
                    results_.append(result)
                    if result.status is Status.FAILED and stop_on_first_fail_:
                        [f.cancel() for f in coroutines_]
                except exceptions.IgnoreTestException:
                    pass
        
        routines, coroutines = [], []
        for k, test in group.tests.items():
            test_run = TestMethodRun(test, self.test_parameters_func, self.log_manager, self.module.name, self.package_object)
            if inspect.iscoroutinefunction(test.func):
                coroutines.append(test_run)
            else:
                routines.append(test_run)
        results = []
        loop = None
        try:
            if self.concurrent_executor:
                future_results = [
                    self.concurrent_executor.submit(test.run)
                    for test in routines
                ]
                try:
                    for future_result in concurrent.futures.as_completed(future_results):
                        try:
                            result = future_result.result()
                            results.append(result)
                            if self.stop_on_fail and result.status is Status.FAILED:
                                raise exceptions.StopTestRunException(result.message)
                        except exceptions.IgnoreTestException:
                            pass
                except exceptions.StopTestRunException as stre:
                    raise
                except:
                    self.log_manager.logger.error(traceback.format_exc())
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(as_completed(coroutines, results, self.stop_on_fail))
                loop.close()
            else:
                try:
                    for test in routines:
                        try:
                            results.append(test.run())
                            if self.stop_on_fail and results[-1].status is Status.FAILED:
                                raise exceptions.StopTestRunException(results[-1].message)
                        except exceptions.IgnoreTestException:
                            pass
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    for test in coroutines:
                        try:
                            results.append(loop.run_until_complete(test.run_async()))
                            if self.stop_on_fail and results[-1].status is Status.FAILED:
                                raise exceptions.StopTestRunException(results[-1].message)
                        except exceptions.IgnoreTestException:
                            pass
                    loop.close()
                except exceptions.StopTestRunException as stre:
                    raise
                except:
                    self.log_manager.logger.error(traceback.format_exc())
            return results
        finally:
            if loop is not None and loop.is_running():
                loop.close()

    def teardown(self, teardown_func) -> Result:
        teardown_logger = self.log_manager.get_teardown_logger(self.module.name)
        args, kwargs = self.test_parameters_func(teardown_logger, self.package_object)
        if inspect.iscoroutinefunction(teardown_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async_test_func(teardown_logger, teardown_func, *args, **kwargs))
            loop.close()
        else:
            result = run_test_func(teardown_logger, teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_module_done(self.module.name, result.to_base())
        return result


class TestMethodRun:
    def __init__(self, test_method: TestMethod, test_parameters_func
                 , log_manager: SuiteLogManager,  module_name: str, package_object: DynamicMroMixin) -> None:
        self.test_method = test_method
        self.test_parameters_func = test_parameters_func
        self.log_manager = log_manager
        self.module_name = module_name
        self.package_object = package_object

    def run(self) -> TestMethodResult:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if inspect.iscoroutinefunction(self.test_method.setup_func):
            setup_result = loop.run_until_complete(
                self._intialize_args_and_setup_async()
            )
        else:
            setup_result = self._intialize_args_and_setup()

        result = self._intialize_args_and_run()
        if result.status is Status.FAILED and hasattr(self.test_method.func, 'on_test_failure'):
            logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
            args, kwargs = self.test_parameters_func(logger, self.package_object)
            if inspect.iscoroutinefunction(self.test_method.func.on_test_failure):
                try:
                    loop.run_until_complete(self.test_method.func.on_test_failure, *args, **kwargs)
                except Exception as e:
                    self.log_manager.logger.error(traceback.format_exc())
            else:
                try:
                    self.test_method.func.on_test_failure(*args, **kwargs)
                except Exception as e:
                    self.log_manager.logger.error(traceback.format_exc())

        if inspect.iscoroutinefunction(self.test_method.teardown_func):
            teardown_result = loop.run_until_complete(
                self._intialize_args_and_teardown_async()
            )
        else:
            teardown_result = self._intialize_args_and_teardown()
        result.setup_result = setup_result
        result.teardown_result = teardown_result
        loop.close()
        return result

    async def run_async(self) -> TestMethodResult:
        if inspect.iscoroutinefunction(self.test_method.setup_func):
            setup_result = await self._intialize_args_and_setup_async()
        else:
            setup_result = self._intialize_args_and_setup()

        result = await self._intialize_args_and_run_async()
        if result.status is Status.FAILED and hasattr(self.test_method.func, 'on_test_failure'):
            logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
            args, kwargs = self.test_parameters_func(logger, self.package_object)
            if inspect.iscoroutinefunction(self.test_method.func.on_test_failure):
                try:
                    await self.test_method.func.on_test_failure(*args, **kwargs)
                except Exception as e:
                    self.log_manager.logger.error(traceback.format_exc())
            else:
                try:
                    self.test_method.func.on_test_failure(*args, **kwargs)
                except Exception as e:
                    self.log_manager.logger.error(traceback.format_exc())

        if inspect.iscoroutinefunction(self.test_method.teardown_func):
            teardown_result = await self._intialize_args_and_teardown_async()
        else:
            teardown_result = self._intialize_args_and_teardown()
        result.setup_result = setup_result
        result.teardown_result = teardown_result
        return result

    def _intialize_args_and_setup(self) -> Result:
        logger = self.log_manager.get_setup_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = run_test_func(logger, self.test_method.setup_func, *args, **kwargs)
        self.log_manager.on_setup_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    async def _intialize_args_and_setup_async(self) -> Result:
        logger = self.log_manager.get_setup_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = await run_async_test_func(logger, self.test_method.setup_func, *args, **kwargs)
        self.log_manager.on_setup_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    def _intialize_args_and_teardown(self) -> Result:
        logger = self.log_manager.get_teardown_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = run_test_func(logger, self.test_method.teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    async def _intialize_args_and_teardown_async(self) -> Result:
        logger = self.log_manager.get_teardown_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = await run_async_test_func(logger, self.test_method.teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    def _intialize_args_and_run(self) -> TestMethodResult:
        logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = run_test_func(logger, self.test_method.func, *(args + self.test_method.parameterized_tuple), **kwargs)
        result.metadata = self.test_method.metadata
        self.log_manager.on_test_done(self.module_name, result)
        return result

    async def _intialize_args_and_run_async(self) -> TestMethodResult:
        logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
        args, kwargs = self.test_parameters_func(logger, self.package_object)
        result = await run_async_test_func(logger, self.test_method.func, *(args + self.test_method.parameterized_tuple), **kwargs)
        result.metadata = self.test_method.metadata
        self.log_manager.on_test_done(self.module_name, result)
        return result


def run_test_func(logger: Logger, func, *args, **kwargs) -> TestMethodResult:
    result = TestMethodResult(func.__name__, status=Status.FAILED)
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
    except exceptions.IgnoreTestException as ite:
        raise
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.message = f'Encountered an exception: {e}'
        logger.error(result.message)
    return result.end()


async def run_async_test_func(logger: Logger, func, *args, **kwargs) -> TestMethodResult:
    result = TestMethodResult(func.__name__, status=Status.FAILED)
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
    except exceptions.IgnoreTestException as ite:
        raise
    except asyncio.CancelledError:
        result.message = 'I got cancelled'
        result.status = Status.SKIPPED
        logger.info(result.message)
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.message = f'Encountered an exception: {e}'
        logger.error(result.message)
    return result.end()
