from src.enums import RunMode


__run_mode__ = RunMode.PARALLEL


def test_python_gotcha_3(logger):
    assert round(1.5) == 2
    assert round(2.5) == 2
    assert round(3.5) == 4
    assert round(4.5) == 4
    logger.info("Odds round up while evens round down")
