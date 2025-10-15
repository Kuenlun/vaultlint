"""Command-line interface for vaultlint."""

import os
import sys
import logging
import argparse
from pathlib import Path
import importlib.metadata as im


LOG = logging.getLogger("vaultlint.cli")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="vaultlint",
        description=(
            "A modular linter for Obsidian that validates Markdown, "
            "YAML front matter, and vault structure"
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the vault directory to check",
    )
    try:
        pkg_version = im.version("vaultlint")
    except im.PackageNotFoundError:
        pkg_version = "0.0.0+local"
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {pkg_version}"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (use -vv for debug)",
    )
    return parser.parse_args(argv)


def _configure_logging(verbosity: int) -> None:
    """Configure logging without clobbering existing handlers (e.g., pytest caplog)."""
    level = logging.INFO if verbosity == 0 else logging.DEBUG

    # Configure our package logger
    pkg_logger = logging.getLogger("vaultlint")
    pkg_logger.setLevel(level)

    # Keep child logger too (the module uses vaultlint.cli)
    mod_logger = logging.getLogger("vaultlint.cli")
    mod_logger.setLevel(level)
    mod_logger.propagate = True  # bubble up to 'vaultlint' if needed

    # If running as a standalone CLI (no handlers configured), attach a simple handler
    root = logging.getLogger()
    if not root.handlers and not pkg_logger.handlers and not mod_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        pkg_logger.addHandler(handler)


def validate_vault_path(path: Path) -> bool:
    """Validate that the given path exists, is a directory, and is readable."""
    try:
        resolved = path.expanduser().resolve()
    except Exception as exc:
        LOG.error("Could not resolve '%s': %s", path, exc)
        return False

    if not resolved.exists():
        LOG.error("The path '%s' does not exist.", resolved)
        return False
    if not resolved.is_dir():
        LOG.error("The path '%s' is not a directory.", resolved)
        return False
    try:
        next(resolved.iterdir(), None)
    except PermissionError:
        LOG.error("The directory '%s' is not readable.", resolved)
        return False
    except OSError as exc:
        LOG.error("Could not access '%s': %s", resolved, exc)
        return False
    if not os.access(resolved, os.R_OK | os.X_OK):
        LOG.warning("Directory exists but may not be fully accessible: %s", resolved)
    return True


def run(vault_path: Path) -> int:
    """Core runner: validate path and (later) dispatch linting."""
    if not validate_vault_path(vault_path):
        return 1
    LOG.info("Vaultlint ready. Checking: %s", vault_path.expanduser().resolve())
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the vaultlint command."""
    args = parse_arguments(argv)
    _configure_logging(args.verbose)
    try:
        return run(args.path)
    except KeyboardInterrupt:
        LOG.error("Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
