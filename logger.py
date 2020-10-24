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

    @staticmethod
    def _set_formatter(logger, infix):
        for handler in logger.handlers:
            handler.setFormatter(create_formatter(infix))

    def on_test_failure(self, logger):
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                print(handler.baseFilename, 'a'*7)

    def create_module_logger(self, module_name: str, test_name: str, formatter_infix: str):
        name = f'{module_name}.{test_name}'
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.setLevel(logging.DEBUG)
            formatter = create_formatter(f'{module_name.split(".")[-1]}::{formatter_infix}')
            logger.addHandler(create_file_handler(os.path.join(self.folder, module_name), test_name, logging.INFO, formatter))
            logger.addHandler(create_stream_handler(formatter=formatter))
            logger.propagate = False
            test_run_memory_handler = ManualFlushHandler(get_log_handler(self.test_run_logger, logging.FileHandler))
            test_run_memory_handler.setFormatter(formatter)
            logger.addHandler(test_run_memory_handler)
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
