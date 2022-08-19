"""
    Constants/Enums for test framework library features
    * Please keep class names alphabetical
    * Please keep variables in classes alphabetical
"""
from enum import Enum


FUNCTION_TYPE = type(lambda: None)
TAGS = '__tags__'


class RunMode(Enum):
    PARALLEL = 'parallel'
    SEQUENTIAL = 'sequential'


class Status(Enum):
    FAILED = 'Failed'
    IGNORED = 'Ignored'
    PASSED = 'Passed'
    SKIPPED = 'Skipped'


class ReservedWords(Enum):
    END = 'end'
    LOGGER = 'logger'
    PACKAGE_OBJECT = 'package_object'
    STEP = 'step'
