# Code Review Findings

**Project:** bright (Monitor Brightness Control)
**Review Date:** 2025-12-30
**Reviewer:** Code Review Assistant

---

## Executive Summary

This code review covers the `bright` project, a Python CLI tool for controlling monitor brightness on Linux systems (X11 and Wayland). The project provides a unified interface for adjusting both hardware backlight and software gamma correction.

Overall, the code is functional and well-structured for its purpose. However, several improvements are recommended in documentation, error handling, and project instrumentation.

---

## 1. README.md Status

### Finding: Missing README.md

**Severity:** High
**Location:** Project root

The project is missing a `README.md` file entirely. This is a critical documentation gap.

**Recommendation:** Create a comprehensive README.md that includes:

1. **Project description** - What the tool does and why it's useful
2. **Installation instructions** - How to install via pip/pipx
3. **Usage examples** - Command-line usage with examples
4. **Dependencies** - System requirements (xrandr, wl-gammarelay-rs, backlight permissions)
5. **Features** - Three-range brightness control (dark gamma, hardware, bright gamma)
6. **Limitations** - Linux-only, requires specific hardware paths, permission requirements
7. **Configuration** - How brightness levels are stored (~/.local/share/brightness_level)
8. **Troubleshooting** - Common issues and solutions

**Suggested README.md structure:**

```markdown
# bright

Simple CLI tool for controlling monitor brightness on Linux.

## Features
- Hardware backlight control via sysfs
- Software gamma correction for extended range
- Wayland support via wl-gammarelay-rs
- X11 support via xrandr

## Installation
pip install bright

## Usage
bright max    # Maximum brightness
bright min    # Minimum brightness
bright +      # Increase brightness
bright -      # Decrease brightness

## Requirements
- Linux with backlight support
- For Wayland: wl-gammarelay-rs
- For X11: xrandr
- Write access to /sys/class/backlight/*/brightness

## License
[Add license]
```

---

## 2. Code Structure and Organization

### Finding 2.1: Good Module Separation

**Severity:** Informational
**Location:** [`Brightness/`](../Brightness/)

The code is well-organized into three modules:
- [`__init__.py`](../Brightness/__init__.py:1) - Public API exports
- [`cli.py`](../Brightness/cli.py:1) - CLI interface using Click
- [`logic.py`](../Brightness/logic.py:1) - Core business logic

**Status:** ✅ Good

### Finding 2.2: Commented-Out Code

**Severity:** Low
**Location:** [`Brightness/cli.py:5-29`](../Brightness/cli.py:5)

The file contains commented-out argparse implementation that should be removed.

**Recommendation:** Remove the commented-out code block (lines 5-29) as it's no longer needed and clutters the file.

### Finding 2.3: Import Inside Function

**Severity:** Low
**Location:** [`Brightness/logic.py:49`](../Brightness/logic.py:49), [`Brightness/logic.py:337`](../Brightness/logic.py:337)

The `time` module is imported inside functions rather than at the top of the file.

**Recommendation:** Move `import time` to the top of the file with other imports for consistency and slight performance improvement.

---

## 3. Code Quality and Style

### Finding 3.1: Typo in Function Parameter

**Severity:** Low
**Location:** [`Brightness/logic.py:111`](../Brightness/logic.py:111)

The function `get_brightness_range` has a parameter named `brighness_level` (missing 't').

**Recommendation:** Rename to `brightness_level` for correctness.

### Finding 3.2: Use of os.system()

**Severity:** Medium
**Location:** [`Brightness/logic.py:221`](../Brightness/logic.py:221), [`Brightness/logic.py:263`](../Brightness/logic.py:263)

The code uses `os.system()` for xrandr commands, which is less secure and doesn't capture output/errors.

**Recommendation:** Replace with `subprocess.run()` for consistency with other subprocess calls in the codebase:

```python
subprocess.run(
    ["xrandr", "--output", primary_monitor, "--gamma", str(gamma_range), "--brightness", str(brightness)],
    capture_output=True
)
```

### Finding 3.3: Magic Numbers

**Severity:** Low
**Location:** [`Brightness/logic.py:166`](../Brightness/logic.py:166)

The alpha value `1.4` in `exp_range` call is a magic number.

**Recommendation:** Define as a named constant:

```python
HARDWARE_BRIGHTNESS_ALPHA = 1.4
```

### Finding 3.4: Hardcoded Paths

**Severity:** Medium
**Location:** [`Brightness/logic.py:129-132`](../Brightness/logic.py:129)

Backlight paths are hardcoded in a list. While this covers common cases, it may not work on all systems.

**Recommendation:** Consider:
1. Adding a configuration option for custom paths
2. Dynamically discovering paths from `/sys/class/backlight/`
3. Documenting supported hardware in README

---

## 4. Potential Bugs and Edge Cases

### Finding 4.1: Missing Error Handling for Brightness File Write

**Severity:** Medium
**Location:** [`Brightness/logic.py:167-168`](../Brightness/logic.py:167)

Writing to brightness file may fail due to permissions, but no error handling exists.

**Recommendation:** Add try/except with informative error message:

```python
try:
    with open(str(path / "brightness"), "w") as f:
        f.write(str(new_brightness))
except PermissionError:
    raise PermissionError(
        f"Cannot write to {path}/brightness. "
        "Try adding user to 'video' group or using udev rules."
    )
```

