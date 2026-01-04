import click

from .config import Config
from .logic import (
    change_brightness,
    set_brightness_high_level,
    set_max_brightness,
    set_min_brightness,
)


def format_output(level: int, keyboard_rgb: tuple[int, int, int] | None) -> str:
    """Format the output message with brightness level and keyboard RGB."""
    if keyboard_rgb is not None:
        r, g, b = keyboard_rgb
        return f"Level: {level}, Keyboard RGB: #{r:02X}{g:02X}{b:02X} ({r}, {g}, {b})"
    else:
        return f"Level: {level}, Keyboard: disabled"


@click.command()
@click.option(
    "--no-keyboard",
    is_flag=True,
    default=False,
    help="Disable keyboard backlight control for this invocation.",
)
@click.argument("operation", type=str, nargs=1)
def main(no_keyboard: bool, operation: str):
    """
    Control monitor brightness.

    OPERATION can be:

    \b
      +       Increase brightness by one step
      -       Decrease brightness by one step
      max     Set maximum brightness (level 19)
      min     Set minimum brightness (level 9)
      0-29    Set specific brightness level

    The keyboard backlight is automatically adjusted based on screen brightness.
    Use --no-keyboard to disable this behavior.

    Configuration file: ~/.config/bright/config.toml
    """
    # Ensure config file exists on first run
    if Config.ensure_config_exists():
        config_path = Config.get_user_config_path()
        click.echo(f"Created default configuration: {config_path}", err=True)

    if operation == "max":
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
            f"Invalid operation: '{operation}'. Valid operations are: +, -, max, min, or 0-29",
            param_hint="'OPERATION'",
        )
