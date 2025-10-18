"""Tests for check manager orchestration functionality."""

import logging
from pathlib import Path
import pytest

from vaultlint.cli import LintContext
from vaultlint.checks.check_manager import check_manager


# ---------- Core orchestration behavior ----------


def test_check_manager_propagates_struct_checker_success(monkeypatch, capsys):
    """Test check_manager returns True when struct_checker succeeds."""
    # Mock struct_checker to return success
    def mock_struct_checker(context):
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    context = LintContext(vault_path=Path("/vault"))
    result = check_manager(context)

    assert result is True
    # Verify Rich output shows success summary
    captured = capsys.readouterr()
    assert "Vault validation completed successfully" in captured.out


def test_check_manager_propagates_struct_checker_failure(monkeypatch, capsys):
    """Test check_manager returns False when struct_checker fails."""
    # Mock struct_checker to return failure
    def mock_struct_checker(context):
        return False

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    context = LintContext(vault_path=Path("/vault"))
    result = check_manager(context)

    assert result is False
    # Verify Rich output shows failure summary
    captured = capsys.readouterr()
    assert "Vault validation failed" in captured.out


def test_check_manager_passes_context_to_struct_checker(monkeypatch):
    """Test check_manager correctly passes LintContext to struct_checker."""
    received_context = None

    def mock_struct_checker(context):
        nonlocal received_context
        received_context = context
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    vault_path = Path("/test/vault")
    spec_path = Path("/test/spec.yaml")
    context = LintContext(vault_path=vault_path, spec_path=spec_path)

    check_manager(context)

    # Verify the exact same context object was passed
    assert received_context is context
    assert received_context.vault_path == vault_path
    assert received_context.spec_path == spec_path


# ---------- Error handling and robustness ----------


def test_check_manager_propagates_exceptions_from_struct_checker(monkeypatch):
    """Test check_manager lets exceptions from struct_checker propagate (current behavior)."""

    def mock_struct_checker_with_exception(context):
        raise RuntimeError("Simulated struct_checker failure")

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker",
        mock_struct_checker_with_exception,
    )

    context = LintContext(vault_path=Path("/vault"))

    # Current behavior: exceptions propagate (no exception handling in check_manager)
    with pytest.raises(RuntimeError, match="Simulated struct_checker failure"):
        check_manager(context)


# ---------- Logging behavior ----------


def test_check_manager_shows_vault_path_in_summary(monkeypatch, capsys):
    """Test check_manager shows the vault path in the summary."""
    def mock_struct_checker(context):
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    vault_path = Path("/specific/vault/path")
    context = LintContext(vault_path=vault_path)

    check_manager(context)

    # Should show the specific vault path in Rich output
    captured = capsys.readouterr()
    assert str(vault_path) in captured.out


# ---------- Future-proofing and extensibility ----------


def test_check_manager_is_stateless(monkeypatch):
    """Test check_manager is stateless and can be called multiple times safely."""
    call_count = 0

    def mock_struct_checker(context):
        nonlocal call_count
        call_count += 1
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    context1 = LintContext(vault_path=Path("/vault1"))
    context2 = LintContext(vault_path=Path("/vault2"))

    result1 = check_manager(context1)
    result2 = check_manager(context2)

    assert result1 is True
    assert result2 is True
    assert call_count == 2  # Each call should invoke struct_checker independently
