"""
Test module to ensure 100% code coverage is maintained.

This test runs the coverage analysis programmatically and fails if coverage
drops below 100%. This ensures that any new code additions or changes
maintain complete test coverage without relying on external CI systems.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_100_percent_coverage():
    """
    Test that ensures 100% code coverage is maintained.

    This test runs pytest with coverage analysis and verifies that the
    total coverage percentage is exactly 100%. If coverage drops below
    100%, the test will fail with detailed information about what's missing.

    Raises:
        AssertionError: If coverage is below 100% or if coverage analysis fails.
    """
    # Get the project root directory (parent of tests directory)
    project_root = Path(__file__).parent.parent

    # Create a temporary file for the coverage JSON report
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_file:
        temp_coverage_path = Path(temp_file.name)

    try:
        # Run pytest with coverage, excluding the current test to avoid recursion
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src/vaultlint",  # Cover the main package
            "--cov-report=term-missing",  # Show missing lines
            f"--cov-report=json:{temp_coverage_path}",  # Generate JSON report
            "--quiet",  # Reduce output noise
            "--tb=short",  # Short tracebacks
            "tests/",  # Run all tests
            "--ignore=tests/test_coverage.py",  # Ignore this coverage test to avoid recursion
        ]

        print(f"Running coverage analysis...")
        print(f"Command: {' '.join(cmd)}")

        # Execute the coverage command with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=60,  # 60 second timeout
        )

        # Print some of the coverage output for debugging (limit to avoid spam)
        stdout_lines = result.stdout.split("\n")
        print("Coverage analysis completed.")

        # Look for coverage summary in output
        for line in stdout_lines:
            if "TOTAL" in line or "coverage" in line.lower():
                print(f"Coverage info: {line}")

        if result.stderr:
            print("Warnings/Errors:")
            stderr_lines = result.stderr.split("\n")[:10]  # Limit error output
            for line in stderr_lines:
                if line.strip():
                    print(f"  {line}")

        # Check if the command succeeded (note: pytest might return 0 even with warnings)
        if result.returncode not in [
            0,
            1,
        ]:  # 0 = success, 1 = some tests failed but coverage ran
            raise AssertionError(
                f"Coverage analysis failed with return code {result.returncode}.\n"
                f"First few lines of stderr: {result.stderr[:500]}"
            )

        # Parse the JSON coverage report for precise percentage
        if temp_coverage_path.exists() and temp_coverage_path.stat().st_size > 0:
            with open(temp_coverage_path, "r", encoding="utf-8") as f:
                coverage_data = json.load(f)

            # Get the total coverage percentage
            total_coverage = coverage_data["totals"]["percent_covered"]

            print(f"Total coverage: {total_coverage:.2f}%")

            # Assert 100% coverage
            if total_coverage < 100.0:
                # Get detailed information about missing coverage
                missing_lines = []
                for filename, file_data in coverage_data["files"].items():
                    file_coverage = file_data["summary"]["percent_covered"]
                    if file_coverage < 100.0:
                        missing = file_data.get("missing_lines", [])
                        excluded = file_data.get("excluded_lines", [])

                        missing_info = f"Coverage: {file_coverage:.1f}%"
                        if missing:
                            missing_info += f", Missing lines: {missing}"
                        if excluded:
                            missing_info += f", Excluded lines: {excluded}"

                        missing_lines.append(f"  {filename}: {missing_info}")

                missing_info = (
                    "\n".join(missing_lines)
                    if missing_lines
                    else "No specific missing lines identified."
                )

                raise AssertionError(
                    f"Code coverage is {total_coverage:.2f}%, which is below the required 100%.\n"
                    f"Files with incomplete coverage:\n{missing_info}\n"
                    f"Please add tests to cover all code paths."
                )

        else:
            # Fallback: parse coverage from stdout if JSON report not available
            stdout_lines = result.stdout.split("\n")
            coverage_line = None

            # Look for the coverage percentage in the output
            for line in stdout_lines:
                if "TOTAL" in line and "%" in line:
                    coverage_line = line
                    break

            if not coverage_line:
                raise AssertionError(
                    "Could not find coverage percentage in output and JSON report not available. "
                    "Make sure pytest-cov is properly installed and configured.\n"
                    f"Command output: {result.stdout[:1000]}"
                )

            # Extract percentage from line like "TOTAL    1234   0   100%"
            parts = coverage_line.split()
            percentage_str = parts[-1].rstrip("%")

            try:
                percentage = float(percentage_str)
            except (ValueError, IndexError):
                raise AssertionError(
                    f"Could not parse coverage percentage from line: {coverage_line}"
                )

            print(f"Total coverage: {percentage}%")

            if percentage < 100.0:
                raise AssertionError(
                    f"Code coverage is {percentage}%, which is below the required 100%. "
                    f"Please add tests to cover all code paths.\n"
                    f"Coverage line: {coverage_line}"
                )

        print("✅ 100% code coverage achieved!")

    except subprocess.TimeoutExpired:
        raise AssertionError(
            "Coverage analysis timed out. This might indicate an infinite loop or "
            "very slow tests. Please check your test suite."
        )

    finally:
        # Clean up the temporary coverage report file
        try:
            temp_coverage_path.unlink(missing_ok=True)
        except Exception:
            pass  # Ignore cleanup errors


def test_coverage_dependencies_available():
    """
    Test that ensures all required coverage dependencies are available.

    This test verifies that pytest-cov is properly installed and importable,
    which is required for the coverage analysis to work.
    """
    try:
        import pytest_cov

        print(f"✅ pytest-cov is available (version: {pytest_cov.__version__})")
    except ImportError:
        raise AssertionError(
            "pytest-cov is not installed. Install it with: pip install pytest-cov"
        )

    # Also verify that coverage module is available
    try:
        import coverage

        print(f"✅ coverage is available (version: {coverage.__version__})")
    except ImportError:
        raise AssertionError(
            "coverage module is not available. This should be installed with pytest-cov."
        )


if __name__ == "__main__":
    # Allow running this test directly for debugging
    test_coverage_dependencies_available()
    test_100_percent_coverage()
    print("All coverage tests passed!")
