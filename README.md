# end² Test Automation Framework
The focus of this framework is:
- Minimal framework with easy learning curve
- e2e type of testing
- For testing that has heavy logging and need to analyze failures in logs rather than test case code
- For folks that like programatic ways instead of configurations


## Intent/Philosophy
- Become better:
    - end² framework is designed to be to also help test writers become better coders as well. Only test functions are allowed in this framework and all test cases are shuffled before they run to make sure no tests depend on each other. All below intents/philosophies tie back to this first one of become better at test writing/coding
- Randomizing:
    - By having tests run randomly, we are ensuring that tests don't need to run in a specific order. If test-1 fails, then test-2 will obviously fail, but test-2 is a false negaive. It might be better to consider test-1 and test-2 as test steps and just combine test-1 and test-2 in one test case instead. Another plus to randomizing is the test writer will be able to find out if there are any side effects on the test case side or the SUT and be able to fix what is necessary. This will make them have a better understanding of there own coding, others memberings coding, and the SUT as well if the side effect is on the SUT itself
- Declaring:
    - Test case design is very important and the design should speak for itself in the file/module. Declaring the concurrency/run-mode in the file lets everyone know that that particular file can run in parallel. Passing that info in the command line can be confusing over time because not everyone will remember what can and can't run parallel
- 1 set of parameters per suite:
    - When we do a suite run we are only testing 1 system, therefore whatever is needed to communicate to the system should be the same throughout all test cases in that suite. As a result parameters should be the same for all test cases
- Root of truth:
    - Single source of truth is a very good thing to have, when the single source is up-to-date and working then everyone will know it is 100% accurate information. By having your test cases as the single-source of truth, you can then publish your truth anywhere necessary and that destination will always have the info of the latest results. So the test cases should speak for themselves and have any doc strings necessary so that everyone can view the latest version of your testing


## Features
- Test Runner:
    - Discovers tests at runtime
    - Can run individual tests and test modules
    - Test Fixtures
    - Can specify tests to ignore
    - Runs tests sequentially and parallelly in 1 run
- Fixtures:
    - setup package
    - teardown package
    - setup module
    - teardown module
    - setup test
    - teardown test
    - metadata
    - parameterize
- Logging:
    - Records are timestamped
    - Assertion failures are logged at `[ERROR]`
    - It will hold folders from the last 10 test runs
    - Each test module will be in its own folder
    - Each test will be in it's own file
    - Failed tests will be renamed to `FAILED_<test_name>.log`


## Getting Started
### Understanding the Runner (psuedo code)
``` python
def discover_suite(parent_path):
     paths = get_all_paths(parent_path)
     modules = []
    for path in paths:
        if is_dir(path):
            package = discover(path)
            package.setup()
            modules += discover_modules(package)
            package.teardown()
        else:
            modules.append(get_module(path))
    return shuffle(modules)

def run_tests(discovered_modules):
    for module in discovered_modules:
        module.setup():
        for test in shuffle(module.tests):
            module.setup_test()
            test()
            module.teardown_test()
        module.teardown()
```

### Simple example of a test module
``` python
from test_framework.enums import RunMode

__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module

def test_1(logger):
    assert 1 == 1        # assert is used for validation; if assertion fails the test fails and exits on that assert
    assert True is True  #
    logger.info('Hi')
```

### Simple example of a driver
``` python
from test_framework.runner import create_test_suite_instance


if __name__ == '__main__':
    run_instance = create_test_run_instance(suite_paths=['tests'])  # This arg is a list of test packages, test modules, and tests methods; more on this in the next section

    def test_parameters(logger_):  # This is how parameters for tests are injected. When overriding this
        return (logger_,), {}      # you must always return a tuple of list and dict. And the only
                                   # parameter is the logger for test module

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=True)  # This kicks off the test run

    exit(test_suite_result.exit_code)
```


