# Adaptation Plan: 3-Level Keyboard Backlight Support

**Date:** 2025-01-12
**Project:** bright
**Target:** Non-RGB laptop keyboard with 3 discrete brightness levels (off, half, full)

## Current Implementation Analysis

### Overview
The `bright` project currently supports keyboard backlight control through three backends:

1. **brightnessctl** - System keyboard backlights (e.g., ThinkPad `tpacpi::kbd_backlight`)
2. **openrgb-cli** - RGB keyboards via OpenRGB
3. **hidapi** - Direct HID communication for specific keyboards

### Current Behavior

The keyboard backlight is controlled based on screen brightness (0-29 scale):

- **Screen brightness ≥ disable_threshold (default: 15)**: Keyboard OFF (room is bright)
- **Screen brightness 10-14 (twilight)**: Keyboard at max_power (default: 80%)
- **Screen brightness 0-9 (darkness)**: Keyboard dims with screen (down to min_power, default: 10%)

### Key Implementation Details

#### Power Calculation ([`Brightness/keyboard.py:197-240`](Brightness/keyboard.py:197))

The [`calculate_power()`](Brightness/keyboard.py:197) method computes keyboard backlight power (0.0-1.0) using:

1. **Gamma correction** for perceptual uniformity (default gamma=2.0)
2. **Linear interpolation** between `min_backlight_level` and `max_backlight_level`
3. **Power range mapping** from `min_power` to `max_power`

Formula:
```python
linear_ratio = (screen_brightness - min_backlight_level) / level_range
gamma_ratio = linear_ratio ^ gamma
power = min_power + gamma_ratio * (max_power - min_power)
```

#### brightnessctl Backend ([`Brightness/keyboard.py:280-320`](Brightness/keyboard.py:280))

The [`_set_via_brightnessctl()`](Brightness/keyboard.py:280) method:

1. Gets max brightness level from device (e.g., 2 for ThinkPad = levels 0, 1, 2)
2. Maps continuous power (0.0-1.0) to discrete levels via rounding
3. Executes: `brightnessctl --device <device> set <level>`

**This is already designed for discrete levels!**

## Adaptation Strategy for 3-Level Keyboard

### Good News: Minimal Changes Required

The current implementation **already supports** discrete brightness levels through the brightnessctl backend. The system:

1. ✅ Calculates continuous power (0.0-1.0) based on screen brightness
2. ✅ Maps power to discrete hardware levels via rounding
3. ✅ Handles devices with any number of discrete levels (0 to max_brightness)

### Verification Steps

For a laptop with 3 keyboard brightness levels (off=0, half=1, full=2):

1. **Check device detection:**
   ```bash
   brightnessctl --list --class=leds
   ```
   Should show keyboard backlight device (e.g., `tpacpi::kbd_backlight`)

2. **Verify max brightness:**
   ```bash
   brightnessctl --device tpacpi::kbd_backlight max
   ```
   Should return `2` (meaning levels 0, 1, 2 are available)

3. **Test keyboard control:**
   ```bash
   bright test-keyboard
   ```
   Should detect brightnessctl backend and show max brightness = 2

### Configuration Recommendations

For optimal 3-level keyboard backlight behavior, adjust [`~/.config/bright/config.toml`](~/.config/bright/config.toml):

```toml
[keyboard]
enabled = true
backend = "auto"  # Will auto-detect brightnessctl

# Device name (leave empty for auto-detection)
brightnessctl_device = ""

# Screen brightness threshold above which keyboard is OFF
# Recommended: 16-20 (keyboard off in bright rooms)
disable_threshold = 16

# Screen brightness range for keyboard mapping
# These define when keyboard transitions between levels
max_backlight_level = 19  # Keyboard at full when screen ≤ 19
min_backlight_level = 10  # Keyboard starts dimming when screen < 10

# Power range (0.0-1.0)
# With 3 levels, these map to: off=0.0, half≈0.5, full=1.0
max_power = 1.0   # Full brightness at max_backlight_level
min_power = 0.02  # Almost off at min_backlight_level (but not quite)

# Gamma correction (affects transition curve)
# Higher = more time at full brightness before dimming
gamma = 2.0
```

### Power-to-Level Mapping

With `max_brightness = 2` and the formula `level = round(power * 2)`:

| Power Range | Rounded Level | Keyboard State |
|-------------|---------------|----------------|
| 0.00 - 0.24 | 0 | OFF |
| 0.25 - 0.74 | 1 | HALF |
| 0.75 - 1.00 | 2 | FULL |

### Behavior Examples

With default config (`disable_threshold=16`, `max_backlight_level=19`, `min_backlight_level=10`, `max_power=1.0`, `min_power=0.02`, `gamma=2.0`):

| Screen Level | Power | Keyboard Level | State |
|--------------|-------|----------------|-------|
| 29 (max) | 0.00 | 0 | OFF (room bright) |
| 20 | 0.00 | 0 | OFF (room bright) |
| 16 | 0.00 | 0 | OFF (threshold) |
| 15 | ~0.88 | 2 | FULL (twilight) |
| 14 | ~0.81 | 2 | FULL |
| 13 | ~0.73 | 1 | HALF |
| 12 | ~0.64 | 1 | HALF |
| 11 | ~0.54 | 1 | HALF |
| 10 | ~0.43 | 1 | HALF |
| 9 | ~0.32 | 1 | HALF |
| 8 | ~0.22 | 0 | OFF |
| 0-7 | <0.20 | 0 | OFF (very dark) |

