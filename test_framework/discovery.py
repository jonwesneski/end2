import importlib
import inspect
import os
from random import shuffle

from test_framework.fixtures import get_fixture
from test_framework.enums import RunMode
from test_framework.popo import TestMethod, TestModule


FUNCTION_TYPE = type(lambda: None)


def discover_suites(suite_paths: list) -> tuple:
    # """
    # >>> sequential, parallel, ignored, failed = discover_suites(['test_framework.example.smoke.!ignored_module,sample1', 'test_framework.example.regression'])
    # >>> sequential
    # 0
    # >>> parallel
    # 0
    # >>> failed
    # 0
    # >>> assert len(sequential) == 2 and len(parallel) == 2 and not failed
    # """
    importables, ignored_modules = _parse_suite_paths(suite_paths)
    ignored_paths = [x.replace('.', os.sep) for x in ignored_modules]
    modules, failed_imports = {}, set()
    for importable in importables:
        m, f = _recursive_discover(importable, ignored_paths)
        for k, v in m.items():
            if k in modules:
                modules[k].update(v)
            else:
                modules[k] = v
        failed_imports |= f
    sequential_modules = list(filter(lambda x: x.module.__run_mode__ == RunMode.SEQUENTIAL, modules.values()))
    parallel_modules = list(filter(lambda x: x.module.__run_mode__ in [RunMode.PARALLEL, RunMode.PARALLEL_TEST], modules.values()))
    shuffle(sequential_modules)
    shuffle(parallel_modules)
    return sequential_modules, parallel_modules, tuple(ignored_modules), tuple(failed_imports)