### Finding 4.2: Race Condition in wl-gammarelay-rs Start

**Severity:** Low
**Location:** [`Brightness/logic.py:42-50`](../Brightness/logic.py:42)

The `start_wl_gammarelay()` function uses a fixed 0.5s sleep which may not be sufficient on slow systems.

**Recommendation:** Implement a retry loop with exponential backoff:

```python
def start_wl_gammarelay():
    if not is_wl_gammarelay_running():
        subprocess.Popen(...)
        for _ in range(10):
            time.sleep(0.1)
            if is_wl_gammarelay_running():
                return
        raise RuntimeError("Failed to start wl-gammarelay-rs")
```

### Finding 4.3: Empty Primary Monitor Return

**Severity:** Medium
**Location:** [`Brightness/logic.py:327`](../Brightness/logic.py:327)

`get_primary_monitor()` returns empty string if no primary monitor found, which could cause silent failures.

**Recommendation:** Raise an exception instead:

```python
raise RuntimeError("No primary monitor found. Check xrandr output.")
```

### Finding 4.4: CLI Invalid Operation Handling

**Severity:** Low
**Location:** [`Brightness/cli.py:48`](../Brightness/cli.py:48)

Invalid operations just print a message but don't return a non-zero exit code.

**Recommendation:** Use Click's error handling:

```python
else:
    raise click.BadParameter(f"Invalid operation: {operation}")
```

---

## 5. Project Instrumentation

### Finding 5.1: Justfile Actions

**Status:** ✅ Now Present (Added in this review)

The following justfile actions are now defined:
- `setup` - Install dependencies and pre-commit hooks
- `format` - Run formatting hooks
- `test` - Run pytest with coverage
- `validate` - Run all pre-commit hooks

Additional useful actions added:
- `typecheck` - Run pyright
- `package` - Build wheel
- `clean` - Clean artifacts
- `test-package` - Smoke test the built package

### Finding 5.2: Pre-commit Hooks

**Status:** ✅ Now Present (Added in this review)

Pre-commit configuration includes:
- Code formatting: ruff, ruff-format, beautysh
- Linting: ruff, yamllint, shell-lint
- Security: ripsecrets
- Type checking: pyright
- Spell checking: codespell
- File hygiene: end-of-file-fixer, trailing-whitespace, mixed-line-ending
- Validation: check-json, check-toml, check-yaml, poetry-check

---

## 6. Files Not in Repository - Analysis

### Finding 6.1: New Files Added (Should Be Committed)

The following files were created during this review and should be added to the repository:

| File | Purpose | Recommendation |
|------|---------|----------------|
| `.pre-commit-config.yaml` | Pre-commit hook configuration | **Add to repo** |
| `justfile` | Task automation | **Add to repo** |
| `poetry.toml` | Poetry configuration | **Add to repo** |
| `tests/pytest.ini` | Pytest configuration | **Add to repo** |
| `tests/test_logic.py` | Unit tests for logic module | **Add to repo** |
| `tests/test_cli.py` | Unit tests for CLI module | **Add to repo** |
| `scripts/test-package.sh` | Package smoke test | **Add to repo** |
| `docs/README.md` | Documentation directory readme | **Add to repo** |
| `docs/code-review-findings.md` | This document | **Add to repo** |

### Finding 6.2: Missing Files That Should Be Created

| File | Purpose | Priority |
|------|---------|----------|
| `README.md` | Project documentation | **High** |
| `LICENSE` | License file | **High** |
| `CHANGELOG.md` | Version history | Medium |
| `CONTRIBUTING.md` | Contribution guidelines | Low |
| `py.typed` | PEP 561 marker for type hints | Low |

---

## 7. Recommendations Summary

### High Priority

1. **Create README.md** with installation, usage, and requirements
2. **Add LICENSE file** to clarify usage terms
3. **Add error handling** for brightness file writes (permission errors)
4. **Replace os.system()** with subprocess.run() for xrandr calls

### Medium Priority

5. **Fix typo** in `brighness_level` parameter name
6. **Improve primary monitor detection** error handling
7. **Add CLI exit codes** for invalid operations
8. **Document system requirements** (backlight permissions, wl-gammarelay-rs)

### Low Priority

9. **Remove commented-out code** in cli.py
10. **Move imports to top** of logic.py
11. **Define magic numbers** as named constants
12. **Add type hints** to all functions for better IDE support

---

## 8. Positive Observations

1. **Good separation of concerns** - CLI, logic, and exports are well-separated
2. **Wayland and X11 support** - Handles both display servers
3. **Caching** - Primary monitor is cached to avoid repeated xrandr calls
4. **Graceful fallback** - Multiple backlight paths are tried
5. **Click for CLI** - Modern CLI framework with good UX
6. **Exponential brightness scaling** - Better perceptual brightness control

---

## Appendix: Files Reviewed

- [`Brightness/__init__.py`](../Brightness/__init__.py)
- [`Brightness/cli.py`](../Brightness/cli.py)
- [`Brightness/logic.py`](../Brightness/logic.py)
- [`pyproject.toml`](../pyproject.toml)
- [`.gitignore`](../.gitignore)
