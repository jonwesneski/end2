from inspect import getmro
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


class DynamicMroMixin:
    @classmethod
    def _get_mros(cls):
        return getmro(cls)[::-1]

    @classmethod
    def __getattrcls__(cls, name):
        for a in cls._get_mros():
            if hasattr(a, name):
                return getattr(a, name)
        raise AttributeError(f"No atrribute named {name}")
    
    @classmethod
    def __setattrcls__(cls, name, value):
        for a in cls._get_mros():
            if hasattr(a, name):
                setattr(a, name, value)
                return
        setattr(cls, name, value)

    def __getattr__(self, name):
        return self.__getattrcls__(name)
    
    def __setattr__(self, name, value):
        return self.__setattrcls__(name, value)


def add_mixin(name, current_mixin: DynamicMroMixin):
    return type(
        f"{name.replace('.', 'Dot')}Dot{DynamicMroMixin.__name__}"
        (current_mixin.__class__,),
        {}
    )()


class TestPackageNode:
    def __init__(self, package, package_object: DynamicMroMixin = None):
        self.name = package.__name__
        self.package = package
        self.package_object = package_object or DynamicMroMixin()
        self.setup_done = False
        self.teardown_done = False
        self.setup_func = get_fixture(self.package, 'setup')
        self.teardown_func = get_fixture(self.package, 'teardown')

    def setup(self):
        if not self.setup_done:
            self.setup_func(self.package_object)
            self.setup_done = True

    def teardown(self):
        if not self.teardown_done:
            self.teardown_func(self.package_object)
            self.teardown_done = True


class TestPackages:
    def __init__(self, package):
        self.packages = [TestPackageNode(package)]

    def append(self, package):
        self.packages.append(
            TestPackageNode(package, add_mixin(package.__name__, self.package_object))
        )

    def slice(self):
        packages = TestPackages(self.packages[0].package)
        packages.packages = self.packages[:]
        return packages

    @property
    def package_object(self):
        return self.packages[-1].package_object

    def setup(self):
        for p in self.packages:
            p.setup()

    def teardown(self):
        for p in reversed(self.packages):
            p.teardown()
