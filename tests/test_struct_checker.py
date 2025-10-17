"""Tests for struct_checker functionality."""

import logging
import tempfile
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

from vaultlint.cli import LintContext
from vaultlint.checks.structure.struct_checker import struct_checker, load_spec_file


@contextmanager
def temp_yaml_file(content: str):
    """Context manager for creating temporary YAML files with automatic cleanup."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        yield temp_path
    finally:
        temp_path.unlink(missing_ok=True)  # Cleanup even if file doesn't exist


# ---------- Core contract behavior ----------


def test_struct_checker_skips_when_no_spec_provided(caplog):
    """Test struct_checker returns True and logs when no spec_path in context."""
    caplog.set_level(logging.INFO, logger="vaultlint.checks.structure_checker")

    context = LintContext(vault_path=Path("/vault"), spec_path=None)
    result = struct_checker(context)

    assert result is True
    assert any(
        "No specification file provided" in r.getMessage() for r in caplog.records
    )
    assert any("Skipping structure checks" in r.getMessage() for r in caplog.records)


def test_struct_checker_loads_valid_spec_file(caplog):
    """Test struct_checker successfully loads and processes valid YAML spec."""
    caplog.set_level(logging.INFO, logger="vaultlint.checks.structure_checker")

    yaml_content = """
version: 0.0.1
allow_extra_dirs: false
structure:
  - type: dir
    name: ".obsidian"
"""

    with temp_yaml_file(yaml_content) as spec_path:
        context = LintContext(vault_path=Path("/vault"), spec_path=spec_path)
        result = struct_checker(context)

        assert result is True  # Should succeed when spec loads
        assert any(
            "Loaded specification from" in r.getMessage() for r in caplog.records
        )
        assert any(str(spec_path) in r.getMessage() for r in caplog.records)


def test_struct_checker_handles_missing_spec_file(caplog):
    """Test struct_checker returns False when spec file doesn't exist."""
    caplog.set_level(logging.ERROR, logger="vaultlint.checks.structure_checker")

    nonexistent_spec = Path("/nonexistent/spec.yaml")
    context = LintContext(vault_path=Path("/vault"), spec_path=nonexistent_spec)

    result = struct_checker(context)

    assert result is False
    assert any(
        "Failed to process specification file" in r.getMessage() for r in caplog.records
    )


def test_struct_checker_handles_invalid_yaml(caplog):
    """Test struct_checker returns False when spec file contains invalid YAML."""
    caplog.set_level(logging.ERROR, logger="vaultlint.checks.structure_checker")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [unclosed")  # Invalid YAML
        spec_path = Path(f.name)

    try:
        context = LintContext(vault_path=Path("/vault"), spec_path=spec_path)
        result = struct_checker(context)

        assert result is False
        assert any(
            "Failed to process specification file" in r.getMessage()
            for r in caplog.records
        )
    finally:
        spec_path.unlink()


# ---------- load_spec_file utility function tests ----------


def test_load_spec_file_success():
    """Test load_spec_file loads valid YAML correctly."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        test_content = {
            "version": "0.0.1",
            "structure": [{"type": "dir", "name": ".obsidian"}],
        }
        f.write(
            """
version: "0.0.1"
structure:
  - type: dir
    name: .obsidian
"""
        )
        spec_path = Path(f.name)

    try:
        result = load_spec_file(str(spec_path))

        assert isinstance(result, dict)
        assert result["version"] == "0.0.1"
        assert "structure" in result
        assert isinstance(result["structure"], list)
    finally:
        spec_path.unlink()


def test_load_spec_file_missing_file():
    """Test load_spec_file raises FileNotFoundError for missing files."""
    nonexistent_path = "/definitely/does/not/exist.yaml"

    try:
        load_spec_file(nonexistent_path)
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "File not found" in str(e)
        # Path normalization may change slashes, so just check the filename is there
        assert "exist.yaml" in str(e)


def test_load_spec_file_logs_success(caplog):
    """Test load_spec_file logs when YAML is loaded successfully."""
    caplog.set_level(logging.INFO, logger="vaultlint.checks.structure_checker")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("version: 1.0")
        spec_path = Path(f.name)

    try:
        load_spec_file(str(spec_path))

        assert any(
            "YAML file loaded successfully" in r.getMessage() for r in caplog.records
        )
    finally:
        spec_path.unlink()


# ---------- Context integration behavior ----------


def test_struct_checker_uses_context_spec_path_correctly():
    """Test struct_checker uses the exact spec_path from context."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("version: test")
        expected_spec_path = Path(f.name)

    # Mock load_spec_file to verify it receives the correct path
    actual_path_received = None

    def mock_load_spec_file(path_str):
        nonlocal actual_path_received
        actual_path_received = path_str
        return {"version": "test"}

    try:
        with patch(
            "vaultlint.checks.structure.struct_checker.load_spec_file",
            mock_load_spec_file,
        ):
            context = LintContext(
                vault_path=Path("/vault"), spec_path=expected_spec_path
            )
            struct_checker(context)

            assert actual_path_received == str(expected_spec_path)
    finally:
        expected_spec_path.unlink()


# ---------- Error resilience ----------


def test_struct_checker_graceful_degradation_philosophy():
    """Test struct_checker philosophy: no spec = success (graceful degradation)."""
    # This test documents the design decision that missing spec is not an error
    # but a graceful degradation scenario

    context_no_spec = LintContext(vault_path=Path("/vault"), spec_path=None)
    result = struct_checker(context_no_spec)

    # Design philosophy: If no spec is provided, assume everything is OK
    # This allows the tool to work even without configuration
    assert (
        result is True
    ), "Missing spec should be treated as success (graceful degradation)"


def test_struct_checker_current_placeholder_behavior():
    """Test current placeholder behavior - always returns True for valid specs."""
    # This test documents the current state and will need updating when real logic is implemented

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("version: 1.0\nallow_extra_dirs: false")  # Any valid YAML
        spec_path = Path(f.name)

    try:
        context = LintContext(vault_path=Path("/vault"), spec_path=spec_path)
        result = struct_checker(context)

        # Current behavior: return True if spec loads (placeholder)
        # This test will need updating when real validation logic is implemented
        assert (
            result is True
        ), "Current implementation should return True for loadable specs"
    finally:
        spec_path.unlink()
