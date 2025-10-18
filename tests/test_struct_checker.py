"""Tests for struct_checker functionality."""

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


def test_struct_checker_skips_when_no_spec_provided():
    """Test struct_checker returns True when no spec_path in context."""
    context = LintContext(vault_path=Path("/vault"), spec_path=None)
    result = struct_checker(context)

    assert result is True  # Should succeed when no spec is required


def test_struct_checker_loads_valid_spec_file():
    """Test struct_checker successfully loads and processes valid YAML spec."""
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


def test_struct_checker_handles_missing_spec_file():
    """Test struct_checker returns False when spec file doesn't exist."""
    nonexistent_spec = Path("/nonexistent/spec.yaml")
    context = LintContext(vault_path=Path("/vault"), spec_path=nonexistent_spec)

    result = struct_checker(context)

    assert result is False  # Should fail when spec file is missing


def test_struct_checker_handles_invalid_yaml():
    """Test struct_checker returns False when spec file contains invalid YAML."""
    invalid_yaml_content = "invalid: yaml: content: [unclosed"  # Invalid YAML

    with temp_yaml_file(invalid_yaml_content) as spec_path:
        context = LintContext(vault_path=Path("/vault"), spec_path=spec_path)
        result = struct_checker(context)

        assert result is False  # Should fail when YAML is invalid


# ---------- load_spec_file utility function tests ----------


def test_load_spec_file_success():
    """Test load_spec_file loads valid YAML correctly."""
    yaml_content = """version: "0.0.1"
structure:
  - type: dir
    name: .obsidian"""

    with temp_yaml_file(yaml_content) as spec_path:
        result = load_spec_file(str(spec_path))

        assert isinstance(result, dict)
        assert result["version"] == "0.0.1"
        assert "structure" in result
        assert isinstance(result["structure"], list)
        assert len(result["structure"]) == 1
        assert result["structure"][0]["type"] == "dir"
        assert result["structure"][0]["name"] == ".obsidian"


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


def test_load_spec_file_loads_yaml_successfully():
    """Test load_spec_file successfully loads and returns YAML content."""
    yaml_content = "version: 1.0\nname: test"

    with temp_yaml_file(yaml_content) as spec_path:
        result = load_spec_file(str(spec_path))

        assert result is not None
        assert isinstance(result, dict)
        assert result["version"] == 1.0  # YAML parses 1.0 as float
        assert result["name"] == "test"


# ---------- Context integration behavior ----------


def test_struct_checker_uses_context_spec_path_correctly():
    """Test struct_checker uses the exact spec_path from context."""
    yaml_content = "version: test"

    with temp_yaml_file(yaml_content) as expected_spec_path:
        # Mock load_spec_file to verify it receives the correct path
        actual_path_received = None

        def mock_load_spec_file(path_str):
            nonlocal actual_path_received
            actual_path_received = path_str
            return {"version": "test"}

        with patch(
            "vaultlint.checks.structure.struct_checker.load_spec_file",
            mock_load_spec_file,
        ):
            context = LintContext(
                vault_path=Path("/vault"), spec_path=expected_spec_path
            )
            struct_checker(context)

            assert actual_path_received == str(expected_spec_path)


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
    yaml_content = "version: 1.0\nallow_extra_dirs: false"  # Any valid YAML

    with temp_yaml_file(yaml_content) as spec_path:
        context = LintContext(vault_path=Path("/vault"), spec_path=spec_path)
        result = struct_checker(context)

        # Current behavior: return True if spec loads (placeholder)
        # This test will need updating when real validation logic is implemented
        assert (
            result is True
        ), "Current implementation should return True for loadable specs"
