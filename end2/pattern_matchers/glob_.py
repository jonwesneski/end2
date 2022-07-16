from glob import glob
import re

from end2.pattern_matchers.default import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)


class GlobModulePatternMatcher(DefaultModulePatternMatcher):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return cls(glob(pattern, recursive=True), pattern, include)


class GlobTestCasePatternMatcher(DefaultTestCasePatternMatcher):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        pattern_ = pattern.replace('?', '.').replace('*', '.*')
        return cls([], pattern_, True)

    def included(self, func) -> bool:
        return True if re.match(self._pattern, func.__name__) else False
