"""Tests for CLI integration and end-to-end functionality."""

import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from vaultlint.cli import (
    LOG,
    WINDOWS_MAX_SAFE_PATH_LENGTH,
    _resolve_path_safely,
    main,
    run,
)

# ========================================================================
# CORE FUNCTION INTEGRATION TESTS
# Tests for individual CLI functions (run(), validate_vault_path(), etc.)
# ========================================================================


def test_run_integration_validation_failure(monkeypatch, caplog, tmp_path):
    """Test run() returns exit code 1 when path validation fails."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: False)
    rc = run(tmp_path)
    assert rc == 1
    # No success info log expected
    assert not [
        r for r in caplog.records if "vaultlint ready. Checking:" in r.getMessage()
    ]


def test_run_integration_success_output(monkeypatch, tmp_path, capsys):
    """Test run() shows success output and returns exit code 0."""
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: True)

    # Use tmp_path instead of non-existent path
    rc = run(tmp_path, None)
    assert rc == 0

    # Check that we get Rich output instead of log messages
    captured = capsys.readouterr()
    assert "Checking vault:" in captured.out


def test_run_integration_resolve_path_failure_after_validation(tmp_path, monkeypatch):
    """Test run() handles path resolution failure after successful validation.

    This covers the case where validate_vault_path succeeds but _resolve_path_safely fails.
    """
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock _resolve_path_safely to fail ONLY in the run() function context
    # We need validate_vault_path to succeed but _resolve_path_safely to fail later
    original_resolve_path_safely = _resolve_path_safely
    call_count = 0

    def selective_resolve_failure(path, use_warnings=False):
        nonlocal call_count
        call_count += 1
        # Let the first call (in validate_vault_path) succeed
        if call_count == 1:
            return original_resolve_path_safely(path, use_warnings=use_warnings)
        # Make the second call (in run()) fail
        return None

    monkeypatch.setattr("vaultlint.cli._resolve_path_safely", selective_resolve_failure)

    # Should exit with validation error code when path resolution fails in run()
    rc = main([str(tmp_path)])
    assert rc == 1  # EXIT_VALIDATION_ERROR


# ========================================================================
# MAIN() CLI INTEGRATION TESTS
# End-to-end tests for the main() entry point
# ========================================================================


def test_cli_integration_valid_vault(tmp_path, caplog):
    """Test main() integration with valid vault structure."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main([str(tmp_path)])
    assert rc == 0


def test_cli_integration_invalid_path(tmp_path, capsys):
    """Test main() integration with nonexistent path returns exit code 1."""
    missing = tmp_path / "nope"
    rc = main([str(missing)])
    assert rc == 1
    # Check Rich error output instead of logs
    captured = capsys.readouterr()
    assert "does not exist" in captured.out


def test_cli_integration_with_spec_file(tmp_path, capsys):
    """Test main() with a specification file present."""
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Create a vspec.yaml file in vault root
    spec_file = tmp_path / "vspec.yaml"
    spec_file.write_text(
        """
checks:
  structure:
    require_obsidian_folder: true
"""
    )

    # Run main - should detect and use the spec file
    rc = main([str(tmp_path)])
    assert rc == 0  # Should succeed

    # Check that it prints using spec message
    captured = capsys.readouterr()
    assert "Using specification: vspec.yaml" in captured.out


def test_cli_integration_keyboard_interrupt(tmp_path, monkeypatch, capsys):
    """Test main() handles KeyboardInterrupt gracefully with exit code 130."""
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock check_manager to raise KeyboardInterrupt during processing
    def interrupt_during_checks(context):
        raise KeyboardInterrupt("User pressed Ctrl+C")

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.check_manager", interrupt_during_checks
    )

    # Should handle KeyboardInterrupt and return appropriate exit code
    rc = main([str(tmp_path)])
    assert rc == 130  # EXIT_KEYBOARD_INTERRUPT

    # Check error message
    captured = capsys.readouterr()
    assert "Operation interrupted by user" in captured.out


# ========================================================================
# COMMAND LINE ARGUMENT TESTS
# Tests for argument parsing, verbose flags, etc.
# ========================================================================


def test_cli_integration_verbose_info_logging(tmp_path):
    """Test main() integration with single -v enables INFO logging."""
    # single -v should enable INFO but not DEBUG
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main(["-v", str(tmp_path)])
    assert rc == 0
    assert LOG.isEnabledFor(logging.INFO)
    assert not LOG.isEnabledFor(logging.DEBUG)


def test_cli_integration_verbose_debug_logging(tmp_path):
    """Test main() integration with double -vv enables DEBUG logging."""
    # double -vv should enable DEBUG
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main(["-vv", str(tmp_path)])
    assert rc == 0
    assert LOG.isEnabledFor(logging.DEBUG)


