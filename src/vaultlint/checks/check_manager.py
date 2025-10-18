"""Check manager that coordinates execution of all validation checks."""

import logging
from typing import TYPE_CHECKING

from vaultlint.checks.structure.struct_checker import struct_checker
from vaultlint.output import output

if TYPE_CHECKING:
    from vaultlint.cli import LintContext

LOG = logging.getLogger("vaultlint.checks.check_manager")


def check_manager(context: "LintContext") -> bool:
    """Run all registered checks with the given lint context.

    Args:
        context: LintContext containing vault_path, spec_path, and other configuration

    Returns:
        bool: True if all checks passed, False otherwise
    """
    # Show progress with spinner
    with output.show_progress("Running structure checks") as progress:
        progress.add_task("Running structure checks", total=None)
        
        # Execute structure check with context
        result = struct_checker(context)
    
    # Print appropriate summary
    spec_name = context.spec_path.name if context.spec_path else None
    
    if result:
        output.print_summary_success(
            vault_path=str(context.vault_path),
            spec_name=spec_name,
            checks_run=1  # Currently only structure check
        )
    else:
        # For now, we don't have detailed issue tracking, so just show generic failure
        output.print_summary_failure(
            vault_path=str(context.vault_path),
            spec_name=spec_name,
            checks_run=1,
            issues=["Structure validation failed"]  # Generic message for now
        )

    return result
