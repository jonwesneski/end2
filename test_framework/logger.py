from datetime import datetime
import logging
from logging.handlers import MemoryHandler
import os
import platform
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys

# from pytz import timezone

from test_framework.enums import Status
from test_framework.popo import (
    Result,
    TestMethodResult,
    TestModuleResult,
    TestSuiteResult
)


CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET
FOLDER = 'logs'
_DATEFORMAT = '%Y-%m-%d %H:%M:%S CDT'
_FORMATTER = logging.Formatter(fmt=f'%(asctime)s [%(levelname)s]   %(message)s', datefmt=_DATEFORMAT)
_FILTER_FORMATTER = logging.Formatter(fmt=f'%(asctime)s [%(levelname)s] %(infix)s   %(message)s', datefmt=_DATEFORMAT)
try:
    _MAX_SUB_FOLDERS = int(os.getenv('AUTOMATION_LOGS_SUB_FOLDER_COUNT'))
except:
    _MAX_SUB_FOLDERS = 10


empty_logger = logging.getLogger('EMPTY')
empty_logger.propagate = False
empty_logger.disabled = True


def get_terminal_size():
        """ getTerminalSize()
         - get width and height of console
         - works on linux,os x,windows,cygwin(windows)
         originally retrieved from:
         http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
        """
        current_os = platform.system()
        tuple_xy = None
        if current_os == 'Windows':
            tuple_xy = _get_terminal_size_windows()
            if tuple_xy is None:
                tuple_xy = _get_terminal_size_tput()
                # needed for window's python in cygwin's xterm!
        if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
            tuple_xy = _get_terminal_size_linux()
        if tuple_xy is None:
            print()
            "default"
            tuple_xy = (80, 25)  # default value
        return tuple_xy

def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
                left, top, right, bottom,
                maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass

def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass

def _get_terminal_size_linux():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])


_COLUMN_SIZE = get_terminal_size()[0]



def create_file_handler(folder: str, name: str, file_level: int = logging.DEBUG, filter_: logging.Filter = None, mode: str = 'w') -> logging.FileHandler:
    os.makedirs(folder, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(folder, f'{name}.log'), mode=mode)
    file_handler.setLevel(file_level)
    if filter_:
        file_handler.addFilter(filter_)
        file_handler.setFormatter(_FILTER_FORMATTER)
    else:
        file_handler.setFormatter(_FORMATTER)
    return file_handler


def create_stream_handler(stream_level: int = logging.INFO, filter_: logging.Filter = None) -> logging.StreamHandler:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(stream_level)
    if filter_:
        stream_handler.addFilter(filter_)
        stream_handler.setFormatter(_FILTER_FORMATTER)
    else:
        stream_handler.setFormatter(_FORMATTER)
    return stream_handler


def create_full_logger(name: str, base_folder: str = FOLDER, stream_level: int = logging.INFO) -> logging.Logger:
    return LogManager(name, base_folder, stream_level).logger


def create_file_logger(name: str, base_folder: str = FOLDER) -> logging.Logger:
    return LogManager(name, base_folder).create_file_logger(name)


def create_stream_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_stream_handler(logging.DEBUG))
    return logger


def get_log_handler(logger: logging.Logger, handler_type: type) -> logging.Handler:
    for handler in logger.handlers:
        if type(handler) == handler_type:
            return handler