def test_cli_integration_expanduser_resolution(tmp_path, monkeypatch, capsys):
    """Test main() integration with user home path expansion."""
    home = tmp_path / "homeuser"
    vault = home / "vault"
    vault.mkdir(parents=True)

    # Create a valid vault structure
    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir()

    # Monkeypatch Path.expanduser itself, since run() uses Path.expanduser()
    def fake_expand(self: Path):
        return Path(str(self).replace("~", str(home)))

    monkeypatch.setattr(Path, "expanduser", fake_expand)

    rc = main(["-v", "~/vault"])
    assert rc == 0
    # The resolved path should appear in Rich output (may be formatted with colors/breaks)
    captured = capsys.readouterr()
    # Check for key parts of the path since Rich may format it with colors and line breaks
    vault_parts = str(vault.resolve()).split("\\")  # Split Windows path
    # Check that at least the last few unique parts appear in output
    assert "homeuser" in captured.out
    assert "vault" in captured.out


# ========================================================================
# ERROR HANDLING AND EDGE CASE TESTS
# Tests for logging errors, configuration failures, etc.
# ========================================================================


def test_cli_integration_logging_configuration_error(tmp_path, monkeypatch):
    """Test main() handles logging configuration errors gracefully."""
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock logging to force the handler creation path and make it fail
    def mock_stream_handler():
        raise IOError("Failed to create stream handler")

    # Mock getLogger to return loggers with no handlers
    class MockLogger:
        def __init__(self):
            self.handlers = []  # No handlers to force the creation path
            self.level = 0
            self.propagate = True

        def setLevel(self, level):
            self.level = level

        def addHandler(self, handler):
            pass

        def removeHandler(self, handler):  # Add this for pytest compatibility
            pass

    mock_logger = MockLogger()
    monkeypatch.setattr("vaultlint.cli.logging.getLogger", lambda name="": mock_logger)
    monkeypatch.setattr("vaultlint.cli.logging.StreamHandler", mock_stream_handler)

    # Should exit with validation error code when logging setup fails
    with pytest.raises(SystemExit) as excinfo:
        main([str(tmp_path)])
    assert excinfo.value.code == 1  # EXIT_VALIDATION_ERROR


def test_cli_integration_logging_setup_when_no_handlers(tmp_path, monkeypatch):
    """Test main() sets up logging when no handlers are present."""
    # Create valid vault
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Track if logging setup was attempted
    setup_called = False

    def mock_getLogger(name=""):
        logger = Mock()
        logger.handlers = []  # No handlers - triggers setup path
        logger.setLevel = Mock()
        logger.addHandler = Mock()
        nonlocal setup_called
        setup_called = True
        return logger

    monkeypatch.setattr("vaultlint.cli.logging.getLogger", mock_getLogger)
    monkeypatch.setattr("vaultlint.cli.logging.StreamHandler", Mock)
    monkeypatch.setattr("vaultlint.cli.logging.Formatter", Mock)

    rc = main([str(tmp_path)])
    assert rc == 0
    assert setup_called, "Logging setup should have been called"


# ========================================================================
# SIMPLE INTEGRATION TESTS
# Basic tests to verify overall functionality
# ========================================================================


def test_main_script_integration(tmp_path):
    """Test that main() function works when called as a script."""
    # Create a valid vault for testing
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Simple integration test - just verify main() can be called and returns correct exit code
    from vaultlint.cli import main

    rc = main([str(tmp_path)])
    assert rc == 0  # Should succeed with valid vault


def test_main_as_script_execution(monkeypatch, tmp_path):
    """Test __main__ execution path (covers line 306: sys.exit(main())).

    This covers the final line when the module is executed as a script using runpy.
    """
    import runpy
    import sys

    # Create a valid vault for testing
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock sys.argv for the script execution
    monkeypatch.setattr("sys.argv", ["vaultlint.cli", str(tmp_path)])

    # Mock sys.exit to capture and prevent actual exit
    exit_called = []
    original_exit = sys.exit

    def mock_exit(code=0):
        exit_called.append(code)
        # Don't actually exit, just record the call
        return

    monkeypatch.setattr("sys.exit", mock_exit)

    # Execute the cli module as __main__ - this WILL execute line 306
    # runpy.run_module executes the actual module code including if __name__ == "__main__"
    # Suppress the RuntimeWarning about module already being in sys.modules
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", ".*found in sys.modules.*", RuntimeWarning)
        try:
            runpy.run_module("vaultlint.cli", run_name="__main__")
        except SystemExit:
            pass  # Expected if any other exit path is taken

    # Verify that sys.exit was called (line 306 executed)
    assert len(exit_called) >= 1, "sys.exit should have been called from line 306"
    assert exit_called[0] == 0, "Should exit with success code"
