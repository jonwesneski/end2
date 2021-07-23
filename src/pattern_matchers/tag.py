from src.pattern_matchers.default import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)


class TagModulePatternMatcher(DefaultModulePatternMatcher):
    pass


class TagTestCasePatternMatcher(TagModulePatternMatcher):
    delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return super(TagTestCasePatternMatcher, cls).parse_str(pattern, include)

    def included(self, func) -> bool:
        try:
            result = super().included(func.metadata['tag'])
        except:
            result = False
        return result
