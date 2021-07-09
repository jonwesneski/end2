import re
import os

from src.pattern_matchers.base import PatternMatcherBase


class RegexModulePatternMatcher(PatternMatcherBase):
    regex_path_separator = f'\{os.sep}'
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        items = []
        for i, p in enumerate(pattern.split(cls.regex_path_separator, maxsplit=1)):
            for item in os.listdir(os.getcwd()):
                if re.match(p, item):
                    items.append(item)
        return cls(items, pattern, include)

    @classmethod
    def _resolve_path(cls, pattern, path: str):
        full_path = ''
        if cls.regex_path_separator in path:
            path.split(cls.regex_path_separator, maxsplit=1)
            return cls._resolve_path()
        else:
            return re.match(pattern, path)


class RegexTestCasePatternMatcher(PatternMatcherBase):
    @classmethod
    def parse_str(cls, pattern: str, include: bool = True):
        return cls([], pattern, True)

    def included(self, item: str) -> bool:
        return True if re.match(self._pattern, item) else False
