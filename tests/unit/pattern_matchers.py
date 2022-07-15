import unittest

from end2.pattern_matchers import PatternMatcherBase


class TestPatternMatcherBase(unittest.TestCase):
    def test_include_item(self):
        matcher_include = PatternMatcherBase(['a'], 'a', True)
        self.assertTrue(matcher_include.included('a'))
        self.assertFalse(matcher_include.excluded('a'))
        
    def test_include_item_no(self):
        matcher_include = PatternMatcherBase(['a'], 'a', True)
        self.assertFalse(matcher_include.included('b'))
        self.assertTrue(matcher_include.excluded('b'))

    def test_exclude_item(self):
        matcher_exclude = PatternMatcherBase(['a'], 'a', False)
        self.assertFalse(matcher_exclude.included('a'))
        self.assertTrue(matcher_exclude.excluded('a'))

    def test_exclude_item_no(self):
        matcher_exclude = PatternMatcherBase(['a'], 'a', False)
        self.assertTrue(matcher_exclude.included('b'))
        self.assertFalse(matcher_exclude.excluded('b'))
        
    def test_include_all(self):
        matcher_include = PatternMatcherBase([], '', True)
        self.assertTrue(matcher_include.included('a'))
        self.assertFalse(matcher_include.excluded('a'))

    def test_exclude_none(self):
        matcher_exclude = PatternMatcherBase(['a'], 'a', False)
        self.assertTrue(matcher_exclude.included('b'))
        self.assertFalse(matcher_exclude.excluded('b'))
