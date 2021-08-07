import importlib
import inspect
import os
from random import shuffle
from typing import Tuple

from src.fixtures import (
    setup,
    setup_test,
    teardown,
    teardown_test
)
from src.enums import RunMode
from src.exceptions import MoreThan1FixtureException
from src.models.test_popo import (
    TestGroups,
    empty_func,
    TestMethod,
    TestModule,
    TestPackages
)


FUNCTION_TYPE = type(lambda: None)

def a():
    raise
def _shuffle_dict(dict_: dict) -> dict:
    list_ = list(dict_.items())
    shuffle(list_)
    return dict(list_)

def discover_suite2():
    class TestPackageTree:
        def __init__(self, package = None, modules = None):
            self.packages = [TestPackage(package, modules)] if package else []

        def find(self, rhs):
            for package in self.packages:
                if package == rhs:
                    return package
                elif package.sub_packages:
                    for sub_package in package.sub_packages:
                        if sub_package == rhs:
                            return sub_package

        def find_by_str(self, rhs: str):
            for package in self.packages:
                if package.name == rhs:
                    return package
                elif package.sub_packages:
                    for sub_package in package.sub_packages:
                        if sub_package.name == rhs:
                            return sub_package

        def append(self, package):
            found_package = self.find(package)
            if found_package:
                self.merge(found_package, package)
            else:
                found_parent = self.find_by_str(".".join(package.name.split('.'))[:-1])
                if found_parent:
                    found_parent.sub_packages.append(package)
                else:
                    self.packages.append(package)
            print('found', found_package.name if found_package else None)

        def merge(self, lhs, rhs):
            for rm in rhs.modules:
                updated = False
                for lm in lhs.modules:
                    updated = False
                    if lm == rm:
                        updated = True
                        lm.update(rm)
                        break
                if not updated:
                    lhs.modules.append(rm)
            for i, lhs_sp in enumerate(lhs.sub_packages):
                self.merge(lhs_sp, rhs.sub_packages[i])

    class TestPackage:
        def __init__(self, package, modules = None):
            self.package = package
            self.name = self.package.__name__
            self.description = self.package.__doc__
            self.suite_object = None
            self.modules = modules or []
            self.sub_packages = []

        def __eq__(self, o) -> bool:
            return self.name == o.name

        def append(self, package):
            self.sub_packages.append(TestPackage(package))

        def tail(self, package, index: int = -1):
            self._tail(TestPackage(package), index)

        def _tail(self, package, index: int = -1):
            sub_packages = self.sub_packages
            if sub_packages:
                sub_package = sub_packages[index]
                sub_package._tail(package, -1)
            else:
                self.sub_packages.append(package)

        def last(self, index: int = -1):
            if not self.sub_packages:
                return self
            sub_package = self.sub_packages[index]
            while sub_package.sub_packages:
                sub_package = sub_package.sub_packages[-1]
            return sub_package

        def find(self, rhs: str, index: int = -1):
            if self.name == rhs:
                return self
            elif self.sub_packages:
                return self.sub_packages[index].find(rhs)

    def discover_packages2(importable, test_pattern_matcher, test_package: TestPackage = None):
        names = importable.replace(os.sep, '.').split('.')
        package_names = []
        if test_package:
            package_names = [f'{test_package.name}.{names[-1]}']
            # new_package = importlib.import_module(package_names[0])
            # test_package.tail(new_package)
        else:
            for i in range(len(names)):
                package_names.append(".".join(names[:i+1]))
        new_package = importlib.import_module(package_names[0])
        package_ = test_package or TestPackage(new_package)
        for package_name in package_names[1:]:
            new_package = importlib.import_module(package_name)
            package_.tail(new_package)
        print(package_names)
        items = list(filter(lambda x: '__pycache__' not in x and x != '__init__.py', os.listdir(importable)))
        shuffle(items)
        end_package = package_.find(package_names[-1])
        for item in items:
            full_path = os.path.join(importable, item)
            if os.path.isdir(full_path):
                discover_packages2(full_path, test_pattern_matcher, end_package)
            else:
                pass#end_package.modules.append(discover_module(full_path, test_pattern_matcher))
        return package_
    
    # importables = _shuffle_dict(paths)
    # sequential_modules = set()
    # parallel_modules = set()
    # failed_imports = set()
    # for importable, test_pattern_matcher in importables.items():
    package_tree = TestPackageTree()
    for importable in ['examples\\package_objects\\package1\\package2a', 'examples\\package_objects\\package1']:
        package_name = importable.replace(os.sep, '.')
        package = package_tree.find_by_str()
        if os.path.isdir(importable):
            package_tree.append(discover_packages2(importable, package))
        else:
            package_names = []
            if not package:
                names = package.split('.')
                for i in range(len(names)):
                    package_names.append(".".join(names[:i+1]))
                new_package = importlib.import_module(package_names[0])
                package = TestPackage(new_package)
                for package_name in package_names[1:]:
                    new_package = importlib.import_module(package_name)
                    package.tail(new_package)
            package.modules.append(discover_module(importable, test_pattern_matcher))
            package_tree.append(package)
    return package_tree
