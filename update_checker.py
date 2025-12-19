#!/usr/bin/env python3
"""
DubSync Update Checker

Checks and installs dependencies from the main requirements.txt
and from all plugin requirements.txt files.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


def get_project_root() -> Path:
    """Project root directory."""
    return Path(__file__).parent


def find_requirements_files(root: Path) -> List[Path]:
    """
    Find all requirements.txt files.
    
    Order:
    1. Main requirements.txt
    2. Plugin requirements.txt files (builtin and external)
    """
    requirements_files = []
    
    # Main requirements.txt
    main_req = root / "requirements.txt"
    if main_req.exists():
        requirements_files.append(main_req)
    
    # Plugin directories
    plugin_dirs = [
        root / "src" / "dubsync" / "plugins" / "builtin",
        root / "src" / "dubsync" / "plugins" / "external",
    ]
    
    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            continue
        
        # Direct plugin folders
        for subdir in plugin_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("_"):
                req_file = subdir / "requirements.txt"
                if req_file.exists():
                    requirements_files.append(req_file)
    
    return requirements_files


def parse_requirements(file_path: Path) -> Set[str]:
    """
    Read requirements file.
    
    Returns:
        Set of packages
    """
    packages = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Skip -r include (recursive include)
                if line.startswith('-r'):
                    continue
                
                packages.add(line)
    except Exception as e:
        print(f"  [!] Error reading file ({file_path}): {e}")
    
    return packages


def get_installed_packages() -> Set[str]:
    """
    List installed packages.
    
    Returns:
        Installed package names (lowercase)
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True
        )
        
        packages = set()
        for line in result.stdout.split('\n'):
            if '==' in line:
                pkg_name = line.split('==')[0].lower()
                packages.add(pkg_name)
        
        return packages
    except Exception:
        return set()


def extract_package_name(requirement: str) -> str:
    """
    Extract package name from requirement string.
    
    "package>=1.0.0" -> "package"
    """
    for sep in ['>=', '<=', '==', '!=', '~=', '>', '<']:
        if sep in requirement:
            return requirement.split(sep)[0].lower().strip()
    
    return requirement.lower().strip()


def check_and_install(requirements_files: List[Path], auto_install: bool = True) -> Tuple[int, int]:
    """
    Check and install missing dependencies.
    
    Args:
        requirements_files: List of requirements files
        auto_install: Automatic installation
        
    Returns:
        (installed, missing) package count
    """
    all_requirements = set()
    
    print("[*] Searching for requirements files...")
    for req_file in requirements_files:
        rel_path = req_file.relative_to(get_project_root())
        print(f"    - {rel_path}")
        all_requirements.update(parse_requirements(req_file))
    
    if not all_requirements:
        print("[OK] No dependencies defined.")
        return 0, 0
    
    print(f"\n[*] Found {len(all_requirements)} dependencies in total.")
    
    # Installed packages
    installed = get_installed_packages()
    
    # Search for missing packages
    missing = []
    for req in all_requirements:
        pkg_name = extract_package_name(req)
        if pkg_name not in installed:
            missing.append(req)
    
    if not missing:
        print("[OK] All dependencies are installed.")
        return 0, 0
    
    print(f"\n[!] {len(missing)} missing dependencies:")
    for pkg in missing:
        print(f"    - {pkg}")
    
    if not auto_install:
        return 0, len(missing)
    
    # Installation
    print("\n[*] Installing dependencies...")
    
    installed_count = 0
    for req in missing:
        try:
            print(f"    Installing: {req}...", end=" ", flush=True)
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', req],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("OK")
                installed_count += 1
            else:
                print("ERROR")
                print(f"      {result.stderr[:200]}")
        except Exception as e:
            print(f"ERROR: {e}")
    
    return installed_count, len(missing) - installed_count


def main():
    """Main entry point."""
    print()
    print("=" * 50)
    print("  DubSync - Dependency Checker")
    print("=" * 50)
    print()
    
    root = get_project_root()
    requirements_files = find_requirements_files(root)
    
    if not requirements_files:
        print("[!] No requirements.txt file found.")
        return 1
    
    installed, failed = check_and_install(requirements_files, auto_install=True)
    
    print()
    if failed > 0:
        print(f"[!] {failed} package installation failed.")
        return 1
    else:
        print("[OK] All dependencies are OK.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
