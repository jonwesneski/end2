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
    def __init__(self, name: str, tests: Dict[str, TestMethod]
                 , setup_func=empty_func, teardown_func=empty_func) -> None:
        self.name = name
        self.setup_func = setup_func
        self.tests = tests
        self.teardown_func = teardown_func
        self.children = []

    def append(self, group) -> None:
        self.children.append(group)

    def update(self, same_group):
        for ignored in same_group.ignored_tests:
            self.tests.pop(ignored, None)
        self.tests.update(same_group.tests)
        self.ignored_tests.update(same_group.ignored_tests)


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

    def update(self, same_module):
        for ignored in same_module.ignored_tests:
            for group in self.groups:
                for child in group.children:
                    child.tests.pop(ignored, None)
        for group in same_module.groups:
            for child in group.children:
                for self_group in self.groups:
                    for self_child in self_group:
                        if child.name == self_child.name:
                            self.tests.update(same_module.tests)
        self.ignored_tests.update(same_module.ignored_tests)


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
                if len(rhs.sub_packages) - 1 > i:
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