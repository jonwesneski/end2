from test_framework.enums import RunMode


__run_mode__ = RunMode.PARALLEL



def test_1(logger):
    assert False, "I SHOULD NOT RUN BECAUSE MODULE IS IGNORED"
