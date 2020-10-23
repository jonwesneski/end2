from datetime import datetime
import inspect
import logging
from logging.handlers import MemoryHandler
import os
from pathlib import Path
import shutil
import sys

from pytz import timezone


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


def create_full_logger(folder: str, name: str, stream_level: int, file_level: int = logging.DEBUG, propagate: bool = True):
    formatter = create_formatter()
    filter_ = TestFilter(name)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    logger.addHandler(create_file_handler(folder, name, file_level, formatter, filter_))
    logger.addHandler(create_stream_handler(stream_level, formatter, filter_))
    logger.propagate = propagate
    return logger


def create_module_logger(folder: str, name: str, level):
    logger = create_full_logger(folder, name, level)

    test_run_logger = logging.getLogger('test_run')
    test_run_memory_handler = ManualFlushHandler(get_log_handler(test_run_logger, logging.FileHandler))
    logger.addHandler(test_run_memory_handler)
    return logger


def create_file_logger(name):
    formatter = create_formatter()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    os.makedirs(FOLDER, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(FOLDER, f'{name}.log'), mode='w')
    file_handler.setFormatter(formatter)
    file_handler.addFilter(TestFilter(name))
    logger.addHandler(file_handler)
    return logger


def create_simple_file_logger(name, extension='log'):
    formatter = logging.Formatter(fmt='%(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    os.makedirs(FOLDER, exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(FOLDER, f'{name}.{extension}'), mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def create_simple_stream_logger(name=''):
    formatter = logging.Formatter(fmt='%(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def create_formatter2():
    return logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(module_method)s   %(message)s', datefmt='%Y-%m-%d %H:%M:%S CDT')

def create_formatter(infix: str = ''):
    return logging.Formatter(fmt=f'%(asctime)s [%(levelname)s] {infix}   %(message)s', datefmt='%Y-%m-%d %H:%M:%S CDT')

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
    def __init__(self, run_logger_name: str = 'test_run', base: str = FOLDER, stream_level: int = logging.INFO):
        self.run_logger_name = run_logger_name
        self.folder = os.path.join(base, datetime.now().strftime("%m-%d-%Y_%H-%M-%S"))
        os.makedirs(self.folder, exist_ok=True)
        self.formatter = create_formatter()
        create_full_logger(self.folder, self.run_logger_name, stream_level, file_level=logging.INFO, propagate=False)
        self._rotate_folders(base, 10)
        self.teardown_file_handlers = []

    @staticmethod
    def _rotate_folders(base_folder: str, max_folders: int):
        sub_folders = sorted(Path(base_folder).iterdir(), key=os.path.getmtime)
        count = len(sub_folders) - max_folders
        if count > 0:
            for i in range(count):
                shutil.rmtree(sub_folders[i])

    @property
    def test_run_logger(self):
        return logging.getLogger(self.run_logger_name)

    # TODO: I think I will get rid of all filter logic and just recreate formatter
    # @staticmethod
    # def _set_log_filter(logger, test_name):
    #     for handler in logger.handlers:
    #         for filter_ in handler.filters:
    #             if type(filter_) is TestFilter:
    #                 filter_.test_name = test_name

    @staticmethod
    def _set_formatter(logger, infix):
        for handler in logger.handlers:
            handler.setFormatter(create_formatter(infix))

    def create_module_logger(self, folder: str, name: str, level):
        logger = create_full_logger(folder, name, level)
        test_run_memory_handler = ManualFlushHandler(get_log_handler(self.test_run_logger, logging.FileHandler))
        logger.addHandler(test_run_memory_handler)
        return logger

    def get_setup_logger(self, module_name: str):
        # logger = create_full_logger(folder, name, level)
        # test_run_memory_handler = ManualFlushHandler(get_log_handler(self.test_run_logger, logging.FileHandler))
        # logger.addHandler(test_run_memory_handler)
        logger = create_module_logger(self.folder, f'{module_name}.setup', logging.INFO)
        LogManager._set_formatter(logger, 'setup')
        return logger

    def get_setup_test_logger(self, module_name: str, test_name: str):
        logger = create_module_logger(self.folder, f'{module_name}.{test_name}', logging.INFO)
        LogManager._set_formatter(logger, 'setup_test')
        return logger

    def get_test_logger(self, module_name: str, test_name: str):
        # logger = logging.getLogger(f'{module_name}.{test_name}')
        # logger.filters.clear()
        logger = create_module_logger(self.folder, f'{module_name}.{test_name}', logging.INFO)
        LogManager._set_formatter(logger, test_name)
        return logger

    def get_teardown_test_logger(self, module_name: str, test_name: str):
        logger = logging.getLogger(f'{module_name}.{test_name}')
        LogManager._set_formatter(logger, 'teardown_test')
        return logger

    def get_teardown_logger(self, module_name: str):
        logger = create_module_logger(self.folder, f'{module_name}.teardown', logging.INFO)
        LogManager._set_formatter(logger, 'teardown')
        return logger


class LogManagerCustom(LogManager):
    def get_test_logger(self, module_name: str, test_name: str):
        logger = super().get_test_logger(module_name, test_name)
        self.add_setup_logs(setup_logger, logger)
        return logger

    def get_setup_logger(self, module_name: str):
        formatter = create_formatter()
        filter_ = TestFilter(name)
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        buffer_handler = NoShouldBuffer()
        buffer_handler.setLevel(logging.DEBUG)
        buffer_handler.setFormatter(formatter)
        buffer_handler.addFilter(filter_)
        logger.addHandler(buffer_handler)
        return logger

    def get_teardown_logger(self, module_name: str):
        pass

    def _add_setup_logs(self, setup_logger, test_logger):
        pass


class NoShouldBuffer(logging.handlers.BufferingHandler):
    def __init__(self):
        super().__init__(capacity=None)

    def shouldFlush(self, record):
        return False


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
