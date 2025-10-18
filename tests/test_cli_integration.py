"""Tests for CLI integration and end-to-end functionality."""

import logging
from pathlib import Path

from vaultlint.cli import run, main, LOG


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


def test_cli_integration_keyboard_interrupt(monkeypatch, caplog, tmp_path):
    """Test main() integration handles KeyboardInterrupt with exit code 130."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")

    def raise_kbi(path, spec=None):
        raise KeyboardInterrupt

    monkeypatch.setattr("vaultlint.cli.run", raise_kbi)
    # call with -v so INFO logs are emitted
    rc = main(["-v", str(tmp_path)])
    assert rc == 130
    assert any("Interrupted by user" in r.getMessage() for r in caplog.records)


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
