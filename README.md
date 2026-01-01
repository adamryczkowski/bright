# bright

Simple CLI tool for controlling monitor brightness on Linux with extended range support.

## Features

- **Hardware backlight control** via sysfs (`/sys/class/backlight/`)
- **Software gamma correction** for extended brightness range beyond hardware limits
- **Wayland support** via [wl-gammarelay-rs](https://github.com/MaxVerevkin/wl-gammarelay-rs)
- **X11 support** via xrandr
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

## How it works

The tool provides a unified 30-level brightness scale:

1. **Levels 0-9 (Dark gamma)**: Hardware brightness at minimum, software gamma reduces brightness further (0.1 to 1.0)
2. **Levels 10-19 (Hardware)**: Native backlight control with exponential scaling for perceptual uniformity
3. **Levels 20-29 (Bright gamma)**: Hardware brightness at maximum, software gamma increases brightness (gamma 1.0 to 2.0 on X11, 1.0 to 0.5 on Wayland)

## Dependencies

- Python >= 3.9
- numpy
- click

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
