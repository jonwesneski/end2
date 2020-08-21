import functools
import json


def setup(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.setup = None
    return wrapper


def teardown(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.teardown = None
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


def parameterize(parameters_list, first_arg_is_name=False):
    def wrapper(func):
        if first_arg_is_name:
            func.names = [f'{func.__name__} {i} {args[0]}' for i, args in enumerate(parameters_list, start=1)]
            func.parameterized_list = [p[1:] for p in parameters_list]
        else:
            func.names = [f'{func.__name__} {i}' for i in range(1, len(parameters_list)+1)]
            func.parameterized_list = parameters_list
        return func
    return wrapper


class Metrics:
    _data = {}

    @staticmethod
    def add_one(*args):

        def recurse(dict_, args):
            if args:
                if args[0] not in dict_:
                    dict_[args[0]] = {} if len(args) > 1 else 1
                    recurse(dict_[args[0]], args[1:])
                elif isinstance(dict_[args[0]], int):
                    dict_[args[0]] += 1
        recurse(Metrics._data, args)

    @staticmethod
    def update(source_dict):

        def recurse(source_dict_, target_dict):
            for k, v in source_dict_.items():
                if k not in target_dict:
                    target_dict[k] = v
                elif isinstance(v, int):
                    target_dict[k] += v
                else:
                    recurse(source_dict_[k], target_dict[k])
        recurse(source_dict, Metrics._data)

    @staticmethod
    def save(path='metrics.json'):
        if Metrics._data:
            try:
                with open(path, mode='w') as f:
                    f.write(json.dumps(Metrics._data, indent=4))
            except:
                pass
