#!/usr/bin/env python3
from test_framework.runner import create_test_suite_instance


if __name__ == '__main__':
    # Must run from inside examples folder
    import argparse

    parser = argparse.ArgumentParser()
    default=['example_tests.smoke.!ignored_module;sample1::test_ignored_test,test_2']
    default2=['example_tests.smoke.!ignored_module']
    default3=['example_tests.smoke.sample1', 'example_tests.regression']
    default4=['example_tests.regression.sample4::test_11']
    default5=['example_tests.regression.sample4::test_11[4]']
    parser.add_argument('--suites', nargs='*', default=default4)
    args = parser.parse_args()

    def test_parameters(logger_):
        return (logger_,), {}

    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, test_parameters_func=test_parameters)
    test_suite_result = run_instance.execute(parallel=False)

    exit(1 if run_instance.suite_result.failed_count > 0 else 0)
