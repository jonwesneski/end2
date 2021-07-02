
class SkipTestException(Exception):
    def __init__(self, *args):
        self.message = args[0]


class StopTestRunException(Exception):
    def __init__(self, *args):
        self.message = args[0]


class TestCodeException(Exception):
    def __init__(self, *args):
        self.message = args[0]
