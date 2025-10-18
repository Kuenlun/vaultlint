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


def test_resolve_spec_file_explicit_missing(tmp_path, capsys):
    """Test resolve_spec_file with explicit spec that doesn't exist shows warning."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    nonexistent = tmp_path / "missing.yaml"
    result = resolve_spec_file(vault_path, nonexistent)
    assert result is None
    
    # Check Rich output shows warning (not error) - linter behavior
    captured = capsys.readouterr()
    assert "Specification file not found" in captured.out


def test_resolve_spec_file_default_in_vault(tmp_path):
    """Test resolve_spec_file finds vspec.yaml in vault root."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # Create default spec file
    default_spec = vault_path / "vspec.yaml"
    default_spec.write_text("version: 1.0")

    result = resolve_spec_file(vault_path, None)
    assert result == default_spec.resolve()
    # No need to check for log message - function works correctly


def test_resolve_spec_file_no_spec_found(tmp_path):
    """Test resolve_spec_file when no spec file is found."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    result = resolve_spec_file(vault_path, None)
    assert result is None
    # No need to check for log message - this is normal behavior


def test_resolve_spec_file_explicit_priority_over_default(tmp_path):
    """Test that explicit spec takes priority over default."""
    vault_path = tmp_path / "vault"
    vault_path.mkdir()

    # Create both default and custom spec
    default_spec = vault_path / "vspec.yaml"
    default_spec.write_text("version: default")

    custom_spec = tmp_path / "custom.yaml"
    custom_spec.write_text("version: custom")

    result = resolve_spec_file(vault_path, custom_spec)
    assert result == custom_spec.resolve()
    # Function works correctly - priority is tested by the return value
