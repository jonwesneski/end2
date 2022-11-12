from argparse import Namespace
import asyncio
from cmd import Cmd
import concurrent.futures
import inspect
from logging import Logger
import pathlib
import threading
from time import sleep
import traceback
import sys
from typing import (
    Callable,
    List,
    Tuple
)

from end2 import exceptions
from end2.discovery import discover_suite
from end2.constants import ReservedWords, Status
from end2.logger import SuiteLogManager
from end2.models.result import (
    Result,
    TestMethodResult,
    TestModuleResult,
    TestStepResult,
    TestSuiteResult,
)
from end2.models.testing_containers import (
    DynamicMroMixin,
    TestGroups,
    TestMethod,
    TestModule,
    TestPackage,
    TestPackageTree
)
from end2.resource_profile import create_last_run_rc


def default_test_parameters(logger, package_object) -> Tuple[tuple, dict]:
    return (logger,), {}


def create_test_run(parsed_args: Namespace, test_parameters_func=default_test_parameters
                    , log_manager: SuiteLogManager = None) -> Tuple['SuiteRun', Tuple[str]]:
    test_packages, failed_imports = discover_suite(parsed_args.suite.paths)
    suite_run = SuiteRun(parsed_args, test_parameters_func, test_packages, log_manager)
    return suite_run, failed_imports


def start_test_run(parsed_args: Namespace, test_parameters_func=default_test_parameters
                   , log_manager: SuiteLogManager = None) -> Tuple[TestSuiteResult, Tuple[str]]:
    suite_run, failed_imports = create_test_run(parsed_args, test_parameters_func, log_manager)
    results = suite_run.run()
    suite_run.log_manager.close()
    return results, failed_imports


class SuiteRun:
    def __init__(self, parsed_args: Namespace, test_parameters_func: Callable, test_packages: Tuple[TestPackageTree], log_manager: SuiteLogManager = None) -> None:
        self.parsed_args = parsed_args
        self.test_parameters_func = test_parameters_func
        self.test_packages = test_packages
        self.allow_concurrency = not self.parsed_args.no_concurrency
        self.name = 'suite_run' if not self.parsed_args.watch else 'suite_watch'
        self.results = None
        self.log_manager = log_manager or SuiteLogManager(logger_name=self.name, max_folders=self.parsed_args.max_log_folders)

    @property
    def logger(self):
        return self.log_manager.logger

    def run(self) -> TestSuiteResult:
        self.log_manager.on_suite_start(self.name)
        self.results = TestSuiteResult(self.name)
        try:
            if self.parsed_args.watch:
                self.run_watched()
            else:
                for package in self.test_packages:
                    self.results.extend(self.run_modules(package))
        except exceptions.StopTestRunException as stre:
            self.logger.critical(stre)
        self.results.end()
        self.log_manager.on_suite_stop(self.results)
        create_last_run_rc(self.results)
        return self.results

    def run_modules(self, package: TestPackage) -> List[TestModuleResult]:
        test_parameters_func = package.package_test_parameters_func or self.test_parameters_func 
        package.setup()
        test_module_results = []
        if self.allow_concurrency:
            sequential_modules = package.sequential_modules
            parallel_modules = package.parallel_modules
        else:
            sequential_modules = sequential_modules + parallel_modules
            parallel_modules = tuple()
        for test_module in sequential_modules:
            module_run = TestModuleRun(test_parameters_func, test_module, self.log_manager, package.package_object, self.parsed_args)
            test_module_results.append(module_run.run())

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.parsed_args.max_workers) as executor:
            futures = [
                executor.submit(
                    TestModuleRun(test_parameters_func, test_module, self.log_manager, package.package_object, self.parsed_args, executor).run)
                for test_module in parallel_modules
            ]
            for future in futures:
                test_module_results.append(future.result())
        package.teardown()
        return test_module_results

    def run_watched(self) -> None:
        try:
            suite_cmd = _SuiteWatchCmd(self)
            suite_cmd.cmdloop()
        except KeyboardInterrupt:
            pass
        

