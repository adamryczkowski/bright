"""
Unit tests for Brightness.keyboard module.

These tests verify keyboard backlight control logic with mocked subprocess calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from Brightness.keyboard import (
    KeyboardBacklight,
    detect_keyboard_backend,
    get_brightnessctl_device,
    get_brightnessctl_max_brightness,
    update_keyboard_backlight,
)


def make_config(**overrides):
    """Create a keyboard config dictionary with defaults and overrides."""
    config = {
        "enabled": True,
        "backend": "openrgb-cli",
        "device_index": 0,
        "vendor_id": 0x048D,
        "product_id": 0xC967,
        "brightnessctl_device": "tpacpi::kbd_backlight",
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

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_calls_openrgb(self, mock_popen, mock_which, mock_get_device):
        """set_backlight should call openrgb CLI with correct arguments."""
        mock_get_device.return_value = None
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)  # Some brightness level
        assert success is True
        assert isinstance(rgb, tuple)
        assert len(rgb) == 3
        assert backend == "openrgb-cli"
        assert hw_level is None
        assert error_msg is None
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "openrgb" in cmd
        assert "--noautoconnect" in cmd

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_high_brightness_turns_off(self, mock_popen, mock_which, mock_get_device):
        """set_backlight with high brightness should turn off the backlight."""
        mock_get_device.return_value = None
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(
            make_config(
                backend="openrgb-cli",
                disable_threshold=15,
            )
        )
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(20)  # Above threshold
        assert success is True
        assert rgb == (0, 0, 0)  # Black when off
        assert backend == "openrgb-cli"
        assert error_msg is None
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        # Should set color to black (000000)
        assert "000000" in cmd

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_set_backlight_handles_failure(self, mock_popen, mock_which, mock_get_device):
        """set_backlight should return False on subprocess failure."""
        mock_get_device.return_value = None
        mock_which.return_value = "/usr/bin/openrgb"
        # The exception should be caught by the try/except in _set_via_openrgb_cli
        mock_popen.side_effect = OSError("Command failed")
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)
        assert success is False
        assert backend == "openrgb-cli"
        # RGB is still calculated even if command fails
        assert isinstance(rgb, tuple)
        assert error_msg is None  # openrgb doesn't return error messages

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    def test_set_backlight_returns_false_when_openrgb_missing(self, mock_which, mock_get_device):
        """set_backlight should return False when openrgb is not installed."""
        mock_get_device.return_value = None
        mock_which.return_value = None
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)
        assert success is False
        assert backend == "openrgb-cli"
        # RGB is still calculated even if openrgb is missing
        assert isinstance(rgb, tuple)
        assert error_msg is None  # openrgb doesn't return error messages


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

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.Popen")
    def test_turn_off_sets_black_color(self, mock_popen, mock_which, mock_get_device):
        """turn_off should set color to black."""
        mock_get_device.return_value = None
        mock_which.return_value = "/usr/bin/openrgb"
        kb = KeyboardBacklight(make_config(backend="openrgb-cli"))
        result = kb.turn_off()
        assert result is True
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "000000" in cmd

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    @patch("Brightness.keyboard.get_brightnessctl_max_brightness")
    def test_turn_off_brightnessctl(self, mock_max, mock_run, mock_which, mock_get_device):
        """turn_off with brightnessctl should set brightness to 0."""
        mock_get_device.return_value = "tpacpi::kbd_backlight"
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_max.return_value = 2
        mock_run.return_value = MagicMock(returncode=0)
        kb = KeyboardBacklight(make_config(backend="brightnessctl"))
        result = kb.turn_off()
        assert result is True
        # Should call brightnessctl set 0 (may be called twice: once for device detection, once for set)
        assert mock_run.call_count >= 1
        # Find the call that sets brightness to 0
        set_call_found = False
        for call in mock_run.call_args_list:
            call_args = call[0][0]
            if "set" in call_args and "0" in call_args:
                set_call_found = True
                break
        assert set_call_found, "Expected brightnessctl set 0 call not found"


# ============================================================================
# Tests for brightnessctl backend
# ============================================================================


class TestBrightnessctlBackend:
    """Tests for the brightnessctl backend."""

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    @patch("Brightness.keyboard.get_brightnessctl_max_brightness")
    def test_set_backlight_brightnessctl(self, mock_max, mock_run, mock_which, mock_get_device):
        """set_backlight with brightnessctl should call brightnessctl set."""
        mock_get_device.return_value = "tpacpi::kbd_backlight"
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_max.return_value = 2  # ThinkPad has 3 levels: 0, 1, 2
        mock_run.return_value = MagicMock(returncode=0)
        kb = KeyboardBacklight(make_config(backend="brightnessctl"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)  # Some brightness level
        assert success is True
        assert error_msg is None
        assert backend == "brightnessctl"
        assert hw_level is not None
        # Find the set call
        set_call_found = False
        for call in mock_run.call_args_list:
            call_args = call[0][0]
            if "set" in call_args and "--device" in call_args:
                set_call_found = True
                break
        assert set_call_found, "Expected brightnessctl set call not found"

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    @patch("Brightness.keyboard.get_brightnessctl_max_brightness")
    def test_brightnessctl_maps_power_to_levels(self, mock_max, mock_run, mock_which, mock_get_device):
        """brightnessctl should map power (0-1) to discrete levels."""
        mock_get_device.return_value = "tpacpi::kbd_backlight"
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_max.return_value = 2  # 3 levels: 0, 1, 2
        mock_run.return_value = MagicMock(returncode=0)

        kb = KeyboardBacklight(
            make_config(
                backend="brightnessctl",
                disable_threshold=20,
                max_backlight_level=14,
                min_backlight_level=0,
                max_power=1.0,
                min_power=0.0,
            )
        )

        # At max_backlight_level (power=1.0), should set level 2
        kb.set_backlight(14)
        call_args = mock_run.call_args[0][0]
        assert "2" in call_args

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    def test_brightnessctl_returns_false_when_missing(self, mock_which, mock_get_device):
        """brightnessctl backend should return False when brightnessctl is not installed."""
        mock_get_device.return_value = "tpacpi::kbd_backlight"
        mock_which.return_value = None
        kb = KeyboardBacklight(make_config(backend="brightnessctl"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)
        assert success is False
        assert error_msg is not None  # Should have error message about brightnessctl not found
        assert backend == "brightnessctl"

    @patch("Brightness.keyboard.get_brightnessctl_device")
    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    @patch("Brightness.keyboard.get_brightnessctl_max_brightness")
    def test_brightnessctl_returns_false_on_zero_max(self, mock_max, mock_run, mock_which, mock_get_device):
        """brightnessctl should return False if max brightness is 0."""
        mock_get_device.return_value = "tpacpi::kbd_backlight"
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_max.return_value = 0  # Invalid max brightness
        kb = KeyboardBacklight(make_config(backend="brightnessctl"))
        success, rgb, backend, hw_level, error_msg = kb.set_backlight(10)
        assert success is False
        assert error_msg is not None  # Should have error message about max brightness
        assert backend == "brightnessctl"


# ============================================================================
# Tests for backend detection
# ============================================================================


class TestBackendDetection:
    """Tests for automatic backend detection."""

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    def test_detect_brightnessctl_backend(self, mock_run, mock_which):
        """detect_keyboard_backend should detect brightnessctl with kbd_backlight."""
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"Device 'tpacpi::kbd_backlight' of class 'leds':\n",
        )
        result = detect_keyboard_backend()
        assert result == "brightnessctl"

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    def test_detect_openrgb_backend(self, mock_run, mock_which):
        """detect_keyboard_backend should detect openrgb when brightnessctl has no kbd."""

        def which_side_effect(cmd):
            if cmd == "brightnessctl":
                return None
            if cmd == "openrgb":
                return "/usr/bin/openrgb"
            return None

        mock_which.side_effect = which_side_effect
        result = detect_keyboard_backend()
        assert result == "openrgb-cli"

    @patch("Brightness.keyboard.shutil.which")
    def test_detect_no_backend(self, mock_which):
        """detect_keyboard_backend should return None when no backend is available."""
        mock_which.return_value = None
        result = detect_keyboard_backend()
        assert result is None

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    def test_get_brightnessctl_device(self, mock_run, mock_which):
        """get_brightnessctl_device should parse device name from brightnessctl output."""
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"Device 'tpacpi::kbd_backlight' of class 'leds':\n",
        )
        result = get_brightnessctl_device()
        assert result == "tpacpi::kbd_backlight"

    @patch("Brightness.keyboard.shutil.which")
    @patch("Brightness.keyboard.subprocess.run")
    def test_get_brightnessctl_max_brightness(self, mock_run, mock_which):
        """get_brightnessctl_max_brightness should return max brightness level."""
        mock_which.return_value = "/usr/bin/brightnessctl"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"2\n",
        )
        result = get_brightnessctl_max_brightness("tpacpi::kbd_backlight")
        assert result == 2


# ============================================================================
# Tests for auto backend selection
# ============================================================================


class TestAutoBackend:
    """Tests for auto backend selection in KeyboardBacklight."""

    @patch("Brightness.keyboard.detect_keyboard_backend")
    def test_auto_backend_uses_detection(self, mock_detect):
        """KeyboardBacklight with backend='auto' should use detect_keyboard_backend."""
        mock_detect.return_value = "brightnessctl"
        kb = KeyboardBacklight(make_config(backend="auto"))
        assert kb.backend == "brightnessctl"

    @patch("Brightness.keyboard.detect_keyboard_backend")
    def test_auto_backend_fallback_to_openrgb(self, mock_detect):
        """KeyboardBacklight with backend='auto' should fallback to openrgb-cli."""
        mock_detect.return_value = None
        kb = KeyboardBacklight(make_config(backend="auto"))
        assert kb.backend == "openrgb-cli"

    def test_explicit_backend_not_overridden(self):
        """KeyboardBacklight with explicit backend should not use detection."""
        kb = KeyboardBacklight(make_config(backend="hidapi"))
        assert kb.backend == "hidapi"
