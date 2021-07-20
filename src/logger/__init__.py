import logging

from .har_logger import (
    HarFileHandler,
    HarLogger
)
from .log_manager import (
    LogManager,
    SuiteLogManager
)


empty_logger = logging.getLogger('end²EMPTY')
empty_logger.propagate = False
empty_logger.disabled = True


__all__ = ['empty_logger', 'HarFileHandler', 'HarLogger', 'LogManager', 'SuiteLogManager']
