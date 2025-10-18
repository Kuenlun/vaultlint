"""Tests for CLI integration and end-to-end functionality."""

import logging
from pathlib import Path

import pytest

from vaultlint.cli import (
    LOG,
    WINDOWS_MAX_SAFE_PATH_LENGTH,
    _resolve_path_safely,
    main,
    run,
)

# ---------- Core runner integration tests ----------


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


# ---------- Full CLI integration tests ----------


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


def test_cli_integration_keyboard_interrupt(monkeypatch, capsys, tmp_path):
    """Test main() integration handles KeyboardInterrupt with exit code 130."""

    def raise_kbi(_path, _spec=None):  # Updated to match new signature
        raise KeyboardInterrupt

    monkeypatch.setattr("vaultlint.cli.run", raise_kbi)
    rc = main([str(tmp_path)])
    assert rc == 130
    # Check Rich error output instead of logs
    captured = capsys.readouterr()
    assert "Operation interrupted by user" in captured.out


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


def test_cli_integration_logging_configuration_error(tmp_path, monkeypatch):
    """Test main() integration handles logging configuration errors gracefully.

    This covers the exception handler in _configure_logging when StreamHandler
    creation or formatter configuration fails.
    """
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
    # Use pytest.raises to catch the SystemExit
    import pytest

    with pytest.raises(SystemExit) as excinfo:
        main([str(tmp_path)])
    assert excinfo.value.code == 1  # EXIT_VALIDATION_ERROR


def test_cli_integration_resolve_path_failure_after_validation(tmp_path, monkeypatch):
    """Test main() handles path resolution failure after successful validation (covers line 269).

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


def test_cli_integration_with_spec_file(tmp_path, capsys):
    """Test main() with a specification file present (covers line 279).

    This covers the output.print_using_spec() call when a vspec.yaml file exists.
    """
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
    """Test main() handles KeyboardInterrupt gracefully (covers line 306).

    This covers the KeyboardInterrupt exception handler that returns EXIT_KEYBOARD_INTERRUPT.
    """
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock check_manager to raise KeyboardInterrupt
    # This will happen deep inside run() but still be caught by main()
    def interrupt_during_checks(context):
        raise KeyboardInterrupt("Simulated Ctrl+C during checks")

    monkeypatch.setattr(
        "vaultlint.checks.check_manager.check_manager", interrupt_during_checks
    )

    # Should handle KeyboardInterrupt and return appropriate exit code
    rc = main([str(tmp_path)])
    assert rc == 130  # EXIT_KEYBOARD_INTERRUPT

    # Check error message
    captured = capsys.readouterr()
    assert "Operation interrupted by user" in captured.out


def test_cli_integration_logging_success_path(tmp_path, monkeypatch):
    """Test main() executes successful logging configuration (covers lines 144-147).

    This covers the successful logging setup path when no handlers exist.
    Lines 144-147: StreamHandler creation, formatter setup, handler addition, propagate setting.
    """
    # Create valid vault
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock logging.getLogger to return clean loggers with NO handlers
    class CleanLogger:
        def __init__(self):
            self.handlers = []  # No handlers - forces the setup path
            self.level = 0
            self.propagate = True

        def setLevel(self, level):
            self.level = level

        def addHandler(self, handler):
            # This method execution covers line 146
            self.handlers.append(handler)

        def removeHandler(self, handler):
            # For pytest compatibility
            if handler in self.handlers:
                self.handlers.remove(handler)

    clean_logger = CleanLogger()

    # Mock all getLogger calls to return our clean logger
    monkeypatch.setattr("vaultlint.cli.logging.getLogger", lambda name="": clean_logger)

    # Mock StreamHandler and Formatter to track their creation (lines 144-145)
    handler_created = False
    formatter_created = False

    class MockStreamHandler:
        def __init__(self):
            nonlocal handler_created
            handler_created = True  # Line 144 executed

        def setFormatter(self, formatter):
            nonlocal formatter_created
            formatter_created = True  # Line 145 executed

    class MockFormatter:
        def __init__(self, fmt):
            pass

    monkeypatch.setattr("vaultlint.cli.logging.StreamHandler", MockStreamHandler)
    monkeypatch.setattr("vaultlint.cli.logging.Formatter", MockFormatter)

    # Execute - should go through successful logging setup
    rc = main([str(tmp_path)])
    assert rc == 0

    # Verify the successful logging path was executed
    assert handler_created, "StreamHandler should have been created (line 144)"
    assert formatter_created, "Formatter should have been set (line 145)"
    assert len(clean_logger.handlers) > 0, "Handler should have been added (line 146)"
    assert (
        clean_logger.propagate is False
    ), "Propagate should be set to False (line 147)"


def test_resolve_path_safely_direct_success():
    """Test _resolve_path_safely direct success path (covers line 171/177).

    This test directly calls _resolve_path_safely with conditions that guarantee
    the successful return expanded.resolve(strict=True) line is executed.
    """
    import tempfile
    from pathlib import Path

    # Create a temporary directory that definitely exists
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a path that will need some resolution work
        temp_path = Path(temp_dir)
        nested = temp_path / "subdir"
        nested.mkdir()

        # Create a path with .. that requires resolve() to do actual work
        complex_path = nested / ".." / "subdir"  # Points back to nested

        # This should trigger the successful resolve path
        result = _resolve_path_safely(complex_path)

        # Verify success
        assert result is not None
        assert result.exists()
        assert result == nested  # Should resolve to the actual directory


def test_main_keyboard_interrupt_exact_line_306(tmp_path, monkeypatch, capsys):
    """Test main() KeyboardInterrupt return EXIT_KEYBOARD_INTERRUPT (exact line 306).

    This test specifically ensures line 306 'return EXIT_KEYBOARD_INTERRUPT' executes.
    """
    # Create valid vault
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()

    # Mock run() to raise KeyboardInterrupt - this will be caught by main()
    def run_with_keyboard_interrupt(vault_path, spec_path=None):
        # Simulate user pressing Ctrl+C during processing
        raise KeyboardInterrupt()

    monkeypatch.setattr("vaultlint.cli.run", run_with_keyboard_interrupt)

    # Execute main() - should catch KeyboardInterrupt and return EXIT_KEYBOARD_INTERRUPT
    exit_code = main([str(tmp_path)])

    # Verify exact return code from line 306
    assert exit_code == 130  # EXIT_KEYBOARD_INTERRUPT constant

    # Verify error message was printed
    captured = capsys.readouterr()
    assert "Operation interrupted by user" in captured.out


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


def test_path_length_warning_on_windows(tmp_path, monkeypatch, capsys):
    """Test path length warning on Windows (covers line 171).

    This covers the print_warning line when path exceeds safe length on Windows.
    """
    # Force Windows behavior
    monkeypatch.setattr("os.name", "nt")

    # Create a very long path that exceeds WINDOWS_MAX_SAFE_PATH_LENGTH
    from vaultlint.cli import WINDOWS_MAX_SAFE_PATH_LENGTH

    # Create a path string that definitely exceeds the limit
    long_base = "a" * 200  # Long directory name
    long_path_str = (
        str(tmp_path / long_base) + "\\extra" * 50
    )  # Should exceed 260 chars
    long_path = Path(long_path_str)

    # Call _resolve_path_safely with use_warnings=True to trigger line 171
    result = _resolve_path_safely(long_path, use_warnings=True)

    # Should return None due to length check
    assert result is None

    # Verify the warning was printed (line 171)
    captured = capsys.readouterr()
    assert "Path exceeds maximum safe length" in captured.out
