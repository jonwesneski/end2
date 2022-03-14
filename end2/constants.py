"""
    Constants/Enums for test framework library features
    * Please keep class names alphabetical
    * Please keep variables in classes alphabetical
"""
from enum import Enum


FUNCTION_TYPE = type(lambda: None)


class RunMode(Enum):
    PARALLEL = 'parallel'
    SEQUENTIAL = 'sequential'


class Status(Enum):
    FAILED = 'Failed'
    IGNORED = 'Ignored'
    PASSED = 'Passed'
    SKIPPED = 'Skipped'
