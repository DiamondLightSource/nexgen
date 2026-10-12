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
    log.close_logfiles()
    assert len(dummy_logger.handlers) == 1


def test_closes_logfile_closes_handler(dummy_logger, tmp_path):
    @log.closes_logfile
    def writer(logfile):
        handler = log.config(logfile.as_posix())
        assert handler in dummy_logger.handlers
        return handler

    handler = writer(tmp_path / "test.log")
    assert len(dummy_logger.handlers) == 1
    assert handler.stream is None


def test_closes_logfile_closes_handler_on_error(dummy_logger, tmp_path):
    @log.closes_logfile
    def writer(logfile):
        log.config(logfile.as_posix())
        raise RuntimeError

    with pytest.raises(RuntimeError):
        writer(tmp_path / "test.log")
    assert len(dummy_logger.handlers) == 1


def test_closes_logfile_nested(dummy_logger, tmp_path):
    @log.closes_logfile
    def inner():
        log.config((tmp_path / "inner.log").as_posix())

    @log.closes_logfile
    def outer():
        log.config((tmp_path / "outer.log").as_posix())
        inner()
        assert len(dummy_logger.handlers) == 2
        logging.getLogger("nexgen.test").info("after inner")

    outer()
    assert len(dummy_logger.handlers) == 1
    assert "after inner" in (tmp_path / "outer.log").read_text()
    assert "after inner" not in (tmp_path / "inner.log").read_text()
