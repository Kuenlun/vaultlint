"""Additional unit tests for CLI edge cases and error handling."""

import argparse
from pathlib import Path
from unittest.mock import Mock

import pytest

from vaultlint.cli import RichArgumentParser, parse_arguments
from vaultlint.output import output


def test_rich_argument_parser_missing_path_error():
    """Test RichArgumentParser error handling for missing path argument."""
    parser = RichArgumentParser(prog="test", output_manager=output)

    with pytest.raises(SystemExit) as excinfo:
        parser.error("the following arguments are required: path")

    assert excinfo.value.code == 2  # EXIT_USAGE_ERROR


def test_rich_argument_parser_missing_other_required_error():
    """Test RichArgumentParser error handling for missing non-path argument."""
    parser = RichArgumentParser(prog="test", output_manager=output)

    with pytest.raises(SystemExit) as excinfo:
        parser.error("the following arguments are required: spec")

    assert excinfo.value.code == 2  # EXIT_USAGE_ERROR


def test_rich_argument_parser_unrecognized_argument_error():
    """Test RichArgumentParser error handling for unrecognized arguments."""
    parser = RichArgumentParser(prog="test", output_manager=output)

    with pytest.raises(SystemExit) as excinfo:
        parser.error("unrecognized arguments: --invalid-flag")

    assert excinfo.value.code == 2  # EXIT_USAGE_ERROR


def test_rich_argument_parser_generic_error():
    """Test RichArgumentParser error handling for generic error messages."""
    parser = RichArgumentParser(prog="test", output_manager=output)

    with pytest.raises(SystemExit) as excinfo:
        parser.error("some generic error message")

    assert excinfo.value.code == 2  # EXIT_USAGE_ERROR


def test_parse_arguments_package_not_found_fallback(monkeypatch):
    """Test parse_arguments handles PackageNotFoundError and uses fallback version."""

    # Mock importlib.metadata.version to raise PackageNotFoundError
    def mock_version(package_name):
        if package_name == "vaultlint":
            from importlib.metadata import PackageNotFoundError

            raise PackageNotFoundError(
                f"No package metadata was found for {package_name}"
            )
        return "1.0.0"

    monkeypatch.setattr("vaultlint.cli.im.version", mock_version)

    # This should not raise an error and should use FALLBACK_VERSION
    args = parse_arguments(["/some/path"])
    assert args.path == Path("/some/path")


def test_resolve_path_safely_error_mode_path_too_long(monkeypatch, capsys):
    """Test _resolve_path_safely with error mode for path length (use_warnings=False)."""
    from vaultlint.cli import _resolve_path_safely

    # Force Windows behavior
    monkeypatch.setattr("os.name", "nt")

    # Create a very long path
    long_path_str = "C:\\" + "a" * 300  # Exceeds safe limit
    long_path = Path(long_path_str)

    # Call with use_warnings=False (default)
    result = _resolve_path_safely(long_path)

    assert result is None
    captured = capsys.readouterr()
    assert "Path exceeds maximum safe length" in captured.out


def test_resolve_path_safely_os_error(monkeypatch, capsys):
    """Test _resolve_path_safely handles OSError during path resolution."""
    from vaultlint.cli import _resolve_path_safely

    # Mock Path.resolve to raise OSError
    def mock_resolve(strict=True):
        raise OSError("Permission denied")

    # Create a mock path that will trigger the error
    mock_path = Mock()
    mock_path.expanduser.return_value = mock_path
    mock_path.resolve = mock_resolve
    mock_path.__str__ = lambda self: "/test/path"

    monkeypatch.setattr("os.name", "posix")  # Not Windows

    result = _resolve_path_safely(mock_path)

    assert result is None
    captured = capsys.readouterr()
    assert "Could not resolve path: Permission denied" in captured.out


