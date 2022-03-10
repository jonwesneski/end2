from end2 import RunMode


__run_mode__ = RunMode.PARALLEL


def test_1(logger, package_objects):
    assert hasattr(package_objects, 'package1')
    assert hasattr(package_objects, 'package2a')
    assert not hasattr(package_objects, 'package2b')
    assert hasattr(package_objects, 'package3')
