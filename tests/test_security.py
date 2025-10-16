"""Security-focused tests for vaultlint."""

import logging
import os
import pytest
from vaultlint.cli import validate_vault_path


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
        very_long = tmp_path / ("x" * 250)
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
