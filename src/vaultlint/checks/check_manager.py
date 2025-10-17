"""Check manager that coordinates execution of all validation checks."""

import logging

from vaultlint.checks.structure.struct_checker import struct_checker

LOG = logging.getLogger("vaultlint.checks.check_manager")


def check_manager(vault_path):
    """Run all registered checks on the given vault path."""
    LOG.info("Starting checks on vault: %s", vault_path)

    result = struct_checker()

    LOG.info("All checks completed successfully.")
    return result
