"""Command-line interface for vaultlint."""

import os
import sys
import logging
import argparse
from dataclasses import dataclass
from pathlib import Path
import importlib.metadata as im

# Exit codes
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_KEYBOARD_INTERRUPT = 130

# Logging verbosity level constants
VERBOSITY_QUIET = 0  # Default verbosity level (WARNING)
VERBOSITY_VERBOSE = 1  # Single -v flag (INFO)
VERBOSITY_DEBUG = 2  # Double -vv flag (DEBUG)

# Windows path length constants
WINDOWS_MAX_PATH_LIMIT = 260
WINDOWS_SAFE_PATH_BUFFER = 20  # Safety buffer to avoid edge cases
WINDOWS_MAX_SAFE_PATH_LENGTH = WINDOWS_MAX_PATH_LIMIT - WINDOWS_SAFE_PATH_BUFFER

# Platform-specific access check constants
WINDOWS_ACCESS_CHECK = os.R_OK
UNIX_ACCESS_CHECK = os.R_OK | os.X_OK

# Python version compatibility constants
PYTHON_VERSION_WITH_IS_RELATIVE_TO = (3, 9)  # Path.is_relative_to() added in 3.9

# Package version constants
PACKAGE_NAME = "vaultlint"
FALLBACK_VERSION = "0.0.0+local"


LOG = logging.getLogger("vaultlint.cli")


@dataclass(frozen=True)
class LintContext:
    """Context object containing all configuration for linting operations."""

    vault_path: Path
    spec_path: Path | None = None


def _get_platform_access_check() -> int:
    """Get the appropriate os.access() flags for the current platform."""
    return WINDOWS_ACCESS_CHECK if os.name == "nt" else UNIX_ACCESS_CHECK


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
    parser.add_argument(
        "-s",
        "--spec",
        type=Path,
        help="Path to vault specification file (default: look for vspec.yaml in vault root)",
    )
    try:
        pkg_version = im.version(PACKAGE_NAME)
    except im.PackageNotFoundError:
        pkg_version = FALLBACK_VERSION
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
        if verbosity == VERBOSITY_QUIET
        else (logging.INFO if verbosity == VERBOSITY_VERBOSE else logging.DEBUG)
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


def _resolve_path_safely(path: Path) -> Path | None:
    """Safely resolve a path with proper error handling.

    Args:
        path: Path to resolve

    Returns:
        Resolved Path, or None if resolution failed
    """
    try:
        # First do basic path expansion
        expanded = path.expanduser()

        # Check path length (Windows MAX_PATH is 260, but we'll use a safe limit)
        if os.name == "nt" and len(str(expanded)) > WINDOWS_MAX_SAFE_PATH_LENGTH:
            LOG.error("Path '%s' exceeds maximum safe length", path)
            return None

        # Resolve the path
        return expanded.resolve(strict=True)

    except FileNotFoundError:
        LOG.error("The path '%s' does not exist", path)
        return None
    except (OSError, ValueError) as exc:
        LOG.error("Could not resolve '%s': %s", path, exc)
        return None


def validate_vault_path(path: Path) -> bool:
    """Validate that the given path exists, is a directory, and is readable.

    Performs basic security checks including path length validation.
    """
    resolved = _resolve_path_safely(path)
    if resolved is None:
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
    access_check = _get_platform_access_check()
    if not os.access(resolved, access_check):
        LOG.warning(
            "Directory exists but may not be fully accessible: %s",
            resolved,
        )
    return True


def resolve_spec_file(vault_path: Path, spec_arg: Path | None = None) -> Path | None:
    """Resolve the specification file path.

    Priority:
    1. Explicit --spec argument
    2. vspec.yaml in vault root
    3. None (no spec file found)

    Args:
        vault_path: Path to the vault directory (should already be resolved)
        spec_arg: Optional spec file path from CLI argument

    Returns:
        Resolved Path to spec file, or None if not found
    """
    # First priority: explicit argument
    if spec_arg:
        resolved_spec = _resolve_path_safely(spec_arg)
        if resolved_spec is not None:
            LOG.info("Using specification file: %s", resolved_spec)
            return resolved_spec
        else:
            LOG.error("Could not resolve specified spec file: %s", spec_arg)
            return None

    # Second priority: vspec.yaml in vault root
    default_spec = vault_path / "vspec.yaml"
    if default_spec.exists():
        LOG.info("Found specification file in vault root: %s", default_spec)
        return default_spec.resolve()

    # No spec file found
    LOG.info("No specification file found. Structure checks will be skipped.")
    return None


def run(vault_path: Path, spec_path: Path | None = None) -> int:
    """Core runner: validate path and dispatch linter."""
    if not validate_vault_path(vault_path):
        return EXIT_VALIDATION_ERROR

    # Use _resolve_path_safely instead of duplicating logic
    resolved_vault = _resolve_path_safely(vault_path)
    if resolved_vault is None:
        return EXIT_VALIDATION_ERROR

    # Resolve spec file path
    resolved_spec = resolve_spec_file(resolved_vault, spec_path)

    # Create context object with all configuration
    context = LintContext(vault_path=resolved_vault, spec_path=resolved_spec)

    LOG.info("vaultlint ready. Checking: %s", context.vault_path)
    if context.spec_path:
        LOG.info("Using specification: %s", context.spec_path)

    from .checks.check_manager import check_manager

    # Run checker manager with unified context
    result = check_manager(context)

    return EXIT_SUCCESS if result else EXIT_VALIDATION_ERROR


def main(argv: list[str] | None = None) -> int:
    """Entry point for the vaultlint command."""
    args = parse_arguments(argv)
    _configure_logging(args.verbose)
    try:
        return run(args.path, args.spec)
    except KeyboardInterrupt:
        LOG.error("Interrupted by user")
        return EXIT_KEYBOARD_INTERRUPT


if __name__ == "__main__":
    sys.exit(main())
