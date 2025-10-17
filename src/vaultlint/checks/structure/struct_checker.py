"""Example basic vault structure check."""

from pathlib import Path
import logging
import yaml

LOG = logging.getLogger("vaultlint.checks.structure_checker")


def load_spec_file(path: str):
    """Load a YAML file and return its content as a dictionary."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    LOG.info("YAML file loaded successfully:")
    return data


def struct_checker():
    # Load spec file
    spec_path = (
        "h:/Mi unidad/Obsidian/vaultlint/src/vaultlint/checks/structure/vspec.yaml"
    )
    spec = load_spec_file(spec_path)
    LOG.info("Spec content: %s", spec)

    return 1  # Placeholder return value
