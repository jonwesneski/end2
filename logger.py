from datetime import datetime
import inspect
import logging
from logging.handlers import MemoryHandler
import os
from pathlib import Path
import shutil
import sys

from pytz import timezone

from test_framework.enums import Status
from test_framework.popo import (
    Result,
    TestMethodResult,
    TestModuleResult
)


CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET
FOLDER = 'logs'
FAILURES_FOLDER = os.path.join(FOLDER, 'failures')


def _cdt_time(*args):
    cdt_time = datetime.fromtimestamp(args[1])
    cdt_time_zone = timezone('America/Chicago')
    converted = cdt_time.astimezone(cdt_time_zone)
    return converted.timetuple()


logging.Formatter.converter = _cdt_time


def create_file_handler(folder: str, name: str, file_level: int = logging.DEBUG, formatter=None, filter_=None):
    os.makedirs(folder, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(folder, f'{name}.log'), mode='w')
    file_handler.setLevel(file_level)
    if formatter:
        file_handler.setFormatter(formatter)
    if filter_:
        file_handler.addFilter(filter_)
    return file_handler


def create_stream_handler(stream_level: int = logging.INFO, formatter=None, filter_=None):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(stream_level)
    if formatter:
        stream_handler.setFormatter(formatter)
    if filter_:
        stream_handler.addFilter(filter_)
    return stream_handler


def create_full_logger(folder: str, name: str, stream_level: int, file_name: str = None, file_level: int = logging.DEBUG, propagate: bool = False):
    formatter = create_formatter()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_file_handler(folder, file_name or name, file_level, formatter))
    logger.addHandler(create_stream_handler(stream_level, formatter))
    logger.propagate = propagate
    return logger


def create_file_logger(name):
    formatter = create_formatter()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_file_handler(FOLDER, name, logging.DEBUG, formatter))
    return logger


def create_stream_logger(name):
    formatter = logging.Formatter(fmt='%(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_stream_handler(logging.DEBUG, formatter))
    return logger


def create_formatter(infix: str = ''):
    infix_ = f' {infix}' if infix else ''
    return logging.Formatter(fmt=f'%(asctime)s [%(levelname)s]{infix_}   %(message)s', datefmt='%Y-%m-%d %H:%M:%S CDT')


# TODO: Use this instead once I reimplement Filter() logic
def create_formatter2(use_infix: bool = False):
    infix = ' %(infix)s' if use_infix else ''
    return logging.Formatter(fmt=f'%(asctime)s [%(levelname)s]{infix}   %(message)s', datefmt='%Y-%m-%d %H:%M:%S CDT')


def create_failure_handler(filter_):
    memory_handler = CustomFlushHandler(FAILURES_FOLDER, logging.ERROR, flush_on_close=False)
    memory_handler.addFilter(filter_)
    return memory_handler


def get_log_handler(logger, handler_type):
    for handler in logger.handlers:
        if type(handler) == handler_type:
            return handler


def get_log_handler_level(logger, handler_type):
    return get_log_handler(logger, handler_type).level


class LogManager:
    """
    Used to manage logs: How many log history folders to keep and how to organize the log folders/files inside.
    """
    def __init__(self, run_logger_name: str = 'test_run', base: str = FOLDER, stream_level: int = logging.INFO):
        self.run_logger_name = run_logger_name
        self.folder = os.path.join(base, datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))
        os.makedirs(self.folder, exist_ok=True)
        self.formatter = create_formatter()
        self.test_run_logger = create_full_logger(self.folder, self.run_logger_name, stream_level, file_level=logging.INFO, propagate=False)
        self._rotate_folders(base, 10)
        self._test_separator = '\n' + ('-' * 175)
        self._module_separator = '\n' + ('=' * 175)

    @staticmethod
    def _rotate_folders(base_folder: str, max_folders: int):
        sub_folders = sorted(Path(base_folder).iterdir(), key=os.path.getmtime)
        count = len(sub_folders) - max_folders
        if count > 0:
            for i in range(count):
                shutil.rmtree(sub_folders[i])

    @staticmethod
    def _set_formatter(logger, infix):
        for handler in logger.handlers:
            handler.setFormatter(create_formatter(infix))

    @staticmethod
    def _close_file_handlers(logger):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()

    def on_setup_module_done(self, module_name: str, status: Status):
        # logger = logging.getLogger(f'{module_name}.setup')
        # TODO: Add Filter() logic
        pass

    def on_setup_test_done(self, module_name: str, test_name: str, setup_test_result: Result):
        logger = logging.getLogger(f'{module_name}.{test_name}')
        # TODO: Add Filter() logic
        if setup_test_result and setup_test_result.status == Status.SKIPPED:
            logger.critical(setup_test_result.message)
            file_hanlder = None
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    file_hanlder = handler
                    os.rename(handler.baseFilename, handler.baseFilename.replace(f'{test_name}', f'{Status.SKIPPED.upper()}_{test_name}'))
            logger.removeHandler(file_hanlder)
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.DEBUG))

    def on_test_done(self, module_name: str, test_method_result: TestMethodResult):
        self.test_run_logger.info(f'{test_method_result.status}: {module_name}::{test_method_result.name}')
        self.test_run_logger.info(self._test_separator)
        logger = logging.getLogger(f'{module_name}.{test_method_result.name}')
        self._flush_log_memory_handler(logger)
        if test_method_result.status == Status.FAILED:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    base_name = os.path.basename(handler.baseFilename)
                    os.rename(handler.baseFilename, os.path.join(self.folder, f'{Status.FAILED.upper()}_{module_name}.{base_name}'))

    def _flush_log_memory_handler(self, logger):
        for handler in logger.handlers:
            if isinstance(handler, ManualFlushHandler):
                handler.flush()
                #handler.close()

    def on_parameterized_test_done(self, module_name: str, test_name: str, parameter_result: Result):
        # logger = logging.getLogger(f'{module_name}.setup')
        # TODO: Add Filter() logic
        pass

    def on_teardown_test_done(self, module_name: str, test_name: str, teardown_test_result: Result):
        logger = logging.getLogger(f'{module_name}.{test_name}')
        # TODO: Add Filter() logic
        if teardown_test_result and teardown_test_result.status != Status.PASSED:
            logger.critical(teardown_test_result.message)

    def on_teardown_module_done(self, module_name: str, status: Status):
        # logger = logging.getLogger(f'{module_name}.teardown')
        # TODO: Add Filter() logic
        pass

    def on_module_done(self, test_module_result: TestModuleResult):
        self.test_run_logger.info(self._module_separator)
        if test_module_result.status in [Status.PASSED, Status.SKIPPED]:
            for test_result in test_module_result.test_results:
                LogManager._close_file_handlers(logging.getLogger(f'{test_module_result.name}.{test_result.name}'))
                for i in range(len(test_result.parameterized_results)):
                    LogManager._close_file_handlers(self.get_test_logger(test_module_result.name, f'{test_result.name}[{i}]'))
            for fixture_logger in [self.get_setup_logger(test_module_result.name), self.get_teardown_logger(test_module_result.name)]:
                LogManager._close_file_handlers(fixture_logger)
            os.rename(
                os.path.join(self.folder, test_module_result.name),
                os.path.join(self.folder, f'{test_module_result.status.upper()}_{test_module_result.name}'))

    def create_module_logger(self, module_name: str, test_name: str, formatter_infix: str):
        name = f'{module_name}.{test_name}'
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.setLevel(logging.DEBUG)
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.DEBUG))
            logger.addHandler(create_stream_handler())
            logger.propagate = False
            test_run_memory_handler = ManualFlushHandler(get_log_handler(self.test_run_logger, logging.FileHandler))
            logger.addHandler(test_run_memory_handler)
        LogManager._set_formatter(logger, f'{module_name.split(".")[-1]}::{formatter_infix}')
        return logger

    def get_setup_logger(self, module_name: str):
        return self.create_module_logger(module_name, 'setup', 'setup')

    def get_setup_test_logger(self, module_name: str, test_name: str):
        return self.create_module_logger(module_name, test_name, 'setup_test')

    def get_test_logger(self, module_name: str, test_name: str):
        return self.create_module_logger(module_name, test_name, test_name)

    def get_teardown_test_logger(self, module_name: str, test_name: str):
        return self.create_module_logger(module_name, test_name, 'teardown_test')

    def get_teardown_logger(self, module_name: str):
        return self.create_module_logger(module_name, 'teardown', 'teardown')


