import click

from .logic import change_brightness, set_max_brightness, set_min_brightness


@click.command()
@click.argument("operation", type=str, nargs=1)
def main(operation: str):
    """
    Parses the arguments and runs the appropriate function.
    Operation to perform: + (increase), - (decrease), max, or min.
    """
    if operation == "max":
        set_max_brightness()
    elif operation == "min":
        set_min_brightness()
    elif operation == "+":
        change_brightness(True)
    elif operation == "-":
        change_brightness(False)
    else:
        raise click.BadParameter(
            f"Invalid operation: '{operation}'. Valid operations are: +, -, max, min",
            param_hint="'OPERATION'",
        )
