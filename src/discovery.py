import importlib
import inspect
import os
from random import shuffle
from typing import Generator

from src.fixtures import get_fixture
from src.enums import RunMode
from src.popo import TestMethod, TestModule, GlobalObject


FUNCTION_TYPE = type(lambda: None)


def _shuffle_dict(dict_: dict) -> dict:
    list_ = list(dict_.items())
    shuffle(list_)
    return dict(list_)


def discover_suite(paths: dict) -> Generator:
    importables = _shuffle_dict(paths)
    for importable, test_includer in importables.items():
        if os.path.exists(importable):
            if os.path.isdir(importable):
                yield from discover_package(importable, test_includer)
            else:
                yield discover_module(importable, test_includer)
        else:
            yield [], f"Path: {importable} does not exist"


def discover_package(importable: str, test_includer, test_package_globals: GlobalObject = None) -> tuple:
    try:
        test_package = importlib.import_module(importable.replace(os.sep, '.'))
    
        items = list(filter(lambda x: '__pycache__' not in x and x != '__init__.py', os.listdir(importable)))
        shuffle(items)
        test_package_globals_ = test_package_globals or GlobalObject()
        getattr(test_package, 'setup', lambda x: None)(test_package_globals_)
        for item in items:
            full_path = os.path.join(importable, item)
            if os.path.isdir(full_path):
                yield from discover_package(full_path, test_includer, test_package_globals_)
            elif full_path.endswith('.py'):
                yield discover_module(full_path, test_includer, test_package_globals_)
        getattr(test_package, 'teardown', lambda x: None)(test_package_globals_)
    except Exception as e:
        yield None, f'Failed to load {importable} - {e}'


def discover_module(importable: str, test_includer, test_package_globals: GlobalObject = None) -> tuple:
    # """
    # >>> module, error_str = discover_module('src.example.smoke.sample1', [])
    # >>> assert module and error_str == ''
    # >>> module, error_str = discover_module('src.example.dont_exist', [])
    # >>> assert module is None and error_str
    # """
    test_module, error_str = None, ''
    module_str = importable.replace('.py', '').replace(os.sep, '.')
    try:
        module = importlib.import_module(module_str)
        tests = discover_tests(module, test_includer)
        if tests:
            test_module = TestModule(module, tests, set(test_includer.excluded_items), test_package_globals)
            discover_fixtures(test_module)
    except ModuleNotFoundError as me:
        if me.name == module_str:
            error_str = f"Module doesn't exist - {module_str}"
        else:
            error_str = f"Failed to load {importable} - {me}"
    except Exception as e:
            error_str = f'Failed to load {importable} - {e}'
    return test_module, error_str


def discover_tests(module, test_includer) -> list:
    # """
    # >>> from src.example.smoke import sample1
    # >>> tests, ignored_tests = discover_tests(sample1, [])
    # >>> assert tests and ignored_tests == []
    # >>> tests, ignored_tests = discover_tests(sample1, ['!test_ignored_test', 'test_1', 'test_2'])
    # >>> assert len(tests) == 2 and 'test_ignored_test' in ignored_tests
    # """
    tests = {}
    if inspect.ismodule(module):
        setup = get_fixture(module, 'setup_test')
        teardown = get_fixture(module, 'teardown_test')
        for name in dir(module):
            attribute = getattr(module, name)
            if type(attribute) is FUNCTION_TYPE and name.startswith('test_'):
                if test_includer.included(name):
                    if hasattr(attribute, 'parameterized_list'):
                        range_ = discover_parameterized_test_range(name, attribute.parameterized_list)
                        for i in range_:
                            attribute.range = range_
                            tests[f'{name}[{i}]'] = TestMethod(setup, attribute, teardown, attribute.parameterized_list[i])
                    else:
                        tests[name] = TestMethod(setup, attribute, teardown)
        tests = _shuffle_dict(tests)
    return tests


def discover_parameterized_test_range(test_name: str, parameterized_list: list):
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


def discover_fixtures(test_module):
    pass  #TODO: remove from fixtures.py and implement here
# def get_fixture(module, name: str):
#     fixture = empty_func
#     for key in dir(module):
#         attribute = getattr(module, key)
#         if type(attribute) is FUNCTION_TYPE and  hasattr(attribute, name):
#             fixture = attribute
#             break
#     return fixture
