"""Tests for command-line interface functionality."""

import logging
from pathlib import Path
import pytest

from vaultlint.cli import (
    parse_arguments,
    run,
    main,
    LOG,
)

# ---------- Argument parsing ----------


def test_parse_arguments_returns_path(tmp_path):
    ns = parse_arguments([str(tmp_path)])
    assert isinstance(ns.path, Path)
    assert ns.path == tmp_path


def test_parse_arguments_requires_path():
    # Argparse should exit with code 2 when required positional arg is missing
    with pytest.raises(SystemExit) as exc:
        parse_arguments([])
    assert exc.value.code == 2


def test_parse_arguments_version_flag_prints_version_and_exits(monkeypatch, capsys):
    # Mock version() to ensure deterministic output
    import importlib.metadata as im

    monkeypatch.setattr(im, "version", lambda _: "1.2.3")
    with pytest.raises(SystemExit) as exc:
        parse_arguments(["-V"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    # argparse "version" action prints "<prog> <version>"
    assert "vaultlint 1.2.3" in out


def test_parse_arguments_version_flag_without_package(monkeypatch, capsys):
    import importlib.metadata as im
    from importlib.metadata import PackageNotFoundError

    def raise_not_found(_):
        raise PackageNotFoundError

    monkeypatch.setattr(im, "version", raise_not_found)

    # argparse's "version" action exits with code 0 after printing fallback
    with pytest.raises(SystemExit) as exc:
        parse_arguments(["-V"])
    assert exc.value.code == 0

    out = capsys.readouterr().out
    # format is "<prog> <version>\n"
    assert out.startswith("vaultlint ")
    assert "0.0.0+local" in out


# ---------- Runner behavior ----------


def test_run_returns_1_when_validation_fails(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: False)
    rc = run(tmp_path)
    assert rc == 1
    # No success info log expected
    assert not [
        r for r in caplog.records if "vaultlint ready. Checking:" in r.getMessage()
    ]


def test_run_logs_info_on_success(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: True)
    homey = Path("~") / "some" / "vault"  # exercise expanduser()+resolve()
    rc = run(homey)
    assert rc == 0
    assert any("vaultlint ready. Checking:" in r.getMessage() for r in caplog.records)


# ---------- main() integration ----------


def test_main_success_integration(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main([str(tmp_path)])
    assert rc == 0


def test_main_nonexistent_path_returns_1(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    missing = tmp_path / "nope"
    rc = main([str(missing)])
    assert rc == 1
    assert any("does not exist" in r.getMessage() for r in caplog.records)


def test_main_keyboard_interrupt_returns_130(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")

    def raise_kbi(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("vaultlint.cli.run", raise_kbi)
    # call with -v so INFO logs are emitted
    rc = main(["-v", str(tmp_path)])
    assert rc == 130
    assert any("Interrupted by user" in r.getMessage() for r in caplog.records)


def test_verbose_enables_info_logging(tmp_path):
    # single -v should enable INFO but not DEBUG
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main(["-v", str(tmp_path)])
    assert rc == 0
    assert LOG.isEnabledFor(logging.INFO)
    assert not LOG.isEnabledFor(logging.DEBUG)


def test_verbose_double_enables_debug_logging(tmp_path):
    # double -vv should enable DEBUG
    # Create a valid vault structure
    obsidian_dir = tmp_path / ".obsidian"
    obsidian_dir.mkdir()
    rc = main(["-vv", str(tmp_path)])
    assert rc == 0
    assert LOG.isEnabledFor(logging.DEBUG)


def test_main_expands_user_home(tmp_path, monkeypatch, caplog):
    """Ensure '~' is expanded via Path.expanduser in the run path."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")

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

    # call with -v so INFO logs are emitted
    rc = main(["-v", "~/vault"])
    assert rc == 0
    # The resolved path should appear in the info message
    assert any(str(vault.resolve()) in r.getMessage() for r in caplog.records)
