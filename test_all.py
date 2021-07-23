import os
import traceback

from src import (
    arg_parser,
    discovery,
    logger,
    runner
)


def _test_integration_simple():
    # Can't run this way right now due to https://github.com/pytest-dev/pytest/issues/5908
    # """
    # >>> assert test_simple_e2e()
    # """
    arg_list=['--suite', os.path.join('examples', 'simple', 'smoke', 'sample1.py'), os.path.join('examples', 'simple', 'regression')]
    args = arg_parser.default_parser().parse_args(arg_list)

    def test_parameters(logger_):
        return (logger_,), {}

    results = runner.start_test_run(args, test_parameters)
    assert all(result.status is not None
               and result.end_time is not None
               and result.duration is not None
               for result in results)


if __name__ == '__main__':
    import doctest

    doctest.testmod(arg_parser, verbose=False)
    doctest.testmod(discovery, verbose=False)
    doctest.testmod(runner, verbose=False)

    for _test in [v for k, v in locals().items() if k.startswith('_test_')]:
        try:
            _test()
        except:
            print(traceback.format_exc())
            print("FAILED:", _test.__name__)
