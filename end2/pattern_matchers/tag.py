import os
from typing import Callable

from end2.pattern_matchers.default import (
    PatternMatcherBase,
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)

module_tags_matcher = None


class TagModulePatternMatcher(DefaultModulePatternMatcher):
    tag_delimiter = ','

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        global module_tags_matcher
        pattern_list = pattern.split(os.sep)
        if cls.tag_delimiter in pattern_list[-1]:
            if pattern_list[-1].endswith(cls.tag_delimiter):
                module_tags_matcher = PatternMatcherBase.parse_str(pattern_list[-1][:-1], include)
            else:
                module_tags_matcher = PatternMatcherBase.parse_str(pattern_list[-1], include)
            pattern_list = pattern_list[:-1]
        matcher = super(TagModulePatternMatcher, cls).parse_str(os.sep.join(pattern_list), include)
        return matcher

    def module_included(self, module) -> bool:
        include = True
        if module_tags_matcher and hasattr(module, '__tags__'):
            for tag in module.__tags__:
                include = module_tags_matcher.included(tag)
                if include:
                    break
        return include


class TagTestCasePatternMatcher(DefaultTestCasePatternMatcher):
    delimiter = ','

    def func_included(self, func: Callable) -> bool:
        include = module_tags_matcher._include if module_tags_matcher else self._include
        matcher = module_tags_matcher or self
        try:
            for tag in func.metadata.get('tags', []):
                include = matcher.included(tag)
                if include:
                    break
        except AttributeError:
            pass
        return include
