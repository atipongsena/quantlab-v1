"""Tests for CLI dispatch and commands."""

from apps.cli.main import app


def test_cli_help_and_doctor() -> None:
    assert app(["--help"]) == 0
    assert app(["doctor", "--offline"]) == 0
