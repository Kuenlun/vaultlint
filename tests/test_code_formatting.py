"""Tests for code formatting and style compliance."""

import subprocess
import sys
from pathlib import Path


def test_black_formatting():
    """Test that all Python code is formatted with Black.

    This ensures code follows consistent formatting standards.
    Equivalent to Ctrl+Alt+F in most editors with Black configured.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Run black in check mode (--check doesn't modify files, just reports)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "black",
            "--check",  # Only check, don't modify
            "--diff",  # Show differences if any
            "--color",  # Colorized output
            str(project_root / "src"),
            str(project_root / "tests"),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    # If black finds formatting issues, it returns exit code 1
    if result.returncode != 0:
        print(f"❌ Black formatting issues found:")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        print(f"\n💡 Fix with: python -m black src tests")

    assert result.returncode == 0, (
        f"Code is not properly formatted with Black. "
        f"Run 'python -m black src tests' to fix formatting."
    )


def test_isort_import_sorting():
    """Test that all imports are sorted correctly with isort.

    This ensures imports are consistently organized.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    # Run isort in check mode
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "isort",
            "--check-only",  # Only check, don't modify
            "--diff",  # Show differences if any
            str(project_root / "src"),
            str(project_root / "tests"),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    # If isort finds issues, it returns exit code 1
    if result.returncode != 0:
        print(f"❌ Import sorting issues found:")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        print(f"\n💡 Fix with: python -m isort src tests")

    assert result.returncode == 0, (
        f"Imports are not properly sorted. "
        f"Run 'python -m isort src tests' to fix import order."
    )


def test_formatting_tools_available():
    """Test that formatting tools are available and working.

    This ensures the development environment is properly set up.
    """
    # Test Black is available
    result_black = subprocess.run(
        [sys.executable, "-m", "black", "--version"], capture_output=True
    )
    assert result_black.returncode == 0, "Black is not installed or not working"

    # Test isort is available
    result_isort = subprocess.run(
        [sys.executable, "-m", "isort", "--version"], capture_output=True
    )
    assert result_isort.returncode == 0, "isort is not installed or not working"

    print("✅ All formatting tools are available and working")
