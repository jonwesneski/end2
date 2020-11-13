# Test Automation Framework
This framework is more focused on heavy logging in your tests for easier analysis. This framework makes you create your own driver for your test automation so you can: have more custom control on setup before a test run, use the same parameters for all your test cases, and have custom control on steps after a test run. Tests are written in methods at the module level, and when running tests you can specify a folder to be able to run all tests in that folder. This framework supports the typical test fixtures: setup before any test in a module, setup between tests, teardown between tests, and testdown in a module, and parameterizing tests. These test modules also support running the tests sequentially or parallelly by specifiying the run mode.


## Framework Features:
- Test Runner
    - Discovers tests at runtime
    - Can run individual tests and test modules
    - Test Fixtures
    - Can specify tests to ignore
    - Runs tests sequentially and parallelly in 1 run
- Logging (LogManager):
    - Records are timestamped
    - Assertion failures are logging at `[ERROR]`
    - It will hold folders from the last 10 test runs
    - Each test module will be in its own folder
    - Each test will be in it's own file
    - Failed test will be renamed to `FAILED_<test_name>.log`


## Runner psuedo code
``` python
def discover_modules(parent_path):
     paths = get_all_paths(parent_path)
     modules = []
    for path in paths:
        if is_dir(path):
            modules += discover_modules(path)
        else:
            modules = get_modules(path)
    return modules

def run_tests(discovered_modules):
    for module in discovered_modules:
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
from test_framework.runner import create_test_suite_instance


if __name__ == '__main__':
    logger = create_full_logger('logger_name', stream_level=logging.INFO, file_level=logging.DEBUG)
    run_instance = create_test_run_instance(['tests'], logger)  # 1st arg is a list of test packages
                                                                # To run a single test module: ['path.to.single_module']
                                                                # To run a single test: ['path.to.single_module::test_name']

    def test_parameters(logger_):  # This is how parameters for tests are injected. When overriding this
        return (logger_,), {}      # you must always return a tuple of list and dict. And the only
                                   # parameter is the logger for test module

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=True)  # This kicks off the test run

    exit(test_suite_result.exit_code)
```

## There are a few logger factories already created for you
If you want to create other tools in your repo you can use these logging factories to keep the logging format consistent
- test_framework.logger.create_stream_logger()
    - Creates a console logger with the custom formatter

- test_framework.logger.create_file_logger()
    - Creates a logger with a file handler with the custom formatter

- test_framework.logger.create_full_logger()
    - Creates a logger that has both a stream and file handler with the custom formatter


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
    logger.info('do something during setup')


@setup_test
def my_setup_test(logger):
    logger.info('do something during setup test')


@teardown_test
def my_teardown_test(logger):
    logger.info('do something during teardown test')


@teardown
def my_teardown(logger):
    logger.info('do something during teardown')


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
