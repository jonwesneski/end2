import importlib
import inspect
import os
from random import shuffle

from src.fixtures import (
    setup,
    setup_test,
    teardown,
    teardown_test
)
from src.enums import RunMode
from src.exceptions import MoreThan1FixtureException
from src.models.test_popo import (
    empty_func,
    GlobalPackageObject,
    TestMethod,
    TestModule,
    TestPackageList
)


FUNCTION_TYPE = type(lambda: None)


def _shuffle_dict(dict_: dict) -> dict:
    list_ = list(dict_.items())
    shuffle(list_)
    return dict(list_)


def discover_suite(paths: dict) -> tuple:
    importables = _shuffle_dict(paths)
    sequential_modules = set()
    parallel_modules = set()
    failed_imports = set()
    for importable, test_pattern_matcher in importables.items():
        if os.path.exists(importable):
            if os.path.isdir(importable):
                sm, pm, fi = discover_package(importable, test_pattern_matcher, TestPackageList())
                sequential_modules |= sm
                parallel_modules |= pm
                failed_imports |= fi
            else:
                m, fi = discover_module(importable, test_pattern_matcher, TestPackageList())
                if m:
                    if m.run_mode is RunMode.SEQUENTIAL:
                        sequential_modules.add(m)
                    else:
                        parallel_modules.add(m)
                else:
                    failed_imports.add(fi)
        else:
            failed_imports.add(f"Path: {importable} does not exist")
    return tuple(sequential_modules), tuple(parallel_modules), tuple(failed_imports)


def discover_package(importable: str, test_pattern_matcher, test_package_list: TestPackageList) -> tuple:
    sequential_modules = set()
    parallel_modules = set()
    failed_imports = set()
    try:
        test_package = importlib.import_module(importable.replace(os.sep, '.'))
        items = list(filter(lambda x: '__pycache__' not in x and x != '__init__.py', os.listdir(importable)))
        shuffle(items)
        test_package_list_ = test_package_list
        test_package_list_.append(test_package)
        for item in items:
            full_path = os.path.join(importable, item)
            if os.path.isdir(full_path):
                temp = None
                sm, pm, fi = discover_package(full_path, test_pattern_matcher, temp or test_package_list_)
                sequential_modules |= sm
                parallel_modules |= pm
                failed_imports |= fi
                temp = TestPackageList.copy(test_package_list)
            elif full_path.endswith('.py'):
                m, fi = discover_module(full_path, test_pattern_matcher, test_package_list_)
                if m:
                    if m.run_mode is RunMode.SEQUENTIAL:
                        sequential_modules.add(m)
                    else:
                        parallel_modules.add(m)
                else:
                    failed_imports.add(fi)
    except Exception as e:
        failed_imports.add(f'Failed to load {importable} - {e}')
    return sequential_modules, parallel_modules, failed_imports


def discover_module(importable: str, test_pattern_matcher, test_package_list: TestPackageList) -> tuple:
    """
    >>> from src.pattern_matchers import PatternMatcherBase
    >>> matcher = PatternMatcherBase([], '', True)
    >>> module, error_str = discover_module(os.path.join('examples', 'simple', 'smoke', 'sample1'), matcher)
    >>> assert module and error_str == ''
    >>> module, error_str = discover_module('examples.dont_exist', matcher)
    >>> assert module is None and error_str
    """
    test_module, error_str = None, ''
    module_str = importable.replace('.py', '').replace(os.sep, '.')
    try:
        module = importlib.import_module(module_str)
        tests = discover_tests(module, test_pattern_matcher)
        if tests:
            test_module = TestModule(module, tests, set(test_pattern_matcher.excluded_items), test_package_list=test_package_list)
            test_module.setup_func = _get_fixture(test_module.module, setup.__name__)
            test_module.teardown_func = _get_fixture(test_module.module, teardown.__name__)
            if test_module.run_mode not in RunMode:
                error = f'{test_module.run_mode} is not a valid RunMode'
                test_module = None
                raise Exception(error)
    except ModuleNotFoundError as me:
        if me.name == module_str:
            error_str = f"Module doesn't exist - {module_str}"
        else:
            error_str = f"Failed to load {importable} - {me}"
    except MoreThan1FixtureException as mt1fe:
        error_str = mt1fe.message
    except Exception as e:
            error_str = f'Failed to load {importable} - {e}'
    return test_module, error_str


