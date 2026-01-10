# bright

Simple CLI tool for controlling monitor brightness on Linux with extended range support.

## Features

- **Hardware backlight control** via sysfs (`/sys/class/backlight/`)
- **Software gamma correction** for extended brightness range beyond hardware limits
- **Wayland support** via [wl-gammarelay-rs](https://github.com/MaxVerevkin/wl-gammarelay-rs)
- **X11 support** via xrandr
- **Keyboard backlight integration** - automatically adjusts keyboard backlight based on screen brightness
  - **brightnessctl** for system keyboard backlights (ThinkPad, etc.)
  - **OpenRGB** for RGB keyboards
  - **Auto-detection** of available backend
- **TOML configuration** for persistent settings
- **30-level brightness scale** with three ranges:
  - Dark gamma range (levels 0-9): Software dimming below hardware minimum
  - Hardware range (levels 10-19): Native backlight control
  - Bright gamma range (levels 20-29): Software boost above hardware maximum

## Installation

### From PyPI

```bash
pip install bright
```

### From source

```bash
git clone https://github.com/adamryczkowski/bright.git
cd bright
pip install .
```

### Development installation

```bash
git clone https://github.com/adamryczkowski/bright.git
cd bright
just setup
```

## Usage

```bash
# Set maximum brightness (hardware max, no gamma correction)
bright max

# Set minimum brightness (lowest gamma-corrected level)
bright min

# Increase brightness by one step
bright +

# Decrease brightness by one step
bright -

# Disable keyboard backlight control for this invocation
bright --no-keyboard +
```

## System Requirements

### Linux

This tool only works on Linux systems with backlight support.

### Supported backlight devices

The tool automatically detects backlight devices in this order:
- `/sys/class/backlight/amdgpu_bl1`
- `/sys/class/backlight/amdgpu_bl0`
- `/sys/class/backlight/nvidia_wmi_ec_backlight`
- `/sys/class/backlight/intel_backlight`
- `/sys/class/backlight/acpi_video0`
- `/sys/class/backlight/acpi_video1`

### Permissions

To control hardware brightness, you need write access to `/sys/class/backlight/*/brightness`.

**Option 1: Add user to video group**
```bash
sudo usermod -aG video $USER
# Log out and back in
```

**Option 2: Create udev rule**
```bash
echo 'ACTION=="add", SUBSYSTEM=="backlight", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"' | sudo tee /etc/udev/rules.d/90-backlight.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Wayland requirements

For Wayland gamma correction, install [wl-gammarelay-rs](https://github.com/MaxVerevkin/wl-gammarelay-rs):

```bash
# Arch Linux
paru -S wl-gammarelay-rs

# From source
cargo install wl-gammarelay-rs
```

The tool will automatically start `wl-gammarelay-rs` if needed.

### X11 requirements

For X11 gamma correction, ensure `xrandr` is installed:

```bash
# Debian/Ubuntu
sudo apt install x11-xserver-utils

# Fedora
sudo dnf install xrandr

# Arch Linux
sudo pacman -S xorg-xrandr
```

## Configuration

Brightness level is stored in `~/.local/share/brightness_level`.

The default brightness level is 19 (maximum hardware brightness without gamma correction).

### Configuration File

You can customize behavior using a TOML configuration file at `~/.config/bright/config.toml`.

See [`docs/config.toml.example`](docs/config.toml.example) for all available options.

Example configuration:

```toml
[brightness]
default_level = 19
state_file = "~/.local/share/brightness_level"

[keyboard]
enabled = true
backend = "auto"  # auto-detect: brightnessctl, openrgb-cli, or hidapi
disable_threshold = 15
max_power = 0.8
min_power = 0.1
base_color = "#FFFFFF"
```

### Keyboard Backlight

The keyboard backlight is automatically adjusted based on screen brightness.

#### Supported Backends

- **brightnessctl**: For system keyboard backlights (ThinkPad `tpacpi::kbd_backlight`, etc.)
  - Requires `brightnessctl` to be installed
  - Supports discrete brightness levels (typically 0, 1, 2)
- **openrgb-cli**: For RGB keyboards via [OpenRGB](https://openrgb.org/)
  - Requires `openrgb` to be installed
  - Supports full RGB color control
- **hidapi**: Direct HID communication for specific keyboards (Lenovo Legion, etc.)
  - Requires the `hid` Python package

The default `backend = "auto"` will automatically detect and use the first available backend.

#### Behavior

- **Above threshold (default: level 15)**: Keyboard backlight is OFF (room is bright enough)
- **At twilight (levels 10-14)**: Keyboard backlight at maximum power (80% by default)
- **In darkness (levels 0-9)**: Keyboard backlight dims with screen brightness (down to 10%)

This behavior ensures:
- In bright rooms, you don't need keyboard illumination
- At twilight, you get maximum keyboard visibility when you need it most
- In total darkness, a dim keyboard won't blind you

To disable keyboard control:
- Permanently: Set `enabled = false` in config file
- Per-invocation: Use `--no-keyboard` flag

## How it works

The tool provides a unified 30-level brightness scale:

1. **Levels 0-9 (Dark gamma)**: Hardware brightness at minimum, software gamma reduces brightness further (0.1 to 1.0)
2. **Levels 10-19 (Hardware)**: Native backlight control with exponential scaling for perceptual uniformity
3. **Levels 20-29 (Bright gamma)**: Hardware brightness at maximum, software gamma increases brightness (gamma 1.0 to 2.0 on X11, 1.0 to 0.5 on Wayland)

## Dependencies

### Required

- Python >= 3.9
- numpy
- click
- tomli (for Python < 3.11)

### Optional

- [brightnessctl](https://github.com/Hummer12007/brightnessctl) - for system keyboard backlight control (ThinkPad, etc.)
- [OpenRGB](https://openrgb.org/) - for RGB keyboard backlight control

## Development

```bash
# Setup development environment
just setup

# Run tests
just test

# Run all checks (format, lint, type check, tests)
just validate

# Build package
just package
```

## License

[Add license information]

## Author

Adam Ryczkowski <adam@statystyka.net>
