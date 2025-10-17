"""Example basic vault structure check."""

from pathlib import Path
import logging
import yaml
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vaultlint.cli import LintContext

LOG = logging.getLogger("vaultlint.checks.structure_checker")


def load_spec_file(path: str):
    """Load a YAML file and return its content as a dictionary."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data


def struct_checker(context: "LintContext") -> bool:
    """Check vault structure against specification.

    Args:
        context: LintContext containing vault_path and spec_path

    Returns:
        bool: True if structure check passed, False otherwise
    """
    if context.spec_path is None:
        # No spec file - this is normal, not an error
        return True  # Consider this a success if no spec is required

    try:
        spec = load_spec_file(str(context.spec_path))
        # Keep only debug logging for development
        LOG.debug("Loaded specification from: %s", context.spec_path)
        LOG.debug("Spec content: %s", spec)

        # TODO: Implement actual structure validation logic here
        # For now, just validate that we can load the spec

        return True  # Placeholder - return True if spec loads successfully

    except Exception as e:
        LOG.error("Failed to process specification file: %s", e)
        return False
