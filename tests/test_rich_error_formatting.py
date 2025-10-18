"""Tests for rich error formatting in CLI argument parsing.

This module specifically tests the rich formatting aspect of error messages,
ensuring consistent visual presentation across all CLI error scenarios.
"""

from unittest.mock import patch

import pytest

from vaultlint.cli import RichArgumentParser
from vaultlint.output import OutputManager, output


class TestRichArgumentParser:
    """Tests for the RichArgumentParser class that provides rich-formatted error messages."""

    def test_missing_required_argument_formatting(self):
        """Test rich formatting when required arguments are missing.

        Ensures that missing argument errors use consistent rich formatting
        with the rest of the application (red error icon, clear message).
        """
        parser = RichArgumentParser(prog="vaultlint", output_manager=OutputManager())
        parser.add_argument("path", help="Path to vault")

        with patch("vaultlint.output.console") as mock_console:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args([])

            # Verify correct exit code (standard argparse behavior)
            assert exc_info.value.code == 2

            # Verify rich formatting was used (should be 2 calls: error + help suggestion)
            assert mock_console.print.call_count == 2

            # Verify error message uses rich formatting
            error_call = mock_console.print.call_args_list[0]
            help_call = mock_console.print.call_args_list[1]

            # Check for consistent rich formatting elements
            assert "[red]✗ Error:[/red]" in str(error_call)
            assert "Missing required argument 'path'" in str(error_call)
            assert "[bold magenta]vaultlint --help[/bold magenta]" in str(help_call)

    def test_unrecognized_argument_formatting(self):
        """Test rich formatting when unrecognized arguments are provided.

        Ensures that invalid argument errors use consistent rich formatting
        and provide clear feedback about what went wrong.
        """
        parser = RichArgumentParser(prog="vaultlint", output_manager=OutputManager())
        parser.add_argument("path", help="Path to vault")

        with patch("vaultlint.output.console") as mock_console:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["somepath", "--nonexistent-flag"])

            # Verify correct exit code
            assert exc_info.value.code == 2

            # Verify rich formatting was used
            assert mock_console.print.call_count == 2

            # Verify error message format and content
            error_call = mock_console.print.call_args_list[0]
            help_call = mock_console.print.call_args_list[1]

            assert "[red]✗ Error:[/red]" in str(error_call)
            assert "Unrecognized argument: --nonexistent-flag" in str(error_call)
            assert "[bold magenta]vaultlint --help[/bold magenta]" in str(help_call)

    def test_multiple_unrecognized_arguments_formatting(self):
        """Test rich formatting when multiple unrecognized arguments are provided.

        Ensures proper handling and formatting when users provide multiple invalid flags.
        """
        parser = RichArgumentParser(prog="testprog", output_manager=OutputManager())
        parser.add_argument("path", help="Path to vault")

        with patch("vaultlint.output.console") as mock_console:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["somepath", "-x", "-y", "--invalid"])

            assert exc_info.value.code == 2
            assert mock_console.print.call_count == 2

            error_call = mock_console.print.call_args_list[0]
            # Should include the first unrecognized argument
            assert "[red]✗ Error:[/red]" in str(error_call)
            assert "Unrecognized argument:" in str(error_call)

    def test_generic_required_argument_formatting(self):
        """Test rich formatting for generic required arguments (non-'path').

        This covers the else branch in error handling for any required argument
        that is not specifically the 'path' argument.
        """
        parser = RichArgumentParser(prog="vaultlint", output_manager=OutputManager())
        parser.add_argument("path", help="Path to vault")
        parser.add_argument("--required-flag", required=True, help="Some required flag")

        with patch("vaultlint.output.console") as mock_console:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(["somepath"])  # Missing required --required-flag

            assert exc_info.value.code == 2
            assert mock_console.print.call_count == 2

            error_call = mock_console.print.call_args_list[0]
            # Should use the generic "Missing required argument:" format
            assert "[red]✗ Error:[/red]" in str(error_call)
            assert "Missing required argument:" in str(error_call)
            assert "required-flag" in str(error_call)


class TestOutputUsageErrorMethod:
    """Tests for the output module's print_usage_error method."""

    def test_print_usage_error_formatting(self):
        """Test the print_usage_error method produces correct rich formatting.

        This is a critical test ensuring the output method that powers
        the RichArgumentParser works correctly and consistently.
        """
        with patch("vaultlint.output.console") as mock_console:
            output.print_usage_error("testprog", "Test error message")

            # Should make exactly two calls: error message + help suggestion
            assert mock_console.print.call_count == 2

            # Verify the formatting matches expected pattern
            error_call = mock_console.print.call_args_list[0]
            help_call = mock_console.print.call_args_list[1]

            assert "[red]✗ Error:[/red] Test error message" in str(error_call)
            assert "[bold magenta]testprog --help[/bold magenta]" in str(help_call)

    def test_print_usage_error_with_different_programs(self):
        """Test that print_usage_error works with different program names.

        Ensures the method is reusable and correctly incorporates the program name.
        """
        with patch("vaultlint.output.console") as mock_console:
            output.print_usage_error("different-tool", "Some error")

            assert mock_console.print.call_count == 2
            help_call = mock_console.print.call_args_list[1]
            assert "[bold magenta]different-tool --help[/bold magenta]" in str(
                help_call
            )
