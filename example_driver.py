#!/usr/bin/env python3
from src.runner import start_test_run
from src.arg_parser import default_parser



if __name__ == '__main__':
    temp_args0=['--suite', 'example_tests\\smoke\\!ignored_module.py;sample1.py::test_ignored_test,test_2']
    temp_args1=['--suite', 'example_tests.py']
    temp_args2=['--suite', 'example_tests\\smoke\\!ignored_module.py']
    temp_args3=['--suite', 'example_tests\\smoke\\sample1.py', 'example_tests\\regression.py']
    temp_args4=['--suite', 'example_tests\\regression\\sample4.py::test_11']
    temp_args5=['--suite', 'example_tests\\regression\\sample4.py::test_11[4]']
    args = default_parser().parse_args()

    def test_parameters(logger_):
        return (logger_,), {}

    start_test_run(args, test_parameters)

    exit()

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=False)

    exit(test_suite_result.exit_code)
