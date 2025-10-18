"""Unit tests for CLI helper functions and utilities."""

import tempfile
from pathlib import Path

import pytest

from vaultlint.cli import WINDOWS_MAX_SAFE_PATH_LENGTH, _resolve_path_safely


def test_resolve_path_safely_success():
    """Test _resolve_path_safely with a valid path."""
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
        # Compare resolved paths to handle system differences (like short names on Windows)
        assert result.resolve() == nested.resolve()


def test_resolve_path_safely_nonexistent():
    """Test _resolve_path_safely with nonexistent path."""
    nonexistent = Path("/this/path/should/not/exist/anywhere")
    result = _resolve_path_safely(nonexistent)
    assert result is None


def test_path_length_warning_on_windows(monkeypatch, capsys):
    """Test path length warning on Windows."""
    # Force Windows behavior
    monkeypatch.setattr("os.name", "nt")

    # Create a very long path that exceeds WINDOWS_MAX_SAFE_PATH_LENGTH
    long_base = "a" * 200  # Long directory name
    long_path_str = "C:\\" + long_base + "\\extra" * 50  # Should exceed 260 chars
    long_path = Path(long_path_str)

    # Call _resolve_path_safely with use_warnings=True to trigger warning
    result = _resolve_path_safely(long_path, use_warnings=True)

    # Should return None due to length check
    assert result is None

    # Verify the warning was printed
    captured = capsys.readouterr()
    assert "Path exceeds maximum safe length" in captured.out


def test_resolve_path_safely_with_warnings(monkeypatch, capsys):
    """Test _resolve_path_safely with use_warnings=True for nonexistent path."""
    nonexistent = Path("/this/path/should/not/exist")
    result = _resolve_path_safely(nonexistent, use_warnings=True)

    assert result is None
    captured = capsys.readouterr()
    assert "Specification file not found" in captured.out
