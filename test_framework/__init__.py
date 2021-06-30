from .fixtures import (
    metadata,
    setup,
    setup_test,
    teardown,
    teardown_test
)


if __name__ == '__main__':
    import doctest

    import arg_parser
    import discovery
    doctest.testmod(arg_parser, verbose=False)
    doctest.testmod(discovery, verbose=False)
