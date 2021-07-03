import functools

from src.enums import FUNCTION_TYPE


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


def metadata(func, **kwargs):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.metadata = kwargs
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
            func.names = [f'{func.__name__}[{i}] {args[0]}' for i, args in enumerate(parameters_list)]
            func.parameterized_list = tuple(p[1:] for p in parameters_list)
        else:
            func.names = [f'{func.__name__}[{i}]' for i in range(len(parameters_list))]
            func.parameterized_list = tuple(parameters_list)
        func.range = range(len(parameters_list))  # TODO: do I still need this?
        return func
    return wrapper

def empty_func(*args, **kwargs):
    pass

def get_fixture(module, name: str):
    fixture = empty_func
    for key in dir(module):
        attribute = getattr(module, key)
        if type(attribute) is FUNCTION_TYPE and  hasattr(attribute, name):
            fixture = attribute
            break
    return fixture
