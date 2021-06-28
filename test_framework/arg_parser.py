import argparse


def default_parser() -> argparse.ArgumentParser:
    parent_parser = argparse.ArgumentParser()
    parent_parser.add_argument('--suite', nargs='*', action=SuiteFactoryAction, help="""works by specifying a file path examples:
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
    parent_parser.add_argument('--suite-glob', nargs='*', action=SuiteFactoryAction, help="list of glob expression to search for tests")
    parent_parser.add_argument('--suite-regex', nargs='*', action=SuiteFactoryAction, help="list of regex expression to search for tests")
    parent_parser.add_argument('--max-workers', type=int, defualt=20, help='Total number of workers allowed to run concurrently')
    parent_parser.add_argument('--max-sub-folders', type=int, help='Total number of max log folders')
    parent_parser.add_argument('--no-concurrency', action='store_true', help='Make all tests run sequentially')
    print(parent_parser.parse_args().suite)
    exit()
    return parent_parser


class SuiteFactoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if option_string == '--suite':
            setattr(namespace, 'suite', self._parse_suite(values))
        elif option_string == '--suite-glob':
            setattr(namespace, 'suite', self._parse_suite_glob(values))
        elif option_string == '--suite-regex':
            setattr(namespace, 'suite', self._parse_suite_regex(values))

    def _parse_suite(self, suite: list) -> list:
        return Paths(suite, ModuleIncludeExclude, TestCaseIncludeExclude)

    def _parse_suite_glob(self, suite: list) -> list:
        raise NotImplementedError()

    def _parse_suite_regex(self, suite: list) -> list:
        raise NotImplementedError()


class IncludeExclude:
    def __init__(self, items: list, include: bool):
        self.items = items
        self.include_ = include

    @classmethod
    def parse_str(cls, string: str, delimiter: str = ',', include: bool = True):
        return cls(string.split(delimiter), include)

    def __str__(self) -> str:
        return f"{'include' if self.include_ else 'exclude'}: {self.items}"

    def include(self, item: str) -> bool:
        """
        >>> IncludeExclude.include(IncludeExclude(['a'], True), 'a')
        True
        >>> IncludeExclude.include(IncludeExclude(['a'], True), 'b')
        False
        >>> IncludeExclude.include(IncludeExclude(['a'], False), 'a')
        False
        >>> IncludeExclude.include(IncludeExclude(['a'], False), 'b')
        True
        >>> IncludeExclude.include(IncludeExclude([], True), 'a')
        True
        >>> IncludeExclude.include(IncludeExclude([], False), 'b')
        True
        """
        if item in self.items:
            value = self.include_
        else:
            value = not self.include_
            if not self.items:
                value = True
        return value


class ModuleIncludeExclude(IncludeExclude):
    excluder = '!'

    @property
    def suite_modules(self):
        return self.items

    @classmethod
    def parse_str(cls, string: str, delimiter: str = ';', include: bool = True):
        index, include = None, True
        if string.startswith(cls.excluder):
            index = 1
            include = False
        return cls(string[index:].split(delimiter) if string else [], include)


class TestCaseIncludeExclude(ModuleIncludeExclude):
    @property
    def test_cases(self):
        return self.items

    @classmethod
    def parse_str(cls, string: str, delimiter: str = ',', include: bool = True):
        return super(TestCaseIncludeExclude, cls).parse_str(string, delimiter, include)


class Paths:
    def __init__(self, paths: list, module_class: IncludeExclude, test_class: IncludeExclude):
        self.suite_modules = {}
        for path in paths:
            modules_str, tests_str = path, ''
            if '::' in path:
                modules_str, tests_str = path.split('::')
            self.suite_modules[path] = {
                "module": module_class.parse_str(modules_str),
                "tests": test_class.parse_str(tests_str)
            }

    def __str__(self):
        temp_ = {}
        for k, v in self.suite_modules.items():
            temp_[k] = {
                "module": str(v['module']),
                "tests": str(v['tests'])
            }
        return str(temp_)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
