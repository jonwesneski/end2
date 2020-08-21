"""
    Enums for test framework library features
    * Please keep class names alphabetical
    * Please keep variables in classes alphabetical
"""


FUNCTION_TYPE = type(lambda: None)


class RunMode:
    PARALLEL = 'parallel'
    PARALLEL_TEST = 'parallel_test'
    SEQUENTIAL = 'sequential'


class Status:
    FAILED = 'Failed'
    IGNORED = 'Ignored'
    PASSED = 'Passed'
    SKIPPED = 'Skipped'
