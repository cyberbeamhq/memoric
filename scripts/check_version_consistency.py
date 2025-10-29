#!/usr/bin/env python3
"""
Version Consistency Checker for Memoric

This script ensures that all version numbers across configuration files are consistent.
Run this before making a release to catch any discrepancies.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def extract_version_from_file(filepath: Path, pattern: str) -> str | None:
    """Extract version string from a file using regex pattern."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1) if match else None


def check_versions() -> Tuple[Dict[str, str], List[str]]:
    """Check version consistency across all config files."""
    root = Path(__file__).parent.parent
    versions: Dict[str, str] = {}
    errors: List[str] = []

    # Files to check and their patterns
    files_to_check = {
        "memoric/__init__.py": (
            root / "memoric" / "__init__.py",
            r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']',
        ),
        "setup.py": (root / "setup.py", r'version\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']'),
        "pyproject.toml": (root / "pyproject.toml", r'version\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']'),
    }

    print(f"\n{BOLD}{BLUE}Checking version consistency...{RESET}\n")

    # Extract versions
    for name, (filepath, pattern) in files_to_check.items():
        version = extract_version_from_file(filepath, pattern)
        if version:
            versions[name] = version
            print(f"  {name:20} -> {version}")
        else:
            error = f"Could not find version in {name}"
            errors.append(error)
            print(f"  {RED}✗ {error}{RESET}")

    # Check consistency
    if len(set(versions.values())) > 1:
        errors.append("Version mismatch detected!")
        print(f"\n{RED}{BOLD}✗ Version mismatch detected!{RESET}")
        print(f"\n  Found versions:")
        for name, version in versions.items():
            print(f"    {name}: {version}")
    elif versions:
        version = list(versions.values())[0]
        print(f"\n{GREEN}{BOLD}✓ All versions are consistent: {version}{RESET}")
    else:
        errors.append("No versions found!")

    return versions, errors


def check_dependencies() -> List[str]:
    """Check that dependencies are consistent between setup.py and pyproject.toml."""
    root = Path(__file__).parent.parent
    errors: List[str] = []

    setup_py = root / "setup.py"
    pyproject_toml = root / "pyproject.toml"

    print(f"\n{BOLD}{BLUE}Checking dependency consistency...{RESET}\n")

    if not setup_py.exists() or not pyproject_toml.exists():
        error = "Missing setup.py or pyproject.toml"
        errors.append(error)
        print(f"  {RED}✗ {error}{RESET}")
        return errors

    # Extract dependencies from pyproject.toml
    pyproject_content = pyproject_toml.read_text()
    pyproject_deps = set()

    in_deps_section = False
    for line in pyproject_content.split("\n"):
        if line.strip() == "dependencies = [":
            in_deps_section = True
        elif in_deps_section:
            if line.strip() == "]":
                break
            # Extract package name (before >=, ==, etc.)
            match = re.match(r'\s*"([a-zA-Z0-9_-]+)', line)
            if match:
                pyproject_deps.add(match.group(1).lower())

    # Extract dependencies from setup.py
    setup_content = setup_py.read_text()
    setup_deps = set()

    # Look for install_requires
    match = re.search(r"install_requires\s*=\s*\[(.*?)\]", setup_content, re.DOTALL)
    if match:
        for line in match.group(1).split("\n"):
            match = re.match(r'\s*["\']([a-zA-Z0-9_-]+)', line)
            if match:
                setup_deps.add(match.group(1).lower())

    # Compare
    if pyproject_deps != setup_deps:
        only_in_pyproject = pyproject_deps - setup_deps
        only_in_setup = setup_deps - pyproject_deps

        if only_in_pyproject:
            error = f"Dependencies only in pyproject.toml: {only_in_pyproject}"
            errors.append(error)
            print(f"  {YELLOW}⚠ {error}{RESET}")

        if only_in_setup:
            error = f"Dependencies only in setup.py: {only_in_setup}"
            errors.append(error)
            print(f"  {YELLOW}⚠ {error}{RESET}")
    else:
        print(f"  {GREEN}✓ Dependencies are consistent{RESET}")

    return errors


