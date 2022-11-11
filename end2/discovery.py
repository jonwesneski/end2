import importlib
import inspect
import os
from random import shuffle
from typing import (
    List,
    Tuple,
    Callable
)

from end2.fixtures import (
    empty_func,
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
from end2.exceptions import MoreThan1SameFixtureException
from end2.models.testing_containers import (
    Importable,
    TestGroups,
    TestMethod,
    TestModule,
    TestPackage,
    TestPackageTree
)
from end2.pattern_matchers import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)


def _shuffle_dict(dict_: dict) -> dict:
    list_ = list(dict_.items())
    shuffle(list_)
    return dict(list_)


def discover_suite(importables: List[Importable]) -> Tuple[TestPackageTree, set]:    
    shuffle(importables)
    failed_imports = set()
    package_tree = TestPackageTree()
    for importable in importables:
        package_name = importable.path.replace(os.sep, '.')
        package = package_tree.find_by_str(package_name)
        if os.path.isdir(importable.path):
            p, f = discover_packages(importable.path, importable.module_matcher, importable.test_matcher, package)
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
            m, f = discover_module(importable.path, importable.module_matcher, importable.test_matcher)
            if m:
                package.append_module(m)
            elif f:
                failed_imports.add(f)
            package_tree.append(package)
    return package_tree, failed_imports


def discover_packages(importable: str, module_pattern_matcher: DefaultModulePatternMatcher, test_pattern_matcher: DefaultTestCasePatternMatcher, test_package: TestPackage = None) -> tuple:
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
            _, f = discover_packages(full_path, module_pattern_matcher, test_pattern_matcher, end_package)
            failed_imports |= f
        else:
            m, f = discover_module(full_path, module_pattern_matcher, test_pattern_matcher)
            if m:
                end_package.append_module(m)
            elif f:
                failed_imports.add(f)
    return package_, failed_imports


def discover_module(importable: str, module_pattern_matcher: DefaultModulePatternMatcher, test_pattern_matcher: DefaultTestCasePatternMatcher) -> Tuple[TestModule, str]:
    test_module, error_str = None, ''
    module_str = importable.replace('.py', '').replace(os.sep, '.')
    try:
        module = importlib.import_module(module_str)
        if module_pattern_matcher.module_included(module):
            groups = discover_groups(module, test_pattern_matcher)
            if groups.has_tests():
                test_module = TestModule(module, groups, ignored_tests=set(test_pattern_matcher.excluded_items))
                if test_module.run_mode not in RunMode:
                    error = f'{test_module.run_mode} is not a valid RunMode'
                    raise Exception(error)
    except ModuleNotFoundError as me:
        if me.name == module_str:
            error_str = f"Module doesn't exist - {module_str}"
        else:
            error_str = f"Failed to load {importable} - {me}"
    except MoreThan1SameFixtureException as mt1fe:
        error_str = mt1fe.message
    except Exception as e:
        error_str = f'Failed to load {importable} - {e}'
    return test_module, error_str


def discover_groups(test_group, test_pattern_matcher: DefaultTestCasePatternMatcher) -> TestGroups:
    setup_fixture, _, _, teardown_fixture = discover_group_fixtures(test_group)
    group = TestGroups(test_group.__name__, discover_tests(test_group, test_pattern_matcher), setup_fixture, teardown_fixture)
    for name in dir(test_group):
        attribute = getattr(test_group, name)
        if inspect.isclass(attribute) and name.startswith('Group'):
            group.append(discover_groups(attribute, test_pattern_matcher))
    return group


def discover_group_fixtures(group) -> Tuple[Callable]:
    setup_fixture = empty_func
    setup_test_fixture = empty_func
    teardown_fixture = empty_func
    teardown_test_fixture = empty_func
    found_map = {}

    def check_if_found_already(fixture: Callable):
        nonlocal found_map
        if found_map.get(fixture.__name__):
            try:
                raise MoreThan1SameFixtureException(fixture.__name__, group.__name__)
            except:
                print(dir(group), group.__name__)
                raise
        if fixture != empty_func:
            found_map[fixture.__name__] = True
    
    for key in dir(group):
        attribute = getattr(group, key)
        if type(attribute) is FUNCTION_TYPE:
            setup_fixture, setup_test_fixture, \
            teardown_test_fixture, teardown_fixture = \
                discover_func_fixtures(attribute, setup, setup_test, teardown_test, teardown, default=empty_func)
            check_if_found_already(setup_fixture)
            check_if_found_already(setup_test_fixture)
            check_if_found_already(teardown_test_fixture)
            check_if_found_already(teardown_fixture)
    return setup_fixture, setup_test_fixture, teardown_fixture, teardown_test_fixture


def discover_func_fixtures(func, *fixtures, default=empty_func) -> List[Callable]:
    fixture_names = [x.__name__ for x in fixtures]
    discovered_fixtures = [default] * len(fixtures)
    found_map = {}
    for i, fixture_name in enumerate(fixture_names):
        if hasattr(func, fixture_name):
            if found_map.get(fixture_name):
                raise MoreThan1SameFixtureException(fixture_name, func.__name__)
            discovered_fixtures[i] = fixtures[i]
            found_map[fixture_name] = True
    return discovered_fixtures


def discover_tests(module, test_pattern_matcher: DefaultTestCasePatternMatcher) -> dict:
    tests = {}
    setup_test_ = get_fixture(module, setup_test.__name__)
    teardown_test_ = get_fixture(module, teardown_test.__name__)
    for name in dir(module):
        attribute = getattr(module, name)
        if type(attribute) is FUNCTION_TYPE and name.startswith('test_'):
            if test_pattern_matcher.func_included(attribute):
                if hasattr(attribute, 'parameterized_list'):
                    range_ = discover_parameterized_test_range(name, attribute.parameterized_list)
                    for i in range_:
                        attribute.range = range_
                        tests[f'{name}[{i}]'] = TestMethod(attribute, setup_test_, teardown_test_, attribute.parameterized_list[i])
                else:
                    tests[name] = TestMethod(attribute, setup_test_, teardown_test_)
    return _shuffle_dict(tests)


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
