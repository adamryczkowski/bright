# Keyboard Backlight Configuration Summary

**Date:** 2025-01-12
**Configuration File:** [`config.toml`](../config.toml)
**Target:** 3-level keyboard backlight (OFF/HALF/FULL)

## Requirements

- **Screen brightness > 60%**: Keyboard OFF
- **Screen brightness 20-60%**: Keyboard FULL
- **Screen brightness < 20%**: Keyboard HALF

## Configuration

```toml
[keyboard]
disable_threshold = 18      # OFF when screen ≥ 18 (≥ 60%)
max_backlight_level = 17    # Upper bound of active range
min_backlight_level = 5     # Lower bound (just below 20%)
max_power = 1.0             # Power at level 17
min_power = 0.74            # Power at levels 0-5
gamma = 1.0                 # Linear interpolation
```

## How It Works

### Brightness Scale
- **30 levels total** (0-29)
- **60% = level 18** (levels 0-17 are below 60%)
- **20% = level 6** (levels 0-5 are below 20%)

### Power Calculation Logic

From [`Brightness/keyboard.py:197-240`](../Brightness/keyboard.py:197):

```python
if screen_brightness >= disable_threshold:
    return 0.0  # OFF
if screen_brightness <= min_backlight_level:
    return min_power  # 0.74
if screen_brightness >= max_backlight_level:
    return max_power  # 1.0
# Otherwise: interpolate with gamma correction
linear_ratio = (screen_brightness - min_backlight_level) / (max_backlight_level - min_backlight_level)
gamma_ratio = linear_ratio ^ gamma
power = min_power + gamma_ratio * (max_power - min_power)
```

### Hardware Level Mapping

From [`Brightness/keyboard.py:309`](../Brightness/keyboard.py:309):

```python
level = round(power * max_level)  # max_level = 2 for 3-level keyboard
```

| Power Range | Hardware Level | Keyboard State |
|-------------|----------------|----------------|
| 0.00 - 0.24 | 0 | OFF |
| 0.25 - 0.74 | 1 | HALF |
| 0.75 - 1.00 | 2 | FULL |

## Behavior Verification

| Screen Level | Condition | Power Calculation | Power | HW Level | State | ✓ |
|--------------|-----------|-------------------|-------|----------|-------|---|
| 29 | ≥ 18 | disabled | 0.00 | 0 | OFF | ✓ |
| 20 | ≥ 18 | disabled | 0.00 | 0 | OFF | ✓ |
| 18 | ≥ 18 | disabled | 0.00 | 0 | OFF | ✓ |
| 17 | = max | max_power | 1.00 | 2 | FULL | ✓ |
| 15 | interpolate | 0.74 + (10/12)×0.26 | 0.957 | 2 | FULL | ✓ |
| 12 | interpolate | 0.74 + (7/12)×0.26 | 0.891 | 2 | FULL | ✓ |
| 10 | interpolate | 0.74 + (5/12)×0.26 | 0.848 | 2 | FULL | ✓ |
| 8 | interpolate | 0.74 + (3/12)×0.26 | 0.805 | 2 | FULL | ✓ |
| 6 | interpolate | 0.74 + (1/12)×0.26 | 0.762 | 2 | FULL | ✓ |
| 5 | ≤ min | min_power | 0.74 | 1 | HALF | ✓ |
| 3 | ≤ min | min_power | 0.74 | 1 | HALF | ✓ |
| 0 | ≤ min | min_power | 0.74 | 1 | HALF | ✓ |

**All requirements met!** ✓

## Installation

1. Copy the configuration file:
   ```bash
   mkdir -p ~/.config/bright
   cp config.toml ~/.config/bright/config.toml
   ```

2. Test keyboard detection:
   ```bash
   bright test-keyboard
   ```

3. Test at different brightness levels:
   ```bash
   bright 29  # Should show keyboard OFF
   bright 17  # Should show keyboard FULL
   bright 6   # Should show keyboard FULL
   bright 5   # Should show keyboard HALF
   bright 0   # Should show keyboard HALF
   ```

## Key Insight

The critical configuration value is **`min_power = 0.74`**, which:
- Is just below the 0.75 threshold for FULL (rounds to HALF at levels 0-5)
- Ensures that even at level 6 (20%), the interpolated power (0.762) exceeds 0.75 for FULL
- Provides smooth linear transition from FULL to HALF at exactly the 20% boundary

## Adjustments

If the transition point needs fine-tuning:

- **Move transition lower** (more FULL): Increase `min_power` to 0.75-0.80
- **Move transition higher** (more HALF): Decrease `min_power` to 0.70-0.73
- **Sharper transition**: Increase `gamma` to 2.0 or higher
- **Gentler transition**: Decrease `gamma` to 0.5-0.9

## References

- Main implementation: [`Brightness/keyboard.py`](../Brightness/keyboard.py)
- Detailed analysis: [`docs/keyboard-backlight-3-level-adaptation-plan.md`](keyboard-backlight-3-level-adaptation-plan.md)
- Configuration example: [`docs/config.toml.example`](config.toml.example)