def test_resolve_path_safely_value_error(monkeypatch, capsys):
    """Test _resolve_path_safely handles ValueError during path resolution."""
    from vaultlint.cli import _resolve_path_safely

    # Mock Path.resolve to raise ValueError
    def mock_resolve(strict=True):
        raise ValueError("Invalid path characters")

    # Create a mock path that will trigger the error
    mock_path = Mock()
    mock_path.expanduser.return_value = mock_path
    mock_path.resolve = mock_resolve
    mock_path.__str__ = lambda self: "/test/path"

    monkeypatch.setattr("os.name", "posix")  # Not Windows

    result = _resolve_path_safely(mock_path)

    assert result is None
    captured = capsys.readouterr()
    assert "Could not resolve path: Invalid path characters" in captured.out


def test_resolve_path_safely_with_warnings_os_error(monkeypatch, capsys):
    """Test _resolve_path_safely with use_warnings=True and OSError."""
    from vaultlint.cli import _resolve_path_safely

    # Mock Path.resolve to raise OSError
    def mock_resolve(strict=True):
        raise OSError("Access denied")

    # Create a mock path that will trigger the error
    mock_path = Mock()
    mock_path.expanduser.return_value = mock_path
    mock_path.resolve = mock_resolve
    mock_path.__str__ = lambda self: "/spec/file"

    monkeypatch.setattr("os.name", "posix")

    result = _resolve_path_safely(mock_path, use_warnings=True)

    assert result is None
    captured = capsys.readouterr()
    assert "Could not resolve specification file: Access denied" in captured.out


def test_validate_vault_path_not_directory(tmp_path, capsys):
    """Test validate_vault_path when path is not a directory."""
    from vaultlint.cli import validate_vault_path

    # Create a file instead of directory
    test_file = tmp_path / "notadirectory.txt"
    test_file.write_text("test")

    result = validate_vault_path(test_file)

    assert result is False
    captured = capsys.readouterr()
    assert "The path is not a directory" in captured.out


def test_validate_vault_path_permission_error(tmp_path, monkeypatch, capsys):
    """Test validate_vault_path handles PermissionError when trying to read directory."""
    from vaultlint.cli import validate_vault_path

    # Create a directory
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    # Mock iterdir to raise PermissionError
    def mock_iterdir(self):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "iterdir", mock_iterdir)

    result = validate_vault_path(test_dir)

    assert result is False
    captured = capsys.readouterr()
    assert "The directory is not readable" in captured.out


def test_validate_vault_path_os_error(tmp_path, monkeypatch, capsys):
    """Test validate_vault_path handles OSError when accessing directory."""
    from vaultlint.cli import validate_vault_path

    # Create a directory
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    # Mock iterdir to raise OSError
    def mock_iterdir(self):
        raise OSError("Device not ready")

    monkeypatch.setattr(Path, "iterdir", mock_iterdir)

    result = validate_vault_path(test_dir)

    assert result is False
    captured = capsys.readouterr()
    assert "Could not access directory: Device not ready" in captured.out


def test_validate_vault_path_access_warning(tmp_path, monkeypatch, capsys):
    """Test validate_vault_path shows warning when directory may not be fully accessible."""
    from vaultlint.cli import validate_vault_path

    # Create a directory
    test_dir = tmp_path / "testdir"
    test_dir.mkdir()

    # Mock os.access to return False
    monkeypatch.setattr("os.access", lambda path, mode: False)

    result = validate_vault_path(test_dir)

    assert result is True  # Still returns True but shows warning
    captured = capsys.readouterr()
    assert "Directory may not be fully accessible" in captured.out


def test_resolve_spec_file_explicit_spec(tmp_path):
    """Test resolve_spec_file with explicit spec file that exists."""
    from vaultlint.cli import resolve_spec_file

    # Create spec file
    spec_file = tmp_path / "custom.yaml"
    spec_file.write_text("test: spec")

    result = resolve_spec_file(tmp_path, spec_file)

    assert result == spec_file.resolve()


def test_resolve_spec_file_default_spec_exists(tmp_path):
    """Test resolve_spec_file finds default vspec.yaml in vault root."""
    from vaultlint.cli import resolve_spec_file

    # Create default spec file
    spec_file = tmp_path / "vspec.yaml"
    spec_file.write_text("test: spec")

    result = resolve_spec_file(tmp_path, None)

    assert result == spec_file.resolve()
