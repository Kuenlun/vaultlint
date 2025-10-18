"""Tests for output.py module - comprehensive coverage of OutputManager."""

from unittest.mock import patch

from vaultlint.output import OutputManager


class TestOutputManager:
    """Tests for OutputManager class methods."""

    def test_print_using_spec(self):
        """Test print_using_spec method."""
        output_mgr = OutputManager()

        with patch("vaultlint.output.console") as mock_console:
            output_mgr.print_using_spec("test-spec.yaml")

            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert "Using specification: [bold]test-spec.yaml[/bold]" in str(args)

    def test_print_no_spec(self):
        """Test print_no_spec method."""
        output_mgr = OutputManager()

        with patch("vaultlint.output.console") as mock_console:
            output_mgr.print_no_spec()

            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert "Using default checks (no specification file)" in str(args)

    def test_print_success(self):
        """Test print_success method."""
        output_mgr = OutputManager()

        with patch("vaultlint.output.console") as mock_console:
            output_mgr.print_success("All tests passed")

            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert "[green]✓[/green] All tests passed" in str(args)

    def test_print_warning_without_path(self):
        """Test print_warning method without path parameter."""
        output_mgr = OutputManager()

        with patch("vaultlint.output.console") as mock_console:
            output_mgr.print_warning("This is a warning")

            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0]
            assert "[yellow]⚠ This is a warning[/yellow]" in str(args)

    def test_show_progress(self):
        """Test show_progress method returns Progress instance."""
        output_mgr = OutputManager()

        progress = output_mgr.show_progress("Processing...")

        # Should return a Progress instance
        assert progress is not None
        assert hasattr(progress, "add_task")

    def test_print_summary_success(self):
        """Test print_summary_success method."""
        output_mgr = OutputManager()
        output_mgr.start_time = 1000.0  # Set a start time

        with patch("vaultlint.output.console") as mock_console:
            with patch("time.time", return_value=1002.5):  # 2.5 seconds elapsed
                output_mgr.print_summary_success(
                    vault_path="/test/vault",
                    spec_name="test.yaml",
                    files_checked=10,
                    checks_run=5,
                )

                mock_console.print.assert_called_once()
                # Verify it's a Panel with success content
                args = mock_console.print.call_args[0]
                assert len(args) == 1  # Should be a Panel object

    def test_print_summary_failure(self):
        """Test print_summary_failure method."""
        output_mgr = OutputManager()
        output_mgr.start_time = 1000.0  # Set a start time

        with patch("vaultlint.output.console") as mock_console:
            with patch("time.time", return_value=1003.0):  # 3 seconds elapsed
                output_mgr.print_summary_failure(
                    vault_path="/test/vault",
                    spec_name="test.yaml",
                    files_checked=10,
                    checks_run=5,
                    issues=["Error 1", "Error 2"],
                )

                mock_console.print.assert_called_once()
                # Verify it's a Panel with failure content
                args = mock_console.print.call_args[0]
                assert len(args) == 1  # Should be a Panel object
