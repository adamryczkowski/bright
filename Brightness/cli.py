import importlib.util
import sys
from importlib.metadata import version as get_version

import click

from .config import Config
from .keyboard import (
    KeyboardBacklight,
    detect_keyboard_backend,
    get_brightnessctl_device,
    get_brightnessctl_max_brightness,
)
from .logic import (
    DisplayNotAvailableError,
    change_brightness,
    set_brightness_high_level,
    set_max_brightness,
    set_min_brightness,
)


def get_package_version() -> str:
    """Get the package version from metadata."""
    try:
        return get_version("bright")
    except Exception:
        return "unknown"


def format_output(level: int, keyboard_info: tuple[tuple[int, int, int], str, int | None, str | None] | None) -> str:
    """Format the output message with brightness level and keyboard information."""
    if keyboard_info is not None:
        rgb, backend, hw_level, error_msg = keyboard_info
        r, g, b = rgb

        # Format hardware level information
        if backend == "brightnessctl":
            hw_info = f" (brightnessctl, HW level: {hw_level})" if hw_level is not None else " (brightnessctl)"
        elif backend == "openrgb-cli":
            hw_info = " (OpenRGB)"
        elif backend == "hidapi":
            hw_info = " (HID)"
        else:
            hw_info = ""

        output = f"Level: {level}, Keyboard RGB: #{r:02X}{g:02X}{b:02X} ({r}, {g}, {b}){hw_info}"

        # Add error message if present
        if error_msg:
            output += f"\nWarning: {error_msg}"

        return output
    else:
        return f"Level: {level}, Keyboard: disabled"


@click.command()
@click.version_option(version=None, prog_name="bright", package_name="bright", message="%(prog)s %(version)s")
@click.option(
    "--no-keyboard",
    is_flag=True,
    default=False,
    help="Disable keyboard backlight control for this invocation.",
)
@click.argument("operation", type=str, nargs=1, required=False)
def main(no_keyboard: bool, operation: str | None):
    """
    Control monitor brightness.

    OPERATION can be:

    \b
      +              Increase brightness by one step
      -              Decrease brightness by one step
      max            Set maximum brightness (level 19)
      min            Set minimum brightness (level 9)
      0-29           Set specific brightness level
      test-keyboard  Test keyboard backlight detection and control

    The keyboard backlight is automatically adjusted based on screen brightness.
    Use --no-keyboard to disable this behavior.

    Configuration file: ~/.config/bright/config.toml
    """
    # Handle missing operation argument
    if operation is None:
        raise click.UsageError("Missing argument 'OPERATION'.")

    # Ensure config file exists on first run
    if Config.ensure_config_exists():
        config_path = Config.get_user_config_path()
        click.echo(f"Created default configuration: {config_path}", err=True)

    try:
        if operation == "test-keyboard":
            _test_keyboard()
        elif operation == "max":
            level, keyboard_rgb = set_max_brightness(no_keyboard=no_keyboard)
            click.echo(format_output(level, keyboard_rgb))
        elif operation == "min":
            level, keyboard_rgb = set_min_brightness(no_keyboard=no_keyboard)
            click.echo(format_output(level, keyboard_rgb))
        elif operation == "+":
            level, keyboard_rgb = change_brightness(True, no_keyboard=no_keyboard)
            click.echo(format_output(level, keyboard_rgb))
        elif operation == "-":
            level, keyboard_rgb = change_brightness(False, no_keyboard=no_keyboard)
            click.echo(format_output(level, keyboard_rgb))
        elif operation.isdigit():
            # Set specific brightness level
            target_level = int(operation)
            if target_level < 0 or target_level > 29:
                raise click.BadParameter(
                    f"Brightness level must be between 0 and 29, got {target_level}",
                    param_hint="'OPERATION'",
                )
            level, keyboard_rgb = set_brightness_high_level(target_level, no_keyboard=no_keyboard)
            click.echo(format_output(level, keyboard_rgb))
        else:
            raise click.BadParameter(
                f"Invalid operation: '{operation}'. Valid operations are: +, -, max, min, test-keyboard, or 0-29",
                param_hint="'OPERATION'",
            )
    except DisplayNotAvailableError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _test_keyboard():
    """Test keyboard backlight detection and control."""
    import shutil

    click.echo("=== Keyboard Backlight Test ===\n")

    # Load config
    config = Config.load()
    keyboard_config = config.get("keyboard", {})

    click.echo("1. Configuration:")
    click.echo(f"   Enabled: {keyboard_config.get('enabled', True)}")
    click.echo(f"   Configured backend: {keyboard_config.get('backend', 'auto')}")
    click.echo(f"   Config file: {Config.get_user_config_path()}")
    click.echo()

    # Check available backends
    click.echo("2. Backend Detection:")

    # Check brightnessctl
    brightnessctl_available = shutil.which("brightnessctl") is not None
    click.echo(f"   brightnessctl installed: {brightnessctl_available}")
    if brightnessctl_available:
        device = get_brightnessctl_device()
        if device:
            max_brightness = get_brightnessctl_max_brightness(device)
            click.echo(f"   brightnessctl device: {device}")
            click.echo(f"   brightnessctl max brightness: {max_brightness}")
        else:
            click.echo("   brightnessctl device: (no keyboard backlight found)")

    # Check openrgb
    openrgb_available = shutil.which("openrgb") is not None
    click.echo(f"   openrgb installed: {openrgb_available}")

    # Check hidapi
    hidapi_available = importlib.util.find_spec("hid") is not None
    click.echo(f"   hidapi available: {hidapi_available}")

    # Auto-detection result
    detected = detect_keyboard_backend()
    click.echo(f"   Auto-detected backend: {detected or '(none)'}")
    click.echo()

    # Test actual backend
    click.echo("3. Keyboard Backlight Test:")
    kb = KeyboardBacklight(keyboard_config)
    click.echo(f"   Active backend: {kb.backend}")

    # Try to set backlight to max
    click.echo("   Testing: Setting keyboard to maximum brightness...")
    success, rgb, backend, hw_level, error_msg = kb.set_backlight(0)  # Level 0 = max keyboard brightness
    if success:
        hw_info = f", HW level: {hw_level}" if hw_level is not None else ""
        click.echo(f"   Result: SUCCESS - RGB set to #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}{hw_info}")
        click.echo(f"   Backend used: {backend}")
    else:
        click.echo("   Result: FAILED - Could not set keyboard backlight")
        if error_msg:
            click.echo(f"   Error: {error_msg}")
        else:
            click.echo("   Hint: Check if the backend is correctly configured")

    click.echo()
    click.echo("4. Recommendations:")
    if keyboard_config.get("backend") != "auto" and detected:
        click.echo(f"   - Your config uses '{keyboard_config.get('backend')}' but '{detected}' was detected.")
        click.echo("   - Consider changing 'backend' to 'auto' in your config file.")
    elif not detected:
        click.echo("   - No keyboard backlight backend was detected.")
        click.echo("   - Install brightnessctl or openrgb for keyboard backlight support.")
    else:
        click.echo("   - Keyboard backlight configuration looks good!")
