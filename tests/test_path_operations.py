"""Tests for path resolution and validation operations."""

import logging
import os
from pathlib import Path
import pytest

from vaultlint.cli import (
    _resolve_path_safely,
    validate_vault_path,
    WINDOWS_MAX_SAFE_PATH_LENGTH,
)


# ---------- Path resolution functions ----------


def test_resolve_path_safely_existing_path(tmp_path):
    """Test _resolve_path_safely with existing path."""
    result = _resolve_path_safely(tmp_path)
    assert result is not None
    assert result.is_absolute()
    assert result.exists()


def test_resolve_path_safely_nonexistent_path(caplog):
    """Test _resolve_path_safely with non-existent path."""
    caplog.set_level(logging.ERROR, logger="vaultlint.cli")
    nonexistent = Path("/definitely/does/not/exist")
    result = _resolve_path_safely(nonexistent)
    assert result is None
    assert any("does not exist" in r.getMessage() for r in caplog.records)


def test_resolve_path_safely_expanduser(tmp_path, monkeypatch):
    """Test _resolve_path_safely expands user home."""
    # Create a test file in tmp_path to make it exist
    test_file = tmp_path / "test_file.txt"
    test_file.write_text("test")

    # Mock expanduser to return our tmp_path when called with "~"
    original_expanduser = Path.expanduser

    def fake_expanduser(self):
        if str(self) == "~":
            return tmp_path
        return original_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", fake_expanduser)

    result = _resolve_path_safely(Path("~"))
    assert result is not None
    assert result == tmp_path.resolve()


# ---------- Vault path validation ----------


def test_validate_vault_path_ok(tmp_path, caplog):
    """Test basic validation of a valid path."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    ok = validate_vault_path(tmp_path)
    assert ok is True
    # No error-level logs expected
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_validate_vault_path_nonexistent(tmp_path, caplog):
    """Test validation of a nonexistent path."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    missing = tmp_path / "does-not-exist"
    ok = validate_vault_path(missing)
    assert ok is False
    assert any("does not exist" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_file_instead_of_dir(tmp_path, caplog):
    """Test validation when path points to a file instead of directory."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    f = tmp_path / "file.txt"
    f.write_text("hi")
    ok = validate_vault_path(f)
    assert ok is False
    assert any("is not a directory" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_permission_error_simulated(tmp_path, caplog, monkeypatch):
    """Simulate PermissionError on iterdir in a cross-platform safe way."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    real_iterdir = Path.iterdir

    def guarded_iterdir(self):
        if self.resolve() == tmp_path.resolve():
            raise PermissionError("simulated permission denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    ok = validate_vault_path(tmp_path)
    assert ok is False
    assert any("not readable" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_warns_when_os_access_fails(tmp_path, caplog, monkeypatch):
    """Test warning when os.access reports limited permissions."""
    caplog.set_level(logging.WARNING, logger="vaultlint.cli")
    monkeypatch.setattr(os, "access", lambda *_args, **_kw: False)
    ok = validate_vault_path(tmp_path)
    assert ok is True
    assert any("may not be fully accessible" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_with_traversal(tmp_path, caplog):
    """Test that path traversal to existing directories works correctly.

    Note: This function no longer prevents path traversal - it simply validates
    that the resolved path exists and is accessible. Path traversal prevention
    is not needed for a CLI tool where users specify vault directories.
    """
    caplog.set_level(logging.INFO, logger="vaultlint.cli")

    # Test 1: Navigate to parent directory using ".."
    parent = tmp_path.parent
    traversal_to_parent = tmp_path / ".."

    # This should succeed because it resolves to the parent directory which exists
    ok = validate_vault_path(traversal_to_parent)
    assert ok is True  # Parent directory should exist and be accessible

    # Test 2: Create a non-existent traversal path
    nonexistent_traversal = tmp_path / ".." / "nonexistent_directory_12345"
    ok_nonexistent = validate_vault_path(nonexistent_traversal)
    assert ok_nonexistent is False
    assert any("does not exist" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_unicode(tmp_path, caplog):
    """Test Unicode path handling."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    unicode_path = tmp_path / "测试"
    unicode_path.mkdir()
    ok = validate_vault_path(unicode_path)
    assert ok is True


def test_validate_vault_path_long_path(tmp_path, caplog):
    """Test handling of excessively long paths."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    if os.name == "nt":  # Windows specific test
        very_long = tmp_path / (
            "x" * (WINDOWS_MAX_SAFE_PATH_LENGTH + 10)
        )  # Exceed safe limit by 10 chars
        ok = validate_vault_path(very_long)
        assert ok is False
        assert any(
            "maximum safe length" in r.getMessage().lower() for r in caplog.records
        )


def test_validate_vault_path_symlink(tmp_path, caplog):
    """Test strict symlink resolution."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "link"
    try:
        symlink.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation not supported")

    ok = validate_vault_path(symlink)
    # Should succeed since it's a valid symlink
    assert ok is True


def test_path_traversal_behavior_documentation(tmp_path):
    """Regression test to document path traversal behavior.

    This test exists to prevent accidental re-introduction of broken
    path traversal validation logic. The validate_vault_path function
    should NOT attempt to prevent path traversal - it should simply
    validate that the resolved path exists and is accessible.

    If someone tries to add path traversal validation in the future,
    this test will help ensure it's implemented correctly.
    """
    from vaultlint.cli import validate_vault_path

    # Create a test scenario
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    # Path that traverses up and then down - should work if target exists
    traversal_path = subdir / ".." / "subdir"  # Points back to subdir

    # This should succeed because it resolves to an existing directory
    result = validate_vault_path(traversal_path)
    assert result is True  # Should pass validation

    # Verify it actually resolves to the same directory
    assert traversal_path.resolve() == subdir.resolve()

    # A path that traverses to non-existent location should fail
    bad_traversal = subdir / ".." / "nonexistent"
    result_bad = validate_vault_path(bad_traversal)
    assert result_bad is False  # Should fail because directory doesn't exist
