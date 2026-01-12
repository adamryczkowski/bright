# Installation Instructions for Keyboard Backlight Configuration

## Quick Start

Copy the configuration file to your home directory:

```bash
mkdir -p ~/.config/bright
cp config.toml ~/.config/bright/config.toml
```

## Test the Configuration

After copying the file, test at different brightness levels:

```bash
# Test at maximum brightness (level 19) - keyboard should be OFF
bright max
# Expected output: Level: 19, Keyboard RGB: #000000 (0, 0, 0)

# Test at minimum brightness (level 9) - keyboard should be FULL
bright min
# Expected output: Level: 9, Keyboard RGB: #BEBEBE (190, 190, 190) or similar

# Test at very low brightness (level 5) - keyboard should be HALF
bright 5
# Expected output: Level: 5, Keyboard RGB: #949494 (148, 148, 148) or similar

# Test at 20% threshold (level 6) - keyboard should be FULL
bright 6
# Expected output: Level: 6, Keyboard RGB: #C2C2C2 (194, 194, 194) or similar
```

## Expected Behavior

| Screen Brightness | Level | Keyboard State | Approximate RGB |
|-------------------|-------|----------------|-----------------|
| > 60% | 18-29 | OFF | #000000 (0, 0, 0) |
| 20-60% | 6-17 | FULL | #C2C2C2 to #FFFFFF |
| < 20% | 0-5 | HALF | #949494 (148, 148, 148) |

## Verify Configuration is Loaded

Check that your configuration file exists:

```bash
ls -la ~/.config/bright/config.toml
```

If the file doesn't exist, the system will use default values which won't match the desired behavior.

## Troubleshooting

### Configuration Not Applied

If you see RGB values but they don't match expectations:

1. **Verify config file location:**
   ```bash
   cat ~/.config/bright/config.toml | grep -A 5 "\[keyboard\]"
   ```

2. **Check if brightnessctl is detected:**
   ```bash
   bright test-keyboard
   ```
   Should show "Active backend: brightnessctl" and max brightness = 2

3. **Manually test brightnessctl:**
   ```bash
   # Find your keyboard device
   brightnessctl --list --class=leds

   # Test setting levels (replace device name as needed)
   brightnessctl --device tpacpi::kbd_backlight set 0  # OFF
   brightnessctl --device tpacpi::kbd_backlight set 1  # HALF
   brightnessctl --device tpacpi::kbd_backlight set 2  # FULL
   ```

### Keyboard Not Responding

If RGB shows #000000 for all levels:

1. **Check if keyboard backlight is enabled:**
   ```bash
   grep "enabled" ~/.config/bright/config.toml
   ```
   Should show `enabled = true`

2. **Check permissions:**
   ```bash
   # Add user to video group if needed
   sudo usermod -aG video $USER
   # Log out and back in for changes to take effect
   ```

3. **Verify brightnessctl works:**
   ```bash
   brightnessctl --device tpacpi::kbd_backlight max
   # Should return 2
   ```

## Configuration Details

The configuration uses these key values:

```toml
[keyboard]
disable_threshold = 18      # OFF when screen ≥ 18 (≥ 60%)
max_backlight_level = 17    # Upper bound
min_backlight_level = 5     # Just below 20%
max_power = 1.0             # FULL at top of range
min_power = 0.74            # HALF at bottom (critical!)
gamma = 1.0                 # Linear interpolation
```

The `min_power = 0.74` value is critical:
- It's just below 0.75 (the threshold for FULL)
- At levels 0-5: power = 0.74 → rounds to 1 → HALF ✓
- At level 6+: power > 0.75 → rounds to 2 → FULL ✓

## Documentation

For more details, see:
- [`docs/keyboard-config-summary.md`](docs/keyboard-config-summary.md) - Quick reference
- [`docs/keyboard-backlight-3-level-adaptation-plan.md`](docs/keyboard-backlight-3-level-adaptation-plan.md) - Full technical details
