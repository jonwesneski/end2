import argparse
from typing import (
    Dict,
    List,
    Set
)
from end2.models.testing_containers import Importable

from end2.resource_profile import (
    get_last_run_rc,
    get_rc
)
from end2.pattern_matchers import (
    DefaultModulePatternMatcher,
    DefaultTestCasePatternMatcher,
    GlobModulePatternMatcher,
    GlobTestCasePatternMatcher,
    RegexModulePatternMatcher,
    RegexTestCasePatternMatcher,
    TagModulePatternMatcher,
    TagTestCasePatternMatcher
)


def default_parser() -> argparse.ArgumentParser:
    rc = get_rc()
    parent_parser = argparse.ArgumentParser()
    parent_parser.add_argument('--suite', nargs='*', action=SuiteFactoryAction,
                               help="""works by specifying a file path examples:
folder:
--suite folder
file:
 --suite path/to/file1.py path/to/file2.py
file-delimited:
--suite path/to/file1.py;file2.py
test-case:
--suite path/to/file1.py::test_1
test-case-delimited:
--suite path/to/file.py::test_1,test_2
excluding - anything on the right side of a '\!' will be excluded:
--suite path/to/\!file.py  # will run everything under path/to except path/to/file.py
--suite path/to/file.py::\!test_1,test_2  # will run everything under path/to/file.py except test_1 and test_2""")
    parent_parser.add_argument('--suite-glob', nargs='*', action=SuiteFactoryAction,
                               help="List of glob expression to search for tests")
    parent_parser.add_argument('--suite-regex', nargs='*', action=SuiteFactoryAction,
                               help="List of regex expression to search for tests")
    parent_parser.add_argument('--suite-tag', nargs='*', action=SuiteFactoryAction,
                               help="List of path-tags to search for tests")
    parent_parser.add_argument('--suite-last-failed', nargs=0, action=SuiteFactoryAction,
                               help="List of regex expression to search for tests")
    parent_parser.add_argument('--max-workers', type=int, default=rc['settings'].getint('max-workers'),
                               help='Total number of workers allowed to run concurrently')
    parent_parser.add_argument('--max-log-folders', type=int, default=rc['settings'].getint('max-log-folders'),
                               help='Total number of max log folders')
    parent_parser.add_argument('--no-concurrency', action='store_true', default=rc['settings'].getboolean('no-concurrency'),
                               help='Make all tests run sequentially')
    parent_parser.add_argument('--stop-on-fail', action='store_true', default=rc['settings'].getboolean('stop-on-fail'),
                               help='Make all tests run sequentially')
    parent_parser.add_argument('--event-timeout', type=float, default=rc['settings'].getfloat('event-timeout'),
                               help='Timeout value in seconds used if end() is not called in time')
    parent_parser.add_argument('--watch', action='store_true', help='Watches files matched in suite arg')
    return parent_parser


class SuiteArg:
    rc_alias = 'suite-alias'
    rc_disabled = 'suite-disabled'

    def __init__(self, paths: List[str], module_class: DefaultModulePatternMatcher, test_class: DefaultTestCasePatternMatcher) -> None:
        self.paths = []
        self.excluded_paths = []
        rc = get_rc()
        disabled_suites = list(rc[self.rc_disabled].keys())
        for path in self._resolve_paths(set(paths), rc[self.rc_alias], disabled_suites):
            paths_str, tests_str = path, ''
            if '::' in path:
                paths_str, tests_str = path.split('::')
            module_matcher = module_class.parse_str(paths_str)
            if module_matcher.included_items:
                for path in module_matcher.included_items:
                    self.paths.append(
                        Importable(path, module_matcher, test_class.parse_str(tests_str))
                    )
            else:
                self.excluded_paths.extend(module_matcher.excluded_items)
        self.excluded_paths.extend(disabled_suites)

    @staticmethod
    def _resolve_paths(paths: Set[str], suite_aliases: Dict[str, str], disabled_suites: List[str]) -> Set[str]:
        paths_ = set()
        for path in paths:
            if path not in disabled_suites:
                if path in suite_aliases:
                    paths_ |= SuiteArg._resolve_paths(
                        suite_aliases[path].split(' '), suite_aliases, disabled_suites
                    )
                else:
                    paths_.add(path)
        return paths_

    def __str__(self) -> str:
        temp_ = {
            "included_modules": self.paths,
            "excluded_modules": self.excluded_paths
        }
        return str(temp_)


class SuiteFactoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if values or option_string == '--suite-last-failed':
            arg_to_name = f"_parse_{option_string[2:].replace('-', '_')}"
            setattr(namespace, 'suite', getattr(self, arg_to_name)(values))

    def _parse_suite(self, suite: list) -> SuiteArg:
        return SuiteArg(suite, DefaultModulePatternMatcher, DefaultTestCasePatternMatcher)

    def _parse_suite_glob(self, suite: list) -> SuiteArg:
        return SuiteArg(suite, GlobModulePatternMatcher, GlobTestCasePatternMatcher)

    def _parse_suite_regex(self, suite: list) -> SuiteArg:
        return SuiteArg(suite, RegexModulePatternMatcher, RegexTestCasePatternMatcher)

    def _parse_suite_tag(self, suite: list) -> SuiteArg:
        return SuiteArg(suite, TagModulePatternMatcher, TagTestCasePatternMatcher)

    def _parse_suite_last_failed(self, _: list) -> SuiteArg:
        return self._parse_suite(get_last_run_rc()['failures'])
