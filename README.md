# end² Test Automation Framework
The focus of this framework is:
- A Minimal framework only using the standard library
- More for E2E and/or Functional type of testing
- For testing that has heavy logging and needs to analyze failures in logs rather than test case code
- For folks that like programatic ways instead of plugins with configuration files

## Contents
- [Intent/Philosophy](#intent/philosophy)
- [Features](#features)
- [Getting Started](#getting-started)
- [CLI](#cli)
- [Resource Files](#resource-files)
- [Log Manager](#log-manager)
- [Packages Object](#packages-object)

## Intent/Philosophy
- Shuffling:
    - By having tests run in random order, we are ensuring that tests don't need to run in a specific order. If test-1 fails, then test-2 will obviously fail, but test-2 is a false negative. It might be better to consider test-1 and test-2 as test steps and just combine test-1 and test-2 in one test case instead. Another plus to Shuffling is the test writer will be able to find out if there are any side effects on the test case side or the SUT and be able to fix what is necessary. This will make them have a better understanding of there own coding, others members coding, and the SUT as well if the side effect is on the SUT itself
- Create you own script entry point:
    - This is the entrypoint for your testing. It is your own python module that you will write that defines what the test parameters are and uses `default_parser()` to add any additional args before you start your testing. You can name it whatever you want but in below examples I refer to it as `run.py` 
- Declaring:
    - Test case design is very important and the design should speak for itself in the file/module. Declaring the concurrency/run-mode in the file lets everyone know that that particular file can run in parallel. Passing that info in the command line can be confusing over time because not everyone will remember what can and can't run parallel
- 1 set of parameters per suite:
    - When we do a suite run we are only testing 1 system, therefore whatever is needed to communicate to the system should be the same throughout all test cases in that suite. As a result parameters should be the same for all test cases. This always helps keep test cases dry and makes them more step focused
- Root of truth:
    - Single source of truth is a very good thing to have, when the single source is up-to-date and working then everyone will know it is 100% accurate information. By having your test cases as the single-source of truth, you can then publish your truth anywhere necessary and that destination will always have the info of the latest results. So the test cases should speak for themselves and have any doc strings necessary so that everyone can view the latest version of your testing


## Features
- Test Runner:
    - Discovers tests at runtime
    - Test Pattern Matching: Can run individual tests and test modules
    - Runs tests sequentially and parallelly in 1 run
    - Test Fixtures
    - Package Objects
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
    - It will hold folders from the last n test runs
    - Each test module will be in its own folder
    - Each test will be in it's own file
    - Failed tests will be renamed to `FAILED_<test_name>.log`
    - HAR logger

## Getting Started
### Understanding the end² Flow (Psuedo Code)
``` python
def discover_suite(parent_path):
     paths = get_all_paths(parent_path)
     modules = []
    for path in paths:
        if is_dir(path):
            modules += discover_suite(path)
        else:
            modules.append(discover_module(path))
    return shuffle(modules)


def discover_module(path):
    module = import_module(path)
    for function in module:
        if is_test(function):
            module.add_test(function)
    return shuffle(module.tests)


def run_tests(discovered_modules):
    for package in discovered_packages:
        package.setup()
        for module in package.discovered_modules:
            module.setup():
            for test in module.tests:
                module.setup_test()
                args, kwargs = test_parameters(logger, package_object)
                test(*args, **kwargs)
                module.teardown_test()
            module.teardown()
        package.teardown()

```

### Simple Example of a Run script
``` python
#!/usr/bin/env python3
from end2.runner import start_test_run
from end2.arg_parser import default_parser


if __name__ == '__main__':
    args = default_parser().parse_args()  # You can add your own arguments to default_parser if you want before you
                                          # call parse_args()

    def test_parameters(logger, package_object) -> tuple:  # This is how parameters for tests are injected. When
        return (create_client(logger),), {}                # overriding this you must always return a tuple of tuple
                                                           # and dict. The logger arg here will be the logger
                                                           # specific to the test. This method will be called
                                                           # on every fixture and test

    test_suite_result, failed_imports = start_test_run(args, test_parameters)
    exit(test_suite_result.exit_code)

```

### Simple Example of a Test Module
In order for a method to become a discoverable test you must prefix your method name with `test_`. Each test method will have the same parameters
``` python
from end2 import RunMode


__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module


def test_1(client, logger):
    assert 1 == 1        # assert is used for validation; if assertion fails the test fails and exits on that assert
    assert True is True  #
    logger.info('Hi')


async def test_2(client, logger):  # Both sync and async test methods can exist in the same file
    actual = await client.get_stuff()
    assert actual == "some expected data"
    logger.info('Hi async')


def helper():  # Not a test method
    return {'a': 1}

```

### Simple Example of Checking Test Case Readiness at Runtime
``` python
from end2 import (
    IgnoreTestException,
    RunMode,
    SkipTestException
)


__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module


def test_1(client, logger):
    if not client.something_ready():
        raise IgnoreTestException()  # You may ignore tests are runtime if necessary. No test result will be made
    assert client.get_stuff()
    logger.info('Hi')


async def test_2(client, logger):  # Both sync and async test methods can exist in the same file
    if not client.something_else_ready():
        raise SkipTestException("thing not ready")  # You may skip tests are runtime if necessary as well.
    actual = await client.get_stuff()               # A test result will be made with status of skipped and the
    assert actual == "some expected data"           # message of what was supplied in the SkipTestException()
    logger.info('Hi async')

```

## Fixture Example of a Test Module
``` python
from end2 import (
    on_failures_in_module,
    on_test_failure,
    parameterize,
    RunMode,
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


@on_failures_in_module
def my_teardown(logger):  # Runs once at the end of the test module if you have 1 or more failed test cases
    logger.info('do something')


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


@metadata(defect_id='SR-432', case_id='C-23451')  # Use metadata when you want to add extra info to your test
def test_2(logger):                               # This data will also be available to you after the test run
    assert True is True


@metadata(tags=['yellow', 'potato'])  # tags is a special keyword used for Pattern Matching. As long as at
def test_3(logger):                   # least 1 tag matches test will run (when using --suite-tag)
    assert True is True


def cleanup(logger):
    logger.info('do some cleanup')


@on_test_failure(cleanup)  # This fixture will run the function in the decorator argument only if the test fails
def test_4(logger):
    assert True is True
```

## Packages Object
This is an object that you can build from within your packages. Since test parameters are always fresh objects you may want to pass data around and be able to access it in packages. This feature is kind of experimental but here are some ideas:
- Build reports in the middle of runs
- Building metrics

#### Example of Test Package
``` python
# test_package/__init__.py
from end2 import (
    setup,
    teardown
)
from end2.fixtures import package_test_parameters


@setup
def my_setup(package_globals):
    package_globals.stuff = ['my_static_stuff']


@teardown
def my_setup(package_globals):
    package_globals.stuff.clear()


@package_test_parameters
def my_custom_test_parameters(logger, pacakge_object):  # Use if you want to override the test_parameters defined
    return (some_other_client(logger),) {}              # in your 'run.py'

```
``` python
# test_package/test_sub_package/__init__.py
from end2 import (
    setup,
    teardown
)


@setup
def my_setup(package_globals):
    package_globals.stuff  # will be ['my_static_stuff']
    package_globals.sub_package_stuff = ['other stuff']


@teardown
def my_setup(package_globals):
    package_globals.sub_package_stuff.clear()

```
``` python
# test_package/test_sub_package/my_test_module.py
from end2 import RunMode


__run_mode__ = RunMode.PARALLEL  # This is required for every test module


def test_1(logger, package_globals):
    assert package_globals.stuff == ['my_static_stuff']
    assert package_globals.sub_package_stuff = ['other stuff']

```

## Test Groups
Test groups allow you to organize your tests around setup and teardown. Maybe some of your tests the setup only needs to be run for 2 of your tests. Or maybe you want the same setup for all tests but you want an additional setup for 4 of the tests. Groups are declared as classes and the methods are techincally static but without decorating with `@staticmethod`
``` python
# test_package/test_sub_package/test_module.py
from end2 import (
    RunMode,
    setup_test,
    teardown
)


__run_mode__ = RunMode.PARALLEL  # This is required for every test module


@setup_test
def setup_all(logger):
    pass  # do something at the start of each test.


def test_1(logger):
    assert package_globals.stuff == ['my_static_stuff']
    assert package_globals.sub_package_stuff = ['other stuff']


class Group1:
    @setup_test
    def setup_all1(logger):
        pass  # do an extra something after setup_all

    def test_2(logger):
        pass

    class Group2:
        @setup_test
        def setup_all2(logger):
            pass  # do an extra something after setup_all and setup_all1

        def test_2(logger):
            pass

```

## CLI
It is best to run the `--help` arg on your "run.py" to get the latest information. Since **Pattern Matchers** are a little more complicated below is a more desciptive overview

### Suite Pattern Matchers
#### Default
A suite path is a string that contains the path to the module delimited by a period:
- To run a single test package: `--suite path/to/package`
- To run a single test module: `--suite path/to/file.py`
- To run multiple test packages: `--suite path/to/package path2/to/package`
- To run multiple test packages and modules: `--suite path/to/package path2/to/package path3/to/package/module.py path4/to/package/module.py`
It can also contains filters:
- `::` which is to run specific tests in a module: `--suite path/to/package/module.py::test_1`
- `;` which is delimiter for modules: `--suite path/to/package/module.py;module2.py`
- `,` which is a delimiter for tests: `--suite path/to/package/module.py::test_1,test_2;module2.py`
- `!` which means run everything before the `!` but nothing after:
    - `--suite path/to/package/!module.py;module2.py`  runs everything in `path/to/package` except `module.py` and `module2.py`
    - `--suite path/to/package/module.py::!test_1,test_2;module2.py`  runs `module2.py` and everything in `module.py` except `test_1` and `test_2`
- `[n]` which will run specific parameterized tests:
    - `--suite path/to/package/module.py::test_name[1]`  runs the 2nd test in the parameterized list
    - `--suite path/to/module.py::test_name[2:6]`  runs tests 2 through 6 in the parameterized list
    - `--suite path/to/module.py::test_name[2:6:2]`  runs the 2nd, 4th, 6th test in the parameterized list

#### Tags
Tags can be defined by using `@metadata` in you test as mentioned [above](#fixture-example-of-a-test-module). They works pretty similar to the **Default Pattern Matcher** but uses a tag instead of a test name:
- `--suite-tag path/to/module.py::tag_name1,tag_name2`

#### regex and glob
These 2 are pretty similar to each and I split module and test the same:
- `--suite-regex <regex for module>::<regex for test>`
- `--suite-glob <glob for module>::<glob for test>`

#### Last Failed
You can also run only the tests that failed in the last run
- `--suite-last-failed`

## Resource Files
- `.end2rc`: defines a default value for cli as well as:
    - Aliases: a short name given to a suite that is long. Aliases can also mention other aliases
    - Disabled Suites: The is a list of disabled suites/tests; this way you don't have to remember which ones to disable. Also the list of suites/tests are centralized here; you won't have to hunt them down in each file
- `logs/.lastrunrc`: defines a list of tests that failed in the last run

## Log Manager
A **Log Manager** is meant to help organize your logging into timestamped folders that rotate every n number of folders. You can subclass **LogManager** if you want, or use the default own. You can use this if you have other tools in you repo that have logging as well

##### Default Suite Log Manager
For Suite runs you will use a **Suite Log Manager**. The default does what is described below and you can also subclass **SuiteLogManager** if you want:
- Rotates your suite run log folders
- Logs INFO to stdin
- Logs INFO to a standalone file as well and it is not interlaced
- Has a delimiter for both modules and tests
- Handles events before and after on:
    - suite
    - modules
    - fixtures
    - tests
- Creates a log subfolder for each module
- Creates a file for both setup and teardown of a module
- Creates a log file for each test
- Marks (Prefixes) file name as PASSED, FAILED, SKIPPED when test is finished
