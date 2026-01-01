import click

from .logic import change_brightness, set_max_brightness, set_min_brightness

# Convert to click:
# def main():
#     """
#     Parses the arguments and runs the appropriate function.
#     """
#     import argparse
#
#     parser = argparse.ArgumentParser(description="Adjust screen brightness using gamma and hardware range.")
#     parser.add_argument("operation", type=str, help="Operation to perform: + (increase), - (decrease), max, or min.")
#     args = parser.parse_args()
#
#     if args.operation == "max":
#         set_max_brightness()
#     elif args.operation == "min":
#         set_min_brightness()
#     elif args.operation == "+":
#         change_brightness(True)
#     elif args.operation == "-":
#         change_brightness(False)
#     else:
#         print("Invalid operation")
#
#
# if __name__ == "__main__":
#     main()


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
        print("Invalid operation")
