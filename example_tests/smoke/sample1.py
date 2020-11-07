from test_framework.enums import RunMode
from test_framework.fixtures import (
    setup_test,
    teardown
)

__run_mode__ = RunMode.PARALLEL


_my_list = []


@setup_test
def my_setup_test(logger):
    logger.info('running setup test')
    _my_list.append(len(_my_list))


@teardown
def my_teardown(logger):
    logger.info('running teardown')
    global _my_list
    _my_list = []


def test_1(logger):
    assert len(_my_list) > 0
    logger.info(_my_list)


def test_2(logger):
    assert len(_my_list) != 0
    logger.info(_my_list)
    assert False
    logger.info('Unreachable')


def test_ignored_test(logger):
    assert False, "I SHOULD BE IGNORED"
