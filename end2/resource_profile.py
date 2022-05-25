from configparser import ConfigParser
import os

from end2.constants import Status
from end2.models.result import TestSuiteResult


_PRODUCT_NAME = 'end2'
_FILE_NAME = f'.{_PRODUCT_NAME}rc'
LAST_RUN_PATH = os.path.join('logs', f'.{_PRODUCT_NAME}lastrunrc')


def get_rc() -> ConfigParser:
    file_name = f'.{_PRODUCT_NAME}rc'
    rc = ConfigParser(comment_prefixes=('#',))
    if not rc.read(file_name):
        # Temporarily recreating with a different comment_prefix
        # so I can have comments
        rc = ConfigParser(comment_prefixes=(';',))
        rc.read_string(_create_default_rc_string())
        with open(_FILE_NAME, 'w') as configfile:
            rc.write(configfile)
        rc = ConfigParser(comment_prefixes=('#',))
        rc.read(_FILE_NAME)
    else:
        rc = _check_for_corruption(_FILE_NAME)
    return rc


_default_rc_dict = {
    'settings': {
        'max-workers': (int, 20),
        'max-log-folders': (int, 10),
        'no-concurrency': (bool, False),
        'stop-on-fail': (bool, False)
    },
    'suite-alias': {
        '# Examples': (str, ''),
        '# short_suite_name': (str, 'path/to/suite1.py path/to/another/suite2.py'),
        '# super_suite': (str, 'short_suite_name path/to/suite3.py')
    },
    'suite-disabled': {
        '# Examples': (str, ''),
        '# path/to/suite3.py': (str, 'BUG-1234'),
        '# short_suite_name': (str, 'Need to refactor stuff')
    }
}

def _create_default_rc_string() -> str:
    lines = []
    for section, options in _default_rc_dict.items():
        lines.append(f'[{section}]' + "\n")
        for k, v in options.items():
            lines.append(f"{k} = {str(v[1])}" + "\n")
        lines.append("\n")
    return ''.join(lines)


def _check_for_corruption(file_name: str) -> ConfigParser:
    corrupted = False
    rc = ConfigParser(comment_prefixes=(';',))
    rc.read(file_name)
    for section, options in _default_rc_dict.items():
        if section == 'settings':
            for k, v in options.items():
                if section in rc:
                    if not isinstance(rc[section][k], v[0]):
                        corrupted = True
                        rc[section][k] = str(v[1])
                else:
                    corrupted = True
                    rc[section] = {k: str(v[1])}
        elif section not in rc:
            corrupted = True
            rc[section] = _default_rc_dict[section]
    if corrupted:
        with open(file_name, 'w') as configfile:
            rc.write(configfile)
        rc = ConfigParser(comment_prefixes=('#',))
        rc.read(file_name)
    return rc


def create_last_run_rc(results: TestSuiteResult) -> None:
    failed_test_dict = {}
    for module in results:
        if module.status is Status.FAILED:
            if module.failed_count == module.total_count:
                failed_test_dict[module.file_name] = "All Failed"
            else:
                test_list = []
                for test in module:
                    if test.status is Status.FAILED:
                        test_list.append(test.name)
                failed_test_dict[f'{module.file_name}::{",".join(test_list)}'] = "Some failed"
    with open(LAST_RUN_PATH, 'w') as configfile:
        rc = ConfigParser()
        rc.read_dict({
            'failures': failed_test_dict
        })
        rc.write(configfile)


def get_last_run_rc() -> ConfigParser:
    rc = ConfigParser()
    if not rc.read(LAST_RUN_PATH):
        raise FileNotFoundError(LAST_RUN_PATH)
    return rc
