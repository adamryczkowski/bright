"""
Configuration management for bright.

Loads configuration from TOML files following XDG Base Directory Specification:
- Primary: ~/.config/bright/config.toml
- Fallback: /etc/bright/config.toml (system-wide defaults)
"""

import os
import sys
from pathlib import Path
from typing import Any

# Use built-in tomllib for Python 3.11+, fall back to tomli for older versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]


class Config:
    """Configuration manager for bright."""

    # Default configuration values
    DEFAULT_CONFIG: dict[str, Any] = {
        "brightness": {
            "default_level": 19,
            "state_file": "~/.local/share/brightness_level",
        },
        "keyboard": {
            "enabled": True,
            "backend": "auto",  # auto-detect: brightnessctl, openrgb-cli, or hidapi
            "device_index": 0,
            "mode": "direct",
            "vendor_id": 0x048D,
            "product_id": 0xC967,
            "brightnessctl_device": "",  # auto-detect if empty
            "disable_threshold": 16,
            "max_backlight_level": 19,
            "min_backlight_level": 10,
            "max_power": 1.0,
            "min_power": 0.02,
            "gamma": 2.0,
            "base_color": "#FF7A00",
        },
    }

    _cached_config: dict[str, Any] | None = None

    @classmethod
    def get_config_paths(cls) -> list[Path]:
        """
        Get list of configuration file paths to search, in order of priority.

        Returns:
            List of paths to search for configuration files.
        """
        paths = []

        # XDG_CONFIG_HOME or ~/.config
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            paths.append(Path(xdg_config_home) / "bright" / "config.toml")
        else:
            paths.append(Path.home() / ".config" / "bright" / "config.toml")

        # System-wide config
        paths.append(Path("/etc/bright/config.toml"))

        return paths

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary with default values.
            override: Dictionary with values to override.

        Returns:
            Merged dictionary.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def load(cls, config_path: str | Path | None = None, force_reload: bool = False) -> dict[str, Any]:
        """
        Load configuration from file, merging with defaults.

        Args:
            config_path: Optional explicit path to configuration file.
            force_reload: If True, bypass cache and reload from disk.

        Returns:
            Configuration dictionary with all settings.
        """
        # Return cached config if available and not forcing reload
        if cls._cached_config is not None and not force_reload and config_path is None:
            return cls._cached_config

        # Start with defaults
        config = cls._deep_merge({}, cls.DEFAULT_CONFIG)

        # Determine which config file to load
        paths_to_try = [Path(config_path)] if config_path is not None else cls.get_config_paths()

        # Try to load config file
        loaded_config: dict[str, Any] = {}
        for path in paths_to_try:
            if path.exists():
                try:
                    loaded_config = cls._load_toml_file(path)
                    break
                except Exception:
                    # If config file is invalid, continue to next or use defaults
                    continue

        # Merge loaded config with defaults
        if loaded_config:
            config = cls._deep_merge(config, loaded_config)

        # Cache the result (only for default path lookups)
        if config_path is None:
            cls._cached_config = config

        return config

    @classmethod
    def _load_toml_file(cls, path: Path) -> dict[str, Any]:
        """
        Load a TOML file and return its contents as a dictionary.

        Args:
            path: Path to the TOML file.

        Returns:
            Dictionary with file contents.

        Raises:
            ImportError: If tomli is not available on Python < 3.11.
            Exception: If file cannot be read or parsed.
        """
        if tomllib is None:
            raise ImportError(
                "TOML parsing requires Python 3.11+ or the 'tomli' package. Install with: pip install tomli"
            )

        with open(path, "rb") as f:
            return tomllib.load(f)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached configuration."""
        cls._cached_config = None

    @classmethod
    def get_user_config_path(cls) -> Path:
        """
        Get the path to the user configuration file.

        Returns:
            Path to the user config file (first path in get_config_paths).
        """
        return cls.get_config_paths()[0]

    @classmethod
    def write_default_config(cls, path: Path | None = None) -> Path:
        """
        Write the default configuration to a file.

        Args:
            path: Path to write to. If None, uses the user config path.

        Returns:
            Path to the written config file.
        """
        if path is None:
            path = cls.get_user_config_path()

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate TOML content from defaults
        content = cls._generate_toml_content()

        # Write the file
        with open(path, "w") as f:
            f.write(content)

        return path

    @classmethod
    def _generate_toml_content(cls) -> str:
        """
        Generate TOML content from the default configuration.

        Returns:
            TOML-formatted string with comments.
        """
        lines = [
            "# Bright Configuration File",
            "# Generated automatically on first run.",
            "# Edit this file to customize behavior.",
            "#",
            "# BRIGHTNESS LEVEL SCALE:",
            "#   Levels are integers from 0 to 29 (30 discrete steps).",
            "#   Non-integer values are not supported.",
            "#",
            "#   Ranges:",
            "#     0-9:   Dark gamma range (software dimming at min hardware brightness)",
            "#     10-19: Hardware brightness range (actual backlight control)",
            "#     20-29: Bright gamma range (software brightening at max hardware)",
            "#",
            "#   Key levels:",
            "#     0  = absolute minimum (very dark)",
            "#     9  = 'bright min' command",
            "#     19 = 'bright max' command",
            "#     29 = absolute maximum (overbright)",
            "",
            "[brightness]",
            "# Default brightness level when state file doesn't exist (0-29)",
            f"default_level = {cls.DEFAULT_CONFIG['brightness']['default_level']}",
            "",
            "# Path to the file that stores the current brightness level",
            f'state_file = "{cls.DEFAULT_CONFIG["brightness"]["state_file"]}"',
            "",
            "[keyboard]",
            "# Enable/disable keyboard backlight control",
            f"enabled = {'true' if cls.DEFAULT_CONFIG['keyboard']['enabled'] else 'false'}",
            "",
            "# Backend to use for keyboard control",
            '# Options: "auto" (recommended), "brightnessctl", "openrgb-cli", "hidapi"',
            "# - auto: Automatically detect available backend (brightnessctl > openrgb > hidapi)",
            "# - brightnessctl: System keyboard backlight (ThinkPad, etc.) via brightnessctl",
            "# - openrgb-cli: RGB keyboards via OpenRGB command-line tool",
            "# - hidapi: Direct HID communication for specific keyboards",
            f'backend = "{cls.DEFAULT_CONFIG["keyboard"]["backend"]}"',
            "",
            "# brightnessctl device name (only for brightnessctl backend)",
            '# Leave empty for auto-detection, or specify e.g., "tpacpi::kbd_backlight"',
            f'brightnessctl_device = "{cls.DEFAULT_CONFIG["keyboard"]["brightnessctl_device"]}"',
            "",
            "# OpenRGB device index (use `openrgb --list-devices` to find your keyboard)",
            f"device_index = {cls.DEFAULT_CONFIG['keyboard']['device_index']}",
            "",
            "# OpenRGB mode to use (use `openrgb --list-devices` to see available modes)",
            '# Common modes: "direct", "static", "breathing", "rainbow"',
            f'mode = "{cls.DEFAULT_CONFIG["keyboard"]["mode"]}"',
            "",
            "# Screen brightness level (0-29) above which keyboard backlight is disabled",
            "# When room is bright enough to need high screen brightness, keyboard backlight is off",
            f"disable_threshold = {cls.DEFAULT_CONFIG['keyboard']['disable_threshold']}",
            "",
            "# Screen brightness level range (0-29) for keyboard backlight mapping",
            "# Keyboard power interpolates from min_power to max_power across this range",
            f"max_backlight_level = {cls.DEFAULT_CONFIG['keyboard']['max_backlight_level']}",
            f"min_backlight_level = {cls.DEFAULT_CONFIG['keyboard']['min_backlight_level']}",
            "",
            "# Keyboard backlight power range (0.0-1.0)",
            "# Power multiplies the base_color RGB values",
            "# max_power: keyboard brightness at max_backlight_level (twilight)",
            "# min_power: keyboard brightness at min_backlight_level (total darkness)",
            f"max_power = {cls.DEFAULT_CONFIG['keyboard']['max_power']}",
            f"min_power = {cls.DEFAULT_CONFIG['keyboard']['min_power']}",
            "",
            "# Gamma correction: controls keyboard brightness curve",
            "# Higher values = gentler changes at low brightness, rapid at high",
            "# 2.0 is a good default for matching screen brightness perception",
            f"gamma = {cls.DEFAULT_CONFIG['keyboard']['gamma']}",
            "",
            "# Base color for keyboard backlight (hex format)",
            "# This is the color at max_power (100%)",
            "# Actual RGB = base_color * power",
            f'base_color = "{cls.DEFAULT_CONFIG["keyboard"]["base_color"]}"',
            "",
        ]
        return "\n".join(lines)

    @classmethod
    def ensure_config_exists(cls) -> bool:
        """
        Ensure the user config file exists, creating it with defaults if not.

        Returns:
            True if a new config file was created, False if it already existed.
        """
        user_config = cls.get_user_config_path()
        if not user_config.exists():
            cls.write_default_config(user_config)
            return True
        return False

    @classmethod
    def get_state_file_path(cls) -> Path:
        """
        Get the path to the brightness state file.

        Returns:
            Path to the state file, with ~ expanded.
        """
        config = cls.load()
        state_file = config["brightness"]["state_file"]
        return Path(os.path.expanduser(state_file))