class CustomFlushHandler(logging.handlers.MemoryHandler):
    """
    This class will not flush on "shutdown" and flushes to a separate file.
    """
    def __init__(self, folder, flush_level, flush_on_close):
        super().__init__(capacity=None, flushLevel=flush_level, target=None, flushOnClose=flush_on_close)
        self.folder = folder

    def _get_test_name(self):
        for filter_ in self.filters:
            if isinstance(filter_, TestFilter) and filter_.test_name:
                return f'{filter_.name}-{filter_.test_name.replace(" ", "_")}'

    def shouldFlush(self, record):
        return record.levelno >= self.flushLevel

    def flush(self):
        if inspect.stack()[1][3] != 'shutdown' and not self.flushOnClose:
            test_name = self._get_test_name()
            if test_name:
                separate_handler = logging.FileHandler(os.path.join(self.folder, f'{test_name}.log'), mode='w')
                separate_handler.setLevel(logging.DEBUG)
                separate_handler.setFormatter(create_formatter())
                self.setTarget(separate_handler)
            super().flush()
        self.setTarget(None)


class ManualFlushHandler(logging.handlers.MemoryHandler):
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


class TestFilter(logging.Filter):
    def __init__(self, module_name):
        super().__init__(module_name.split('.')[-1])
        self._path = self.name
        self._test_name = None

    @property
    def test_name(self):
        return self._test_name

    @test_name.setter
    def test_name(self, test_name):
        if test_name and isinstance(test_name, str):
            self._test_name = test_name
            self._path = f'{self.name}::{self._test_name}'
        else:
            self._test_name = None
            self._path = self.name

    @property
    def path(self):
        return self._path

    def filter(self, record):
        # When flushing I don't wan't it to pick up the current value of self.path
        stack = inspect.stack()
        if len(stack) >= 4 and stack[3][3] != 'flush':
            record.module_method = self.path
        return True
