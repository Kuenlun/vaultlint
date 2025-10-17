"""Tests for check manager orchestration functionality."""

import logging
from pathlib import Path
import pytest

from vaultlint.cli import LintContext
from vaultlint.checks.check_manager import check_manager


# ---------- Core orchestration behavior ----------


def test_check_manager_propagates_struct_checker_success(monkeypatch, caplog):
    """Test check_manager returns True when struct_checker succeeds."""
    caplog.set_level(logging.INFO, logger="vaultlint.checks.check_manager")

    # Mock struct_checker to return success
    def mock_struct_checker(context):
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    context = LintContext(vault_path=Path("/vault"))
    result = check_manager(context)

    assert result is True
    assert any(
        "All checks completed successfully" in r.getMessage() for r in caplog.records
    )


def test_check_manager_propagates_struct_checker_failure(monkeypatch, caplog):
    """Test check_manager returns False when struct_checker fails."""
    caplog.set_level(logging.ERROR, logger="vaultlint.checks.check_manager")

    # Mock struct_checker to return failure
    def mock_struct_checker(context):
        return False

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    context = LintContext(vault_path=Path("/vault"))
    result = check_manager(context)

    assert result is False
    assert any("Some checks failed" in r.getMessage() for r in caplog.records)


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


def test_check_manager_logs_vault_path_on_start(monkeypatch, caplog):
    """Test check_manager logs the vault path when starting checks."""
    caplog.set_level(logging.INFO, logger="vaultlint.checks.check_manager")

    def mock_struct_checker(context):
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker
    )

    vault_path = Path("/specific/vault/path")
    context = LintContext(vault_path=vault_path)

    check_manager(context)

    # Should log the specific vault path
    assert any(str(vault_path) in r.getMessage() for r in caplog.records)
    assert any("Starting checks on vault" in r.getMessage() for r in caplog.records)


def test_check_manager_logs_appropriate_level_for_results(monkeypatch, caplog):
    """Test check_manager logs success at INFO level and failure at ERROR level."""
    caplog.set_level(
        logging.DEBUG, logger="vaultlint.checks.check_manager"
    )  # Capture all levels

    # Test success case
    def mock_struct_checker_success(context):
        return True

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker_success
    )

    context = LintContext(vault_path=Path("/vault"))
    check_manager(context)

    success_records = [
        r
        for r in caplog.records
        if "All checks completed successfully" in r.getMessage()
    ]
    assert len(success_records) == 1
    assert success_records[0].levelno == logging.INFO

    caplog.clear()

    # Test failure case
    def mock_struct_checker_failure(context):
        return False

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.struct_checker", mock_struct_checker_failure
    )

    check_manager(context)

    failure_records = [
        r for r in caplog.records if "Some checks failed" in r.getMessage()
    ]
    assert len(failure_records) == 1
    assert failure_records[0].levelno == logging.ERROR


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
