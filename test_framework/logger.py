from datetime import datetime
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


def _cdt_time(*args):
    cdt_time = datetime.fromtimestamp(args[1])
    cdt_time_zone = timezone('America/Chicago')
    converted = cdt_time.astimezone(cdt_time_zone)
    return converted.timetuple()


logging.Formatter.converter = _cdt_time


def create_file_handler(folder: str, name: str, file_level: int = logging.DEBUG, filter_:logging.Filter = None, mode: str = 'w'):
    os.makedirs(folder, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(folder, f'{name}.log'), mode=mode)
    file_handler.setLevel(file_level)
    if filter_:
        file_handler.addFilter(filter_)
        file_handler.setFormatter(_FILTER_FORMATTER)
    else:
        file_handler.setFormatter(_FORMATTER)
    return file_handler


def create_stream_handler(stream_level: int = logging.INFO, filter_:logging.Filter = None):
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(stream_level)
    if filter_:
        stream_handler.addFilter(filter_)
        stream_handler.setFormatter(_FILTER_FORMATTER)
    else:
        stream_handler.setFormatter(_FORMATTER)
    return stream_handler


def create_full_logger(folder: str, name: str, stream_level: int, file_name: str = None,
                       file_level: int = logging.DEBUG, filter_:logging.Filter = None,  propagate: bool = False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_file_handler(folder, file_name or name, file_level, filter_, mode='a+'))
    logger.addHandler(create_stream_handler(stream_level, filter_))
    logger.propagate = propagate
    return logger


def create_file_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_file_handler(FOLDER, name, logging.DEBUG))
    return logger


def create_stream_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(create_stream_handler(logging.DEBUG))
    return logger


def get_log_handler(logger, handler_type):
    for handler in logger.handlers:
        if type(handler) == handler_type:
            return handler


