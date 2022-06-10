"""
Logging configuration.
"""

import logging
import logging.config

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
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "nexgen": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        }
    },
}

logging.config.dictConfig(logging_config)


def config(logfile: str = None, write_mode: str = "a"):
    """
    Configure the logging.

    Args:
        logfile (str, optional): If passed, create a file handler for the logger to write to file the log output. Defaults to None.
        write_mode (str, optional): String indicating writing mode for the output .log file. Defaults to "a".
    """
    nexgen_logger = logging.getLogger("nexgen")
    if logfile:
        fileFormatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s || %(message)s",
            datefmt="%d-%m-%Y %I:%M:%S",
        )
        FH = logging.FileHandler(logfile, mode=write_mode, encoding="utf-8")
        FH.setLevel(logging.DEBUG)
        FH.setFormatter(fileFormatter)
        nexgen_logger.addHandler(FH)


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
