import os
import numpy as np
from typing import Iterator
from pathlib import Path


LEVEL_SIZES = [10, 10, 10]

STEP_SIZE = 1
DARK_GAMMA_RANGE = 0
HARDWARE_RANGE = 1
BRIGHT_GAMMA_RANGE = 2


def exp_range(xmin, xmax, n, alpha=1.):
    """
    Returns a list of n values that divide the range (xmin, xmax) in exponentially-increasing range within xmin..xmax.
    """
    flat_range = np.linspace(0, n, n + 1)
    exp_range = np.exp(flat_range * np.log(alpha)) - 1

    # Normalize the range to (xmin, xmax)
    exp_range = (exp_range - exp_range[0]) / (exp_range[-1] - exp_range[0])
    exp_range = exp_range * (xmax - xmin) + xmin

    return exp_range


def linear_range(xmin, xmax, n):
    """
    Returns a list of n values that divide the range (xmin, xmax) in linearly-increasing range within xmin..xmax.
    """
    return np.linspace(xmin, xmax, n + 1)


def inv_exp_range_transform(xmin, xmax, n, alpha, level):
    """
    Transforms the value in the range xmin..xmax into an integer i that corresponds most closely to the i-th element
    of the exp_range(xmin, xmax, n, alpha).
    """
    exp_range_vals = exp_range(xmin, xmax, n, alpha)
    exp_range_vals = np.round(exp_range_vals).astype(np.int64)
    level = int(level)
    idx = (np.abs(exp_range_vals - level)).argmin()

    return idx


def write_brightness_level(level: int):
    """
    Writes the level of brightness to the file "~/.local/share/brightness_level".
    """
    brightness_file = os.path.expanduser("~/.local/share/brightness_level")
    with open(brightness_file, "w") as f:
        f.write(str(level))


def read_brightness_level() -> int:
    """
    Reads the level of brightness from the file "~/.local/share/brightness_level".
    """
    brightness_file = os.path.expanduser("~/.local/share/brightness_level")
    if os.path.exists(brightness_file):
        with open(brightness_file, "r") as f:
            level = int(f.read().strip())
    else:
        level = LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1  # i.e. maximum brightness_file level without gamma correction
        write_brightness_level(level)

    return level


def get_brightness_range(brighness_level: int) -> int:
    """
    Returns the range of brightness levels, one of 0, 1 and 2, corresponding to
    DARK_GAMMA_RANGE, HARDWARE_RANGE and BRIGHT_GAMMA_RANGE respectively.
    Each range consists of 10 levels.
    """
    if brighness_level < LEVEL_SIZES[0]:
        return DARK_GAMMA_RANGE
    elif brighness_level < LEVEL_SIZES[0] + LEVEL_SIZES[1]:
        return HARDWARE_RANGE
    else:
        return BRIGHT_GAMMA_RANGE


def get_brightness_paths() -> Iterator[Path]:
    """
    Gets the path to the brightness file.
    """
    paths = [Path(p) for p in ["/sys/class/backlight/amdgpu_bl1", "/sys/class/backlight/amdgpu_bl0",
                               "/sys/class/backlight/nvidia_wmi_ec_backlight",
                               "/sys/class/backlight/intel_backlight"]]
    flag_returned = False
    for path in paths:
        if os.path.exists(path / "brightness") and os.path.exists(path / "max_brightness"):
            flag_returned = True
            yield path
    if not flag_returned:
        raise FileNotFoundError("No brightness file found.")


def get_max_hardware_brightness(path: Path) -> int:
    """
    Reads the maximum hardware brightness from the file specified in the path returned by get_brightness_path().
    """
    with open(path / "max_brightness", "r") as f:
        max_brightness = int(f.read().strip())
    return max_brightness


def get_current_hardware_brightness(path: Path) -> int:
    """
    Reads the current hardware brightness from the file specified in the path returned by get_brightness_path().
    """
    with open(path / "brightness", "r") as f:
        current_brightness = int(f.read().strip())
    return current_brightness


