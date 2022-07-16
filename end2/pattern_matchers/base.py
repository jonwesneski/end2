from typing import List


class PatternMatcherBase:
    def __init__(self, items: List[str], pattern: str, include: bool):
        self._items = items
        self._pattern = pattern
        self._include = include

    @classmethod
    def parse_str(cls, string: str, include: bool = True):
        return cls([], string, include)

    def __str__(self) -> str:
        return f"{'include' if self._include else 'exclude'}: {self._items}"

    @property
    def included_items(self) -> List[str]:
        return self._items if self._include else []

    @property
    def excluded_items(self) -> List[str]:
        return self._items if not self._include else []

    def included(self, item: str) -> bool:
        if item in self._items:
            value = self._include
        else:
            value = not self._include
            if not self._items:
                value = True
        return value

    def excluded(self, item: str) -> bool:
        return not self.included(item)
