import os
from time import sleep
import unittest

from end2 import (
    arg_parser,
    runner
)
from examples.fake_clients import run as clients


class TestStartRun(unittest.TestCase):
    def setUp(self):
        # Sleeping because I want a different timestamp folder name for each integration test
        sleep(1)

    # def test_integration_simple(self):
    #     arg_list=['--suite', os.path.join('examples', 'simple', 'regression')]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger_, package_object):
    #         return (logger_,), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     self.assertTrue(all(result.status is not None
    #                         and result.end_time is not None
    #                         and result.duration is not None
    #                         for result in results))

    # def test_integration_module(self):
    #     arg_list=['--suite', os.path.join('examples', 'simple', 'smoke', 'sample1.py'), os.path.join('examples', 'simple', 'regression')]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger_, package_object):
    #         return (logger_,), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     self.assertTrue(all(result.status is not None
    #                         and result.end_time is not None
    #                         and result.duration is not None
    #                         for result in results))

    # def test_integration_package_object(self):
    #     arg_list=['--suite', os.path.join('examples', 'package_objects', 'package1')]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger_, package_object):
    #         return (logger_, package_object), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     self.assertTrue(all(result.status is not None
    #                         and result.end_time is not None
    #                         and result.duration is not None
    #                         for result in results))

    # def test_integration_end_timeout(self):
    #     timeout = 2.0
    #     arg_list=['--suite', os.path.join('examples', 'fake_clients', 'regression', 'sample3.py::test_32'), '--event-timeout', str(timeout)]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger, package_object):
    #         return (clients.Client(logger), clients.AsyncClient(logger)), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     self.assertIn(f'time out reached: {timeout}s', results.test_modules[0].test_results[0].record)

    # def test_integration_end_timeout_async(self):
    #     timeout = 2.0
    #     arg_list=['--suite', os.path.join('examples', 'fake_clients', 'regression', 'sample3.py::test_33'), '--event-timeout', str(timeout)]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger, package_object):
    #         return (clients.Client(logger), clients.AsyncClient(logger)), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     self.assertIn(f'time out reached: {timeout}s', results.test_modules[0].test_results[0].record)

    def test_integration_step(self):
        arg_list=['--suite', os.path.join('examples', 'fake_clients', 'regression', 'sample2.py::test_21,test_22')]
        args = arg_parser.default_parser().parse_args(arg_list)

        def test_parameters(logger, package_object):
            return (clients.Client(logger), clients.AsyncClient(logger)), {}

        results, _ = runner.start_test_run(args, test_parameters)
        self.assertGreater(len(results.test_modules[0].test_results[0].steps), 0)
        self.assertGreater(len(results.test_modules[0].test_results[1].steps), 0)

    # def test_tag_pattern_matcher(self):
    #     timeout = 2.0
    #     arg_list=['--suite-tag', os.path.join('examples', 'fake_clients', 'regression', 'product,'),'--event-timeout', str(timeout)]
    #     args = arg_parser.default_parser().parse_args(arg_list)

    #     def test_parameters(logger, package_object):
    #         return (clients.Client(logger), clients.AsyncClient(logger)), {}

    #     results, _ = runner.start_test_run(args, test_parameters)
    #     test_module_names = [x.name for x in results.test_modules]
    #     self.assertNotIn('examples.fake_clients.regression.sample2', test_module_names)
    #     self.assertIn('examples.fake_clients.regression.sample3', test_module_names)
    #     self.assertEqual(results.total_count, 6)
