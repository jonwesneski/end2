from inspect import getmro
import os
from typing import Dict

from src.fixtures import get_fixture


def build_full_name(module_name: str, test_name: str) -> str:
    return f'{module_name}::{test_name}'


def empty_func(*args, **kwargs) -> None:
    pass


class TestMethod:
    def __init__(self, func, setup_func=empty_func, teardown_func=empty_func
                 , parameterized_tuple: tuple = None) -> None:
        self.name = func.__name__
        self.full_name = build_full_name(func.__module__, self.name)
        self.func = func
        self.description = func.__doc__
        self.setup_func = setup_func
        self.teardown_func = teardown_func
        self.parameterized_tuple = parameterized_tuple or tuple()
        self.metadata = getattr(func, 'metadata', {})

    def __eq__(self, rhs) -> bool:
        return self.full_name == rhs.full_name

    def __hash__(self) -> int:
        return id(self.full_name)


class TestGroups:
    def __init__(self, tests: Dict[str, TestMethod], setup_func=empty_func
                 , teardown_func=empty_func) -> None:
        self.setup_func = setup_func
        self.tests = tests
        self.teardown_func = teardown_func
        self.children = []

    def append(self, group) -> None:
        self.children.append(group)


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
        f"{name.replace('.', 'Dot')}Dot{DynamicMroMixin.__name__}",
        (current_mixin.__class__,),
        {}
    )()


class TestPackageNode:
    def __init__(self, package, package_object: DynamicMroMixin = None) -> None:
        self.name = package.__name__
        self.package = package
        self.description = package.__doc__
        self.package_object = package_object or DynamicMroMixin()
        self.setup_done = False
        self.teardown_done = False
        self.setup_func = get_fixture(self.package, 'setup')
        self.teardown_func = get_fixture(self.package, 'teardown')

    def setup(self) -> None:
        if not self.setup_done:
            self.setup_func(self.package_object)
            self.setup_done = True

    def teardown(self) -> None:
        if not self.teardown_done:
            self.teardown_func(self.package_object)
            self.teardown_done = True


class TestPackages:
    def __init__(self, package) -> None:
        self.packages = [TestPackageNode(package)]

    def append(self, package) -> None:
        self.packages.append(
            TestPackageNode(package, add_mixin(package.__name__, self.package_object))
        )

    def slice(self) -> None:
        packages = TestPackages(self.packages[0].package)
        packages.packages = self.packages[:]
        return packages

    @property
    def package_object(self) -> DynamicMroMixin:
        return self.packages[-1].package_object

    def setup(self) -> None:
        for p in self.packages:
            p.setup()

    def teardown(self) -> None:
        for p in reversed(self.packages):
            p.teardown()


class TestModule:
    def __init__(self, module, groups: TestGroups, ignored_tests: set = None
                 , test_package_list: TestPackages = None) -> None:
        self.module = module
        self.name = module.__name__
        self.file_name = os.path.relpath(module.__file__)
        self.run_mode = module.__run_mode__
        self.description = module.__doc__
        self.groups = groups
        self.ignored_tests = ignored_tests or set()
        self.test_package_list = test_package_list

    def __eq__(self, rhs) -> bool:
        return self.name == rhs.name

    def __hash__(self) -> int:
        return id(self.module)
