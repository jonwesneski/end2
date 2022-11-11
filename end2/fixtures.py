import functools

from end2.constants import FUNCTION_TYPE
from end2.exceptions import MoreThan1SameFixtureException


def setup_module(func):
    func.setup_module = None
    return func


def teardown_module(func):
    func.teardown_module = None
    return func


def on_failures_in_module(func):
    func.on_failures_in_module = None
    return func


def on_test_failure(func):
    def inner(func_):
        @functools.wraps(func_)
        def wrapper(*args, **kwargs):
            return func_(*args, **kwargs)
        wrapper.on_test_failure = func
        return wrapper
    return inner


def setup(func):
    func.setup = None
    return func


def setup_test(func):
    func.setup_test = None
    return func


def teardown_test(func):
    func.teardown_test = None
    return func


def teardown(func):
    func.teardown = None
    return func


def package_test_parameters(func):
    func.package_test_parameters = None
    return func


def metadata(**kwargs):
    def inner(func):
        func.metadata = kwargs
        return func
    return inner


def parameterize(parameters_list: list, first_arg_is_name: bool = False):
    def wrapper(func):
        if first_arg_is_name:
            func.names = [f'{func.__name__}[{i}] {args[0]}' for i, args in enumerate(parameters_list)]
            func.parameterized_list = tuple(p[1:] for p in parameters_list)
        else:
            func.names = [f'{func.__name__}[{i}]' for i in range(len(parameters_list))]
            func.parameterized_list = tuple(parameters_list)
        return func
    return wrapper


def empty_func(*args, **kwargs) -> None:
    return


def get_fixture(module, name: str, default=empty_func):
    fixture = default
    found = False
    for key in dir(module):
        attribute = getattr(module, key)
        if type(attribute) is FUNCTION_TYPE and hasattr(attribute, name):
            if found:
                raise MoreThan1SameFixtureException(name, module.__name__)
            fixture = attribute
            found = True
    return fixture