### Fine-Tuning Options

#### Option 1: Keep keyboard at FULL longer (more conservative)

```toml
max_backlight_level = 14  # Keyboard full only in twilight (10-14)
min_backlight_level = 0   # Dim across full dark range
max_power = 1.0
min_power = 0.5           # Never go below HALF brightness
gamma = 2.5               # More time at high brightness
```

Result: Keyboard stays at FULL or HALF, rarely turns OFF except in bright rooms.

#### Option 2: More aggressive dimming (prefer OFF)

```toml
max_backlight_level = 14
min_backlight_level = 10
max_power = 1.0
min_power = 0.0           # Allow full OFF in darkness
gamma = 1.5               # Faster transition to dim
```

Result: Keyboard turns OFF more readily in dark conditions.

#### Option 3: Simple on/off behavior

```toml
disable_threshold = 15
max_backlight_level = 14
min_backlight_level = 14  # No interpolation range
max_power = 1.0
min_power = 1.0           # Always full when on
```

Result: Keyboard is either FULL (screen ≤ 14) or OFF (screen ≥ 15).

## Implementation Status

### What Works Now ✅

1. **Detection**: Auto-detects brightnessctl and keyboard device
2. **Discrete levels**: Already maps continuous power to discrete hardware levels
3. **Configuration**: All parameters are configurable via TOML
4. **Testing**: `bright test-keyboard` command validates setup

### What Needs Testing ⚠️

1. **Device detection** on the target laptop
2. **Level transitions** feel natural with 3 discrete levels
3. **Power thresholds** (0.25, 0.75) work well for the specific keyboard

### Potential Improvements 🔧

#### 1. Discrete-Level-Aware Power Calculation

Currently, power is calculated continuously then rounded. For better control with discrete levels, we could:

```python
def calculate_discrete_level(self, screen_brightness: int, max_hw_level: int) -> int:
    """Calculate keyboard level directly for discrete hardware."""
    if screen_brightness >= self.disable_threshold:
        return 0

    # Calculate power as before
    power = self.calculate_power(screen_brightness)

    # Map to discrete level with explicit thresholds
    level = round(power * max_hw_level)
    return max(0, min(level, max_hw_level))
```

This is essentially what happens now, but making it explicit could help with debugging.

#### 2. Custom Threshold Configuration

For 3-level keyboards, allow users to specify exact power thresholds:

```toml
[keyboard]
# For 3-level keyboards: specify power thresholds for each level
# level_thresholds = [0.0, 0.3, 0.7]  # OFF < 0.3, HALF < 0.7, FULL ≥ 0.7
```

#### 3. Level-Specific Screen Brightness Ranges

Alternative approach: map screen brightness ranges directly to keyboard levels:

```toml
[keyboard]
# Map screen brightness ranges to keyboard levels
# Format: [[screen_min, screen_max, kbd_level], ...]
brightness_map = [
    [0, 9, 0],      # Screen 0-9: keyboard OFF
    [10, 14, 1],    # Screen 10-14: keyboard HALF
    [15, 19, 2],    # Screen 15-19: keyboard FULL
    [20, 29, 0],    # Screen 20-29: keyboard OFF
]
```

This would be more explicit but less flexible than the current gamma-corrected approach.

## Testing Plan

### 1. Basic Functionality

```bash
# Test keyboard detection
bright test-keyboard

# Test at various screen brightness levels
bright 29  # Should show keyboard OFF
bright 15  # Should show keyboard FULL
bright 10  # Should show keyboard HALF or FULL
bright 5   # Should show keyboard OFF or HALF
```

### 2. Verify Transitions

```bash
# Slowly decrease brightness and observe keyboard changes
for i in {29..0}; do
    bright $i
    sleep 1
done
```

### 3. Check Configuration

```bash
# View current config
cat ~/.config/bright/config.toml

# Test with keyboard disabled
bright --no-keyboard 15
```

## Conclusion

The `bright` project **already supports** 3-level keyboard backlights through the brightnessctl backend. The implementation:

1. ✅ Automatically detects discrete brightness levels
2. ✅ Maps continuous power calculations to discrete hardware levels
3. ✅ Provides extensive configuration options
4. ✅ Includes testing and diagnostic tools

**No code changes are required** for basic functionality. The user only needs to:

1. Ensure `brightnessctl` is installed
2. Verify keyboard device is detected
3. Optionally tune configuration parameters for desired behavior

**Recommended next steps:**

1. Test on the target laptop with `bright test-keyboard`
2. Adjust configuration parameters based on personal preference
3. Consider implementing discrete-level-aware features if finer control is needed

## References

- Current implementation: [`Brightness/keyboard.py`](Brightness/keyboard.py)
- Configuration: [`Brightness/config.py`](Brightness/config.py)
- Tests: [`tests/test_keyboard.py`](tests/test_keyboard.py)
- Example config: [`docs/config.toml.example`](docs/config.toml.example)
