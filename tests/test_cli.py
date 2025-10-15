# tests/test_cli.py
import logging
import os
from pathlib import Path

import pytest

from vaultlint.cli import (
    parse_arguments,
    validate_vault_path,
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


# ---------- Path validation ----------


def test_validate_vault_path_ok(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    ok = validate_vault_path(tmp_path)
    assert ok is True
    # No error-level logs expected
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_validate_vault_path_nonexistent(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    missing = tmp_path / "does-not-exist"
    ok = validate_vault_path(missing)
    assert ok is False
    assert any("does not exist" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_file_instead_of_dir(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    f = tmp_path / "file.txt"
    f.write_text("hi")
    ok = validate_vault_path(f)
    assert ok is False
    assert any("is not a directory" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_permission_error_simulated(tmp_path, caplog, monkeypatch):
    """Simulate PermissionError on iterdir in a cross-platform safe way."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    real_iterdir = Path.iterdir

    def guarded_iterdir(self):
        if self.resolve() == tmp_path.resolve():
            raise PermissionError("simulated permission denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)
    ok = validate_vault_path(tmp_path)
    assert ok is False
    assert any("not readable" in r.getMessage() for r in caplog.records)


def test_validate_vault_path_warns_when_os_access_fails(tmp_path, caplog, monkeypatch):
    caplog.set_level(logging.WARNING, logger="vaultlint.cli")
    # Make os.access report False to trigger the warning branch
    monkeypatch.setattr(os, "access", lambda *_args, **_kw: False)
    ok = validate_vault_path(tmp_path)
    assert ok is True
    assert any("may not be fully accessible" in r.getMessage() for r in caplog.records)


# ---------- Runner behavior ----------


def test_run_returns_1_when_validation_fails(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: False)
    rc = run(tmp_path)
    assert rc == 1
    # No success info log expected
    assert not [
        r for r in caplog.records if "Vaultlint ready. Checking:" in r.getMessage()
    ]


def test_run_logs_info_on_success(monkeypatch, caplog, tmp_path):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    monkeypatch.setattr("vaultlint.cli.validate_vault_path", lambda _p: True)
    homey = Path("~") / "some" / "vault"  # exercise expanduser()+resolve()
    rc = run(homey)
    assert rc == 0
    assert any("Vaultlint ready. Checking:" in r.getMessage() for r in caplog.records)


# ---------- main() integration ----------


def test_main_success_integration(tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="vaultlint.cli")
    rc = main([str(tmp_path)])
    assert rc == 0
    assert any("Vaultlint ready. Checking:" in r.getMessage() for r in caplog.records)


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
    rc = main([str(tmp_path)])
    assert rc == 130
    assert any("Interrupted by user" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("flag", ["-v", "-vv"])
def test_verbose_enables_debug_logging(tmp_path, flag):
    # After -v/-vv, logger should enable DEBUG level
    rc = main([flag, str(tmp_path)])
    assert rc == 0
    assert LOG.isEnabledFor(logging.DEBUG)


def test_main_expands_user_home(tmp_path, monkeypatch, caplog):
    """Ensure '~' is expanded via Path.expanduser in the run path."""
    caplog.set_level(logging.INFO, logger="vaultlint.cli")

    home = tmp_path / "homeuser"
    vault = home / "vault"
    vault.mkdir(parents=True)

    # Monkeypatch Path.expanduser itself, since run() uses Path.expanduser()
    def fake_expand(self: Path):
        return Path(str(self).replace("~", str(home)))

    monkeypatch.setattr(Path, "expanduser", fake_expand)

    rc = main(["~/vault"])
    assert rc == 0
    # The resolved path should appear in the info message
    assert any(str(vault.resolve()) in r.getMessage() for r in caplog.records)
