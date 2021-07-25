
from src import setup, teardown


@setup
def my_smoke_setup(global_object):
    global_object.package2a = "package2a"


@teardown
def my_smoke_teardown(global_object):
    print(global_object.package2a)
