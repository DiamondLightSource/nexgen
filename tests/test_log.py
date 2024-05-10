import logging
from unittest.mock import MagicMock

import pytest

from nexgen import log


@pytest.fixture
def dummy_logger():
    logger = logging.getLogger("nexgen")
    yield logger


def test_basic_logging_config(dummy_logger):
    assert dummy_logger.hasHandlers() is True
    assert len(dummy_logger.handlers) == 1
    assert dummy_logger.handlers[0].level == logging.INFO


def test_logging_config_with_filehandler(dummy_logger):
    logfile = MagicMock()
    log.config(logfile, delayed=True)
    assert len(dummy_logger.handlers) == 2
    assert dummy_logger.handlers[1].level == logging.DEBUG
    # Clear FileHandler to avoid other tests failing if open
    dummy_logger.removeHandler(dummy_logger.handlers[1])
