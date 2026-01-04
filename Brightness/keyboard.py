"""
Keyboard backlight control for bright.

Controls keyboard backlight brightness based on screen brightness level.
Supports multiple backends:
- openrgb-cli: Uses OpenRGB command-line tool in one-shot mode (no daemon)
- hidapi: Direct HID communication for specific keyboards
"""

import math
import shutil
import subprocess
from typing import Any

# Gamma correction exponent for perceptual uniformity
# Higher values = more brightness at lower levels (less aggressive dimming)
# 2.2 is standard sRGB gamma, we use 2.0 for a slightly more linear feel
KEYBOARD_GAMMA = 2.0


class KeyboardBacklight:
    """Controls keyboard backlight via OpenRGB CLI or direct HID."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize keyboard backlight controller.

        Args:
            config: Keyboard configuration dictionary from Config.load()["keyboard"].
        """
        self.config = config
        self.backend = config.get("backend", "openrgb-cli")
        self.device_index = config.get("device_index", 0)
        self.mode = config.get("mode", "direct")  # "direct" works for most keyboards
        self.vendor_id = config.get("vendor_id", 0x048D)
        self.product_id = config.get("product_id", 0xC967)
        self.disable_threshold = config.get("disable_threshold", 15)
        self.max_backlight_level = config.get("max_backlight_level", 14)
        self.min_backlight_level = config.get("min_backlight_level", 0)
        self.max_power = config.get("max_power", 0.8)
        self.min_power = config.get("min_power", 0.0)  # Default to 0 (off at min)
        self.gamma = config.get("gamma", KEYBOARD_GAMMA)
        self.base_color = self._parse_color(config.get("base_color", "#FFFFFF"))

    def _parse_color(self, color: str) -> tuple[int, int, int]:
        """
        Parse a hex color string to RGB tuple.

        Args:
            color: Hex color string like "#FFFFFF" or "FFFFFF".

        Returns:
            Tuple of (red, green, blue) values 0-255.
        """
        color = color.lstrip("#")
        if len(color) != 6:
            return (255, 255, 255)  # Default to white
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            return (r, g, b)
        except ValueError:
            return (255, 255, 255)  # Default to white

    def calculate_power(self, screen_brightness: int) -> float:
        """
        Calculate keyboard backlight power based on screen brightness.

        Uses gamma correction for perceptual uniformity - the same principle
        used for screen brightness. This ensures that the perceived brightness
        change is uniform across the range.

        The mapping is:
        - screen_brightness >= disable_threshold: power = 0.0 (OFF)
        - screen_brightness <= min_backlight_level: power = min_power
        - screen_brightness >= max_backlight_level: power = max_power
        - Between min and max: gamma-corrected interpolation

        Args:
            screen_brightness: Current screen brightness level (0-29).

        Returns:
            Keyboard backlight power from 0.0 to 1.0.
        """
        if screen_brightness >= self.disable_threshold:
            return 0.0  # Keyboard OFF when room is bright

        if screen_brightness <= self.min_backlight_level:
            return self.min_power

        if screen_brightness >= self.max_backlight_level:
            return self.max_power

        # Gamma-corrected interpolation between min and max
        level_range = self.max_backlight_level - self.min_backlight_level
        if level_range <= 0:
            return self.min_power

        # Calculate linear ratio (0.0 at min_backlight_level, 1.0 at max_backlight_level)
        linear_ratio = (screen_brightness - self.min_backlight_level) / level_range

        # Apply gamma correction: gentle changes at low brightness, rapid at high
        # gamma_ratio = linear_ratio ^ gamma creates a concave curve
        # With gamma=2.0: ratio 0.5 -> power 0.25, ratio 0.64 -> power 0.41
        gamma_ratio = math.pow(linear_ratio, self.gamma)

        # Map to power range
        return self.min_power + gamma_ratio * (self.max_power - self.min_power)

    def calculate_rgb(self, screen_brightness: int) -> tuple[int, int, int]:
        """
        Calculate the RGB color for keyboard backlight based on screen brightness.

        Args:
            screen_brightness: Current screen brightness level (0-29).

        Returns:
            Tuple of (red, green, blue) values 0-255.
        """
        power = self.calculate_power(screen_brightness)
        r = int(self.base_color[0] * power)
        g = int(self.base_color[1] * power)
        b = int(self.base_color[2] * power)
        return (r, g, b)

    def set_backlight(self, screen_brightness: int) -> tuple[bool, tuple[int, int, int]]:
        """
        Set keyboard backlight based on screen brightness level.

        Args:
            screen_brightness: Current screen brightness level (0-29).

        Returns:
            Tuple of (success, rgb) where rgb is (red, green, blue) values 0-255.
        """
        power = self.calculate_power(screen_brightness)
        rgb = self.calculate_rgb(screen_brightness)

        if self.backend == "openrgb-cli":
            return (self._set_via_openrgb_cli(power), rgb)
        elif self.backend == "hidapi":
            return (self._set_via_hidapi(power), rgb)
        else:
            return (False, rgb)

    def _set_via_openrgb_cli(self, power: float) -> bool:
        """
        Set backlight via OpenRGB CLI (one-shot, no daemon).

        Runs OpenRGB in the background (non-blocking) to avoid the 1-3 second
        delay that would otherwise block the main process.

        Args:
            power: Brightness power from 0.0 to 1.0.

        Returns:
            True if the command was started, False otherwise.
        """
        # Check if openrgb is available
        if not shutil.which("openrgb"):
            return False

        # Scale color by power
        r = int(self.base_color[0] * power)
        g = int(self.base_color[1] * power)
        b = int(self.base_color[2] * power)
        color = f"{r:02X}{g:02X}{b:02X}"

        try:
            # Run OpenRGB in background (non-blocking) to avoid delay
            # --noautoconnect prevents starting the SDK server
            # We use Popen instead of run() so we don't wait for completion
            subprocess.Popen(
                [
                    "openrgb",
                    "--noautoconnect",
                    "-d",
                    str(self.device_index),
                    "-m",
                    self.mode,
                    "-c",
                    color,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent process
            )
            return True
        except (FileNotFoundError, OSError):
            return False

    def _set_via_hidapi(self, power: float) -> bool:
        """
        Set backlight via direct HID communication.

        This is for keyboards where we know the HID protocol (e.g., Lenovo Legion).

        Args:
            power: Brightness power from 0.0 to 1.0.

        Returns:
            True if successful, False otherwise.
        """
        try:
            import hid  # type: ignore[import-not-found]
        except ImportError:
            return False

        # Scale color by power
        r = int(self.base_color[0] * power)
        g = int(self.base_color[1] * power)
        b = int(self.base_color[2] * power)

        try:
            device = hid.device()
            device.open(self.vendor_id, self.product_id)
            try:
                # Enable software mode (Lenovo Legion protocol)
                packet = [0x07, 0xB2] + [0] * 190
                device.send_feature_report(packet)

                # Set all zones to the same color
                for zone in range(4):
                    packet = [0x07, 0xA0 + zone, 1, 0, 0x01, r, g, b] + [0] * 184
                    device.send_feature_report(packet)

                return True
            finally:
                device.close()
        except Exception:
            return False

    def turn_off(self) -> bool:
        """
        Turn off keyboard backlight.

        Returns:
            True if successful, False otherwise.
        """
        # Set power to 0 (all LEDs off)
        if self.backend == "openrgb-cli":
            return self._set_via_openrgb_cli(0.0)
        elif self.backend == "hidapi":
            return self._set_via_hidapi(0.0)
        return False


def update_keyboard_backlight(brightness_level: int, no_keyboard: bool = False) -> tuple[int, int, int] | None:
    """
    Update keyboard backlight based on screen brightness.

    This is the main entry point for keyboard backlight control.
    Silently fails if keyboard control is disabled or unavailable.

    Args:
        brightness_level: Current screen brightness level (0-29).
        no_keyboard: If True, skip keyboard backlight update.

    Returns:
        Tuple of (red, green, blue) values 0-255 if keyboard was updated,
        None if keyboard control was skipped or failed.
    """
    if no_keyboard:
        return None

    # Import here to avoid circular imports
    from .config import Config

    try:
        config = Config.load()
        keyboard_config = config.get("keyboard", {})

        if not keyboard_config.get("enabled", True):
            return None

        kb = KeyboardBacklight(keyboard_config)
        _success, rgb = kb.set_backlight(brightness_level)
        return rgb
    except Exception:
        # Silently fail - keyboard backlight is optional
        return None