class _SuiteWatchCmd(Cmd):
    prompt = ''

    def __init__(self, suite_run: SuiteRun) -> None:
        super().__init__()
        self.intro = '\nWatch Mode: Press Ctrl+C to exit...\n'
        self.suite_run = suite_run
        self.ran_at_least_once = False

    def cmdloop(self, intro: str = None) -> None:
        self._run_watch()
        return super().cmdloop(self.intro)

    def postcmd(self, stop: bool, line: str) -> bool:
        return super().postcmd(stop, line)

    def _run_watch(self) -> None:
        self.cmdqueue.append(self.do_watch_modules.__name__.replace('do_', ''))

    def do_watch_modules(self, line: str) -> None:
        for package in self.suite_run.test_packages:
            package_ = TestPackage(package.package, package_object=package.package_object)
            for sequential_module in package.sequential_modules:
                if self._has_changed(sequential_module):
                    package_.sequential_modules.add(sequential_module)
            for parallel_module in package.parallel_modules:
                if self._has_changed(parallel_module):
                    package_.parallel_modules.add(parallel_module)
            if package_.parallel_modules or package_.parallel_modules:
                if self.ran_at_least_once:
                    self.suite_run.log_manager = self.suite_run.log_manager.new_instance()
                self.suite_run.run_modules(package_)
                self.suite_run.log_manager.on_suite_stop(TestSuiteResult(self.suite_run.name))
                self.suite_run.log_manager.close()
                self.stdout.write(self.intro)
                self.ran_at_least_once = True
        sleep(7)
        self._run_watch()
    
    @staticmethod
    def _has_changed(module: TestModule) -> bool:
        last_modified = pathlib.Path(module.file_name).stat().st_mtime
        changed = False
        if last_modified > module.last_modified:
            module.last_modified = last_modified
            changed = True
        return changed


