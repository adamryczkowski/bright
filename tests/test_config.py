"""
Unit tests for Brightness.config module.

These tests verify configuration loading, merging, and path resolution.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from Brightness.config import Config

# ============================================================================
# Tests for Config.get_config_paths
# ============================================================================


def test_get_config_paths_returns_list():
    """get_config_paths should return a list of Path objects."""
    paths = Config.get_config_paths()
    assert isinstance(paths, list)
    assert all(isinstance(p, Path) for p in paths)


def test_get_config_paths_includes_user_config():
    """get_config_paths should include user config directory."""
    paths = Config.get_config_paths()
    # Should include ~/.config/bright/config.toml or XDG equivalent
    user_config = Path.home() / ".config" / "bright" / "config.toml"
    assert any(p == user_config for p in paths) or any("bright" in str(p) for p in paths)


def test_get_config_paths_includes_system_config():
    """get_config_paths should include system config directory."""
    paths = Config.get_config_paths()
    system_config = Path("/etc/bright/config.toml")
    assert system_config in paths


def test_get_config_paths_respects_xdg_config_home():
    """get_config_paths should respect XDG_CONFIG_HOME environment variable."""
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/custom/config"}):
        paths = Config.get_config_paths()
        expected = Path("/custom/config/bright/config.toml")
        assert expected in paths


# ============================================================================
# Tests for Config._deep_merge
# ============================================================================


def test_deep_merge_empty_override():
    """_deep_merge with empty override should return base unchanged."""
    base = {"a": 1, "b": {"c": 2}}
    result = Config._deep_merge(base, {})
    assert result == base


def test_deep_merge_simple_override():
    """_deep_merge should override simple values."""
    base = {"a": 1, "b": 2}
    override = {"b": 3}
    result = Config._deep_merge(base, override)
    assert result == {"a": 1, "b": 3}


def test_deep_merge_nested_override():
    """_deep_merge should merge nested dictionaries."""
    base = {"a": {"b": 1, "c": 2}}
    override = {"a": {"b": 10}}
    result = Config._deep_merge(base, override)
    assert result == {"a": {"b": 10, "c": 2}}


def test_deep_merge_add_new_keys():
    """_deep_merge should add new keys from override."""
    base = {"a": 1}
    override = {"b": 2}
    result = Config._deep_merge(base, override)
    assert result == {"a": 1, "b": 2}


def test_deep_merge_does_not_modify_base():
    """_deep_merge should not modify the base dictionary."""
    base = {"a": {"b": 1}}
    override = {"a": {"b": 2}}
    Config._deep_merge(base, override)
    assert base == {"a": {"b": 1}}


# ============================================================================
# Tests for Config.load
# ============================================================================


def test_load_returns_dict():
    """Config.load should return a dictionary."""
    Config.clear_cache()
    config = Config.load()
    assert isinstance(config, dict)


def test_load_includes_default_sections():
    """Config.load should include default configuration sections."""
    Config.clear_cache()
    config = Config.load()
    assert "brightness" in config
    assert "keyboard" in config


def test_load_includes_keyboard_defaults():
    """Config.load should include keyboard configuration defaults."""
    Config.clear_cache()
    config = Config.load()
    keyboard = config["keyboard"]
    assert "enabled" in keyboard
    assert "backend" in keyboard
    assert "disable_threshold" in keyboard
    assert "max_power" in keyboard
    assert "min_power" in keyboard
    assert "base_color" in keyboard


def test_load_from_explicit_path():
    """Config.load should load from explicit path when provided."""
    Config.clear_cache()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[keyboard]\nenabled = false\n")
        f.flush()
        try:
            config = Config.load(config_path=f.name)
            assert config["keyboard"]["enabled"] is False
            # Other defaults should still be present
            assert "backend" in config["keyboard"]
        finally:
            os.unlink(f.name)


def test_load_caches_result():
    """Config.load should cache the result for subsequent calls."""
    Config.clear_cache()
    config1 = Config.load()
    config2 = Config.load()
    assert config1 is config2


def test_load_force_reload_bypasses_cache():
    """Config.load with force_reload should bypass cache."""
    Config.clear_cache()
    config1 = Config.load()
    config2 = Config.load(force_reload=True)
    # They should be equal but not the same object
    assert config1 == config2
    # After force reload, cache is updated
    config3 = Config.load()
    assert config2 is config3


def test_load_handles_missing_file():
    """Config.load should return defaults when config file doesn't exist."""
    Config.clear_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent = Path(tmpdir) / "nonexistent.toml"
        config = Config.load(config_path=str(nonexistent))
        # Should return defaults
        assert config == Config.DEFAULT_CONFIG


def test_load_merges_partial_config():
    """Config.load should merge partial config with defaults."""
    Config.clear_cache()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[keyboard]\nmax_power = 0.5\n")
        f.flush()
        try:
            config = Config.load(config_path=f.name)
            # Custom value should be present
            assert config["keyboard"]["max_power"] == 0.5
            # Default values should still be present
            assert config["keyboard"]["min_power"] == 0.02  # Default
            assert config["keyboard"]["enabled"] is True
        finally:
            os.unlink(f.name)


# ============================================================================
# Tests for Config.clear_cache
# ============================================================================


def test_clear_cache_resets_cached_config():
    """Config.clear_cache should reset the cached configuration."""
    Config.load()
    Config.clear_cache()
    assert Config._cached_config is None


# ============================================================================
# Tests for Config.get_state_file_path
# ============================================================================


def test_get_state_file_path_returns_path():
    """Config.get_state_file_path should return a Path object."""
    Config.clear_cache()
    path = Config.get_state_file_path()
    assert isinstance(path, Path)


def test_get_state_file_path_expands_tilde():
    """Config.get_state_file_path should expand ~ in path."""
    Config.clear_cache()
    path = Config.get_state_file_path()
    assert "~" not in str(path)


# ============================================================================
# Tests for DEFAULT_CONFIG constant
# ============================================================================


def test_default_config_has_required_keys():
    """DEFAULT_CONFIG should have all required configuration keys."""
    assert "brightness" in Config.DEFAULT_CONFIG
    assert "keyboard" in Config.DEFAULT_CONFIG


def test_default_keyboard_config_values():
    """DEFAULT_CONFIG keyboard section should have sensible defaults."""
    keyboard = Config.DEFAULT_CONFIG["keyboard"]
    assert keyboard["enabled"] is True
    assert keyboard["backend"] == "auto"  # auto-detect backend
    assert 0 <= keyboard["max_power"] <= 1
    assert 0 <= keyboard["min_power"] <= 1
    assert keyboard["min_power"] <= keyboard["max_power"]
    assert keyboard["disable_threshold"] >= 0
