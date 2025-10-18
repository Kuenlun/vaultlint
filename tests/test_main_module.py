"""Tests for __main__.py module entry point."""

import runpy
import sys
from unittest.mock import patch

import pytest


def test_main_module_execution_help():
    """Test __main__.py execution with --help using runpy (official Python way)."""
    with patch.object(sys, "argv", ["vaultlint", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("vaultlint", run_name="__main__")

        # --help should exit with code 0
        assert exc_info.value.code == 0


def test_main_module_execution_version():
    """Test __main__.py execution with --version."""
    with patch.object(sys, "argv", ["vaultlint", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("vaultlint", run_name="__main__")

        # --version should exit with code 0
        assert exc_info.value.code == 0


def test_main_module_execution_invalid_args():
    """Test __main__.py execution with invalid arguments."""
    with patch.object(sys, "argv", ["vaultlint"]):  # Missing required path
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("vaultlint", run_name="__main__")

        # Should exit with code 2 for argument errors
        assert exc_info.value.code == 2
