import importlib
import inspect
import os
from random import shuffle
from typing import Tuple

from end2.fixtures import (
    get_fixture,
    setup,
    setup_test,
    teardown,
    teardown_test
)
from end2.constants import (
    FUNCTION_TYPE,
    RunMode
)
from end2.exceptions import MoreThan1FixtureException
from end2.models.testing_containers import (
    TestGroups,
    TestMethod,
    TestModule,
    TestPackage,
    TestPackageTree
)
from end2.pattern_matchers import PatternMatcherBase


def _shuffle_dict(dict_: dict) -> dict:
    list_ = list(dict_.items())
    shuffle(list_)
    return dict(list_)


def discover_suite(paths: dict) -> Tuple[TestPackageTree, set]:    
    importables = _shuffle_dict(paths)
    failed_imports = set()
    package_tree = TestPackageTree()
    for importable, test_pattern_matcher in importables.items():
        package_name = importable.replace(os.sep, '.')
        package = package_tree.find_by_str(package_name)
        if os.path.isdir(importable):
            p, f = discover_packages(importable, test_pattern_matcher, package)
            if p:
                package_tree.append(p)
            failed_imports |= f
        else:
            package_names = []
            if not package:
                names = package_name.split('.')
                if package_name.endswith('.py'):
                    names = names[:-2]
                for i in range(len(names)):
                    package_names.append(".".join(names[:i+1]))
                new_package = importlib.import_module(package_names[0])
                package = TestPackage(new_package)
                for package_name in package_names[1:-1]:
                    new_package = importlib.import_module(package_name)
                    package.tail(new_package)
            m, f = discover_module(importable, test_pattern_matcher)
            if m:
                package.append_module(m)
            else:
                failed_imports.add(f)
            package_tree.append(package)
    return package_tree, failed_imports


def discover_packages(importable: str, test_pattern_matcher: PatternMatcherBase, test_package: TestPackage = None) -> tuple:
    names = importable.replace(os.sep, '.').split('.')
    package_names = []
    package_ = None
    failed_imports = set()
    if test_package:
        package_names = [f'{test_package.name}.{names[-1]}']
    else:
        for i in range(len(names)):
            package_names.append(".".join(names[:i+1]))
    if test_package and test_package.name == ".".join(names):
        # Handling same package conflict
        new_package = None
        end_package = test_package
    else:
        new_package = importlib.import_module(package_names[0])
    if new_package:
        if test_package:
            package_ = test_package
            package_.tail(new_package)
        else:
            package_ = TestPackage(new_package)
        for package_name in package_names[1:]:
            new_package = importlib.import_module(package_name)
            package_.tail(new_package)
        end_package = package_.find(package_names[-1])
    items = list(filter(lambda x: '__pycache__' not in x and x != '__init__.py', os.listdir(importable)))
    shuffle(items)
    for item in items:
        full_path = os.path.join(importable, item)
        if os.path.isdir(full_path):
            _, f = discover_packages(full_path, test_pattern_matcher, end_package)
            failed_imports |= f
        else:
            m, f = discover_module(full_path, test_pattern_matcher)
            if m:
                end_package.append_module(m)
            else:
                failed_imports.add(f)
    return package_, failed_imports


def discover_module(importable: str, test_pattern_matcher: PatternMatcherBase) -> Tuple[TestModule, str]:
    test_module, error_str = None, ''
    module_str = importable.replace('.py', '').replace(os.sep, '.')
    try:
        module = importlib.import_module(module_str)
        groups = discover_groups(module, test_pattern_matcher)
        test_module = TestModule(module, groups, ignored_tests=set(test_pattern_matcher.excluded_items))
        if test_module.run_mode not in RunMode:
            error = f'{test_module.run_mode} is not a valid RunMode'
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


def discover_tests(module, test_pattern_matcher: PatternMatcherBase) -> dict:
    tests = {}
    setup_test_ = get_fixture(module, setup_test.__name__)
    teardown_test_ = get_fixture(module, teardown_test.__name__)
    for name in dir(module):
        attribute = getattr(module, name)
        if type(attribute) is FUNCTION_TYPE and name.startswith('test_'):
            if test_pattern_matcher.included(attribute):
                if hasattr(attribute, 'parameterized_list'):
                    range_ = discover_parameterized_test_range(name, attribute.parameterized_list)
                    for i in range_:
                        attribute.range = range_
                        tests[f'{name}[{i}]'] = TestMethod(attribute, setup_test_, teardown_test_, attribute.parameterized_list[i])
                else:
                    tests[name] = TestMethod(attribute, setup_test_, teardown_test_)
    return _shuffle_dict(tests)


def discover_groups(test_module, test_pattern_matcher: PatternMatcherBase) -> TestGroups:
    setup_func = get_fixture(test_module, setup.__name__)
    teardown_func = get_fixture(test_module, teardown.__name__)
    group = TestGroups(test_module.__name__, discover_tests(test_module, test_pattern_matcher), setup_func, teardown_func)
    for name in dir(test_module):
        attribute = getattr(test_module, name)
        if inspect.isclass(attribute) and name.startswith('Group'):
            group.append(discover_groups(attribute, test_pattern_matcher))
    return group


def discover_parameterized_test_range(test_name: str, parameterized_list: list) -> range:
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
