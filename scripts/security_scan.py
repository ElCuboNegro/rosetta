"""Local security scanning script.

Run this script locally to check for security vulnerabilities before committing.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status.

    Args:
        cmd: Command to run
        description: Description of the command

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"ERROR: Command not found: {cmd[0]}")
        print(f"Please install it: pip install {cmd[0]}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    """Run all security scans."""
    print("ROSETTA DICTIONARY - SECURITY SCAN")
    print("="*80)

    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    results = {}

    # 1. Safety check for known vulnerabilities
    results["safety"] = run_command(
        ["safety", "check", "--json"],
        "Safety: Checking for known vulnerabilities in dependencies"
    )

    # 2. pip-audit for CVE scanning
    results["pip-audit"] = run_command(
        ["pip-audit", "--desc"],
        "pip-audit: Scanning for CVEs in dependencies"
    )

    # 3. Bandit for code security issues
    results["bandit"] = run_command(
        ["bandit", "-r", str(src_dir), "-ll"],  # Only show medium+ severity
        "Bandit: Scanning code for security issues"
    )

    # 4. Gitleaks for secrets (if available)
    print(f"\n{'='*80}")
    print("Optional: Gitleaks for secret scanning")
    print(f"{'='*80}\n")
    print("To scan for secrets, install gitleaks:")
    print("  https://github.com/gitleaks/gitleaks")
    print("  Then run: gitleaks detect --no-git")

    # Summary
    print(f"\n{'='*80}")
    print("SECURITY SCAN SUMMARY")
    print(f"{'='*80}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for check, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {check:20} {status}")

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All security checks passed!")
        return 0
    else:
        print("\n⚠ Some security checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
