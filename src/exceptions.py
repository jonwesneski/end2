

class IgnoreTestException(Exception):
    pass


class MoreThan1FixtureException(Exception):
    def __init__(self, *args):
        # args[0] is fixture name args[1] is module name
        self.message = f'More than 1 {args[0]} in {args[1]}'


class SkipTestException(Exception):
    def __init__(self, *args):
        self.message = args[0]


class StopTestRunException(Exception):
    def __init__(self, *args):
        self.message = args[0]


class TestCodeException(Exception):
    def __init__(self, *args):
        self.message = args[0]
