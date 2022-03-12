import os
import unittest

from end2 import (
    arg_parser,
    runner
)


class TestStartRun(unittest.TestCase):
    def test_integration_simple(self):
        arg_list=['--suite', os.path.join('examples', 'simple', 'regression')]
        args = arg_parser.default_parser().parse_args(arg_list)

        def test_parameters(logger_, package_object):
            return (logger_,), {}

        results, _ = runner.start_test_run(args, test_parameters)
        self.assertTrue(all(result.status is not None
                            and result.end_time is not None
                            and result.duration is not None
                            for result in results))

    def test_integration_module(self):
        arg_list=['--suite', os.path.join('examples', 'simple', 'smoke', 'sample1.py'), os.path.join('examples', 'simple', 'regression')]
        args = arg_parser.default_parser().parse_args(arg_list)

        def test_parameters(logger_, package_object):
            return (logger_,), {}

        results, _ = runner.start_test_run(args, test_parameters)
        self.assertTrue(all(result.status is not None
                            and result.end_time is not None
                            and result.duration is not None
                            for result in results))

    def test_integration_package_object(self):
        arg_list=['--suite', os.path.join('examples', 'package_objects', 'package1')]
        args = arg_parser.default_parser().parse_args(arg_list)

        def test_parameters(logger_, package_object):
            return (logger_, package_object), {}

        results, _ = runner.start_test_run(args, test_parameters)
        self.assertTrue(all(result.status is not None
                            and result.end_time is not None
                            and result.duration is not None
                            for result in results))
