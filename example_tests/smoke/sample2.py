from test_framework.enums import RunMode
from test_framework.fixtures import setup_test


__run_mode__ = RunMode.PARALLEL


@setup_test
def my_bad(logger):
    assert False, "FAILING SETUP_TEST ON PURPOSE"


def test_1(logger):
    assert 1 == 1
    assert True is True
    logger.info('Hi')


def test_2(logger):
    assert f"testing: {test_2.__name__} using logger: {logger.name}"