def discover_tests(module, test_pattern_matcher) -> dict:
    """
    >>> from src.pattern_matchers import DefaultTestCasePatternMatcher
    >>> matcher = DefaultTestCasePatternMatcher([], '', True)
    >>> from examples.simple.smoke import sample1
    >>> tests = discover_tests(sample1, matcher)
    >>> assert tests
    >>> matcher = DefaultTestCasePatternMatcher(['test_1', 'test_2'], '', True)
    >>> tests = discover_tests(sample1, matcher)
    >>> assert len(tests) == 2
    """
    tests = {}
    if inspect.ismodule(module):
        setup = _get_fixture(module, setup_test.__name__)
        teardown = _get_fixture(module, teardown_test.__name__)
        for name in dir(module):
            attribute = getattr(module, name)
            if type(attribute) is FUNCTION_TYPE and name.startswith('test_'):
                if test_pattern_matcher.included(attribute):
                    if hasattr(attribute, 'parameterized_list'):
                        range_ = discover_parameterized_test_range(name, attribute.parameterized_list)
                        for i in range_:
                            attribute.range = range_
                            tests[f'{name}[{i}]'] = TestMethod(attribute, setup, teardown, attribute.parameterized_list[i])
                    else:
                        tests[name] = TestMethod(attribute, setup, teardown)
        tests = _shuffle_dict(tests)
    return tests


def discover_parameterized_test_range(test_name: str, parameterized_list: list) -> range:
    """
    >>> x = [1, 2, 3, 4, 5, 6, 7, 8]
    >>> assert discover_parameterized_test_range('test_1', x) == range(len(x))
    >>> discover_parameterized_test_range('test_1[0]', x)
    range(0, 1)
    >>> assert discover_parameterized_test_range('test_1[-1:]', x) == range(-1, len(x))
    >>> assert discover_parameterized_test_range('test_1[:-1]', x) == range(0, len(x)-1)
    >>> assert discover_parameterized_test_range('test_1', x) == range(len(x))
    >>> assert discover_parameterized_test_range('test_1[::-1]', x) == range(0, len(x), -1)
    >>> discover_parameterized_test_range('test_1[1:1:1]', x)
    range(1, 1)
    >>> discover_parameterized_test_range('test_1[]', x)
    range(0, 0)
    >>> discover_parameterized_test_range('test_1[', x)
    range(0, 0)
    >>> discover_parameterized_test_range('test_1]', x)
    range(0, 0)
    >>> discover_parameterized_test_range('test_1][', x)
    range(0, 0)
    """
    open_bracket_index = test_name.find('[') + 1
    close_bracket_index = -1
    range_ = range(0)
    access_token = test_name[open_bracket_index:close_bracket_index]
    if open_bracket_index and test_name[close_bracket_index] == ']' and access_token:
        range_args = [None, None, None]
        if ':' in access_token:
            segments = access_token.split(':')
            if len(segments) <= 3:
                try:
                    for i, segment in enumerate(segments):
                        if segment == '':
                            if i == 0:
                                range_args[0] = 0
                            elif i == 1:
                                range_args[1] = len(parameterized_list)
                        else:
                            int_ = int(segment)
                            if i == 0:
                                range_args[0] = int_
                            elif i == 1:
                                if int_ < 0:
                                    range_args[1] = len(parameterized_list) + int_
                                else:
                                    range_args[1] = int_
                            elif i == 2:
                                range_args[2] = int_
                    if range_args[2] is not None:
                        range_ = range(*range_args)
                    else:
                        range_ = range(range_args[0], range_args[1])
                except:
                    pass
        else:
            try:
                int_ = int(access_token)
                if int_ < 0:
                    range_args[0] = len(parameterized_list) - int_
                else:
                    range_args[0] = int_
                range_args[1] = range_args[0] + 1
                range_ = range(range_args[0], range_args[1])
            except:
                pass
    elif '[' not in test_name and ']' not in test_name:
        range_ = range(len(parameterized_list))
    return range_


def _get_fixture(module, name: str):
        fixture = empty_func
        for key in dir(module):
            attribute = getattr(module, key)
            if type(attribute) is FUNCTION_TYPE and  hasattr(attribute, name):
                fixture = attribute
                break
        return fixture
