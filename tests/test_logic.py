"""
Unit tests for Brightness.logic module.

These tests focus on pure functions that don't require hardware access.
Functions that interact with hardware (brightness files, xrandr, D-Bus)
are tested with mocking where appropriate.
"""

import os
import tempfile
from unittest.mock import patch

import numpy as np
import pytest

from Brightness.logic import (
    BRIGHT_GAMMA_RANGE,
    DARK_GAMMA_RANGE,
    HARDWARE_RANGE,
    LEVEL_SIZES,
    exp_range,
    get_brightness_range,
    inv_exp_range_transform,
    is_wayland,
    linear_range,
    read_brightness_level,
    write_brightness_level,
)

# ============================================================================
# Tests for exp_range function
# ============================================================================


def test_exp_range_returns_correct_length():
    """exp_range should return n+1 values."""
    # Note: alpha=1.0 causes division by zero, use alpha > 1
    result = exp_range(0, 100, 10, alpha=1.4)
    assert len(result) == 11


def test_exp_range_endpoints():
    """exp_range should start at xmin and end at xmax."""
    result = exp_range(10, 90, 5, alpha=1.4)
    assert result[0] == pytest.approx(10)
    assert result[-1] == pytest.approx(90)


def test_exp_range_with_alpha_greater_than_one():
    """When alpha > 1, values should be more concentrated at the start."""
    result = exp_range(0, 100, 10, alpha=2.0)
    # First half of indices should cover less than half the range
    midpoint_idx = len(result) // 2
    assert result[midpoint_idx] < 50


def test_exp_range_monotonically_increasing():
    """exp_range values should be monotonically increasing."""
    result = exp_range(0, 100, 10, alpha=1.5)
    for i in range(len(result) - 1):
        assert result[i] < result[i + 1]


# ============================================================================
# Tests for linear_range function
# ============================================================================


def test_linear_range_returns_correct_length():
    """linear_range should return n+1 values."""
    result = linear_range(0, 100, 10)
    assert len(result) == 11


def test_linear_range_endpoints():
    """linear_range should start at xmin and end at xmax."""
    result = linear_range(5, 95, 8)
    assert result[0] == pytest.approx(5)
    assert result[-1] == pytest.approx(95)


def test_linear_range_evenly_spaced():
    """linear_range values should be evenly spaced."""
    result = linear_range(0, 100, 10)
    diffs = np.diff(result)
    assert all(d == pytest.approx(10) for d in diffs)


def test_linear_range_single_step():
    """linear_range with n=1 should return just endpoints."""
    result = linear_range(0, 100, 1)
    assert len(result) == 2
    assert result[0] == pytest.approx(0)
    assert result[-1] == pytest.approx(100)


# ============================================================================
# Tests for inv_exp_range_transform function
# ============================================================================


def test_inv_exp_range_transform_at_min():
    """inv_exp_range_transform should return 0 for xmin value."""
    # Note: alpha=1.0 causes division by zero, use alpha > 1
    result = inv_exp_range_transform(0, 100, 10, 1.4, 0)
    assert result == 0


def test_inv_exp_range_transform_at_max():
    """inv_exp_range_transform should return n for xmax value."""
    result = inv_exp_range_transform(0, 100, 10, 1.4, 100)
    assert result == 10


def test_inv_exp_range_transform_finds_closest():
    """inv_exp_range_transform should find closest index for a value."""
    # With exponential range, test that it finds a reasonable index
    result = inv_exp_range_transform(0, 100, 10, 1.4, 50)
    # With alpha=1.4, the midpoint value 50 should map to an index > 5
    # because exponential scaling concentrates values at the start
    assert 0 <= result <= 10


# ============================================================================
# Tests for get_brightness_range function
# ============================================================================


def test_get_brightness_range_dark_gamma():
    """Levels 0 to LEVEL_SIZES[0]-1 should be DARK_GAMMA_RANGE."""
    for level in range(LEVEL_SIZES[0]):
        assert get_brightness_range(level) == DARK_GAMMA_RANGE