class LogManager:
    """
    Used to manage logs: How many log history folders to keep and how to organize the log folders/files inside.
    """
    def __init__(self, run_logger_name: str = 'test_run', base: str = FOLDER, stream_level: int = logging.INFO):
        self.run_logger_name = run_logger_name
        self.folder = os.path.join(base, datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))
        os.makedirs(self.folder, exist_ok=True)
        self.filter = InfixFilter(self.run_logger_name)
        self.test_run_logger = create_full_logger(self.folder, self.run_logger_name, stream_level, file_level=logging.INFO, filter_=self.filter, propagate=False)
        self.test_run_file_handler = get_log_handler(self.test_run_logger, logging.FileHandler)
        self._rotate_folders(base, 10)
        self._test_terminator = '\n' + ('-' * 175)
        self._module_terminator = '\n' + ('=' * 175)

    @staticmethod
    def _rotate_folders(base_folder: str, max_folders: int):
        sub_folders = sorted(Path(base_folder).iterdir(), key=os.path.getmtime)
        count = len(sub_folders) - max_folders
        if count > 0:
            for i in range(count):
                shutil.rmtree(sub_folders[i])

    @staticmethod
    def _close_file_handlers(logger):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()

    def _log_test_run_message(self, message):
        # TODO: This sometimes cause logging issues with logging parallel tests since I am adding and removing the same file handler
        # test1-> addHandler
        # test2-> addHandler
        # test2-> write message
        # test2-> remove handler
        # test1-> write message; but handler no longer exists
        self.test_run_logger.addHandler(self.test_run_file_handler)
        self.test_run_logger.info(message)
        self.test_run_logger.removeHandler(self.test_run_file_handler)

    def _change_filter_name(self, logger, name):
        for handler in logger.handlers:
            for filter in handler.filters:
                filter.name = name

    def on_suite_start(self):
        LogManager._close_file_handlers(self.test_run_logger)
        self.test_run_logger.removeHandler(self.test_run_file_handler)

    def on_suite_stop(self, suite_result: TestSuiteResult):
        self._log_test_run_message(str(suite_result))

    def on_setup_module_done(self, module_name: str, result: Result):
        logger = logging.getLogger(f'{module_name}.setup')
        if result and result.status == Status.SKIPPED:
            self._log_test_run_message(f'Skipping all tests: {result.message}')
        self._flush_log_memory_handler(logger)
        LogManager._close_file_handlers(logger)

    def on_setup_test_done(self, module_name: str, test_name: str, setup_test_result: Result):
        logger = logging.getLogger(f'{module_name}.{test_name}')
        if setup_test_result and setup_test_result.status == Status.SKIPPED:
            logger.critical(setup_test_result.message)
            file_handler = None
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    file_handler = handler
                    os.rename(handler.baseFilename, handler.baseFilename.replace(f'{test_name}', f'{Status.SKIPPED.upper()}_{test_name}'))
            logger.removeHandler(file_handler)
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.DEBUG))

    def on_test_done(self, module_name: str, test_method_result: TestMethodResult):
        logger = logging.getLogger(f'{module_name}.{test_method_result.name}')
        self._flush_log_memory_handler(logger)
        self._log_test_run_message(f'{test_method_result.status}: {module_name}::{test_method_result.name}{self._test_terminator}')
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

    def on_parameterized_test_done(self, module_name: str, parameter_result: Result):
        self.on_test_done(module_name, parameter_result)

    def on_teardown_test_done(self, module_name: str, test_name: str, teardown_test_result: Result):
        logger = logging.getLogger(f'{module_name}.{test_name}')
        if teardown_test_result and teardown_test_result.status != Status.PASSED:
            logger.critical(teardown_test_result.message)
        self._flush_log_memory_handler(logger)

    def on_teardown_module_done(self, module_name: str, result: Result):
        logger = logging.getLogger(f'{module_name}.teardown')
        if result and result.status == Status.FAILED:
            self._log_test_run_message(f'Teardown Failed: {result.message}')
        self._flush_log_memory_handler(logger)
        LogManager._close_file_handlers(logger)

    def on_module_done(self, test_module_result: TestModuleResult):
        if test_module_result.status in [Status.PASSED, Status.SKIPPED]:
            for test_result in test_module_result.test_results:
                LogManager._close_file_handlers(logging.getLogger(f'{test_module_result.name}.{test_result.name}'))
                for result in test_result.parameterized_results:
                    LogManager._close_file_handlers(self.get_test_logger(test_module_result.name, result.name))
            for fixture_logger in [self.get_setup_logger(test_module_result.name), self.get_teardown_logger(test_module_result.name)]:
                LogManager._close_file_handlers(fixture_logger)
                self._flush_log_memory_handler(fixture_logger)
            os.rename(
                os.path.join(self.folder, test_module_result.name),
                os.path.join(self.folder, f'{test_module_result.status.upper()}_{test_module_result.name}'))
        self._log_test_run_message(f'{test_module_result}{self._module_terminator}')

    def get_setup_logger(self, module_name: str) -> logging.Logger:
        return self.create_logger(module_name, 'setup', 'setup')

    def get_setup_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        return self.create_logger(module_name, test_name, 'setup_test')

    def get_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        return self.create_logger(module_name, test_name, test_name)

    def get_teardown_test_logger(self, module_name: str, test_name: str) -> logging.Logger:
        return self.create_logger(module_name, test_name, 'teardown_test')

    def get_teardown_logger(self, module_name: str) -> logging.Logger:
        return self.create_logger(module_name, 'teardown', 'teardown')

    def create_logger(self, module_name: str, test_name: str, formatter_infix: str) -> logging.Logger:
        name = f'{module_name}.{test_name}'
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            filter_ = InfixFilter(f'{module_name.split(".")[-1]}::{formatter_infix}')
            logger.setLevel(logging.DEBUG)
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.DEBUG, filter_=filter_))
            logger.addHandler(create_stream_handler(filter_=filter_))
            logger.propagate = False
            test_run_memory_handler = ManualFlushHandler(
                create_file_handler(self.folder, self.run_logger_name, logging.INFO, filter_=filter_, mode='a+')
            )
            test_run_memory_handler.setFormatter(_FILTER_FORMATTER)
            test_run_memory_handler.addFilter(filter_)
            logger.addHandler(test_run_memory_handler)
        else:
            self._change_filter_name(logger, f'{module_name.split(".")[-1]}::{formatter_infix}')
        return logger


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


class InfixFilter(logging.Filter):
    def filter(self, record):
        record.infix = self.name
        return True
