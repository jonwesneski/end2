from src.enums import RunMode


__run_mode__ = RunMode.PARALLEL



def test_1(logger):
    assert False, "I SHOULD NOT RUN BECAUSE THIS MODULE SHOULD BE IGNORED"
