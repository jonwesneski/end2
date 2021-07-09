from glob import glob
import re

from src.pattern_matchers.base import PatternMatcherBase


class GlobModulePatternMatcher(PatternMatcherBase):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return cls(glob(pattern, recursive=True), pattern, include)


class GlobTestCasePatternMatcher(PatternMatcherBase):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        pattern_ = pattern.replace('?', '.').replace('*', '.*')
        return cls([], pattern_, True)

    def included(self, item: str) -> bool:
        return True if re.match(self._pattern, item) else False
