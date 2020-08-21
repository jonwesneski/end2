from test_framework.enums import RunMode

__run_mode__ = RunMode.PARALLEL


def test_1(logger):
    assert 1 == 1
    assert True is True
    logger.info('Hi')


def test_2(logger):
    assert f"testing: {test_2.__name__} using logger: {logger.name}"
