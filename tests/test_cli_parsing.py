"""Tests for CLI argument parsing functionality."""

import pytest
from pathlib import Path

from vaultlint.cli import parse_arguments


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


def test_parse_arguments_spec_flag_short():
    """Test -s flag for spec file."""
    ns = parse_arguments(["/some/path", "-s", "/spec/file.yaml"])
    assert isinstance(ns.spec, Path)
    assert ns.spec == Path("/spec/file.yaml")


def test_parse_arguments_spec_flag_long():
    """Test --spec flag for spec file."""
    ns = parse_arguments(["/some/path", "--spec", "/spec/file.yaml"])
    assert isinstance(ns.spec, Path)
    assert ns.spec == Path("/spec/file.yaml")


def test_parse_arguments_spec_flag_optional():
    """Test that spec flag is optional."""
    ns = parse_arguments(["/some/path"])
    assert ns.spec is None


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
