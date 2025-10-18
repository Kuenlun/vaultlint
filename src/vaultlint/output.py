"""
Output utilities using Rich for professional CLI display.
Minimal, clean, and consistent styling.
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Global console instance
console = Console()


class OutputManager:
    """Manages clean, professional output for vaultlint."""

    def __init__(self):
        self.start_time = None

    def start_timing(self):
        """Start timing for operations."""
        self.start_time = time.time()

    def get_elapsed_time(self):
        """Get elapsed time since start_timing() was called."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def print_checking_vault(self, vault_path: str):
        """Print vault checking message with Obsidian purple color."""
        console.print(f"Checking vault: [bold magenta]{vault_path}[/bold magenta]")

    def print_using_spec(self, spec_name: str):
        """Print specification being used."""
        console.print(f"Using specification: [bold]{spec_name}[/bold]")

    def print_no_spec(self):
        """Print message when no specification file found."""
        console.print("Using default checks (no specification file)")

    def print_success(self, message: str):
        """Print success message with green checkmark."""
        console.print(f"[green]✓[/green] {message}")

    def print_error(self, message: str, path: str = None):
        """Print error message with red X."""
        if path:
            console.print(f"[red]✗ {message} '[bold red]{path}[/bold red]'[/red]")
        else:
            console.print(f"[red]✗ {message}[/red]")

    def print_warning(self, message: str, path: str = None):
        """Print warning message with yellow warning triangle."""
        if path:
            console.print(
                f"[yellow]⚠ {message} '[bold yellow]{path}[/bold yellow]'[/yellow]"
            )
        else:
            console.print(f"[yellow]⚠ {message}[/yellow]")

    def print_usage_error(self, prog: str, message: str):
        """Print argument parsing error with rich formatting."""
        console.print(f"[red]✗ Error:[/red] {message}")
        console.print(f"\nFor help, use: [bold magenta]{prog} --help[/bold magenta]")

    def show_progress(self, description: str):
        """Show animated progress spinner."""
        return Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=console,
        )

    def print_summary_success(
        self,
        vault_path: str,
        spec_name: str = None,
        files_checked: int = 0,
        checks_run: int = 0,
    ):
        """Print success summary panel."""
        elapsed = self.get_elapsed_time()

        content = f"Vault validation completed successfully\n\n"
        content += f"Vault: [bold magenta]{vault_path}[/bold magenta]\n"
        if spec_name:
            content += f"Specification: [bold]{spec_name}[/bold]\n"
        if files_checked > 0:
            content += f"Files checked: [bold]{files_checked}[/bold]\n"
        if checks_run > 0:
            content += f"Checks run: [bold]{checks_run}[/bold]\n"
        content += f"Issues found: [bold]0[/bold]\n"
        content += f"Time taken: [dim]{elapsed:.1f} seconds[/dim]"

        panel = Panel(content, title="Summary", border_style="green")
        console.print(panel)

    def print_summary_failure(
        self,
        vault_path: str,
        spec_name: str = None,
        files_checked: int = 0,
        checks_run: int = 0,
        issues: list = None,
    ):
        """Print failure summary panel."""
        elapsed = self.get_elapsed_time()
        issue_count = len(issues) if issues else 0

        content = f"Vault validation failed\n\n"
        content += f"Vault: [bold magenta]{vault_path}[/bold magenta]\n"
        if spec_name:
            content += f"Specification: [bold]{spec_name}[/bold]\n"
        if files_checked > 0:
            content += f"Files checked: [bold]{files_checked}[/bold]\n"
        if checks_run > 0:
            content += f"Checks run: [bold]{checks_run}[/bold]\n"
        content += f"Issues found: [bold red]{issue_count}[/bold red]\n"
        content += f"Time taken: [dim]{elapsed:.1f} seconds[/dim]"

        if issues:
            content += f"\n\n"
            for issue in issues:
                content += f"[red]✗ {issue}[/red]\n"

        panel = Panel(content, title="Summary", border_style="red")
        console.print(panel)


# Global output manager instance
output = OutputManager()
