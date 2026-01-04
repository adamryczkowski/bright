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
        mock_max.return_value = (19, (255, 255, 255))
        result = runner.invoke(main, ["max"])
        assert result.exit_code == 0
        mock_max.assert_called_once()
        assert "Level: 19" in result.output


def test_cli_min_operation(runner):
    """CLI 'min' operation should call set_min_brightness."""
    with patch("Brightness.cli.set_min_brightness") as mock_min:
        mock_min.return_value = (9, (100, 50, 0))
        result = runner.invoke(main, ["min"])
        assert result.exit_code == 0
        mock_min.assert_called_once()
        assert "Level: 9" in result.output


def test_cli_increase_operation(runner):
    """CLI '+' operation should call change_brightness(True)."""
    with patch("Brightness.cli.change_brightness") as mock_change:
        mock_change.return_value = (15, (200, 100, 50))
        result = runner.invoke(main, ["+"])
        assert result.exit_code == 0
        mock_change.assert_called_once_with(True, no_keyboard=False)
        assert "Level: 15" in result.output


def test_cli_decrease_operation(runner):
    """CLI '-' operation should call change_brightness(False)."""
    with patch("Brightness.cli.change_brightness") as mock_change:
        mock_change.return_value = (10, (150, 75, 25))
        result = runner.invoke(main, ["-"])
        assert result.exit_code == 0
        mock_change.assert_called_once_with(False, no_keyboard=False)
        assert "Level: 10" in result.output


def test_cli_invalid_operation(runner):
    """CLI with invalid operation should return non-zero exit code and show error."""
    with (
        patch("Brightness.cli.set_max_brightness") as mock_max,
        patch("Brightness.cli.set_min_brightness") as mock_min,
        patch("Brightness.cli.change_brightness") as mock_change,
    ):
        result = runner.invoke(main, ["invalid"])
        assert result.exit_code != 0  # Should fail with non-zero exit code
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
    assert "OPERATION" in result.output
    assert "increase" in result.output.lower() or "+" in result.output


def test_cli_no_keyboard_flag(runner):
    """CLI --no-keyboard flag should disable keyboard backlight control."""
    with patch("Brightness.cli.change_brightness") as mock_change:
        mock_change.return_value = (15, None)
        result = runner.invoke(main, ["--no-keyboard", "+"])
        assert result.exit_code == 0
        mock_change.assert_called_once_with(True, no_keyboard=True)
        assert "Keyboard: disabled" in result.output


def test_cli_set_specific_level(runner):
    """CLI with numeric argument should set specific brightness level."""
    with patch("Brightness.cli.set_brightness_high_level") as mock_set:
        mock_set.return_value = (15, (100, 50, 0))
        result = runner.invoke(main, ["15"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with(15, no_keyboard=False)
        assert "Level: 15" in result.output


def test_cli_set_level_zero(runner):
    """CLI with '0' should set brightness to level 0."""
    with patch("Brightness.cli.set_brightness_high_level") as mock_set:
        mock_set.return_value = (0, (10, 5, 0))
        result = runner.invoke(main, ["0"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with(0, no_keyboard=False)
        assert "Level: 0" in result.output


def test_cli_set_level_max_value(runner):
    """CLI with '29' should set brightness to level 29."""
    with patch("Brightness.cli.set_brightness_high_level") as mock_set:
        mock_set.return_value = (29, (0, 0, 0))
        result = runner.invoke(main, ["29"])
        assert result.exit_code == 0
        mock_set.assert_called_once_with(29, no_keyboard=False)
        assert "Level: 29" in result.output


def test_cli_set_level_out_of_range(runner):
    """CLI with level > 29 should fail."""
    result = runner.invoke(main, ["30"])
    assert result.exit_code != 0
    assert "must be between 0 and 29" in result.output


def test_cli_output_format_with_keyboard(runner):
    """CLI output should include RGB values when keyboard is enabled."""
    with patch("Brightness.cli.set_max_brightness") as mock_max:
        mock_max.return_value = (19, (75, 36, 0))
        result = runner.invoke(main, ["max"])
        assert result.exit_code == 0
        assert "#4B2400" in result.output  # Hex format
        assert "(75, 36, 0)" in result.output  # Decimal format
