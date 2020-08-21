# Test Automation Framework
This framework allows you to create your own driver for your test automation so you can use the same parameters for all your test cases. Tests are written in methods at the module level, and when running tests you can specify a folder to be able to run all tests in that folder. This framework supports the typical test fixtures: setup before any test in a module, setup between tests, teardown between tests, and testdown in a module. These test modules also support running the tests sequentially or parallelly by specifiying the run mode.

## Framework Features:
- Test Runner
    - Test Fixtures
    - Discovers tests at runtime
    - Can run individual tests, test modules, or tagged modules
    - Can specify tests to ignore
    - Runs tests sequentially and parallelly in 1 run
- Logging:
    - A console log level flag as command line argument
    - Console logging will be kept to a minimum; and be very user friendly (when log level is INFO or above)
    - All request and response payloads will be logged and formatted
    - Filtered failure log file that shows every step leading up to the failure
    - Files are segregated by test module
    - Records are timestamped
- Slack Integration:
    - Posts a test run summary
    - Uploads test run logs

## Runner psuedo code
``` python
def recurse_through_tests(parent_path)
    paths = get_all_paths(parent_path)
    for path in paths:
        if is_dir(path):
            recurse_through_tests(path)
        else:
            modules = get_modules(path)
            for module in modules:
                if module.setup():
                    for test in module.tests:
                        module.setup_test()
                        test()
                        module.teardown_test()
                module.teardown()
```

## Simple example of a test module
``` python
from test_framework.enums import RunMode

__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module

def test_1(logger):
    assert 1 == 1        # assert is used for validation; if assertion fails the test fails and exits on that assert
    assert True is True  #
    logger.info('Hi')
```

## Simple example of a driver
``` python
import logging
from test_framework.logger import create_full_logger
from test_framework.runner import create_test_run_instance


if __name__ == '__main__':
    logger = create_full_logger('logger_name', stream_level=logging.INFO, file_level=logging.DEBUG)
    run_instance = create_test_run_instance(['tests'], logger)  # 1st arg is a list of test packages
                                                                # To run a single test module: ['path.to.single_module']
                                                                # To run a single test: ['path.to.single_module::test_name']

    def test_parameters(logger_):  # This is how parameters for tests are injected. When overriding this
        return [logger_], {}       # you must always return a tuple of list and dict. And the only
                                   # parameter is the logger for test module

    run_instance.test_parameters = test_parameters
    run_instance.test_executor_engine(threads=True)  # This kicks off the test run

    exit(1 if run_instance.results.failed_tests > 0 else 0)
```

## There are a few logger factories already created for you
- test_framework.logger.create_simple_file_logger()
    - Creates a logger with a file handler

- test_framework.logger.create_file_logger()
    - Creates a logger with a file handler with a custom formater

- test_framework.logger.create_full_logger()
    - Creates a logger that has both a stream and file handler with a custom formatter

- test_framework.logger.create_module_logger()
    - Like the full_logger, but also will flush records to failures.log (the records that get flushed are records from the beginning of the test all the way up to the failure)

## Fixture example of a test module
``` python
from test_framework.enums import RunMode
from test_framework.utils import (
    parameterize,
    setup,
    setup_test,
    teardown,
    teardown_test
)

__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module


@setup
def my_setup(logger):
    print('do something during setup')


@setup_test
def my_setup_test(logger):
    print('do something during setup test')


@teardown_test
def my_teardown_test(logger):
    print('do something during teardown test')


@teardown
def my_teardown(logger):
    print('do something during teardown')


# Parameterize takes 1 argument: list of tuples
#  - Each tuple must be the same length
@parameterize([
    ('A', 'B', 'AB'),
    (1, 2, 3),
    ([], [1], [1]),
    (1.2, 2.3, 3.5),
    (True, False, 1)
])
def test_1(logger, var1, var2, rhs):  # Parameterized parameters will come in after all runner.test_parameters
    assert var1 + var2 == rhs
    logger.info('Hi')
```
