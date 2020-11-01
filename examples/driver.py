#!/usr/bin/env python3
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), os.path.join('..', '..')))
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from test_framework.logger import create_full_logger
from test_framework.runner import create_test_suite_instance

a = [1, 2, 3, 4, 5, 6, 7, 8]
print(a[-1:], [a[x] for x in range(-1, 0)])
print(a[:-1], [a[x] for x in range(0, len(a)-1)])
print(a[:5], [a[x] for x in range(0, 5)])
print(a[2:], [a[x] for x in range(2, len(a))])
print(a[2:5], [a[x] for x in range(2, 5)])
print(a[2:7:2], [x for x in range(2, 7, 2)])
print(range(2, 7, 2) == range(2, 7, 2))
exit()
if __name__ == '__main__':
    # Must run from inside examples folder
    import argparse
    import logging
    from test_framework.discovery import discover_module
    from test_framework.runner import TestModuleRun

    parser = argparse.ArgumentParser()
    default=['tests.smoke.!ignored_module;sample1::test_ignored_test,test_2']
    default2=['tests.smoke.!ignored_module']
    default3=['tests.smoke.sample1', 'tests.regression']
    default4=['tests.regression.sample4::test_11[0]']
    parser.add_argument('--suites', nargs='*', default=default3)

    args = parser.parse_args()
    #print(args.suites)
    logger = logging.getLogger('bananaman')
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    run_instance, ignored_modules, failed_imports = create_test_suite_instance(args.suites, logger)
    print(failed_imports, ignored_modules)
    test_suite_result = run_instance.execute(False)
    print(test_suite_result)
    # logger = create_full_logger('test_run', stream_level=logging.INFO, file_level=logging.DEBUG)
    # run_instance = create_test_run_instance(['tests'],
    #                                         logger=logger,
    #                                         ignore=['tests.smoke.ignored_module', 'tests.smoke.sample1::test_ignored_test'],
    #                                         stop_on_first_fail=False)

    # def test_parameters(logger_):
    #     return [logger_], {}

    # run_instance.test_parameters = test_parameters
    # logger.info(f'Starting test run on: {run_instance.sequential_modules + run_instance.parallel_modules}')
    # run_instance.test_executor_engine(threads=True)

    # exit(1 if run_instance.results.failed_tests > 0 else 0)
