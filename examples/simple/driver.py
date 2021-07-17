#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join('..', '..'))
from src.runner import start_test_run
from src.arg_parser import default_parser



if __name__ == '__main__':
    # Run from inside exampes\simple
    ## --suite smoke\\!ignored_module.py;sample1.py::test_ignored_test,test_2
    ## --suite smoke/!ignored_module.py;sample1.py::test_ignored_test,test_2
    ## --suite non_existent.py
    ## --suite smoke\\!ignored_module.py
    ## --suite smoke/!ignored_module.py
    ## --suite smoke\\sample1.py regression.py
    ## --suite smoke/sample1.py regression.py
    ## --suite regression\\sample4.py::test_11
    ## --suite regression/sample4.py::test_11
    ## --suite regression\\sample4.py::test_11[4]
    ## --suite regression/sample4.py::test_11[4]
    args = default_parser().parse_args()

    def test_parameters(logger_):
        return (logger_,), {}

    start_test_run(args, test_parameters)

    exit()

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=False)

    exit(test_suite_result.exit_code)
