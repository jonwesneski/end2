from src.fixtures import setup
from src import (
    RunMode,
    setup,
    setup_test,
    teardown,
    teardown_test
)


__run_mode__ = RunMode.PARALLEL


def test_python_gotcha_3(logger):
    assert round(1.5) == 2
    assert round(2.5) == 2
    assert round(3.5) == 4
    assert round(4.5) == 4
    logger.info("Odds round up while evens round down")


class Group1:
    @staticmethod
    @setup
    def my_setup(logger):
        logger.info(f'{Group1.__name__}.{Group1.my_setup.__name__}')

    @staticmethod
    def test_1(logger):
        logger.info(f'{Group1.__name__}.{Group1.test_1.__name__}')

    class Group2:
        @staticmethod
        @setup
        def my_setup(logger):
            logger.info(f'{Group1.Group2.__name__}.{Group1.Group2.my_setup.__name__}')

        @staticmethod
        @setup_test
        def my_setup_test(logger):
            logger.info(f'{Group1.Group2.__name__}.{Group1.Group2.my_setup_test.__name__}')

        @staticmethod
        def test_22(logger):
            logger.info(f'{Group1.Group2.__name__}.{Group1.Group2.test_22.__name__}')

    class Group3:
        @staticmethod
        @setup
        def my_setup(logger):
            logger.info(f'{Group1.Group3.__name__}.{Group1.Group3.my_setup.__name__}')

        @staticmethod
        @teardown
        def my_teardown(logger):
            logger.info(f'{Group1.Group2.__name__}.{Group1.Group3.my_teardown.__name__}')

        @staticmethod
        @teardown_test
        def my_teardown_test(logger):
            logger.info(f'{Group1.Group2.__name__}.{Group1.Group3.my_teardown_test.__name__}')

        @staticmethod
        def test_3(logger):
            logger.info(f'{Group1.Group3.__name__}.{Group1.Group3.test_3.__name__}')

        @staticmethod
        def test_33(logger):
            logger.info(f'{Group1.Group3.__name__}.{Group1.Group3.test_33.__name__}')
