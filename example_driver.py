#!/usr/bin/env python3
from test_framework.runner import create_test_suite_instance


if __name__ == '__main__':
    # Must run from inside examples folder
    import argparse
    import logging
    from test_framework.discovery import discover_module
    from test_framework.runner import TestModuleRun

    parser = argparse.ArgumentParser()
    default=['example_tests.smoke.!ignored_module;sample1::test_ignored_test,test_2']
    default2=['example_tests.smoke.!ignored_module']
    default3=['example_tests.smoke.sample1', 'example_tests.regression']
    default4=['example_tests.regression.sample4::test_11[4]']
    parser.add_argument('--suites', nargs='*', default=default4)

    args = parser.parse_args()
    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites)
    print(failed_imports, ignored_modules)
    test_suite_result = run_instance.execute(False)
    print(test_suite_result)

    # def test_parameters(logger_):
    #     return [logger_], {}

    # run_instance.test_parameters = test_parameters
    # logger.info(f'Starting test run on: {run_instance.sequential_modules + run_instance.parallel_modules}')
    # run_instance.test_executor_engine(parallel=True)

    # exit(1 if run_instance.results.failed_tests > 0 else 0)