def set_hardware_brightness(decimal_level: int):
    """
    High-level function that sets the hardware brightness level using the specified brightness_level in the range 0..10
    """
    for path in get_brightness_paths():
        max_brightness = get_max_hardware_brightness(path)
        new_brightness = int(exp_range(0, max_brightness, LEVEL_SIZES[1] - 1, 1.4)[decimal_level])
        with open(str(path / "brightness"), "w") as f:
            f.write(str(new_brightness))


def set_gamma_correction(decimal_level: int, dark_gamma: bool):
    """
    High-level function that sets the gamma correction using external xrandr program.
    For dark gamma the range is 0.1 ... 1.0 .
    For bright gamma the range is 1.0 ... 2.0 .
    """
    if dark_gamma:
        gamma_range = 1
        brightness = linear_range(0.1, 1.0, LEVEL_SIZES[0])[decimal_level]
    else:
        gamma_range = linear_range(1.0, 2.0, LEVEL_SIZES[2])[decimal_level]
        brightness = 1

    primary_monitor = get_primary_monitor_cached()

    os.system(f"xrandr --output {primary_monitor} --gamma {gamma_range} --brightness {brightness}")


def remove_gamma_correction():
    """
    Removes the gamma correction using external xrandr program.
    """
    primary_monitor = get_primary_monitor_cached()
    os.system(f"xrandr --output {primary_monitor} --gamma 1.0")


def set_brightness_high_level(new_level: int):
    level_range = get_brightness_range(new_level)
    if level_range == HARDWARE_RANGE:
        remove_gamma_correction()
        set_hardware_brightness(new_level - LEVEL_SIZES[0])
    elif level_range == DARK_GAMMA_RANGE:
        set_gamma_correction(new_level, True)
        set_hardware_brightness(0)
    elif level_range == BRIGHT_GAMMA_RANGE:
        set_gamma_correction(new_level - LEVEL_SIZES[0] - LEVEL_SIZES[1], False)
        set_hardware_brightness(LEVEL_SIZES[1] - 1)
    write_brightness_level(new_level)


def change_brightness(flag_increase: bool):
    """
    Increases the brightness by STEP_SIZE and returns the new brightness level.
    """
    level = read_brightness_level()
    if flag_increase:
        new_level = min(level + STEP_SIZE, sum(LEVEL_SIZES) - 1)
    else:
        new_level = max(level - STEP_SIZE, 0)
    set_brightness_high_level(new_level)


def set_max_brightness():
    """
    Sets the maximum brightness and gamma 1.0.
    """
    set_brightness_high_level(LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1)

def get_primary_monitor()->str:
    # Runs `xrandr | grep primary` that produces an example output of
    # "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 193mm"
    # and returns the name "eDP-1"
    import subprocess
    output = subprocess.check_output(["xrandr"]).decode("utf-8")
    for line in output.split("\n"):
        if "primary" in line:
            return line.split()[0]
    return ""

def get_primary_monitor_cached()->str:
    """
    Checks /tmp/primary_monitor file and returns the name of the primary monitor.
    If the file is older than 1 day or absent, it calls get_primary_monitor() and saves the result to the file.
    :return: name of the primary monitor
    """
    import os
    import time
    import datetime
    import subprocess
    import tempfile

    file_name = "/tmp/primary_monitor"
    if os.path.exists(file_name):
        file_time = os.path.getmtime(file_name)
        if time.time() - file_time < 24 * 3600:
            with open(file_name, "r") as f:
                return f.read().strip()

    primary_monitor = get_primary_monitor()
    with open(file_name, "w") as f:
        f.write(primary_monitor)
    return primary_monitor

def set_min_brightness():
    """
    Sets the minimum brightness and gamma 1.0.
    """
    set_brightness_high_level(LEVEL_SIZES[0] - 1)


