import os
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np

LEVEL_SIZES = [10, 10, 10]

STEP_SIZE = 1
DARK_GAMMA_RANGE = 0
HARDWARE_RANGE = 1
BRIGHT_GAMMA_RANGE = 2

# Alpha value for exponential brightness scaling in hardware range
# Higher values create more perceptually uniform brightness steps
HARDWARE_BRIGHTNESS_ALPHA = 1.4


def is_wayland() -> bool:
    """
    Detects if running under Wayland by checking WAYLAND_DISPLAY environment variable.
    """
    return os.environ.get("WAYLAND_DISPLAY") is not None


def is_wl_gammarelay_running() -> bool:
    """
    Checks if wl-gammarelay-rs D-Bus service is available.
    """
    try:
        result = subprocess.run(["busctl", "--user", "status", "rs.wl-gammarelay"], capture_output=True, timeout=2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_wl_gammarelay():
    """
    Starts wl-gammarelay-rs service in background if not already running.
    """
    if not is_wl_gammarelay_running():
        subprocess.Popen(["wl-gammarelay-rs", "run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait a bit for the service to start
        time.sleep(0.5)


def exp_range(xmin, xmax, n, alpha=1.0):
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
        with open(brightness_file) as f:
            level = int(f.read().strip())
    else:
        level = LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1  # i.e. maximum brightness_file level without gamma correction
        write_brightness_level(level)

    return level


def get_brightness_range(brightness_level: int) -> int:
    """
    Returns the range of brightness levels, one of 0, 1 and 2, corresponding to
    DARK_GAMMA_RANGE, HARDWARE_RANGE and BRIGHT_GAMMA_RANGE respectively.
    Each range consists of 10 levels.
    """
    if brightness_level < LEVEL_SIZES[0]:
        return DARK_GAMMA_RANGE
    elif brightness_level < LEVEL_SIZES[0] + LEVEL_SIZES[1]:
        return HARDWARE_RANGE
    else:
        return BRIGHT_GAMMA_RANGE


def get_brightness_paths() -> Iterator[Path]:
    """
    Gets the path to the brightness file.
    """
    paths = [
        Path(p)
        for p in [
            "/sys/class/backlight/amdgpu_bl1",
            "/sys/class/backlight/amdgpu_bl0",
            "/sys/class/backlight/nvidia_wmi_ec_backlight",
            "/sys/class/backlight/intel_backlight",
            "/sys/class/backlight/acpi_video0",
            "/sys/class/backlight/acpi_video1",
        ]
    ]
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
    with open(path / "max_brightness") as f:
        max_brightness = int(f.read().strip())
    return max_brightness


def get_current_hardware_brightness(path: Path) -> int:
    """
    Reads the current hardware brightness from the file specified in the path returned by get_brightness_path().
    """
    with open(path / "brightness") as f:
        current_brightness = int(f.read().strip())
    return current_brightness


def set_hardware_brightness(decimal_level: int):
    """
    High-level function that sets the hardware brightness level using the specified brightness_level in the range 0..10
    """
    for path in get_brightness_paths():
        max_brightness = get_max_hardware_brightness(path)
        new_brightness = int(exp_range(0, max_brightness, LEVEL_SIZES[1] - 1, HARDWARE_BRIGHTNESS_ALPHA)[decimal_level])
        with open(str(path / "brightness"), "w") as f:
            f.write(str(new_brightness))


def set_gamma_correction_wayland(decimal_level: int, dark_gamma: bool):
    """
    Sets gamma correction on Wayland using wl-gammarelay-rs D-Bus interface.
    For dark gamma the brightness range is 0.1 ... 1.0 .
    For bright gamma the gamma range is 1.0 ... 0.5 (inverted from xrandr).

    Note: wl-gammarelay-rs gamma works inversely to xrandr:
    - xrandr: gamma > 1.0 = brighter midtones
    - wl-gammarelay-rs: gamma < 1.0 = brighter image
    """
    start_wl_gammarelay()

    if dark_gamma:
        gamma_value = 1.0
        brightness_value = float(linear_range(0.1, 1.0, LEVEL_SIZES[0])[decimal_level])
    else:
        # For "overbright", use gamma < 1.0 (inverse of xrandr's gamma > 1.0)
        # xrandr uses 1.0 -> 2.0, we use 1.0 -> 0.5
        gamma_value = float(linear_range(1.0, 0.5, LEVEL_SIZES[2])[decimal_level])
        brightness_value = 1.0

    # Set brightness via D-Bus
    subprocess.run(
        [
            "busctl",
            "--user",
            "set-property",
            "rs.wl-gammarelay",
            "/",
            "rs.wl.gammarelay",
            "Brightness",
            "d",
            str(brightness_value),
        ],
        capture_output=True,
    )

    # Set gamma via D-Bus
    subprocess.run(
        [
            "busctl",
            "--user",
            "set-property",
            "rs.wl-gammarelay",
            "/",
            "rs.wl.gammarelay",
            "Gamma",
            "d",
            str(gamma_value),
        ],
        capture_output=True,
    )


def set_gamma_correction_x11(decimal_level: int, dark_gamma: bool):
    """
    Sets gamma correction on X11 using xrandr.
    For dark gamma the brightness range is 0.1 ... 1.0 .
    For bright gamma the gamma range is 1.0 ... 2.0 .
    """
    if dark_gamma:
        gamma_range = 1
        brightness = linear_range(0.1, 1.0, LEVEL_SIZES[0])[decimal_level]
    else:
        gamma_range = linear_range(1.0, 2.0, LEVEL_SIZES[2])[decimal_level]
        brightness = 1

    primary_monitor = get_primary_monitor_cached()
    os.system(f"xrandr --output {primary_monitor} --gamma {gamma_range} --brightness {brightness}")


def set_gamma_correction(decimal_level: int, dark_gamma: bool):
    """
    High-level function that sets the gamma correction.
    Automatically detects X11 or Wayland and uses the appropriate method.
    For dark gamma the range is 0.1 ... 1.0 .
    For bright gamma the range is 1.0 ... 2.0 .
    """
    if is_wayland():
        set_gamma_correction_wayland(decimal_level, dark_gamma)
    else:
        set_gamma_correction_x11(decimal_level, dark_gamma)


def remove_gamma_correction_wayland():
    """
    Removes the gamma correction on Wayland using wl-gammarelay-rs D-Bus interface.
    """
    start_wl_gammarelay()

    # Reset brightness to 1.0
    subprocess.run(
        ["busctl", "--user", "set-property", "rs.wl-gammarelay", "/", "rs.wl.gammarelay", "Brightness", "d", "1.0"],
        capture_output=True,
    )

    # Reset gamma to 1.0
    subprocess.run(
        ["busctl", "--user", "set-property", "rs.wl-gammarelay", "/", "rs.wl.gammarelay", "Gamma", "d", "1.0"],
        capture_output=True,
    )


def remove_gamma_correction_x11():
    """
    Removes the gamma correction on X11 using xrandr.
    """
    primary_monitor = get_primary_monitor_cached()
    os.system(f"xrandr --output {primary_monitor} --gamma 1.0 --brightness 1.0")


def remove_gamma_correction():
    """
    Removes the gamma correction.
    Automatically detects X11 or Wayland and uses the appropriate method.
    """
    if is_wayland():
        remove_gamma_correction_wayland()
    else:
        remove_gamma_correction_x11()


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
    new_level = min(level + STEP_SIZE, sum(LEVEL_SIZES) - 1) if flag_increase else max(level - STEP_SIZE, 0)
    set_brightness_high_level(new_level)


def set_max_brightness():
    """
    Sets the maximum brightness and gamma 1.0.
    """
    set_brightness_high_level(LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1)


def get_primary_monitor() -> str:
    """
    Gets the primary monitor name.
    On X11: Uses xrandr to find the primary monitor.
    On Wayland: Returns a placeholder since wl-gammarelay-rs applies to all outputs.
    """
    if is_wayland():
        # wl-gammarelay-rs applies gamma/brightness to all outputs
        return "wayland-all"

    # X11: Runs `xrandr | grep primary` that produces an example output of
    # "eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 193mm"
    # and returns the name "eDP-1"
    output = subprocess.check_output(["xrandr"]).decode("utf-8")
    for line in output.split("\n"):
        if "primary" in line:
            return line.split()[0]
    return ""


def get_primary_monitor_cached() -> str:
    """
    Checks /tmp/primary_monitor file and returns the name of the primary monitor.
    If the file is older than 1 day or absent, it calls get_primary_monitor() and saves the result to the file.
    Also invalidates cache if display server type changed (X11 <-> Wayland).
    :return: name of the primary monitor
    """
    file_name = "/tmp/primary_monitor"
    wayland_marker = "/tmp/primary_monitor_wayland"

    current_is_wayland = is_wayland()
    cached_is_wayland = os.path.exists(wayland_marker)

    # Invalidate cache if display server type changed
    if current_is_wayland != cached_is_wayland and os.path.exists(file_name):
        os.remove(file_name)

    if os.path.exists(file_name):
        file_time = os.path.getmtime(file_name)
        if time.time() - file_time < 24 * 3600:
            with open(file_name) as f:
                return f.read().strip()

    primary_monitor = get_primary_monitor()
    with open(file_name, "w") as f:
        f.write(primary_monitor)

    # Update wayland marker
    if current_is_wayland:
        Path(wayland_marker).touch()
    elif os.path.exists(wayland_marker):
        os.remove(wayland_marker)

    return primary_monitor


def set_min_brightness():
    """
    Sets the minimum brightness and gamma 1.0.
    """
    set_brightness_high_level(LEVEL_SIZES[0] - 1)
