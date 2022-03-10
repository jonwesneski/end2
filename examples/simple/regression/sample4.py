from end2.enums import RunMode
from end2 import (
    parameterize,
    RunMode,
    setup,
    teardown_test
)

__run_mode__ = RunMode.SEQUENTIAL  # This is required for every test module


_letter = 'a'
_my_dict = {}
_my_var = 423956
_my_bool = True


@setup
def my_setup(logger):
    logger.info('running setup')
    _my_var = ''
    _my_dict['key'] = ord(_letter)


@teardown_test
def my_teardown_test(logger):
    logger.info('running teardown test')
    global _my_bool
    _my_bool = not _my_bool


@parameterize([
    (False, 'B', 'AB'),
    (True, 2, 2),
    (True, [], []),
    (False, [1], (1,)),
    (False, object(), object()),
    (True, 2.0, 2)
])
def test_1(logger, it_works, lhs, rhs):
    logger.info(f'Does it work?  {"Yes" if it_works else "No"}')
    if it_works:
        assert lhs == rhs
    else:
        assert lhs != rhs



@parameterize([
    (False, 'B', 'AB'),
    (True, 2, 2),
    (True, [], []),
    (False, [1], (1,)),
    (False, object(), object()),
    (True, 2.0, 2)
])
def test_11(logger, it_works, lhs, rhs):
    logger.info(f'Does it work?  {"Yes" if it_works else "No"}')
    if it_works:
        assert lhs == rhs
    else:
        assert lhs != rhs


def test_2(logger):
    assert chr(_my_dict['key']) == _letter


def test_python_gotcha_4(logger):
    assert _my_var == 423956
    logger.info('You must specify global keyword when re-assigning a global variable')


def test_my_bool(logger):
    assert _my_bool if _my_bool else not _my_bool
