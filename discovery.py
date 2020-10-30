import importlib
import inspect
import os
from random import shuffle
import sys

sys.path.insert(0, os.getcwd())
from test_framework.fixtures import get_fixture
from test_framework.enums import RunMode
from test_framework.popo import TestMethod, TestModule


FUNCTION_TYPE = type(lambda: None)


def discover_tests(module, test_filters: list) -> tuple:
    """
    >>> from test_framework.examples.tests.smoke import sample1
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
                if test_filters and (f'!{name}' in test_filters or name not in test_filters):
                    ignored_tests.append(name)
                else:
                    if hasattr(attribute, 'parameterized_list'):
                        for test_filter in test_filters:
                            if name in test_filter:
                                slice_ = filter_parameterized_list(test_filter)
                                attribute.parameterized_list = tuple(attribute.parameterized_list[slice_])
                                break
                    tests.append(TestMethod(setup, attribute, teardown))
        shuffle(tests)
    return tests, ignored_tests


def discover_module(module_path: str, test_filters: list) -> tuple:
    """
    >>> module, error_str = discover_module('test_framework.examples.tests.smoke.sample1', [])
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


def discover_suites(suite_paths: list) -> tuple:
    """
    >>> sequential, parallel, ignored, failed = discover_suites(['test_framework.examples.tests.smoke.!ignored_module,sample1', 'test_framework.examples.tests.regression'])
    >>> sequential
    0
    >>> parallel
    0
    >>> failed
    0
    >>> assert len(sequential) == 2 and len(parallel) == 2 and not failed
    """
    modules, ignored_modules, failed_imports = set(), set(), set()
    for p in suite_paths:
        segments = p.split('.')
        if len(segments) > 1:
            for i, s in enumerate(segments):
                comma_separate_modules = s.split(',')
                if len(comma_separate_modules) > 1:
                    for module in comma_separate_modules:
                        if module[0] == '!':
                            ignored_modules.add(f"{'.'.join(segments[:i])}.{module[1:]}")
                        else:
                            m_, test_filters = module, []
                            if '::' in m_:
                                m_, tests = m_.split('::',  maxsplit=1)
                                test_filters = tests.split(';')
                            m_ = f"{'.'.join(segments[:i])}.{m_}"
                            m, f = _recursive_discover(m_.replace('.', os.sep), test_filters)
                            modules |= m
                            failed_imports |= f
                elif i  == len(segments) - 1:
                    m, f = _recursive_discover('.'.join(segments[:i]), [])
                    modules |= m
                    failed_imports |= f
                    continue  # Not sure if I need to do anything yet.
        else:
            m, f = _recursive_discover(segments[0], [])
            modules |= m
            failed_imports |= f
    sequential_modules = list(filter(lambda x: x.module.__run_mode__ == RunMode.SEQUENTIAL, modules))
    parallel_modules = list(filter(lambda x: x.module.__run_mode__ in [RunMode.PARALLEL, RunMode.PARALLEL_TEST], modules))
    shuffle(sequential_modules)
    shuffle(parallel_modules)
    return sequential_modules, parallel_modules, tuple(ignored_modules), tuple(failed_imports)


def filter_parameterized_list(test_name: str) -> int or slice:
    """
    >>> x = [1, 2, 3]
    >>> assert x[filter_parameterized_list('test_1[0]')] == x[0:1]
    >>> assert x[filter_parameterized_list('test_1[-1:]')] == x[-1:]
    >>> assert x[filter_parameterized_list('test_1[:-1]')] == x[:-1]
    >>> assert x[filter_parameterized_list('test_1[::-1]')] == x[::-1]
    >>> assert x[filter_parameterized_list('test_1[1:1:1]')] == x[1:1:1]
    >>> assert filter_parameterized_list('test_1[]') == None
    >>> assert filter_parameterized_list('test_1[') == None
    >>> assert filter_parameterized_list('test_1]') == None
    >>> assert filter_parameterized_list('test_1') == None
    """
    index = test_name.find('[') + 1
    value = None
    if index and test_name[-1] == ']' and test_name[index:-1]:
        if ':' in test_name[index:-1]:
            segments = test_name[index:-1].split(':')
            slice_ = [None, None, None]
            for i in range(len(segments)):
                if segments[i]:
                    slice_[i] = int(segments[i])
            value = slice(*slice_)
        else:
            int_ = int(test_name[index:-1])
            value = slice(int_,int_+1)
    return value


def _recursive_discover(path: str, test_filters: list) -> tuple:
    modules, failed_imports = set(), set()
    if os.path.exists(path):
        if os.path.isdir(path):
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path) and os.path.basename(full_path) != '__pycache__':
                    modules_, failed_import_ = _recursive_discover(full_path, test_filters)
                    modules |= modules_
                    failed_imports |= failed_import_
                elif item.endswith('.py') and item != '__init__.py':
                        module, failed_import = discover_module(f'{path}.{item}', test_filters)
                        if module:
                            modules.add(module)
                        elif failed_import:
                            failed_imports.add(failed_import)
        else:
            module, failed_import = discover_module(path, test_filters)
            modules.add(module)
            failed_imports.add(failed_import)
    else:
        module, failed_import = discover_module(path, test_filters)
        if module:
            modules.add(module)
        elif failed_import:
            failed_imports.add(failed_import)
    return modules, failed_imports