class TestModuleRun:
    def __init__(self, test_parameters_func, module: TestModule, log_manager: SuiteLogManager
                 , package_object: DynamicMroMixin, parsed_args: Namespace
                 , concurrent_executor: concurrent.futures.ThreadPoolExecutor = None) -> None:
        self.test_parameters_func = test_parameters_func
        self.module = module
        self.log_manager = log_manager
        self.package_object = package_object
        self.parsed_args = parsed_args
        self.stop_on_fail = parsed_args.stop_on_fail
        self.concurrent_executor = concurrent_executor
        self.parameters_resolver = ParametersResolver(test_parameters_func, self.package_object, self.parsed_args.event_timeout)

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
            test_results = self._create_skipped_results(group, setup_results[0].record)
        else:
            test_results = self.run_tests(group)
            for group_ in group.children:
                sr, tr, trr = self.run_group(group_)
                setup_results.extend(sr)
                test_results.extend(tr)
                teardown_results.extend(trr)
            teardown_results.append(self.teardown(group.teardown_func))
        if any(x.status is Status.FAILED for x in test_results):
            self._run_on_failures_in_module()
        return setup_results, test_results, teardown_results

    def _run_on_failures_in_module(self):
        teardown_logger = self.log_manager.get_teardown_logger(self.module.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.module.on_failures_in_module, teardown_logger)
        if inspect.iscoroutinefunction(self.module.on_failures_in_module):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_async_test_func(teardown_logger, ender, self.module.on_failures_in_module, *args, **kwargs))
            loop.close()
        else:
            run_test_func(teardown_logger, ender, self.module.on_failures_in_module, *args, **kwargs)

    def _create_skipped_results(self, group: TestGroups, record: str) -> List[TestMethodResult]:
        test_results = [
            TestMethodResult(v.name, status=Status.SKIPPED, record=record, description=v.__doc__, metadata=v.metadata)
            for _, v in group.tests.items()
        ]
        for g in group.children:
            test_results.extend(self._create_skipped_results(g, record))
        return test_results

    def setup(self, setup_func: Callable) -> Result:
        setup_logger = self.log_manager.get_setup_logger(self.module.name)
        args, kwargs, ender = self.parameters_resolver.resolve(setup_func, setup_logger)
        if inspect.iscoroutinefunction(setup_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_async_test_func(setup_logger, ender, setup_func, *args, **kwargs))
            loop.close()
        else:
            result = run_test_func(setup_logger, ender, setup_func, *args, **kwargs)
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
            test_run = TestMethodRun(test, self.parameters_resolver, self.log_manager, self.module.name)
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
                                raise exceptions.StopTestRunException(result.record)
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
                                raise exceptions.StopTestRunException(results[-1].record)
                        except exceptions.IgnoreTestException:
                            pass
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    for test in coroutines:
                        try:
                            results.append(loop.run_until_complete(test.run_async()))
                            if self.stop_on_fail and results[-1].status is Status.FAILED:
                                raise exceptions.StopTestRunException(results[-1].record)
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

    def teardown(self, teardown_func: Callable) -> Result:
        teardown_logger = self.log_manager.get_teardown_logger(self.module.name)
        args, kwargs = self.test_parameters_func(teardown_logger, self.package_object)
        args, kwargs, ender = self.parameters_resolver.resolve(teardown_func, teardown_logger)
        if inspect.iscoroutinefunction(teardown_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(run_async_test_func(teardown_logger, ender, teardown_func, *args, **kwargs))
            loop.close()
        else:
            result = run_test_func(teardown_logger, ender, teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_module_done(self.module.name, result.to_base())
        return result


class Ender:
    def __init__(self, time_out: float = 15.0) -> None:
        self.time_out = time_out
        self.event = threading.Event()
        
    def create(self) -> Callable:
        self.event = threading.Event()
        return Ender.end_wrapper(self.event)

    @staticmethod
    def end_wrapper(event: threading.Event) -> Callable:
        def end() -> None:
            event.set()
        def fail(x: str) -> None:
            event.set()
            raise exceptions.OnEventFailedException(x)
        end.fail = fail
        return end

    def wait(self) -> None:
        in_time = self.event.wait(self.time_out)
        if not in_time:
            raise TimeoutError(f"end() time out reached: {self.time_out}s")


class ParametersResolver:
    def __init__(self, test_parameters_func: Callable, package_object, time_out: float = 15.0) -> None:
        self._package_object = package_object
        self._test_parameters_func = test_parameters_func
        self.time_out = time_out

    def resolve(self, method: Callable, logger: Logger, extra_args: tuple = None) -> tuple:
        args, kwargs = self._test_parameters_func(logger, self._package_object)
        if extra_args:
            args += extra_args
        kwonlyargs = dict.fromkeys(inspect.getfullargspec(method).kwonlyargs, True)
        ender = None
        if kwonlyargs:
            if kwonlyargs.pop(ReservedWords.END.value, False):
                ender = Ender(self.time_out)
                kwargs[ReservedWords.END.value] = ender.create()
            if kwonlyargs.pop(ReservedWords.LOGGER.value, False):
                kwargs[ReservedWords.LOGGER.value] = logger
            if kwonlyargs.pop(ReservedWords.PACKAGE_OBJECT.value, False):
                kwargs[ReservedWords.PACKAGE_OBJECT.value] = self._package_object
            if kwonlyargs.pop(ReservedWords.STEP.value, False):
                kwargs[ReservedWords.STEP.value] = True
            if kwonlyargs:
                raise exceptions.TestCodeException(f"Unknown reserved words found or possibly typos: {list(kwonlyargs.keys())}"
                                                   f"\npossible reserved keywords: {[[x.name for x in ReservedWords]]}")
        return args, kwargs, ender


class TestMethodRun:
    def __init__(self, test_method: TestMethod, parameters_resolver: ParametersResolver
                 , log_manager: SuiteLogManager, module_name: str) -> None:
        self.test_method = test_method
        self.parameters_resolver = parameters_resolver
        self.log_manager = log_manager
        self.module_name = module_name

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
            args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.func.on_test_failure, logger)
            if inspect.iscoroutinefunction(self.test_method.func.on_test_failure):
                loop.run_until_complete(
                    run_async_test_func(self.log_manager.logger, ender, self.test_method.func.on_test_failure, *args, **kwargs)
                )
            else:
                run_test_func(self.log_manager.logger, ender, self.test_method.func.on_test_failure, *args, **kwargs)

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
            args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.func.on_test_failure, logger)
            if inspect.iscoroutinefunction(self.test_method.func.on_test_failure):
                await run_async_test_func(self.log_manager.logger, ender, self.test_method.func.on_test_failure, *args, **kwargs)
            else:
                run_test_func(self.log_manager.logger, ender, self.test_method.func.on_test_failure, *args, **kwargs)

        if inspect.iscoroutinefunction(self.test_method.teardown_func):
            teardown_result = await self._intialize_args_and_teardown_async()
        else:
            teardown_result = self._intialize_args_and_teardown()
        result.setup_result = setup_result
        result.teardown_result = teardown_result
        return result

    def _intialize_args_and_setup(self) -> Result:
        logger = self.log_manager.get_setup_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.setup_func, logger)
        result = run_test_func(logger, ender, self.test_method.setup_func, *args, **kwargs)
        self.log_manager.on_setup_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    async def _intialize_args_and_setup_async(self) -> Result:
        logger = self.log_manager.get_setup_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.setup_func, logger)
        result = await run_async_test_func(logger, ender, self.test_method.setup_func, *args, **kwargs)
        self.log_manager.on_setup_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    def _intialize_args_and_teardown(self) -> Result:
        logger = self.log_manager.get_teardown_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.teardown_func, logger)
        result = run_test_func(logger, ender, self.test_method.teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    async def _intialize_args_and_teardown_async(self) -> Result:
        logger = self.log_manager.get_teardown_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.teardown_func, logger)
        result = await run_async_test_func(logger, ender, self.test_method.teardown_func, *args, **kwargs)
        self.log_manager.on_teardown_test_done(self.module_name, self.test_method.name, result.to_base())
        return result

    def _intialize_args_and_run(self) -> TestMethodResult:
        logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.func, logger, self.test_method.parameterized_tuple)
        result = run_test_func(logger, ender, self.test_method.func, *args, **kwargs)
        result.metadata = self.test_method.metadata
        self.log_manager.on_test_done(self.module_name, result)
        return result

    async def _intialize_args_and_run_async(self) -> TestMethodResult:
        logger = self.log_manager.get_test_logger(self.module_name, self.test_method.name)
        args, kwargs, ender = self.parameters_resolver.resolve(self.test_method.func, logger, self.test_method.parameterized_tuple)
        result = await run_async_test_func(logger, ender, self.test_method.func, *args, **kwargs)
        result.metadata = self.test_method.metadata
        self.log_manager.on_test_done(self.module_name, result)
        return result


