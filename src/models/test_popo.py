import os

from src.fixtures import get_fixture


def build_full_name(module_name: str, test_name: str) -> str:
    return f'{module_name}::{test_name}'


def empty_func(*args, **kwargs):
    pass


class TestMethod:
    def __init__(self, func, setup_func=empty_func, teardown_func=empty_func, parameterized_tuple: tuple = None):
        self.name = func.__name__
        self.full_name = build_full_name(func.__module__, self.name)
        self.func = func
        self.setup_func = setup_func
        self.teardown_func = teardown_func
        self.parameterized_tuple = parameterized_tuple or tuple()

    def __eq__(self, rhs) -> bool:
        return self.full_name == rhs.full_name

    def __hash__(self) -> int:
        return id(self.full_name)


class TestModule:
    def __init__(self, module, tests: dict, setup_func=empty_func, teardown_func=empty_func, ignored_tests: set = None, test_package_list = None):
        self.module = module
        self.name = module.__name__
        self.file_name = os.path.relpath(module.__file__)
        self.run_mode = module.__run_mode__
        self.setup_func = setup_func
        self.tests = tests
        self.teardown_func = teardown_func
        self.ignored_tests = ignored_tests or set()
        self.test_package_list = test_package_list

    def __eq__(self, rhs) -> bool:
        return self.name == rhs.name

    def __hash__(self) -> int:
        return id(self.module)

    def update(self, same_module):
        for ignored in same_module.ignored_tests:
            self.tests.pop(ignored, None)
        self.tests.update(same_module.tests)
        self.ignored_tests.update(same_module.ignored_tests)


class TestPackageNode:
    def __init__(self, package):
        self.name = package.__name__
        self.package = package
        self.child = None
        self.setup_func = get_fixture(self.package, 'setup')
        self.teardown_func = get_fixture(self.package, 'teardown')


class TestPackageList:
    def __init__(self, package=None):
        self.package = None if package is None else TestPackageNode(package)
        self.package_object = GlobalPackageObject()
        self.setup_done = False
        self.teardown_done = False
        self._reversed_children = []

    def append(self, package):
        if self.package is None:
            self.package = TestPackageNode(package)
        else:
            child = self.package
            while child.child:
                child = child.child
            child.child = TestPackageNode(package)

    @staticmethod
    def copy(package_list):
        copy_ = TestPackageList()
        copy_.package = package_list.package
        copy_.package.child = None
        copy_.package_object = package_list.package_object
        return copy_

    def setup(self):
        if self.setup_done is False:
            self.package.setup_func(self.package_object)
            child = self.package.child
            while child:
                self._reversed_children.append(child)
                child.setup_func(self.package_object)
                child = child.child
            self.setup_done = True
            self._reversed_children.reverse()

    def teardown(self):
        if self.teardown_done is False:
            while self._reversed_children:
                child = self._reversed_children.pop()
                child.teardown_func(self.package_object)
            self.teardown_done = True


class GlobalPackageObject:
    def copy(self, obj):
        for attribute in dir(obj):
            if not attribute.startswith('__'):
                setattr(self, attribute, getattr(obj, attribute))
