import os
import unittest

from end2.pattern_matchers import (
    DefaultTestCasePatternMatcher,
    PatternMatcherBase
)
from end2.models.testing_containers import TestPackage
from end2 import discovery

from examples.simple.smoke import sample1


class TestDiscoverModule(unittest.TestCase):
    def test_module_found_and_no_error(self):
        matcher = PatternMatcherBase([], '', True)
        module, error_str = discovery.discover_module(os.path.join('examples', 'simple', 'smoke', 'sample1'), matcher)
        self.assertIsNotNone(module)
        self.assertEqual(error_str, '')

    def test_module_not_found_and_error_str(self):
        matcher = PatternMatcherBase([], '', True)
        module, error_str = discovery.discover_module(os.path.join('examples', 'dont_exist'), matcher)
        self.assertIsNone(module)
        self.assertNotEqual(error_str, '')


class TestDiscoverTests(unittest.TestCase):
    def test_discovered(self):
        matcher = DefaultTestCasePatternMatcher([], '', True)
        tests = discovery.discover_tests(sample1, matcher)
        self.assertIsNotNone(tests)

    def test_partially_discovered(self):
        matcher = DefaultTestCasePatternMatcher(['test_1', 'test_2'], '', True)
        tests = discovery.discover_tests(sample1, matcher)
        assert len(tests) == 2


class TestDiscoverParameterizedTestRange(unittest.TestCase):
    def setUp(self) -> None:
        self.x = [1, 2, 3, 4, 5, 6, 7, 8]
        return super().setUp()

    def test_no_range_defaults_to_all(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1', self.x), range(len(self.x)))

    def test_single_element(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[0]', self.x), range(0, 1))

    def test_last_to_first(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[-1:]', self.x), range(-1, len(self.x)))

    def test_all_except_last(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[:-1]', self.x), range(0, len(self.x)-1))
    
    def test_reverse_without_last(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[::-1]', self.x), range(0, len(self.x), -1))
    
    def test_start_at_1_skip_by_1_stop_after_1(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[1:1:1]', self.x), range(1, 1))

    def test_no_accessor(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[]', self.x), range(0, 0))

    def test_no_accessor_or_closing_bracket(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1[', self.x), range(0, 0))

    def test_no_opening_bracket(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1]', self.x), range(0, 0))

    def test_brackets_in_wrong_order(self):
        self.assertEqual(discovery.discover_parameterized_test_range('test_1][', self.x), range(0, 0))
