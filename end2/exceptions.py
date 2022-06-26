"""
    * Please keep class names alphabetical (except BaseEnd2Exception)
"""

class BaseEnd2Exception(Exception):
    def __init__(self, *args):
        self.message = args[0]


class IgnoreTestException(BaseEnd2Exception):
    pass


class MoreThan1FixtureException(BaseEnd2Exception):
    def __init__(self, *args):
        # args[0] is fixture name args[1] is module name
        self.message = f'More than 1 {args[0]} in {args[1]}'


class OnEventFailedException(BaseEnd2Exception):
    pass


class SkipTestException(BaseEnd2Exception):
    pass


class StopTestRunException(BaseEnd2Exception):
    pass


class TestCodeException(BaseEnd2Exception):
    pass
