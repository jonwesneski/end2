#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join('..', '..'))
from end2.runner import start_test_run
from end2.arg_parser import default_parser



if __name__ == '__main__':
    # Run from inside examples\simple
    ## --suite package1
    args = default_parser().parse_args()

    def test_parameters(logger, package_object):
        return (logger, package_object), {}

    test_suite_result, failed_imports = start_test_run(args, test_parameters)
    print(test_suite_result, failed_imports)
    exit(test_suite_result.exit_code)
