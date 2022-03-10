from end2 import setup, teardown


@setup
def my_smoke_setup(global_object):
    global_object.package2b = "package2b"


@teardown
def my_smoke_teardown(global_object):
    print(global_object.package2b)