class LogManager:
    def __init__(self, logger_name, base_folder: str = FOLDER, stream_level: int = logging.INFO, mode: str = 'w'):
        self.logger_name = logger_name
        self._create_folder(base_folder)
        self._rotate(base_folder)
        self.logger = self.create_full_logger(self.logger_name, stream_level, mode)

    def _create_folder(self, base_folder: str):
        self.folder = os.path.join(base_folder, datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))
        os.makedirs(self.folder, exist_ok=True)

    def _rotate(self, base_folder: str):
        sub_folders = sorted([x for x in Path(base_folder).iterdir() if x.is_dir()], key=os.path.getmtime)
        count = len(sub_folders) - _MAX_SUB_FOLDERS
        if count > 0:
            for i in range(count):
                shutil.rmtree(sub_folders[i])

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(f'{self.folder}.{name}')

    def create_full_logger(self, name: str, stream_level: int = logging.INFO, mode='w') -> logging.Logger:
        logger = self.get_logger(name)
        if not logger.hasHandlers():
            filter_ = InfixFilter(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(create_file_handler(self.folder, name, logging.DEBUG, filter_=filter_, mode=mode))
            logger.addHandler(create_stream_handler(stream_level, filter_))
            logger.propagate = False
        return logger

    def create_file_logger(self, name: str) -> logging.Logger:
        logger = self.get_logger(name)
        if not logger.hasHandlers():
            filter_ = InfixFilter(name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(create_file_handler(self.folder, name, logging.DEBUG, filter_=filter_))
            logger.propagate = False
        return logger


class SuiteLogManager(LogManager):
    """
    Used to manage logs: How many log history folders to keep and how to organize the log folders/files inside.
    """
    def __init__(self, run_logger_name: str = 'suite_run', base_folder: str = FOLDER, stream_level: int = logging.INFO):
        super().__init__(run_logger_name, base_folder, stream_level, mode='a+')
        self.test_run_file_handler = get_log_handler(self.logger, logging.FileHandler)
        self._test_terminator = '\n' + ('-' * _COLUMN_SIZE)
        self._module_terminator = '\n' + ('=' * _COLUMN_SIZE)

    @staticmethod
    def _close_file_handlers(logger: logging.Logger):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                if os.path.exists(handler.baseFilename) and os.stat(handler.baseFilename).st_size == 0:
                    os.remove(handler.baseFilename)

    @staticmethod
    def _change_filter_name(logger: logging.Logger, name: str):
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                for filter in handler.filters:
                    filter.name = name

    def _add_flush_handler(self, logger: logging.Logger, filter_name: str):
        filter_ = InfixFilter(filter_name)
        test_run_memory_handler = ManualFlushHandler(
            #self.test_run_file_handler
            create_file_handler(self.folder, self.logger_name, logging.INFO, filter_=filter_, mode='a+')
        )
        test_run_memory_handler.setFormatter(_FILTER_FORMATTER)
        test_run_memory_handler.addFilter(filter_)
        logger.addHandler(test_run_memory_handler)

    @staticmethod
    def _flush_and_close_log_memory_handler(logger: logging.Logger, infix_name: str):
        handler_ = None
        for handler in logger.handlers:
            if isinstance(handler, ManualFlushHandler) and handler.filters[0].name == infix_name:
                handler.flush()
                handler.close()
                handler_ = handler
                break
        logger.removeHandler(handler_)

    def _get_logger(self, module_name: str, test_name: str, formatter_infix: str = None) -> tuple:
        logger = self.get_logger(f'{module_name}.{test_name}')
        infix_name = f'{module_name.split(".")[-1]}::{formatter_infix or test_name}'
        if not logger.hasHandlers():
            filter_ = InfixFilter(infix_name)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(create_file_handler(
                os.path.join(self.folder, module_name), test_name.replace(' ', '_'),
                logging.DEBUG,
                filter_=filter_))
            logger.addHandler(create_stream_handler(filter_=filter_))
        return logger, infix_name

    def on_suite_start(self, suite_name: str):
        pass

    def on_module_start(self, module_name: str):
        pass

    def on_setup_module_done(self, module_name: str, result: Result):
        logger, infix_name = self._get_logger(module_name, 'setup')
        self._flush_and_close_log_memory_handler(logger, infix_name)
        if result and result.status is Status.SKIPPED:
            self.logger.critical(f'Setup Skipping all tests in {module_name}')
        self._close_file_handlers(logger)

    def on_setup_test_done(self, module_name: str, test_name: str, setup_test_result: Result):
        logger, infix_name = self._get_logger(module_name, test_name, 'setup_test')
        self._flush_and_close_log_memory_handler(logger, infix_name)
        if setup_test_result and setup_test_result.status is Status.SKIPPED:
            logger.critical(f'Setup Test Failed; skipping {test_name}')
            file_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    file_handler = handler
                    os.rename(handler.baseFilename, handler.baseFilename.replace(f'{test_name}', f'{Status.SKIPPED.upper()}_{test_name}'))
            logger.removeHandler(file_handler)
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.DEBUG))

    def on_test_done(self, module_name: str, test_method_result: TestMethodResult):
        logger, infix_name = self._get_logger(module_name, test_method_result.name)
        self._flush_and_close_log_memory_handler(logger, infix_name)

    def on_parameterized_test_done(self, module_name: str, parameter_result: TestMethodResult):
        self.on_test_done(module_name, parameter_result)
        if parameter_result.status is Status.FAILED:
            self._move_failed_test(module_name, self._get_logger(module_name, parameter_result.name)[0])
        self.logger.info(f'{module_name}::{parameter_result}{self._test_terminator}')

    def _move_failed_test(self, module_name: str, logger: logging.Logger):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                base_name = os.path.basename(handler.baseFilename)
                os.rename(handler.baseFilename, os.path.join(self.folder, f'{Status.FAILED.upper()}_{module_name}.{base_name}'))

    def on_teardown_test_done(self, module_name: str, test_name: str, teardown_test_result: Result):
        logger, infix_name = self._get_logger(module_name, test_name, 'teardown_test')
        self._flush_and_close_log_memory_handler(logger, infix_name)
        if teardown_test_result and teardown_test_result.status != Status.PASSED:
            self.logger.critical(f'Teardown Test Failed for {test_name}')

    def on_test_execution_done(self, module_name: str, test_method_result: TestMethodResult):
        logger, _ = self._get_logger(module_name, test_method_result.name, test_method_result.name)
        if test_method_result.status is Status.FAILED:
            self._move_failed_test(module_name, logger)
        self._close_file_handlers(logger) 
        self.logger.info(f'{module_name}::{test_method_result}{self._test_terminator}')

    def on_teardown_module_done(self, module_name: str, result: Result):
        logger, infix_name = self._get_logger(module_name, 'teardown')
        self._flush_and_close_log_memory_handler(logger, infix_name)
        if result and result.status is Status.FAILED:
            self.logger.critical(f'Teardown Module Failed for {module_name}')
        self._close_file_handlers(logger)

    def on_module_done(self, test_module_result: TestModuleResult):
        if test_module_result.status in [Status.PASSED, Status.SKIPPED]:
            for test_result in test_module_result.test_results:
                self._close_file_handlers(self._get_logger(test_module_result.name, test_result.name)[0])
            os.rename(
                os.path.join(self.folder, test_module_result.name),
                os.path.join(self.folder, f'{test_module_result.status.upper()}_{test_module_result.name}'))
        self.logger.info(f'{test_module_result}{self._module_terminator}')

    def on_suite_stop(self, suite_result: TestSuiteResult):
        self.logger.info(str(suite_result))

    def get_setup_logger(self, module_name: str) -> logging.Logger:
        logger, infix_name = self._get_logger(module_name, 'setup')
        self._add_flush_handler(logger, infix_name)
        return logger

    def get_setup_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        logger, infix_name = self._get_logger(module_name, test_name, 'setup_test')
        self._add_flush_handler(logger, infix_name)
        return logger

    def get_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        logger, infix_name = self._get_logger(module_name, test_name)
        self._add_flush_handler(logger, infix_name)
        self._change_filter_name(logger, infix_name)
        return logger

    def get_teardown_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        logger, infix_name = self._get_logger(module_name, test_name, 'teardown_test')
        self._add_flush_handler(logger, infix_name)
        self._change_filter_name(logger, infix_name)
        return logger

    def get_teardown_logger(self, module_name: str) -> logging.Logger:
        logger, infix_name = self._get_logger(module_name, 'teardown')
        self._add_flush_handler(logger, infix_name)
        return logger


class ManualFlushHandler(MemoryHandler):
    """
    This class will only flush on close; also emits at log level or above.
    """
    def __init__(self, target, emit_level=logging.INFO):
        super().__init__(capacity=None, target=target)
        self.emit_level = emit_level

    def emit(self, record):
        if record.levelno >= self.emit_level:
            super().emit(record)

    def shouldFlush(self, record):
        return False


class InfixFilter(logging.Filter):
    def filter(self, record):
        record.infix = self.name
        return True
