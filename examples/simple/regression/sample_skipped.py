from end2 import (
    RunMode,
    setup
)


__run_mode__ = RunMode.PARALLEL


@setup
def my_setup(logger):
    assert False, "FAILING SETUP ON PURPOSE"


def test_skipped(logger):
    assert False, "THIS TEST SHOULD NOT RUN BECAUSE SETUP FAILED"
