"""
Unit tests for Brightness.keyboard module.

These tests verify keyboard backlight control logic with mocked subprocess calls.
"""

from unittest.mock import patch

import pytest

from Brightness.keyboard import KeyboardBacklight, update_keyboard_backlight


def make_config(**overrides):
    """Create a keyboard config dictionary with defaults and overrides."""
    config = {
        "enabled": True,
        "backend": "openrgb-cli",
        "device_index": 0,
        "vendor_id": 0x048D,
        "product_id": 0xC967,
        "disable_threshold": 15,
        "max_backlight_level": 14,
        "min_backlight_level": 0,
        "max_power": 0.8,
        "min_power": 0.1,
        "base_color": "#FFFFFF",
    }
    config.update(overrides)
    return config


# ============================================================================
# Tests for KeyboardBacklight.calculate_power
# ============================================================================


class TestCalculatePower:
    """Tests for the calculate_power method."""

    def test_power_zero_above_threshold(self):
        """Power should be 0 when screen brightness is above threshold."""
        kb = KeyboardBacklight(make_config(disable_threshold=15))
        # Screen brightness above threshold
        assert kb.calculate_power(16) == 0.0
        assert kb.calculate_power(20) == 0.0
        assert kb.calculate_power(29) == 0.0

    def test_power_max_at_max_backlight_level(self):
        """Power should be max_power at the max_backlight_level."""
        kb = KeyboardBacklight(
            make_config(
                disable_threshold=15,
                max_backlight_level=14,
                max_power=0.8,
            )
        )
        # At max_backlight_level (just below threshold)
        power = kb.calculate_power(14)
        assert power == pytest.approx(0.8)

    def test_power_min_at_lowest_brightness(self):
        """Power should be min_power at the lowest screen brightness."""
        kb = KeyboardBacklight(
            make_config(
                min_backlight_level=0,
                min_power=0.1,
            )
        )
        # At min_backlight_level
        power = kb.calculate_power(0)
        assert power == pytest.approx(0.1)

    def test_power_interpolates_with_gamma(self):
        """Power should interpolate with gamma correction between max and min."""
        kb = KeyboardBacklight(
            make_config(
                disable_threshold=15,
                max_backlight_level=14,
                min_backlight_level=0,
                max_power=0.8,
                min_power=0.2,
                gamma=2.0,
            )
        )
        # With gamma correction (concave curve), midpoint brightness level should
        # result in lower power than linear interpolation (gentle at low, rapid at high)
        midpoint = 7
        power = kb.calculate_power(midpoint)
        # Gamma-corrected: linear_ratio = 7/14 = 0.5, gamma_ratio = 0.5^2 = 0.25
        # power = 0.2 + 0.25 * (0.8 - 0.2) = 0.35
        assert power == pytest.approx(0.35, abs=0.01)
        # Should be lower than linear midpoint (0.5)
        linear_midpoint = (0.8 + 0.2) / 2
        assert power < linear_midpoint

    def test_power_clamped_to_valid_range(self):
        """Power should always be between 0 and 1."""
        kb = KeyboardBacklight(
            make_config(
                disable_threshold=15,
                max_power=1.0,
                min_power=0.0,
            )
        )
        for level in range(30):
            power = kb.calculate_power(level)
            assert 0.0 <= power <= 1.0


# ============================================================================
# Tests for KeyboardBacklight.set_backlight
# ============================================================================


class TestSetBacklight:
    """Tests for the set_backlight method."""

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_calls_openrgb(self, mock_popen, mock_which):
        """set_backlight should call openrgb CLI with correct arguments."""
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb = kb.set_backlight(10)  # Some brightness level
        assert success is True
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "openrgb" in cmd
        assert "--noautoconnect" in cmd

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_high_brightness_turns_off(self, mock_popen, mock_which):
        """set_backlight with high brightness should turn off the backlight."""
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(
            make_config(
                backend="openrgb-cli",
                disable_threshold=15,
            )
        )
        success, rgb = kb.set_backlight(20)  # Above threshold
        assert success is True
        assert rgb == (0, 0, 0)  # Black when off
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        # Should set color to black (000000)
        assert "000000" in cmd

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_handles_failure(self, mock_popen, mock_which):
        """set_backlight should return False on subprocess failure."""
        mock_which.return_value = "/usr/bin/openrgb"
        # The exception should be caught by the try/except in _set_via_openrgb_cli
        mock_popen.side_effect = OSError("Command failed")
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb = kb.set_backlight(10)
        assert success is False
        # RGB is still calculated even if command fails
        assert isinstance(rgb, tuple)

    @patch("Brightness.keyboard.shutil.which")
    def test_set_backlight_returns_false_when_openrgb_missing(self, mock_which):
        """set_backlight should return False when openrgb is not installed."""
        mock_which.return_value = None
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb = kb.set_backlight(10)
        assert success is False
        # RGB is still calculated even if openrgb is missing
        assert isinstance(rgb, tuple)


# ============================================================================
# Tests for update_keyboard_backlight function
# ============================================================================


class TestUpdateKeyboardBacklight:
    """Tests for the update_keyboard_backlight convenience function."""

    @patch("Brightness.config.Config")
    def test_update_skipped_when_disabled_by_flag(self, mock_config):
        """update_keyboard_backlight should skip when no_keyboard=True."""
        update_keyboard_backlight(10, no_keyboard=True)
        # Config.load should not be called when no_keyboard=True
        mock_config.load.assert_not_called()

    @patch("Brightness.config.Config.load")
    def test_update_skipped_when_disabled_in_config(self, mock_load):
        """update_keyboard_backlight should skip when disabled in config."""
        mock_load.return_value = {
            "keyboard": {"enabled": False},
        }
        # This should not raise and should not call openrgb
        update_keyboard_backlight(10, no_keyboard=False)
        mock_load.assert_called_once()

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    @patch("Brightness.config.Config.load")
    def test_update_calls_set_backlight(self, mock_load, mock_popen, mock_which):
        """update_keyboard_backlight should call set_backlight."""
        mock_load.return_value = {
            "keyboard": make_config(),
        }
        mock_which.return_value = "/usr/bin/openrgb"
        update_keyboard_backlight(10, no_keyboard=False)
        mock_popen.assert_called_once()


# ============================================================================
# Tests for color parsing
# ============================================================================


class TestColorParsing:
    """Tests for color parsing functionality."""

    def test_parse_color_with_hash(self):
        """Color with # prefix should be parsed correctly."""
        kb = KeyboardBacklight(make_config(base_color="#FF0000"))
        assert kb.base_color == (255, 0, 0)

    def test_parse_color_without_hash(self):
        """Color without # prefix should be parsed correctly."""
        kb = KeyboardBacklight(make_config(base_color="00FF00"))
        assert kb.base_color == (0, 255, 0)

    def test_parse_color_invalid_defaults_to_white(self):
        """Invalid color should default to white."""
        kb = KeyboardBacklight(make_config(base_color="invalid"))
        assert kb.base_color == (255, 255, 255)

    def test_parse_color_short_defaults_to_white(self):
        """Short color string should default to white."""
        kb = KeyboardBacklight(make_config(base_color="#FFF"))
        assert kb.base_color == (255, 255, 255)


# ============================================================================
# Tests for turn_off method
# ============================================================================


class TestTurnOff:
    """Tests for the turn_off method."""

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_turn_off_sets_black_color(self, mock_popen, mock_which):
        """turn_off should set color to black."""
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        result = kb.turn_off()
        assert result is True
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "000000" in cmd
