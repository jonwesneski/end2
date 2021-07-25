from src.pattern_matchers.default import DefaultModulePatternMatcher


class TagModulePatternMatcher(DefaultModulePatternMatcher):
    pass


class TagTestCasePatternMatcher(DefaultModulePatternMatcher):
    delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return super(TagTestCasePatternMatcher, cls).parse_str(pattern, include)

    def included(self, func) -> bool:
        result = False
        try:
            for tag in func.metadata['tags']:
                result = super().included(tag)
                if result:
                    break
        except (KeyError, AttributeError):
            pass
        return result
