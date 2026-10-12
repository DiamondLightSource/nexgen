"""
Logging configuration.
"""

import functools
import logging
import logging.config

import nexgen

# Logging set up
logging.getLogger("nexgen").addHandler(logging.NullHandler())

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "class": "logging.Formatter",
            "format": "%(levelname)s - %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "nexgen": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        }
    },
}

logging.config.dictConfig(logging_config)


# File handlers opened by config(), so that they can be closed again
_file_handlers: list[logging.FileHandler] = []


def config(
    logfile: str = None, write_mode: str = "a", delayed: bool = False
) -> logging.FileHandler | None:
    """
    Configure the logging.

    Any log file opened here stays open until closed with close_logfiles, or
    by a function decorated with closes_logfile returning.

    Args:
        logfile (str, optional): If passed, create a file handler for the logger to write to file the log output. Defaults to None.
        write_mode (str, optional): String indicating writing mode for the output .log file. Defaults to "a".
        delayed (bool, optional): Setting for the FileHandler delay option. If true, then file opening is deferred until the first call\
            to `emit`.Defaults to False.
    """
    nexgen_logger = logging.getLogger("nexgen")
    nexgen_logger.info(f"Using nexgen {nexgen.__version__}")
    if logfile:
        fileFormatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s || %(message)s",
            datefmt="%d-%m-%Y %I:%M:%S",
        )
        FH = logging.FileHandler(
            logfile, mode=write_mode, encoding="utf-8", delay=delayed
        )
        FH.setLevel(logging.DEBUG)
        FH.setFormatter(fileFormatter)
        nexgen_logger.addHandler(FH)
        _file_handlers.append(FH)
        return FH
    return None


def close_logfiles(keep: int = 0):
    """
    Remove and close log file handlers opened by config.

    Args:
        keep (int, optional): Number of the earliest opened handlers to leave open. Defaults to 0.
    """
    nexgen_logger = logging.getLogger("nexgen")
    while len(_file_handlers) > keep:
        handler = _file_handlers.pop()
        nexgen_logger.removeHandler(handler)
        handler.close()


def closes_logfile(func):
    """
    Decorator to close any log file opened by config while the function runs.

    Without this, every call to a writer leaves another open file handler
    attached to the nexgen logger, which leaks file descriptors in
    long-running processes and sends later output to earlier log files.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        n_open = len(_file_handlers)
        try:
            return func(*args, **kwargs)
        finally:
            close_logfiles(keep=n_open)

    return wrapper


class LoggingContext:
    """
    Define a basic context manager for selective logging.
    See https://docs.python.org/3/howto/logging-cookbook.html#using-a-context-manager-for-selective-logging.
    """

    def __init__(self, logger, level=None):
        self.logger = logging.getLogger(logger) if isinstance(logger, str) else logger
        self.level = level

    def __enter__(self):
        if self.level is not None:
            self.old_level = self.logger.level
            self.logger.setLevel(self.level)

    def __exit__(self, et, ev, tb):
        if self.level is not None:
            self.logger.setLevel(self.old_level)
        # implicit return of None => don't swallow exceptions
