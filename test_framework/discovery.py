import importlib
import inspect
import os
from random import shuffle

from test_framework.fixtures import get_fixture
from test_framework.enums import RunMode
from test_framework.popo import TestMethod, TestModule


FUNCTION_TYPE = type(lambda: None)


def discover_suites(suite_paths: list) -> tuple:
    """
    >>> sequential, parallel, ignored, failed = discover_suites(['test_framework.examples.example_tests.smoke.!ignored_module,sample1', 'test_framework.examples.example_tests.regression'])
    >>> sequential
    0
    >>> parallel
    0
    >>> failed
    0
    >>> assert len(sequential) == 2 and len(parallel) == 2 and not failed
    """
    importables, ignored_modules = _parse_suite_paths(suite_paths)
    ignored_paths = [x.replace('.', os.sep) for x in ignored_modules]
    modules, failed_imports = set(), set()
    for importable in importables:
        m, f = _recursive_discover(importable[0].replace('.', os.sep), ignored_paths, test_filters=importable[1])
        modules |= m
        failed_imports |= f
    sequential_modules = list(filter(lambda x: x.module.__run_mode__ == RunMode.SEQUENTIAL, modules))
    parallel_modules = list(filter(lambda x: x.module.__run_mode__ in [RunMode.PARALLEL, RunMode.PARALLEL_TEST], modules))
    shuffle(sequential_modules)
    shuffle(parallel_modules)
    return sequential_modules, parallel_modules, tuple(ignored_modules), tuple(failed_imports)


def _parse_suite_paths(suite_paths: list) -> tuple:
    """
    >>> _parse_suite_paths(['tests'])
    ([('tests', [])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket1'])
    ([('example_tests.regression.bucket1', [])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket1::test1'])
    ([('example_tests.regression.bucket1', ['test1'])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket1::test1,test2'])
    ([('example_tests.regression.bucket1', ['test1', 'test2'])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket1;bucket2::test1,test2'])
    ([('example_tests.regression.bucket1', []), ('example_tests.regression.bucket2', ['test1', 'test2'])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket1;bucket2::!test1,test2'])
    ([('example_tests.regression.bucket1', []), ('example_tests.regression.bucket2', ['!test1', '!test2'])], [])
    >>> _parse_suite_paths(['example_tests.regression.bucket2::!test1,test2;bucket1'])
    ([('example_tests.regression.bucket2', ['!test1', '!test2']), ('example_tests.regression.bucket1', [])], [])
    >>> _parse_suite_paths(['example_tests.regression.!bucket2::!test1,test2;bucket1'])
    ([('example_tests.regression', [])], ['example_tests.regression.bucket2', 'example_tests.regression.bucket1'])
    """
    ignored_imports = []
    importables = []
    for suite in suite_paths:
        paths = suite.split('.')
        ignored_imports_ = []
        importables_ = []
        for i, path in enumerate(paths):
            if path.startswith('!'):
                paths_ = paths[0:i] + path.split(';')
                for path_ in path.split(';'):
                    path_ = path_.split('::')[0]
                    path_ = '.'.join(paths[0:i] + [path_]).replace('!', '')
                    ignored_imports_.append(path_)
                if paths[0:i-1]:
                    importables.append(('.'.join(paths[0:i]), []))
            elif ';' in path:
                paths_ = path.split(';')
                for path_ in paths_:
                    if '::' in path_:
                        module, tests = path_.split('::')
                        tests_ = tests.split(',')
                        if tests.startswith('!'):
                            for j in range(len(tests_)):
                                if not tests_[j].startswith('!'):
                                    tests_[j] = f'!{tests_[j]}'
                        importables_.append(('.'.join(paths[0:i] + [module]), tests_))
                    else:
                        importables_.append(('.'.join(paths[0:i] + [path_]), []))
            elif '::' in path:
                module, tests = path.split('::')
                tests_ = tests.split(',')
                if tests.startswith('!'):
                    for j in range(len(tests_)):
                        if not tests_[j].startswith('!'):
                            tests_[j] = f'!{tests_[j]}'
                importables_.append(('.'.join(paths[0:i] + [module]), tests_))
        if ignored_imports_:
            ignored_imports.extend(ignored_imports_)
        elif importables_:
            importables.extend(importables_)
        else:
            importables.append((suite, []))
    return importables, ignored_imports


