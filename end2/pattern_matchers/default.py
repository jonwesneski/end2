from typing import Callable
from end2.pattern_matchers import PatternMatcherBase


class DefaultModulePatternMatcher(PatternMatcherBase):
    excluder = '!'
    delimiter = ';'

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        index, include = None, True
        if pattern.startswith(cls.excluder):
            index = 1
            include = False
        return cls(pattern[index:].split(cls.delimiter) if pattern else [], pattern, include)

    def module_included(self, module) -> bool:
        return True


class DefaultTestCasePatternMatcher(PatternMatcherBase):
    excluder = '!'
    delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return super(DefaultTestCasePatternMatcher, cls).parse_str(pattern, include)

    def func_included(self, func: Callable) -> bool:
        return self.included(func.__name__)
