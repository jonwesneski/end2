import argparse
from configparser import ConfigParser
import configparser


def default_parser() -> argparse.ArgumentParser:
    rc = _get_rc()
    parent_parser = argparse.ArgumentParser()
    parent_parser.add_argument('--suite', nargs='*', action=SuiteFactoryAction,
                               help="""works by specifying a file path examples:
file:
 --suite path/to/file1.py path/to/file2.py
file-delimited:
--suite path/to/file1.py;file2.py
test-case:
--suite path/to/file1.py::test_1
test-case-delimited:
--suite path/to/file.py::test_1,test_2
excluding - anything on the right side of a '\!' will be excluded:
--suite path/to/!file.py  # will run everything under path/to except path/to/file.py
--suite path/to/file.py::!test_1,test_2  # will run everything under path/to/file.py except test_1 and test_2""")
    parent_parser.add_argument('--suite-glob', nargs='*', action=SuiteFactoryAction,
                               help="list of glob expression to search for tests")
    parent_parser.add_argument('--suite-regex', nargs='*', action=SuiteFactoryAction,
                               help="list of regex expression to search for tests")
    parent_parser.add_argument('--max-workers', type=int, default=rc['settings'].getint('max-workers'),
                               help='Total number of workers allowed to run concurrently')
    parent_parser.add_argument('--max-sub-folders', type=int, default=rc['settings'].getint('max-workers'),
                               help='Total number of max log folders')
    parent_parser.add_argument('--no-concurrency', action='store_true', default=rc['settings'].getboolean('no-concurrency'),
                               help='Make all tests run sequentially')
    parent_parser.add_argument('--stop-on-fail', action='store_true', default=rc['settings'].getboolean('stop-on-fail'),
                               help='Make all tests run sequentially')
    print(parent_parser.parse_args().suite)
    return parent_parser


def _get_rc() -> ConfigParser:
    file_name = 'end2.rc'
    rc = ConfigParser()
    if not rc.read(file_name):
        rc['settings'] = {
            'max-workers': 20,
            'max-sub-folders': 10,
            'no-concurrency': False,
            'stop-on-fail': False
        }
        rc['suite-aliases'] = {}
        with open(file_name, 'w') as configfile:
            rc.write(configfile)
    return rc


class SuiteFactoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '--suite':
            setattr(namespace, 'suite', self._parse_suite(values))
        elif option_string == '--suite-glob':
            setattr(namespace, 'suite', self._parse_suite_glob(values))
        elif option_string == '--suite-regex':
            setattr(namespace, 'suite', self._parse_suite_regex(values))

    def _parse_suite(self, suite: list) -> list:
        return SuiteArg(suite, ModuleIncludeExclude, TestCaseIncludeExclude)

    def _parse_suite_glob(self, suite: list) -> list:
        raise NotImplementedError()

    def _parse_suite_regex(self, suite: list) -> list:
        raise NotImplementedError()


class IncludeExclude:
    def __init__(self, items: list, include: bool):
        self._items = items
        self._include = include

    @classmethod
    def parse_str(cls, string: str, delimiter: str = ',', include: bool = True):
        return cls(string.split(delimiter), include)

    def __str__(self) -> str:
        return f"{'include' if self._include else 'exclude'}: {self._items}"

    @property
    def included_items(self):
        return self._items if self._include else []

    @property
    def excluded_items(self):
        return self._items if not self._include else []

    def included(self, item: str) -> bool:
        """
        >>> IncludeExclude.included(IncludeExclude(['a'], True), 'a')
        True
        >>> IncludeExclude.included(IncludeExclude(['a'], True), 'b')
        False
        >>> IncludeExclude.included(IncludeExclude(['a'], False), 'a')
        False
        >>> IncludeExclude.included(IncludeExclude(['a'], False), 'b')
        True
        >>> IncludeExclude.included(IncludeExclude([], True), 'a')
        True
        >>> IncludeExclude.included(IncludeExclude([], False), 'b')
        True
        """
        if item in self._items:
            value = self._include
        else:
            value = not self._include
            if not self._items:
                value = True
        return value

    def excluded(self, item: str) -> bool:
        """
        >>> IncludeExclude.excluded(IncludeExclude(['a'], True), 'a')
        False
        >>> IncludeExclude.excluded(IncludeExclude(['a'], True), 'b')
        True
        >>> IncludeExclude.excluded(IncludeExclude(['a'], False), 'a')
        True
        >>> IncludeExclude.excluded(IncludeExclude(['a'], False), 'b')
        False
        >>> IncludeExclude.excluded(IncludeExclude([], True), 'a')
        False
        >>> IncludeExclude.excluded(IncludeExclude([], False), 'b')
        False
        """
        return not self.included(item)


class ModuleIncludeExclude(IncludeExclude):
    excluder = '!'

    @classmethod
    def parse_str(cls, string: str, delimiter: str = ';', include: bool = True):
        index, include = None, True
        if string.startswith(cls.excluder):
            index = 1
            include = False
        return cls(string[index:].split(delimiter) if string else [], include)


class TestCaseIncludeExclude(ModuleIncludeExclude):
    @classmethod
    def parse_str(cls, string: str, delimiter: str = ',', include: bool = True):
        return super(TestCaseIncludeExclude, cls).parse_str(string, delimiter, include)



class SuiteArg:
    def __init__(self, paths: list, module_class: IncludeExclude, test_class: IncludeExclude):
        self.modules = {}
        self.excluded_modules = []
        for path in paths:
            modules_str, tests_str = path, ''
            if '::' in path:
                modules_str, tests_str = path.split('::')
            modules = module_class.parse_str(modules_str)
            if modules.included_items:
                self.modules = {item: test_class.parse_str(tests_str) for item in modules.included_items }
            else:
                self.excluded_modules.extend(modules.excluded_items)


    def __str__(self):
        temp_ = {
            "included_modules": {}
        }
        for k, v in self.modules.items():
            temp_["included_modules"][k] = str(v)
        temp_["excluded_modules"] = self.excluded_modules
        return str(temp_)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
