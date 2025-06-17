import argparse

import pytest

from nexgen import __version__
from nexgen.command_line.parse_utils import version_parser


def test_version():
    assert __version__


def test_version_parser(capsys):
    for flag in "-V", "--version":
        with pytest.raises(SystemExit, match="0"):
            version_parser.parse_args([flag])
        assert f"NeXus generation tools {__version__}" in capsys.readouterr().out


def test_version_parser_is_optional():
    assert version_parser.parse_args([]) == argparse.Namespace()


def test_version_parser_has_no_help_flag(capsys):
    with pytest.raises(SystemExit, match="2"):
        version_parser.parse_args(["-h"])
    assert "error: unrecognized arguments: -h" in capsys.readouterr().err
