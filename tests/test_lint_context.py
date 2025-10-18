"""Tests for LintContext dataclass functionality."""

import pytest
from pathlib import Path
from dataclasses import FrozenInstanceError

from vaultlint.cli import LintContext


# ---------- LintContext creation and basic behavior ----------


def test_lint_context_creation_with_spec():
    """Test LintContext creation with explicit spec path."""
    vault_path = Path("/vault")
    spec_path = Path("/spec.yaml")

    context = LintContext(vault_path=vault_path, spec_path=spec_path)

    assert context.vault_path == vault_path
    assert context.spec_path == spec_path


def test_lint_context_creation_without_spec():
    """Test LintContext creation with default spec_path (None)."""
    vault_path = Path("/vault")

    context = LintContext(vault_path=vault_path)

    assert context.vault_path == vault_path
    assert context.spec_path is None


def test_lint_context_creation_explicit_none_spec():
    """Test LintContext creation with explicitly set None spec_path."""
    vault_path = Path("/vault")

    context = LintContext(vault_path=vault_path, spec_path=None)

    assert context.vault_path == vault_path
    assert context.spec_path is None


# ---------- Immutability and dataclass behavior ----------


def test_lint_context_immutability():
    """Test that LintContext is immutable (frozen dataclass)."""
    vault_path = Path("/vault")
    spec_path = Path("/spec.yaml")

    context = LintContext(vault_path=vault_path, spec_path=spec_path)

    # Should not be able to modify vault_path
    with pytest.raises(FrozenInstanceError):
        context.vault_path = Path("/other")

    # Should not be able to modify spec_path
    with pytest.raises(FrozenInstanceError):
        context.spec_path = Path("/other.yaml")


def test_lint_context_equality():
    """Test LintContext equality comparison."""
    vault_path = Path("/vault")
    spec_path = Path("/spec.yaml")

    context1 = LintContext(vault_path=vault_path, spec_path=spec_path)
    context2 = LintContext(vault_path=vault_path, spec_path=spec_path)
    context3 = LintContext(vault_path=vault_path, spec_path=None)

    assert context1 == context2  # Same values should be equal
    assert context1 != context3  # Different spec_path should not be equal


def test_lint_context_hashable():
    """Test that LintContext is hashable (can be used in sets/dicts)."""
    vault_path = Path("/vault")
    spec_path = Path("/spec.yaml")

    context1 = LintContext(vault_path=vault_path, spec_path=spec_path)
    context2 = LintContext(vault_path=vault_path, spec_path=spec_path)

    # Should be hashable and equal contexts should have same hash
    context_set = {context1, context2}
    assert len(context_set) == 1  # Should be deduplicated due to equality

    # Should be usable as dict key
    context_dict = {context1: "test_value"}
    assert context_dict[context2] == "test_value"  # Same context should work as key


# ---------- Path handling ----------


def test_lint_context_with_absolute_paths():
    """Test LintContext works correctly with absolute paths."""
    base_path = Path("/home/user")
    vault_path = base_path / "vault"
    spec_path = base_path / "spec.yaml"

    # Resolve paths to make them absolute
    vault_path = vault_path.resolve()
    spec_path = spec_path.resolve()

    context = LintContext(vault_path=vault_path, spec_path=spec_path)

    assert context.vault_path.is_absolute()
    assert context.spec_path.is_absolute()
    assert context.vault_path == vault_path
    assert context.spec_path == spec_path