p = discover_suite2()
print(p.packages[0].sub_package.sub_package.name)
#exit()

def discover_suite(paths: dict) -> tuple:
    importables = _shuffle_dict(paths)
    sequential_modules = set()
    parallel_modules = set()
    failed_imports = set()
    for importable, test_pattern_matcher in importables.items():
        if os.path.exists(importable):
            if os.path.isdir(importable):
                sm, pm, fi = discover_package(importable, test_pattern_matcher)
                sequential_modules |= sm
                parallel_modules |= pm
                failed_imports |= fi
            else:
                test_package = importlib.import_module(os.path.dirname(importable))
                m, fi = discover_module(importable, test_pattern_matcher, TestPackages(test_package))
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


def discover_package(importable: str, test_pattern_matcher, test_package_list: TestPackages = None) -> tuple:
    sequential_modules = set()
    parallel_modules = set()
    failed_imports = set()
    try:
        test_package = importlib.import_module(importable.replace(os.sep, '.'))
        items = list(filter(lambda x: '__pycache__' not in x and x != '__init__.py', os.listdir(importable)))
        shuffle(items)
        test_package_list_ = test_package_list or TestPackages(test_package)
        test_package_list_.append(test_package)
        for item in items:
            full_path = os.path.join(importable, item)
            if os.path.isdir(full_path):
                test_package_list__ = test_package_list_.slice()
                sm, pm, fi = discover_package(full_path, test_pattern_matcher, test_package_list__)
                sequential_modules |= sm
                parallel_modules |= pm
                failed_imports |= fi
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


def discover_module(importable: str, test_pattern_matcher, test_package_list: TestPackages) -> Tuple[TestModule, str]:
    """
    >>> from src.pattern_matchers import PatternMatcherBase
    >>> from src.models.test_popo import TestPackages
    >>> matcher = PatternMatcherBase([], '', True)
    >>> module, error_str = discover_module(os.path.join('examples', 'simple', 'smoke', 'sample1'), matcher, TestPackages())
    >>> assert module and error_str == ''
    >>> module, error_str = discover_module('examples.dont_exist', matcher, TestPackages())
    >>> assert module is None and error_str
    """
    test_module, error_str = None, ''
    module_str = importable.replace('.py', '').replace(os.sep, '.')
    try:
        module = importlib.import_module(module_str)
        groups = discover_groups(module, test_pattern_matcher)
        test_module = TestModule(module, groups, ignored_tests=set(test_pattern_matcher.excluded_items), test_package_list=test_package_list)
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
    setup_test_ = _get_fixture(module, setup_test.__name__)
    teardown_test_ = _get_fixture(module, teardown_test.__name__)
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


def discover_groups(test_module, test_pattern_matcher) -> TestGroups:
    setup_func = _get_fixture(test_module, setup.__name__)
    teardown_func = _get_fixture(test_module, teardown.__name__)
    group = TestGroups(discover_tests(test_module, test_pattern_matcher), setup_func, teardown_func)
    for name in dir(test_module):
        attribute = getattr(test_module, name)
        if inspect.isclass(attribute) and name.startswith('Group'):
            group.append(discover_groups(attribute, test_pattern_matcher))
    return group



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
