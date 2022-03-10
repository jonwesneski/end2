import unittest

from end2.arg_parser import SuiteArg


class TestSuiteArg(unittest.TestCase):
    def test_b_path_found(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a'}, suite_aliases={'a': 'b'}, disabled_suites=[]), {'b'})

    def test_b_path_still_found(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a', 'b'}, suite_aliases={'a': 'b'}, disabled_suites=[]), {'b'})

    def test_b_and_c_paths_found(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a', 'b'}, suite_aliases={'a': 'c'}, disabled_suites=[]) ^ {'b', 'c'}, set())

    def test_a_b_c_are_all_paths(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a', 'b', 'c'}, suite_aliases={}, disabled_suites=[]) ^ {'a', 'b', 'c'}, set())

    def test_nested__a_resolves_to_b_and_c_which_resolves_to_d_and_e(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a'}, suite_aliases={'a': 'b c', 'b': 'd', 'c': 'e'}, disabled_suites=[]) ^ {'d', 'e'}, set())

    def test_disabled_suites_resolve_to_empty_path(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a'},suite_aliases= {'a': 'b'}, disabled_suites=['b']), set())

    def test_disabled_alias_but_path_still_provided_so_b_exists(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a', 'b'}, suite_aliases={'a': 'b'}, disabled_suites=['a']), {'b'})

    def test_c_path_found(self):
        self.assertEqual(SuiteArg._resolve_paths(paths={'a'}, suite_aliases={'a': 'c'}, disabled_suites=['b']) ^ {'c'}, set())
