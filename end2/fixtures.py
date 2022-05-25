import functools

from end2.constants import FUNCTION_TYPE
from end2.exceptions import MoreThan1FixtureException


def setup_module(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.setup_module = None
    return wrapper


def teardown_module(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.teardown_module = None
    return wrapper


def on_failures_in_module(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.on_failures_in_module = None
    return wrapper


def on_test_failure(func):
    def inner(func_):
        @functools.wraps(func_)
        def wrapper(*args, **kwargs):
            return func_(*args, **kwargs)
        wrapper.on_test_failure = func
        return wrapper
    return inner


def setup(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.setup = None
    return wrapper


def setup_test(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.setup_test = None
    return wrapper


def teardown_test(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.teardown_test = None
    return wrapper


def teardown(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.teardown = None
    return wrapper


def package_test_parameters(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.package_test_parameters = None
    return wrapper


def metadata(**kwargs):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper.metadata = kwargs
        return wrapper
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
                raise MoreThan1FixtureException(name, module.__name__)
            fixture = attribute
            found = True
    return fixture