def _recursive_discover(path: str, ignored_paths: list, test_filters: list) -> tuple:
    modules, failed_imports = set(), set()
    if path not in ignored_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    if os.path.isdir(full_path) and os.path.basename(full_path) != '__pycache__':
                        modules_, failed_import_ = _recursive_discover(full_path, ignored_paths, test_filters)
                        modules |= modules_
                        failed_imports |= failed_import_
                    elif item.endswith('.py') and item != '__init__.py' and full_path.replace('.py', '') not in ignored_paths:
                        modules_, failed_import_ = _recursive_discover(full_path, ignored_paths, test_filters)
                        modules |= modules_
                        failed_imports |= failed_import_
            else:
                module, failed_import = discover_module(path, test_filters)
                if module:
                    modules.add(module)
                if failed_import:
                    failed_imports.add(failed_import)
        else:
            module, failed_import = discover_module(path, test_filters)
            if module:
                modules.add(module)
            elif failed_import:
                failed_imports.add(failed_import)
    return modules, failed_imports


def discover_module(module_path: str, test_filters: list) -> tuple:
    """
    >>> module, error_str = discover_module('test_framework.examples.example_tests.smoke.sample1', [])
    >>> assert module and error_str == ''
    >>> module, error_str = discover_module('test_framework.examples.tests.dont_exist', [])
    >>> assert module is None and error_str
    """
    module_path_ = module_path.replace(os.sep, ".").replace(".py", "")
    test_module, error_str = None, ''
    try:
        module = importlib.import_module(module_path_)
        tests, ignored_tests = discover_tests(module, test_filters)
        test_module = TestModule(module, tests, ignored_tests)
    except ModuleNotFoundError as me:
        if me.name == module_path_:
            error_str = f"Module doesn't exist - {module_path_}"
        else:
            error_str = f"Failed to load {module_path_} - {me}"
    except Exception as e:
            error_str = f'Failed to load {module_path_} - {e}'
    return test_module, error_str


def discover_tests(module, test_filters: list) -> tuple:
    """
    >>> from test_framework.examples.example_tests.smoke import sample1
    >>> tests, ignored_tests = discover_tests(sample1, [])
    >>> assert tests and ignored_tests == []
    >>> tests, ignored_tests = discover_tests(sample1, ['!test_ignored_test', 'test_1', 'test_2'])
    >>> assert len(tests) == 2 and 'test_ignored_test' in ignored_tests
    """
    tests, ignored_tests = [], []
    if inspect.ismodule(module):
        setup = get_fixture(module, 'setup_test')
        teardown = get_fixture(module, 'teardown_test')
        for name in dir(module):
            attribute = getattr(module, name)
            if type(attribute) is FUNCTION_TYPE and name.startswith('test_'):
                if f'!{name}' in test_filters:
                    ignored_tests.append(name)
                elif test_filters:
                    found = False
                    for test_filter in test_filters:
                        open_bracket_index = test_filter.find('[')
                        if name == test_filter:
                            tests.append(TestMethod(setup, attribute, teardown))
                            found = True
                            break
                        elif hasattr(attribute, 'parameterized_list') and (open_bracket_index != -1 and name == test_filter[:open_bracket_index]):
                            attribute.range = _filter_parameterized_list(test_filter, attribute.parameterized_list)
                            tests.append(TestMethod(setup, attribute, teardown))
                            found = True
                            break
                    if not found:
                        ignored_tests.append(name)
                else:
                    tests.append(TestMethod(setup, attribute, teardown))
        shuffle(tests)
    return tests, ignored_tests


def _filter_parameterized_list(test_name: str, parameterized_list: list) -> range:
    """
    x = [1, 2, 3, 4, 5, 6, 7, 8]
    >>> _filter_parameterized_list('test_1[0]', x)
    range(0, 1)
    >>> assert _filter_parameterized_list('test_1[-1:]', x) == range(-1, len(x))
    >>> assert _filter_parameterized_list('test_1[:-1]', x) == range(0, len(x)-1)
    >>> assert _filter_parameterized_list('test_1', x) == range(len(x))
    >>> assert _filter_parameterized_list('test_1[::-1]', x) == range(0, len(x), -1)
    >>> _filter_parameterized_list('test_1[1:1:1]', x)
    range(1, 1)
    >>> _filter_parameterized_list('test_1[]', x)
    range(0, 0)
    >>> _filter_parameterized_list('test_1[', x)
    range(0, 0)
    >>> _filter_parameterized_list('test_1]', x)
    range(0, 0)
    >>> _filter_parameterized_list('test_1][', x)
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