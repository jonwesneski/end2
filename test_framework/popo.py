from datetime import datetime

from test_framework.enums import Status
from test_framework.fixtures import get_fixture


class TestMethod:
    def __init__(self, setup_func, func, teardown_func):
        self.setup_func = setup_func
        self.func = func
        self.name = self.func.__name__
        self.teardown_func = teardown_func


class TestModule:
    def __init__(self, module, tests: tuple, ignored_tests: tuple = None):
        self.module = module
        self.name = module.__name__
        self.setup = get_fixture(self.module, 'setup')
        self.tests = tests
        self.teardown = get_fixture(self.module, 'teardown')
        self.ignored_tests = ignored_tests if ignored_tests else tuple()
        self.skipped_tests = []

    def __eq__(self, rhs):
        return self.name == rhs.name

    def __hash__(self):
        return id(self.module)


class Result:
    def __init__(self, name: str, status: str = None, message: str = None):
        self.name = name
        self.start_time = datetime.now()
        self._end_time = None
        self.duration = None
        self.status = status
        self.message = message
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0

    def __str__(self):
        return f'{self.name} Results: {{Total: {self.passed_count+self.failed_count+self.skipped_count} | Passed: {self.passed_count} | Failed: {self.failed_count} | Skipped: {self.skipped_count} | Duration: {self.duration}}}'

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value: datetime):
        self._end_time = value
        self.duration = self._end_time - self.start_time

    def end(self, status: str = None):
        self.end_time = datetime.now()
        if status:
            self.status = status
        return self


class TestSuiteResult(Result):
    def __init__(self, name: str, test_modules: list = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.test_modules = test_modules if test_modules else []

    @property
    def exit_code(self):
        return 0 if self.status == Status.PASSED else 1

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
    def __init__(self, name: str, setup: Result = None, teardown: Result = None, test_results: list = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.setup = setup
        self.teardown = teardown
        self.test_results = test_results if test_results else []

    def end(self, status: str = None):
        super().end(status)
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0
        if not self.test_results:
            self.status = Status.SKIPPED
        else:
            for result in self.test_results:
                if result.parameterized_results:
                    self.passed_count += result.passed_count
                    self.failed_count += result.failed_count
                    self.skipped_count += result.skipped_count
                else:
                    if result.status == Status.PASSED:
                        self.passed_count += 1
                    elif result.status == Status.FAILED:
                        self.failed_count += 1
                    elif result.status == Status.SKIPPED:
                        self.skipped_count += 1
            self.status = Status.PASSED if self.passed_count > 0 and self.failed_count == 0 and self.skipped_count == 0 else Status.FAILED
        return self


class TestMethodResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.setup = setup
        self.teardown = teardown
        self.parameterized_results = []

    def end(self, status: str = None):
        super().end(status)
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0
        if status != Status.SKIPPED and self.parameterized_results:
            for result in self.parameterized_results:
                if result.status == Status.PASSED:
                    self.passed_count += 1
                elif result.status == Status.FAILED:
                    self.failed_count += 1
                elif result.status == Status.SKIPPED:
                    self.skipped_count += 1
            self.status = Status.PASSED if len(self.parameterized_results) == self.passed_count else Status.FAILED
        return self


class StopTestRunException(Exception):
    def __init__(self, *args):
        self.message = args[0]
