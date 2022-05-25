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


def config(logfile: str = None):
    """
    Configure the logging.

    Args:
        logfile (str, optional): If passed, create a file handler for the logger to write to file the log output. Defaults to None.
    """
    nexgen_logger = logging.getLogger("nexgen")
    if logfile:
        fileFormatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s || %(message)s",
            datefmt="%d-%m-%Y %I:%M:%S",
        )
        FH = logging.FileHandler(logfile, mode="a", encoding="utf-8")
        FH.setLevel(logging.DEBUG)
        FH.setFormatter(fileFormatter)
        nexgen_logger.addHandler(FH)
