"""Command-line interface for vaultlint."""

import os
import sys
import logging
import argparse
from pathlib import Path
import importlib.metadata as im

# Exit codes
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_KEYBOARD_INTERRUPT = 130

# Windows path length constants
WINDOWS_MAX_SAFE_PATH_LENGTH = 240  # Safe limit under Windows MAX_PATH of 260


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
    level = (
        logging.WARNING
        if verbosity == 0
        else (logging.INFO if verbosity == 1 else logging.DEBUG)
    )

    # Configure our package logger
    pkg_logger = logging.getLogger("vaultlint")
    pkg_logger.setLevel(level)

    mod_logger = logging.getLogger("vaultlint.cli")
    mod_logger.setLevel(level)
    mod_logger.propagate = True  # bubble up to 'vaultlint' if needed

    # If running as a standalone CLI (no handlers configured), attach a simple handler
    root = logging.getLogger()
    if not root.handlers and not pkg_logger.handlers and not mod_logger.handlers:
        try:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            pkg_logger.addHandler(handler)
            # Prevent duplicate emission if a root handler is configured later.
            pkg_logger.propagate = False
        except (IOError, LookupError) as exc:
            sys.stderr.write(f"Failed to configure logging: {exc}\n")
            sys.exit(EXIT_VALIDATION_ERROR)


def validate_vault_path(path: Path) -> bool:
    """Validate that the given path exists, is a directory, and is readable.

    Performs security checks including path traversal detection and length validation.
    """
    try:
        # First do basic path expansion
        expanded = path.expanduser()

        # Check path length (Windows MAX_PATH is 260, but we'll use a safe limit)
        if os.name == "nt" and len(str(expanded)) > WINDOWS_MAX_SAFE_PATH_LENGTH:
            LOG.error("Path '%s' exceeds maximum safe length", path)
            return False

        # Resolve the path
        resolved = expanded.resolve(strict=True)

        # Check if the resolved path is a subdirectory of the expanded path's parent
        try:
            expanded_resolved = expanded.resolve()
            # Use is_relative_to if available (Python 3.9+), else fallback to relative_to
            if hasattr(resolved, "is_relative_to"):
                if not resolved.is_relative_to(expanded_resolved):
                    LOG.error("Path '%s' resolves outside the specified vault directory", path)
                    return False
            else:
                try:
                    resolved.relative_to(expanded_resolved)
                except ValueError:
                    LOG.error("Path '%s' resolves outside the specified vault directory", path)
                    return False
        except (OSError, ValueError):
            # If we can't resolve the parent, we can't validate containment
            LOG.error("Could not validate path containment for '%s'", path)
            return False

    except FileNotFoundError:
        LOG.error("The path '%s' does not exist", path)
        return False
    except (OSError, ValueError) as exc:
        LOG.error("Could not resolve '%s': %s", path, exc)
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
    access_check = os.R_OK if os.name == "nt" else (os.R_OK | os.X_OK)
    if not os.access(resolved, access_check):
        LOG.warning(
            "Directory exists but may not be fully accessible: %s",
            resolved,
        )
    return True


def run(vault_path: Path) -> int:
    """Core runner: validate path and (later) dispatch linting."""
    if not validate_vault_path(vault_path):
        return EXIT_VALIDATION_ERROR
    LOG.info("vaultlint ready. Checking: %s", vault_path.expanduser().resolve())
    return EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    """Entry point for the vaultlint command."""
    args = parse_arguments(argv)
    _configure_logging(args.verbose)
    try:
        return run(args.path)
    except KeyboardInterrupt:
        LOG.error("Interrupted by user")
        return EXIT_KEYBOARD_INTERRUPT


if __name__ == "__main__":
    sys.exit(main())
