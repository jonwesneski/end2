
if __name__ == '__main__':
    import doctest

    from src import (
        arg_parser,
        discovery,
        runner
    )
    doctest.testmod(arg_parser, verbose=False)
    doctest.testmod(discovery, verbose=False)
    doctest.testmod(runner, verbose=False)
