"""Check manager that coordinates execution of all validation checks."""

import logging
from typing import TYPE_CHECKING

from vaultlint.checks.structure.struct_checker import struct_checker

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
    LOG.info("Starting checks on vault: %s", context.vault_path)

    # Execute structure check with context
    result = struct_checker(context)

    if result:
        LOG.info("All checks completed successfully.")
    else:
        LOG.error("Some checks failed.")

    return result
