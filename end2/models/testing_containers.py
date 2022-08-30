from inspect import getmro
import os
from typing import Dict, List

from end2.constants import RunMode
from end2.fixtures import (
    empty_func,
    get_fixture,
    on_failures_in_module,
    package_test_parameters,
    setup,
    teardown
)
from end2.pattern_matchers import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher
)


def build_full_name(module_name: str, test_name: str) -> str:
    return f'{module_name}::{test_name}'


class Importable:
    def __init__(self, path: str, module_pattern_matcher: DefaultModulePatternMatcher, test_pattern_matcher: DefaultTestCasePatternMatcher) -> None:
        self.path = path
        self.module_matcher = module_pattern_matcher
        self.test_matcher = test_pattern_matcher

    def __repr__(self):
        return self.path


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
        self.children: List[TestGroups] = []

    def append(self, group) -> None:
        self.children.append(group)

    def update(self, same_group: 'TestModule') -> None:
        for ignored in same_group.ignored_tests:
            self.tests.pop(ignored, None)
        self.tests.update(same_group.tests)
        self.ignored_tests.update(same_group.ignored_tests)

    def has_tests(self) -> bool:
        has_tests = bool(self.tests)
        if not has_tests:
            for child in self.children:
                has_tests = bool(child.tests)
                if has_tests:
                    break
        return has_tests


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
    def __setattrcls__(cls, name, value) -> None:
        for a in cls._get_mros():
            if hasattr(a, name):
                setattr(a, name, value)
                return
        setattr(cls, name, value)

    def __getattr__(self, name):
        return self.__getattrcls__(name)
    
    def __setattr__(self, name, value) -> None:
        return self.__setattrcls__(name, value)

    @staticmethod
    def add_mixin(name, current_mixin):
        return type(
            f"{name.replace('.', 'Dot')}Dot{DynamicMroMixin.__name__}",
            (current_mixin.__class__,),
            {}
        )()


class TestModule:
    def __init__(self, module, groups: TestGroups, ignored_tests: set = None) -> None:
        self.module = module
        self.name = module.__name__
        self.file_name = os.path.relpath(module.__file__)
        self.run_mode = module.__run_mode__
        self.is_parallel = self.run_mode is RunMode.PARALLEL
        self.description = module.__doc__
        self.groups = groups
        self.ignored_tests = ignored_tests or set()
        self.on_failures_in_module = get_fixture(self.module, on_failures_in_module.__name__)

    def __eq__(self, rhs) -> bool:
        return self.name == rhs.name

    def __hash__(self) -> int:
        return id(self.module)

    def update(self, same_module: 'TestModule') -> None:
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


class TestPackage:
    def __init__(self, package, sequential_modules: list = None, parallel_modules: list = None
                 , package_object: DynamicMroMixin = None) -> None:
        self.package = package
        self.setup_func = get_fixture(self.package, setup.__name__)
        self.teardown_func = get_fixture(self.package, teardown.__name__)
        self.package_test_parameters_func = get_fixture(self.package, package_test_parameters.__name__, default=None)
        self.name = self.package.__name__
        self.description = self.package.__doc__
        self.package_object = package_object or DynamicMroMixin()
        self.sequential_modules = sequential_modules or set()
        self.parallel_modules = parallel_modules or set()
        self.sub_packages = []

    def __eq__(self, o) -> bool:
        return self.name == o.name

    def setup(self) -> None:
        self.setup_func(self.package_object)

    def teardown(self) -> None:
        self.teardown_func(self.package_object)

    def append(self, package) -> None:
        package_object = DynamicMroMixin.add_mixin(package.__name__, self.package_object)
        self.sub_packages.append(TestPackage(package, package_object=package_object))
        if self.sub_packages[-1].package_test_parameters_func is None:
            self.sub_packages[-1].package_test_parameters_func = self.package_test_parameters_func

    def append_module(self, module: TestModule) -> None:
        if module.is_parallel:
            self.parallel_modules.add(module)
        else:
            self.sequential_modules.add(module)

    def tail(self, package, index: int = -1) -> None:
        package_object = DynamicMroMixin.add_mixin(package.__name__, self.package_object)
        self._tail(TestPackage(package, package_object=package_object), index)

    def _tail(self, package, index: int = -1) -> None:
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


class TestPackageTree:
        def __init__(self, package = None, modules = None) -> None:
            self.packages = [TestPackage(package, modules)] if package else []

        def __iter__(self):
            def _recurse_sub_packages(sub_packages):
                for sub_package in sub_packages.sub_packages:
                    yield sub_package
                    yield from _recurse_sub_packages(sub_package)

            for package in self.packages:
                yield package
                for sub_package in package.sub_packages:
                    yield sub_package
                    yield from _recurse_sub_packages(sub_package)

        def find(self, rhs: TestPackage):
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

        def append(self, package: TestPackage) -> None:
            found_package = self.find(package)
            if found_package:
                self.merge(found_package, package)
            else:
                found_parent = self.find_by_str(".".join(package.name.split('.'))[:-1])
                if found_parent:
                    found_parent.sub_packages.append(package)
                else:
                    self.packages.append(package)

        def merge(self, lhs: TestPackage, rhs: TestPackage) -> None:
            for rm in rhs.sequential_modules:
                updated = False
                for lm in lhs.sequential_modules:
                    updated = False
                    if lm == rm:
                        updated = True
                        lm.update(rm)
                        break
                if not updated:
                    lhs.sequential_modules.add(rm)
            for i, lhs_sp in enumerate(lhs.sub_packages):
                if len(rhs.sub_packages) - 1 > i:
                    self.merge(lhs_sp, rhs.sub_packages[i])

            for rm in rhs.parallel_modules:
                updated = False
                for lm in lhs.parallel_modules:
                    updated = False
                    if lm == rm:
                        updated = True
                        lm.update(rm)
                        break
                if not updated:
                    lhs.parallel_modules.add(rm)
            for i, lhs_sp in enumerate(lhs.sub_packages):
                if len(rhs.sub_packages) - 1 > i:
                    self.merge(lhs_sp, rhs.sub_packages[i])