def check_optional_deps() -> List[str]:
    """Check that optional dependencies are consistent."""
    root = Path(__file__).parent.parent
    errors: List[str] = []

    setup_py = root / "setup.py"
    pyproject_toml = root / "pyproject.toml"

    print(f"\n{BOLD}{BLUE}Checking optional dependencies...{RESET}\n")

    # Extract extras_require from setup.py
    setup_content = setup_py.read_text()
    setup_extras = {}

    match = re.search(r"extras_require\s*=\s*\{(.*?)\}", setup_content, re.DOTALL)
    if match:
        extras_content = match.group(1)
        for extra_match in re.finditer(r'["\'](\w+)["\']:\s*\[(.*?)\]', extras_content, re.DOTALL):
            extra_name = extra_match.group(1)
            deps = set()
            for dep in extra_match.group(2).split(","):
                dep_match = re.match(r'\s*["\']([a-zA-Z0-9_-]+)', dep)
                if dep_match:
                    deps.add(dep_match.group(1).lower())
            setup_extras[extra_name] = deps

    # Extract optional deps from pyproject.toml
    pyproject_content = pyproject_toml.read_text()
    pyproject_extras = {}

    in_optional_section = False
    current_extra = None

    for line in pyproject_content.split("\n"):
        if "[project.optional-dependencies]" in line:
            in_optional_section = True
        elif in_optional_section:
            if line.startswith("[") and "project.optional-dependencies" not in line:
                break
            # Look for extra name
            extra_match = re.match(r"(\w+)\s*=\s*\[", line)
            if extra_match:
                current_extra = extra_match.group(1)
                pyproject_extras[current_extra] = set()
            elif current_extra and re.match(r'\s*"[a-zA-Z0-9_-]+', line):
                dep_match = re.match(r'\s*"([a-zA-Z0-9_-]+)', line)
                if dep_match:
                    pyproject_extras[current_extra].add(dep_match.group(1).lower())

    # Compare extras
    all_extras = set(setup_extras.keys()) | set(pyproject_extras.keys())

    for extra in sorted(all_extras):
        setup_deps = setup_extras.get(extra, set())
        pyproject_deps = pyproject_extras.get(extra, set())

        if setup_deps != pyproject_deps:
            error = f"Optional deps mismatch for '{extra}'"
            errors.append(error)
            print(f"  {YELLOW}⚠ {error}{RESET}")
            if setup_deps - pyproject_deps:
                print(f"    Only in setup.py: {setup_deps - pyproject_deps}")
            if pyproject_deps - setup_deps:
                print(f"    Only in pyproject.toml: {pyproject_deps - setup_deps}")
        else:
            print(f"  {GREEN}✓ '{extra}' is consistent{RESET}")

    return errors


def main() -> int:
    """Run all consistency checks."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  Memoric Configuration Consistency Checker{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}")

    all_errors: List[str] = []

    # Check versions
    versions, version_errors = check_versions()
    all_errors.extend(version_errors)

    # Check dependencies
    dep_errors = check_dependencies()
    all_errors.extend(dep_errors)

    # Check optional dependencies
    optional_errors = check_optional_deps()
    all_errors.extend(optional_errors)

    # Summary
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}  Summary{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")

    if all_errors:
        print(f"{RED}{BOLD}✗ Found {len(all_errors)} issue(s):{RESET}\n")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print(f"\n{YELLOW}Please fix these issues before releasing.{RESET}\n")
        return 1
    else:
        print(f"{GREEN}{BOLD}✓ All checks passed! Configuration is consistent.{RESET}\n")
        if versions:
            version = list(versions.values())[0]
            print(f"  Current version: {BOLD}{version}{RESET}")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
