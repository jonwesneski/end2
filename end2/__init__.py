# Only exporting stuff commonly used in test modules.
from .constants import RunMode
from .exceptions import (
    IgnoreTestException,
    SkipTestException
)
from .fixtures import (
    on_failures_in_module,
    on_test_failure,
    metadata,
    parameterize,
    setup,
    setup_test,
    teardown,
    teardown_test
)

__all__ = [
    'IgnoreTestException', 'on_failures_in_module', 'on_test_failure',
    'metadata', 'parameterize', 'RunMode', 'setup', 'setup_test',
    'SkipTestException', 'teardown', 'teardown_test'
]

PARALLEL = RunMode.PARALLEL
SEQUENTIAL = RunMode.SEQUENTIAL