class TestStepsRun:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.steps: TestStepResult = []

    def __str__(self) -> str:
        return f'Number of steps: {len(self.steps)} | Duration: {self.duration}'

    def step(self, record: str, assert_lambda: Callable, func: Callable, *args, **kwargs):
        self.logger.info(record)
        step_ = TestStepResult(record)
        try:
            return_value = func(*args, **kwargs)
        finally:
            self.steps.append(step_.end())
            if assert_lambda:
                assert assert_lambda(return_value)
            return return_value

    async def step_async(self, record: str, assert_lambda: Callable, func: Callable, *args, **kwargs):
        self.logger.info(record)
        step_ = TestStepResult(record)
        try:
            return_value = await func(*args, **kwargs)
        finally:
            self.steps.append(step_.end())
            if assert_lambda:
                assert assert_lambda(return_value)
            return return_value


def run_test_func(logger: Logger, ender: Ender, func: Callable, *args, **kwargs) -> TestMethodResult:
    result = TestMethodResult(func.__name__, status=Status.FAILED)
    steps = TestStepsRun(logger)
    if kwargs.get(ReservedWords.STEP.value):
        kwargs[ReservedWords.STEP.value] = steps.step
    try:
        func(*args, **kwargs)
        if ender:
            ender.wait()
        result.status = Status.PASSED
        result.steps = steps.steps
    except AssertionError as ae:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, error_text = tb_info[-1]
        result.record = str(ae) if str(ae) else error_text
        logger.error(result.record)
    except exceptions.SkipTestException as ste:
        result.status = Status.SKIPPED
        result.record = str(ste)
        logger.info(result.record)
    except exceptions.IgnoreTestException:
        raise
    except (TimeoutError, exceptions.OnEventFailedException) as other:
        result.record = f'{other.__class__.__name__}: {other}'
        logger.error(result.record)
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.record = f'Encountered an exception: {e}'
        logger.error(result.record)
    return result.end()


async def run_async_test_func(logger: Logger, ender: Ender, func: Callable, *args, **kwargs) -> TestMethodResult:
    result = TestMethodResult(func.__name__, status=Status.FAILED)
    steps = TestStepsRun(logger)
    if kwargs.get(ReservedWords.STEP.value):
        kwargs[ReservedWords.STEP.value] = steps.step_async
    try:
        await func(*args, **kwargs)
        if ender:
            ender.wait()
        result.status = Status.PASSED
        result.steps = steps.steps
    except AssertionError as ae:
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        filename, line, func, error_text = tb_info[-1]
        result.record = str(ae) if str(ae) else error_text
        logger.error(result.record)
    except exceptions.SkipTestException as ste:
        result.status = Status.SKIPPED
        result.record = str(ste)
        logger.info(result.record)
    except exceptions.IgnoreTestException:
        raise
    except (TimeoutError, exceptions.OnEventFailedException) as other:
        result.record = f'{other.__class__.__name__}: {other}'
        logger.error(result.record)
    except asyncio.CancelledError:
        result.status = Status.SKIPPED
        result.record = 'I got cancelled'
        logger.info(result.record)
    except Exception as e:
        logger.debug(traceback.format_exc())
        result.record = f'Encountered an exception: {e}'
        logger.error(result.record)
    return result.end()
