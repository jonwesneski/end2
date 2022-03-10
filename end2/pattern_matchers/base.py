
class PatternMatcherBase:
    def __init__(self, items: list, pattern: str, include: bool):
        self._items = items
        self._pattern = pattern
        self._include = include

    @classmethod
    def parse_str(cls, string: str, include: bool = True):
        return cls(string, include)

    def __str__(self) -> str:
        return f"{'include' if self._include else 'exclude'}: {self._items}"

    @property
    def included_items(self) -> list:
        return self._items if self._include else []

    @property
    def excluded_items(self) -> list:
        return self._items if not self._include else []

    def included(self, item: str) -> bool:
        """
        >>> PatternMatcherBase.included(PatternMatcherBase(['a'], 'a', True), 'a')
        True
        >>> PatternMatcherBase.included(PatternMatcherBase(['a'], 'a', True), 'b')
        False
        >>> PatternMatcherBase.included(PatternMatcherBase(['a'], 'a', False), 'a')
        False
        >>> PatternMatcherBase.included(PatternMatcherBase(['a'], 'a', False), 'b')
        True
        >>> PatternMatcherBase.included(PatternMatcherBase([], '', True), 'a')
        True
        >>> PatternMatcherBase.included(PatternMatcherBase([], '', False), 'b')
        True
        """
        if item in self._items:
            value = self._include
        else:
            value = not self._include
            if not self._items:
                value = True
        return value

    def excluded(self, item: str) -> bool:
        """
        >>> PatternMatcherBase.excluded(PatternMatcherBase(['a'], 'a', True), 'a')
        False
        >>> PatternMatcherBase.excluded(PatternMatcherBase(['a'], 'a', True), 'b')
        True
        >>> PatternMatcherBase.excluded(PatternMatcherBase(['a'], 'a', False), 'a')
        True
        >>> PatternMatcherBase.excluded(PatternMatcherBase(['a'], 'a', False), 'b')
        False
        >>> PatternMatcherBase.excluded(PatternMatcherBase([], 'a', True), 'a')
        False
        >>> PatternMatcherBase.excluded(PatternMatcherBase([], 'a', False), 'b')
        False
        """
        return not self.included(item)
