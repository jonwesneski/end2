from end2.pattern_matchers.base import PatternMatcherBase


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


class DefaultTestCasePatternMatcher(DefaultModulePatternMatcher):
    delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return super(DefaultTestCasePatternMatcher, cls).parse_str(pattern, include)

    def included(self, func) -> bool:
        return super().included(func.__name__)
