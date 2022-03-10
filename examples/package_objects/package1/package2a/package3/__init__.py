
from end2 import setup, teardown


@setup
def my_smoke_setup(global_object):
    global_object.package3 = "package3"


@teardown
def my_smoke_teardown(global_object):
    print(global_object.package3)
