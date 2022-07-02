from datetime import datetime
from typing import (
    Any,
    Generator,
    List
)

from end2.constants import Status
from end2.models.testing_containers import TestModule


class Result:
    def __init__(self, name: str, status: Status = None, record: str = "") -> None:
        self.name = name
        self._end_time = None
        self.duration = None
        self.status = status
        self.record = record
        self.start()

    def __str__(self) -> str:
        return f'{self.name} Result: {{{self.status} | Duration: {self.duration}}}'

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def end_time(self) -> datetime:
        return self._end_time

    @end_time.setter
    def end_time(self, value: datetime):
        self._end_time = value
        self.duration = self._end_time - self._start_time

    @property
    def total_seconds(self) -> float:
        return 0.0 if not self.duration else self.duration.total_seconds()

    def _now(self) -> datetime:
        return datetime.now()

    def start(self) -> None:
        if self._end_time is None:
            self._start_time = self._now()

    def end(self, status: Status = None):
        self.end_time = datetime.now()
        if status:
            self.status = status
        return self


class TestStepResult(Result):
    def __init__(self, record: str) -> None:
        self.record = record
        self._end_time = None
        self.start()

    def __str__(self) -> str:
        return f'{self.record} | Duration: {self.duration}'


class TestMethodResult(Result):
    def __init__(self, name: str, setup: Result = None, teardown: Result = None
                 , status: Status = None, record: str = "", description: str = ""
                 , metadata: dict = None) -> None:
        super().__init__(name, status, record)
        self.setup_result = setup
        self.teardown_result = teardown
        self.metadata = metadata or {}
        self.description = description
        self.steps = []

    def to_base(self) -> Result:
        result = Result(self.name, self.status, self.record)
        result._start_time = self._start_time
        result._end_time = self._end_time
        return result


class TestModuleResult(Result):
    def __init__(self, module: TestModule, setups: List[Result] = None, teardowns: List[Result] = None
                 , test_results: List[TestMethodResult] = None, status: Status = None
                 , record: str = "") -> None:
        super().__init__(module.name, status, record)
        self.file_name = module.file_name
        self.setups = setups or []
        self.teardowns = teardowns or []
        self.description = module.description
        self.test_results = test_results if test_results else []
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0

    def __str__(self) -> str:
        return f'{self.name} Results: {{Total: {self.total_count} | Passed: {self.passed_count} | Failed: {self.failed_count} | Skipped: {self.skipped_count} | Duration: {self.duration}}}'

    def __iter__(self) -> Generator[TestMethodResult, Any, None]:
        for result in self.test_results:
            yield result

    @property
    def total_count(self) -> int:
        return self.passed_count + self.failed_count + self.skipped_count

    def append(self, test_result) -> None:
        if test_result:
            self.test_results.append(test_result)

    def extend(self, test_results: list) -> None:
        self.test_results.extend(test_results)

    def end(self, status: Status = None):
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


class TestSuiteResult(Result):
    def __init__(self, name: str, test_modules: List[TestModuleResult] = None, status: Status = None, record: str = "") -> None:
        super().__init__(name, status, record)
        self.test_modules = test_modules if test_modules else []
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0

    def __str__(self) -> str:
        return f'{self.name} Results: {{Total: {self.total_count} | Passed: {self.passed_count} | Failed: {self.failed_count} | Skipped: {self.skipped_count} | Duration: {self.duration}}}'

    def __iter__(self) -> Generator[TestModuleResult, Any, None]:
        for result in self.test_modules:
            yield result

    @property
    def exit_code(self) -> int:
        return 0 if self.status is Status.PASSED else 1

    @property
    def total_count(self) -> int:
        return self.passed_count + self.failed_count + self.skipped_count

    def append(self, test_module_result) -> None:
        self.test_modules.append(test_module_result)

    def end(self, status: Status = None):
        super().end(status)
        self.passed_count, self.failed_count, self.skipped_count = 0, 0, 0
        for result in self.test_modules:
            self.passed_count += result.passed_count
            self.failed_count += result.failed_count
            self.skipped_count += result.skipped_count
        self.status = Status.PASSED if self.passed_count > 0 and self.failed_count == 0 and self.skipped_count == 0 else Status.FAILED
        return self