class _ImportableFilters:
    def __init__(self, path: str, tests: list = None, ignored_tests: list = None):
        self._path = path
        self._tests = set(tests or [])
        self._ignored_tests = set(ignored_tests or [])
        self._difference_update()

    @property
    def path(self):
        return self._path.replace('.', os.sep)

    @property
    def tests(self):
        return list(self._tests)
    
    @property
    def parameterized_tests(self):
        return [x for x in self.tests if '[' in x]

    @property
    def ignored_tests(self):
        return list(self._ignored_tests)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, _ImportableFilters):
            eq = self._path == o._path
        else:
            eq = self._path == o
        return eq

    def _difference_update(self):
        self._tests.difference_update(self._ignored_tests)

    def add_tests(self, tests: list):
        self._tests.update(set(tests))
        self._difference_update()

    def add_ignored_tests(self, ignored_tests: list):
        self._ignored_tests.update(set(ignored_tests))
        self._difference_update()

    def can_run_test(self, test_name: str) -> bool:
        can_run = test_name not in self._ignored_tests
        if can_run and self._tests:
            can_run = test_name in self._tests
        return can_run

    def get_parameterized_test(self, test_name: str, parameterized_list: list) -> range:
        for p in self.parameterized_tests:
            if test_name in p:
                return self._filter_parameterized_list(p, parameterized_list)

    @staticmethod
    def _filter_parameterized_list(test_name: str, parameterized_list: list) -> range:
        """
        >>> x = [1, 2, 3, 4, 5, 6, 7, 8]
        >>> assert _filter_parameterized_list('test_1', x) == range(len(x))
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


def _parse_suite_paths(suite_paths: list) -> tuple:
    """
    >>> expected1, empty_tuple = (_ImportableFilters('tests'),), tuple()
    >>> actual1, actual2 = _parse_suite_paths(['tests'])
    >>> assert expected1 == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['tests', 'tests'])
    >>> assert expected1 == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['tests', '!tests'])
    >>> assert empty_tuple == actual1 and ('tests',) == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket1'])
    >>> assert (_ImportableFilters('example.regression.bucket1'),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket1::test1'])
    >>> assert (_ImportableFilters('example.regression.bucket1', ['tests1']),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket1::test1,test2'])
    >>> assert (_ImportableFilters('example.regression.bucket1', ['test1', 'test2']),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket1;bucket2::test1,test2'])
    >>> assert (_ImportableFilters('example.regression.bucket1'), _ImportableFilters('example.regression.bucket2', ['test1', 'test2']),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket1;bucket2::!test1,test2'])
    >>> assert (_ImportableFilters('example.regression.bucket1'), _ImportableFilters('example.regression.bucket2', ignored_tests=['test1', 'test2']),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.bucket2::!test1,test2;bucket1'])
    >>> assert (_ImportableFilters('example.regression.bucket2', ignored_tests=['test1', 'test2']), _ImportableFilters('example.regression.bucket1'),) == actual1 and empty_tuple == actual2
    >>> actual1, actual2 = _parse_suite_paths(['example.regression.!bucket2::!test1,test2;bucket1'])
    >>> assert (_ImportableFilters('example.regression'),) == actual1 and set(('example.regression.bucket1', 'example.regression.bucket2')) == set(actual2)
    """
    ignored_imports = set()
    importables = {}
    for suite in suite_paths:
        paths = suite.split('.')
        added_importable, added_ignored = False, False
        for i, path in enumerate(paths):
            if path.startswith('!'):
                paths_ = paths[0:i] + path.split(';')
                for path_ in path.split(';'):
                    path_ = path_.split('::')[0]
                    path_ = '.'.join(paths[0:i] + [path_]).replace('!', '')
                    ignored_imports.add(path_)
                    added_ignored = True
            elif ';' in path:
                paths_ = path.split(';')
                for path_ in paths_:
                    if '::' in path_:
                        module, tests = path_.split('::')
                        module_path = '.'.join(paths[0:i] + [module])
                        tests_ = tests.split(',')
                        if tests.startswith('!'):
                            tests_[0] = tests_[0][1:]
                            if module_path in importables:
                                importables[module_path].add_ignored_tests(tests_)
                            else:
                                importables[module_path] = _ImportableFilters(module_path, ignored_tests=tests_)
                            added_importable = True
                        else:
                            if module_path in importables:
                                importables[module_path].add_tests(tests_)
                            else:
                                importables[module_path] = _ImportableFilters(module_path, tests_)
                            added_importable = True
                    else:
                        path_path = '.'.join(paths[0:i] + [path_])
                        if path_path not in importables:
                            importables[path_path] = _ImportableFilters(path_path)
                            added_importable = True
            elif '::' in path:
                module, tests = path.split('::')
                tests_ = tests.split(',')
                path_module = '.'.join(paths[0:i] + [module])
                if tests.startswith('!'):
                    tests_[0] = tests_[0][1:]
                    if path_module in importables:
                        importables[path_module].add_ignored_tests(tests_)
                    else:
                        importables[path_module] = _ImportableFilters(path_module, ignored_tests=tests_)
                else:
                    if path_module in importables:
                        importables[path_module].add_tests(tests_)
                    else:
                        importables[path_module] = _ImportableFilters(path_module, tests_)
                added_importable = True
        if added_importable is False and added_ignored is True:
            package_path = '.'.join(paths[0:-1])
            if package_path and package_path not in importables:
                importables[package_path] = _ImportableFilters(package_path)
        elif added_importable is False:
            if suite not in importables:
                importables[suite] = _ImportableFilters(suite)
    for ignored_import in ignored_imports:
        importables.pop(ignored_import, None)
    return tuple(importables.values()), tuple(ignored_imports)


def _recursive_discover(importable: _ImportableFilters, ignored_paths: list) -> tuple:
    modules, failed_imports = {}, set()
    path = importable.path
    if path not in ignored_paths:
        if os.path.exists(path):
            if os.path.isdir(path):
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    if os.path.isdir(full_path) and os.path.basename(full_path) != '__pycache__':
                        modules_, failed_import_ = _recursive_discover(_ImportableFilters(full_path.replace(os.sep, '.')), ignored_paths)
                        modules.update(modules_)
                        failed_imports |= failed_import_
                    elif item.endswith('.py') and item != '__init__.py' and full_path.replace('.py', '') not in ignored_paths:
                        modules_, failed_import_ = _recursive_discover(_ImportableFilters(full_path.replace('.py', '').replace(os.sep, '.'), importable.tests, importable.ignored_tests), ignored_paths)
                        modules.update(modules_)
                        failed_imports |= failed_import_
            else:
                module, failed_import = discover_module(importable)
                if module:
                    modules[path] = module
                if failed_import:
                    failed_imports.add(failed_import)
        else:
            module, failed_import = discover_module(importable)
            if module:
                modules[path] = module
            elif failed_import:
                failed_imports.add(failed_import)
    return modules, failed_imports


def discover_module(importable: _ImportableFilters) -> tuple:
    # """
    # >>> module, error_str = discover_module('test_framework.example.smoke.sample1', [])
    # >>> assert module and error_str == ''
    # >>> module, error_str = discover_module('test_framework.example.dont_exist', [])
    # >>> assert module is None and error_str
    # """
    test_module, error_str = None, ''
    try:
        module = importlib.import_module(importable._path)
        tests = discover_tests(module, importable)
        if tests:
            test_module = TestModule(module, tests, set(importable.ignored_tests))
    except ModuleNotFoundError as me:
        if me.name == importable._path:
            error_str = f"Module doesn't exist - {importable._path}"
        else:
            error_str = f"Failed to load {importable._path} - {me}"
    except Exception as e:
            error_str = f'Failed to load {importable._path} - {e}'
    return test_module, error_str


def discover_tests(module, importable: _ImportableFilters) -> list:
    # """
    # >>> from test_framework.example.smoke import sample1
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
                if importable.can_run_test(name):
                    tests[name] = TestMethod(setup, attribute, teardown)
                elif hasattr(attribute, 'parameterized_list'):
                    range_ = importable.get_parameterized_test(name, attribute.parameterized_list)
                    if range_:
                        attribute.range = range_
                    tests[name] = TestMethod(setup, attribute, teardown)
        temp = list(tests.items())
        shuffle(temp)
        tests = dict(temp)
    return tests
