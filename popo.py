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

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value: datetime):
        self._end_time = value
        self.duration = self._end_time - self.start_time


class TestMethodResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.setup = setup
        self.teardown = teardown


class TestModuleResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None, test_results: list = None, status: str = None, message: str = None):
        super().__init__(name, status, message)
        self.setup = setup
        self.teardown = teardown
        self.test_results = test_results if test_results else []

    def __str__(self):
        passed, failed, skipped = 0, 0, 0
        for result in self.test_results:
            passed += 1 if result.status == Status.PASSED else 0
            failed += 1 if result.status == Status.FAILED else 0
            skipped += 1 if result.status == Status.SKIPPED else 0
        return f'{{Total: {passed+failed+skipped} | Passed: {passed} | Failed: {failed} | Skipped: {skipped} | Duration: {self.duration}}}'


class StopTestRunException(Exception):
    def __init__(self, *args):
        self.message = args[0]
