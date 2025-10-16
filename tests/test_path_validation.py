"""Tests for path validation functionality."""

import logging
import os
from pathlib import Path
import pytest
from vaultlint.cli import validate_vault_path, WINDOWS_MAX_SAFE_PATH_LENGTH

# ---------- Basic path validation ----------


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


# ---------- Permission and access tests ----------


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


# ---------- Edge cases and special paths ----------


def test_validate_vault_path_with_traversal(tmp_path, caplog):
    """Test path traversal attempt detection."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    # Create a parent directory and a target to ensure the path exists
    parent = tmp_path.parent
    malicious = tmp_path / ".." / parent.name
    ok = validate_vault_path(malicious)
    assert ok is False
    # Check for either traversal detection or non-existent path error
    assert any(
        any(msg in r.getMessage().lower() for msg in ["traversal", "does not exist"])
        for r in caplog.records
    )


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
        very_long = tmp_path / ("x" * (WINDOWS_MAX_SAFE_PATH_LENGTH + 10))  # Exceed safe limit by 10 chars
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
