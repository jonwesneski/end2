import argparse

from end2.resource_profile import (
    get_last_run_rc,
    get_rc
)
from end2.pattern_matchers import (
    PatternMatcherBase,
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
                               help="list of glob expression to search for tests")
    parent_parser.add_argument('--suite-regex', nargs='*', action=SuiteFactoryAction,
                               help="list of regex expression to search for tests")
    parent_parser.add_argument('--suite-tag', nargs='*', action=SuiteFactoryAction,
                               help="list of path-tags to search for tests")
    parent_parser.add_argument('--suite-last-failed', nargs=0, action=SuiteFactoryAction,
                               help="list of regex expression to search for tests")
    parent_parser.add_argument('--max-workers', type=int, default=rc['settings'].getint('max-workers'),
                               help='Total number of workers allowed to run concurrently')
    parent_parser.add_argument('--max-log-folders', type=int, default=rc['settings'].getint('max-log-folders'),
                               help='Total number of max log folders')
    parent_parser.add_argument('--no-concurrency', action='store_true', default=rc['settings'].getboolean('no-concurrency'),
                               help='Make all tests run sequentially')
    parent_parser.add_argument('--stop-on-fail', action='store_true', default=rc['settings'].getboolean('stop-on-fail'),
                               help='Make all tests run sequentially')
    return parent_parser


class SuiteFactoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values or option_string == '--suite-last-failed':
            arg_to_name = f"_parse_{option_string[2:].replace('-', '_')}"
            setattr(namespace, 'suite', getattr(self, arg_to_name)(values))

    def _parse_suite(self, suite: list):
        return SuiteArg(suite, DefaultModulePatternMatcher, DefaultTestCasePatternMatcher)

    def _parse_suite_glob(self, suite: list):
        return SuiteArg(suite, GlobModulePatternMatcher, GlobTestCasePatternMatcher)

    def _parse_suite_regex(self, suite: list):
        return SuiteArg(suite, RegexModulePatternMatcher, RegexTestCasePatternMatcher)

    def _parse_suite_tag(self, suite: list):
        return SuiteArg(suite, TagModulePatternMatcher, TagTestCasePatternMatcher)

    def _parse_suite_last_failed(self, _: list):
        return self._parse_suite(get_last_run_rc()['failures'])


class SuiteArg:
    rc_alias = 'suite-alias'
    rc_disabled = 'suite-disabled'

    def __init__(self, paths: list, module_class: PatternMatcherBase, test_class: PatternMatcherBase):
        self.modules = {}
        self.excluded_modules = []
        rc = get_rc()
        disabled_suites = list(rc[self.rc_disabled].keys())
        for path in self._resolve_paths(set(paths), rc[self.rc_alias], disabled_suites):
            modules_str, tests_str = path, ''
            if '::' in path:
                modules_str, tests_str = path.split('::')
            modules = module_class.parse_str(modules_str)
            if modules.included_items:
                for item in modules.included_items:
                    self.modules[item] = test_class.parse_str(tests_str)
            else:
                self.excluded_modules.extend(modules.excluded_items)
        self.excluded_modules.extend(disabled_suites)

    @staticmethod
    def _resolve_paths(paths: set, suite_aliases: dict, disabled_suites: list) -> set:
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

    def __str__(self):
        temp_ = {
            "included_modules": {}
        }
        for k, v in self.modules.items():
            temp_["included_modules"][k] = str(v)
        temp_["excluded_modules"] = self.excluded_modules
        return str(temp_)
