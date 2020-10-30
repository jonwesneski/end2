import functools
from test_framework.enums import FUNCTION_TYPE


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


def parameterize(parameters_list, first_arg_is_name: bool = False):
    def wrapper(func):
        if first_arg_is_name:
            func.names = [f'{func.__name__} {i} {args[0]}' for i, args in enumerate(parameters_list, start=1)]
            func.parameterized_list = tuple(p[1:] for p in parameters_list)
        else:
            func.names = [f'{func.__name__} {i}' for i in range(1, len(parameters_list)+1)]
            func.parameterized_list = tuple(parameters_list)
        return func
    return wrapper


def parallel_parameterize(parameters_list: list, first_arg_is_name: bool = False):
    def wrapper(func):
        if first_arg_is_name:
            func.names = [f'{func.__name__} {i} {args[0]}' for i, args in enumerate(parameters_list, start=1)]
            func.parallel_parameterized_list = tuple(p[1:] for p in parameters_list)
        else:
            func.names = [f'{func.__name__} {i}' for i in range(1, len(parameters_list)+1)]
            func.parallel_parameterized_list = tuple(parameters_list)
        return func
    return wrapper


def get_fixture(module, name: str):
    for key in dir(module):
        attribute = getattr(module, key)
        if type(attribute) is FUNCTION_TYPE and  hasattr(attribute, name):
            return attribute
