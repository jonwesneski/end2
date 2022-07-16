import os
from typing import Callable

from end2.pattern_matchers.default import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)


class TagModulePatternMatcher(DefaultModulePatternMatcher):
    delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        tags = []
        if os.sep in pattern:
            tags = pattern.split(os.sep)[1].split(cls.delimiter)
        # path/to/package/tag1,tag2,tag3
        return cls(tags, pattern, include)

    def module_included(self, module) -> bool:
        include = not self.included_items
        if self.included_items and hasattr(module, '__tags__'):
            for tag in module.__tags__:
                include = self.included(tag)
                if include:
                    break
        return include


class TagTestCasePatternMatcher(DefaultTestCasePatternMatcher):
    delimiter = ','

    # @classmethod
    # def parse_str(cls, pattern: str, include: bool = True):
    #     return super(TagTestCasePatternMatcher, cls).parse_str(pattern, include)

    def func_included(self, func: Callable) -> bool:
        include = False
        try:
            for tag in func.metadata['tags']:
                include = super().included(tag)
                if include:
                    break
        except (AttributeError, KeyError):
            pass
        return include
