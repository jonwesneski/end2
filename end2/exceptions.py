"""
    * Please keep class names alphabetical
"""


class IgnoreTestException(Exception):
    pass


class MoreThan1SameFixtureException(Exception):
    def __init__(self, *args):
        # args[0] is fixture name args[1] is module name
        self.message = f'More than 1 {args[0]} in {args[1]}'

    def __str__(self) -> str:
        return self.message


class OnEventFailedException(Exception):
    pass


class SkipTestException(Exception):
    pass


class StopTestRunException(Exception):
    pass


class TestCodeException(Exception):
    pass
