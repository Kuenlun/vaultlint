"""Tests for specification file resolution functionality."""

import logging

from vaultlint.cli import resolve_spec_file


# ---------- Specification file resolution ----------


def test_resolve_spec_file_explicit_exists(tmp_path):
    """Test resolve_spec_file with explicit spec that exists."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    spec_file = tmp_path / "custom.yaml"
    spec_file.write_text("version: 1.0")

    result = resolve_spec_file(vault_path, spec_file)
    assert result == spec_file.resolve()


def test_resolve_spec_file_explicit_missing(tmp_path, caplog):
    """Test resolve_spec_file with explicit spec that doesn't exist."""
    caplog.set_level(logging.ERROR, logger="vaultlint.cli")
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    nonexistent = tmp_path / "missing.yaml"
    result = resolve_spec_file(vault_path, nonexistent)
    assert result is None
    assert any(
        "Could not resolve specified spec file" in r.getMessage()
        for r in caplog.records
    )


def test_resolve_spec_file_default_in_vault(tmp_path, caplog):
    """Test resolve_spec_file finds vspec.yaml in vault root."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # Create default spec file
    default_spec = vault_path / "vspec.yaml"
    default_spec.write_text("version: 1.0")

    result = resolve_spec_file(vault_path, None)
    assert result == default_spec.resolve()
    assert any(
        "Found specification file in vault root" in r.getMessage()
        for r in caplog.records
    )


def test_resolve_spec_file_no_spec_found(tmp_path, caplog):
    """Test resolve_spec_file when no spec file is found."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    result = resolve_spec_file(vault_path, None)
    assert result is None
    assert any("No specification file found" in r.getMessage() for r in caplog.records)


def test_resolve_spec_file_explicit_priority_over_default(tmp_path, caplog):
    """Test that explicit spec takes priority over default."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # Create both default and custom spec
    default_spec = vault_path / "vspec.yaml"
    default_spec.write_text("version: default")

    custom_spec = tmp_path / "custom.yaml"
    custom_spec.write_text("version: custom")

    result = resolve_spec_file(vault_path, custom_spec)
    assert result == custom_spec.resolve()
    assert any("Using specification file" in r.getMessage() for r in caplog.records)
    # Should not mention finding default spec
    assert not any(
        "Found specification file in vault root" in r.getMessage()
        for r in caplog.records
    )