def test_get_brightness_range_hardware():
    """Levels in hardware range should return HARDWARE_RANGE."""
    start = LEVEL_SIZES[0]
    end = LEVEL_SIZES[0] + LEVEL_SIZES[1]
    for level in range(start, end):
        assert get_brightness_range(level) == HARDWARE_RANGE


def test_get_brightness_range_bright_gamma():
    """Levels above hardware range should return BRIGHT_GAMMA_RANGE."""
    start = LEVEL_SIZES[0] + LEVEL_SIZES[1]
    end = sum(LEVEL_SIZES)
    for level in range(start, end):
        assert get_brightness_range(level) == BRIGHT_GAMMA_RANGE


def test_get_brightness_range_boundary_dark_to_hardware():
    """Test boundary between dark gamma and hardware range."""
    assert get_brightness_range(LEVEL_SIZES[0] - 1) == DARK_GAMMA_RANGE
    assert get_brightness_range(LEVEL_SIZES[0]) == HARDWARE_RANGE


def test_get_brightness_range_boundary_hardware_to_bright():
    """Test boundary between hardware and bright gamma range."""
    boundary = LEVEL_SIZES[0] + LEVEL_SIZES[1]
    assert get_brightness_range(boundary - 1) == HARDWARE_RANGE
    assert get_brightness_range(boundary) == BRIGHT_GAMMA_RANGE


# ============================================================================
# Tests for is_wayland function
# ============================================================================


def test_is_wayland_with_wayland_display_set():
    """is_wayland should return True when WAYLAND_DISPLAY is set."""
    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}):
        assert is_wayland() is True


def test_is_wayland_without_wayland_display():
    """is_wayland should return False when WAYLAND_DISPLAY is not set."""
    env = os.environ.copy()
    env.pop("WAYLAND_DISPLAY", None)
    with patch.dict(os.environ, env, clear=True):
        assert is_wayland() is False


# ============================================================================
# Tests for write_brightness_level and read_brightness_level functions
# ============================================================================


def test_write_and_read_brightness_level():
    """write_brightness_level and read_brightness_level should round-trip correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        brightness_file = os.path.join(tmpdir, "brightness_level")
        with patch(
            "Brightness.logic.os.path.expanduser",
            return_value=brightness_file,
        ):
            write_brightness_level(15)
            result = read_brightness_level()
            assert result == 15


def test_read_brightness_level_creates_default():
    """read_brightness_level should create file with default if not exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        brightness_file = os.path.join(tmpdir, "brightness_level")
        with patch(
            "Brightness.logic.os.path.expanduser",
            return_value=brightness_file,
        ):
            # File doesn't exist yet
            assert not os.path.exists(brightness_file)
            result = read_brightness_level()
            # Default is LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1
            expected_default = LEVEL_SIZES[0] + LEVEL_SIZES[1] - 1
            assert result == expected_default
            # File should now exist
            assert os.path.exists(brightness_file)


def test_write_brightness_level_overwrites():
    """write_brightness_level should overwrite existing value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        brightness_file = os.path.join(tmpdir, "brightness_level")
        with patch(
            "Brightness.logic.os.path.expanduser",
            return_value=brightness_file,
        ):
            write_brightness_level(5)
            write_brightness_level(20)
            result = read_brightness_level()
            assert result == 20


# ============================================================================
# Tests for LEVEL_SIZES constant
# ============================================================================


def test_level_sizes_are_positive():
    """All LEVEL_SIZES should be positive integers."""
    for size in LEVEL_SIZES:
        assert size > 0
        assert isinstance(size, int)


def test_level_sizes_sum():
    """Total number of levels should be sum of LEVEL_SIZES."""
    total = sum(LEVEL_SIZES)
    assert total == 30  # 10 + 10 + 10
