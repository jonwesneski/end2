from datetime import datetime

from test_framework.enums import Status
from test_framework.fixtures import get_fixture


def build_full_name(module_name: str, test_name: str) -> str:
    return f'{module_name}::{test_name}'


class TestMethod:
    def __init__(self, setup_func, func, teardown_func):
        self.setup_func = setup_func
        self.func = func
        self.name = self.func.__name__
        self.full_name = build_full_name(self.func.__module__, self.name)
        self.teardown_func = teardown_func

    def __eq__(self, rhs) -> bool:
        return self.full_name == rhs.full_name

    def __hash__(self) -> int:
        return id(self.full_name)


class TestModule:
    def __init__(self, module, tests: dict, ignored_tests: set = None, package_globals: object = None):
        self.module = module
        self.name = module.__name__
        self.setup = get_fixture(self.module, 'setup')
        self.tests = tests
        self.teardown = get_fixture(self.module, 'teardown')
        self.ignored_tests = ignored_tests if ignored_tests else set()
        self.package_globals = package_globals

    def __eq__(self, rhs) -> bool:
        return self.name == rhs.name

    def __hash__(self) -> int:
        return id(self.module)

    def update(self, same_module):
        for ignored in same_module.ignored_tests:
            self.tests.pop(ignored, None)
        self.tests.update(same_module.tests)
        self.ignored_tests.update(same_module.ignored_tests)



class Result:
    def __init__(self, name: str, status: str = None, message: str = ""):
        self.name = name
        self.start_time = datetime.now()
        self._end_time = None
        self.duration = None
        self.status = status
        self.message = message

    def __str__(self) -> str:
        return f'{self.name} Result: {{{self.status} | Duration: {self.duration}}}'

    @property
    def end_time(self) -> datetime:
        return self._end_time

    @end_time.setter
    def end_time(self, value: datetime):
        self._end_time = value
        self.duration = self._end_time - self.start_time

    @property
    def total_seconds(self) -> float:
        return 0.0 if not self.duration else self.duration.total_seconds()

    def end(self, status: str = None):
        self.end_time = datetime.now()
        if status:
            self.status = status
        return self


class TestSuiteResult(Result):
    def __init__(self, name: str, test_modules: list = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.test_modules = test_modules if test_modules else []
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0

    def __str__(self) -> str:
        return f'{self.name} Results: {{Total: {self.total_count} | Passed: {self.passed_count} | Failed: {self.failed_count} | Skipped: {self.skipped_count} | Duration: {self.duration}}}'

    @property
    def exit_code(self) -> int:
        return 0 if self.status is Status.PASSED else 1

    @property
    def total_count(self) -> int:
        return self.passed_count + self.failed_count + self.skipped_count

    def append(self, test_module_result):
        self.test_modules.append(test_module_result)

    def end(self, status: str = None):
        super().end(status)
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0
        for result in self.test_modules:
            self.passed_count += result.passed_count
            self.failed_count += result.failed_count
            self.skipped_count += result.skipped_count
        self.status = Status.PASSED if self.passed_count > 0 and self.failed_count == 0 and self.skipped_count == 0 else Status.FAILED
        return self


class TestModuleResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None,
                 test_results: list = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.setup = setup
        self.teardown = teardown
        self.test_results = test_results if test_results else []
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0

    def __str__(self) -> str:
        return f'{self.name} Results: {{Total: {self.passed_count+self.failed_count+self.skipped_count} | Passed: {self.passed_count} | Failed: {self.failed_count} | Skipped: {self.skipped_count} | Duration: {self.duration}}}'

    def append(self, test_result):
        if test_result:
            self.test_results.append(test_result)

    def extend(self, test_results: list):
        self.test_results.extend(test_results)

    def end(self, status: str = None):
        super().end(status)
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0
        if self.test_results:
            if all(x.status is Status.SKIPPED for x in self.test_results):
                self.status = Status.SKIPPED
                self.skipped_count = len(self.test_results)
            else:
                for result in self.test_results:
                    if result.status is Status.PASSED:
                        self.passed_count += 1
                    elif result.status is Status.FAILED:
                        self.failed_count += 1
                    elif result.status is Status.SKIPPED:
                        self.skipped_count += 1
                self.status = Status.PASSED if self.passed_count > 0 and self.failed_count == 0 and self.skipped_count == 0 else Status.FAILED
        return self


class TestMethodResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None,
                 status: str = None, message: str = "", metadata: dict = None):
        super().__init__(name, status, message)
        self.setup_result = setup
        self.teardown_result = teardown
        self.metadata = metadata or {}


class GlobalObject:
    def copy(self, obj):
        for attribute in dir(obj):
            if not attribute.startswith('__'):
                setattr(self, attribute) = getattr(obj, attribute)
