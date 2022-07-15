from glob import glob
import os
import re

from end2.pattern_matchers.base import PatternMatcherBase


class RegexModulePatternMatcher(PatternMatcherBase):
    regex_path_separator = f'\{os.sep}'

    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        items = []
        include = False
        for module in filter(lambda x: not x.endswith('__init__.py'),
                             glob(f'.{os.sep}**{os.sep}*.py', recursive=True)):
            if re.match(pattern, module):
                items.append(module)
                include = True
        return cls(items, pattern, include)


class RegexTestCasePatternMatcher(PatternMatcherBase):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return cls([], pattern, True)

    def included(self, func) -> bool:
        return True if re.match(self._pattern, func.__name__) else False
