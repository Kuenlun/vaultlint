"""Basic smoke tests for the CLI."""

from vaultlint.cli import main


def test_main_returns_zero_and_prints(capsys):
    code = main()
    out = capsys.readouterr().out
    assert code == 0
    assert "vaultlint: hello" in out