## TODO:
- [] change suites to be file path instead of dot notation
- [] support async fixtures
- [] make runner use suitelogmanager again
- [x] .testingrc or maybe setting.conf (have this file as a profile with setting about how to configure runner)
    - [x] max threads
    - [x] max sub folder logs
    - [x] suite-aliases
    - [x] disabled tests
- [] cli (overrides .testingrc)
    - [] make a default arparser
        - [x] suite
        - [] suite-glob
        - [] suite-regex
        - [] suite-tag
        - [] run-last-failures (store failures as a text file in logs/)
        - [x] max threads
        - [x] max sub folder logs
- [x] make code use/read cli and .testingrc
- [] keep track of last failed tests in logs folder
- [] update readme
    - [x] focus/intent/philosophy
        - [x] this is for heaving logging
        - [x] more for e2e
        - [x] more for those that like to program more (do there own custom integrations)
        - [x] minimal and not much to learn
        - [x] tests are randomized to ensure they dont depend on other tests and to be state-aware of the thing you are testing
        - [x] there are no tests classes. Test classes means you probably store state for other tests to use; which means they depend on each other
        - [x] The test file itself should have the declaration of concurrency (that way you dont have to memorize what can and cant run parallel or specify it every time in the command line)
        - [x] when we do a suite run we have the same parameters for each test
    - [] update featrues
    - [] getting started
        - [] write a test
        - [] write a test with parameters
    - [] .testingrc or maybe setting.conf
    - [] cli


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
from test_framework.runner import create_test_suite_instance


if __name__ == '__main__':
    run_instance = create_test_run_instance(suite_paths=['tests'])  # This arg is a list of test packages, test modules, and tests methods; more on this in the next section

    def test_parameters(logger_):  # This is how parameters for tests are injected. When overriding this
        return (logger_,), {}      # you must always return a tuple of list and dict. And the only
                                   # parameter is the logger for test module

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=True)  # This kicks off the test run

    exit(test_suite_result.exit_code)
```

## Test Suite Paths
A suite path is a string that contains the path to the module delimited by a period:
- To run a single test package: `['path.to.package']`
- To run a single test module: `['path.to.package.module']`
- To run multiple test packages: ['path.to.package', 'path2.to.package']
- To run multiple test packages and modules: ['path.to.package', 'path2.to.package', 'path3.to.package.module', 'path4.to.package.module']
It can also contains filters:
- `::` which is to run specific tests in a module: `['path.to.package.module::test_1']`
- `;` which is delimiter for modules: `['path.to.package.module;module2']`
- `,` which is a delimiter for tests: `['path.to.package.module::test_1,test_2;module2']`
- `!` which means run everything before the `!` but nothing after:
    - `['path.to.package.!module;module2']`  runs everything in `path.to.package` except `module` and `module2`
    - `['path.to.package.module::!test_1,test_2;module2']`  runs `module2` and everything in `module` except `test_1` and `test_2`
- `[n]` which will run specific parameterized tests:
    - `['path.to.package.module::test_name[1]']`  runs the 2nd test in the parameterized list
    - `['path.to.module::test_name[2:6]']`  runs tests 2 through 6 in the parameterized list
    - `['path.to.module::test_name[2:6:2]']`  runs the 2nd, 4th, 6th test in the parameterized list


## There are a few logger factories already created for you
If you want to create other tools in your repo you can use these logging factories to keep the logging format consistent as well as the rotating timestampted folders
- test_framework.logger.create_stream_logger()
    - Creates a console logger with the custom formatter

- test_framework.logger.create_file_logger()
    - Creates a logger with a file handler with the custom formatter

- test_framework.logger.create_full_logger()
    - Creates a logger that has both a stream and file handler with the custom formatter
- If you want a different number than 10 folders rotating then you can add this to your environment variables `AUTOMATION_LOGS_SUB_FOLDER_COUNT` and set it to a number of your choice


## Fixture example of a test module
``` python
from test_framework.enums import RunMode
from test_framework.fixtures import (
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
