"""
Unit tests for Brightness.cli module.

These tests verify the CLI interface using Click's testing utilities.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from Brightness.cli import main


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


# ============================================================================
# Tests for CLI operations
# ============================================================================


def test_cli_max_operation(runner):
    """CLI 'max' operation should call set_max_brightness."""
    with patch("Brightness.cli.set_max_brightness") as mock_max:
        result = runner.invoke(main, ["max"])
        assert result.exit_code == 0
        mock_max.assert_called_once()


def test_cli_min_operation(runner):
    """CLI 'min' operation should call set_min_brightness."""
    with patch("Brightness.cli.set_min_brightness") as mock_min:
        result = runner.invoke(main, ["min"])
        assert result.exit_code == 0
        mock_min.assert_called_once()


def test_cli_increase_operation(runner):
    """CLI '+' operation should call change_brightness(True)."""
    with patch("Brightness.cli.change_brightness") as mock_change:
        result = runner.invoke(main, ["+"])
        assert result.exit_code == 0
        mock_change.assert_called_once_with(True)


def test_cli_decrease_operation(runner):
    """CLI '-' operation should call change_brightness(False)."""
    with patch("Brightness.cli.change_brightness") as mock_change:
        result = runner.invoke(main, ["-"])
        assert result.exit_code == 0
        mock_change.assert_called_once_with(False)


def test_cli_invalid_operation(runner):
    """CLI with invalid operation should print error message."""
    with (
        patch("Brightness.cli.set_max_brightness") as mock_max,
        patch("Brightness.cli.set_min_brightness") as mock_min,
        patch("Brightness.cli.change_brightness") as mock_change,
    ):
        result = runner.invoke(main, ["invalid"])
        assert result.exit_code == 0
        assert "Invalid operation" in result.output
        mock_max.assert_not_called()
        mock_min.assert_not_called()
        mock_change.assert_not_called()


def test_cli_no_arguments(runner):
    """CLI with no arguments should show error."""
    result = runner.invoke(main, [])
    assert result.exit_code != 0
    assert "Missing argument" in result.output


def test_cli_help(runner):
    """CLI --help should show help message."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Operation to perform" in result.output
    assert "increase" in result.output.lower() or "+" in result.output
