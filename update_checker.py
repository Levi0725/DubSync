#!/usr/bin/env python3
"""
DubSync Update Checker

Ellenőrzi és telepíti a függőségeket a fő requirements.txt-ből
és az összes plugin requirements.txt-jéből.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


def get_project_root() -> Path:
    """Projekt gyökér könyvtár."""
    return Path(__file__).parent


def find_requirements_files(root: Path) -> List[Path]:
    """
    Megkeresi az összes requirements.txt fájlt.
    
    Sorrend:
    1. Fő requirements.txt
    2. Plugin requirements.txt fájlok (builtin és external)
    """
    requirements_files = []
    
    # Fő requirements.txt
    main_req = root / "requirements.txt"
    if main_req.exists():
        requirements_files.append(main_req)
    
    # Plugin könyvtárak
    plugin_dirs = [
        root / "src" / "dubsync" / "plugins" / "builtin",
        root / "src" / "dubsync" / "plugins" / "external",
    ]
    
    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            continue
        
        # Közvetlen plugin mappák
        for subdir in plugin_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("_"):
                req_file = subdir / "requirements.txt"
                if req_file.exists():
                    requirements_files.append(req_file)
    
    return requirements_files


def parse_requirements(file_path: Path) -> Set[str]:
    """
    Requirements fájl beolvasása.
    
    Returns:
        Csomagok halmaza
    """
    packages = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Üres sorok és kommentek kihagyása
                if not line or line.startswith('#'):
                    continue
                
                # -r include kihagyása (rekurzív include)
                if line.startswith('-r'):
                    continue
                
                packages.add(line)
    except Exception as e:
        print(f"  [!] Hiba a fájl olvasásakor ({file_path}): {e}")
    
    return packages


def get_installed_packages() -> Set[str]:
    """
    Telepített csomagok listázása.
    
    Returns:
        Telepített csomag nevek (kisbetűs)
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
    Kinyeri a csomag nevét a requirement stringből.
    
    "package>=1.0.0" -> "package"
    """
    for sep in ['>=', '<=', '==', '!=', '~=', '>', '<']:
        if sep in requirement:
            return requirement.split(sep)[0].lower().strip()
    
    return requirement.lower().strip()


def check_and_install(requirements_files: List[Path], auto_install: bool = True) -> Tuple[int, int]:
    """
    Ellenőrzi és telepíti a hiányzó függőségeket.
    
    Args:
        requirements_files: Requirements fájlok listája
        auto_install: Automatikus telepítés
        
    Returns:
        (telepített, hiányzó) csomagok száma
    """
    all_requirements = set()
    
    print("[*] Requirements fájlok keresése...")
    for req_file in requirements_files:
        rel_path = req_file.relative_to(get_project_root())
        print(f"    - {rel_path}")
        all_requirements.update(parse_requirements(req_file))
    
    if not all_requirements:
        print("[OK] Nincsenek függőségek definiálva.")
        return 0, 0
    
    print(f"\n[*] Összesen {len(all_requirements)} függőség található.")
    
    # Telepített csomagok
    installed = get_installed_packages()
    
    # Hiányzó csomagok keresése
    missing = []
    for req in all_requirements:
        pkg_name = extract_package_name(req)
        if pkg_name not in installed:
            missing.append(req)
    
    if not missing:
        print("[OK] Minden függőség telepítve van.")
        return 0, 0
    
    print(f"\n[!] {len(missing)} hiányzó függőség:")
    for pkg in missing:
        print(f"    - {pkg}")
    
    if not auto_install:
        return 0, len(missing)
    
    # Telepítés
    print("\n[*] Függőségek telepítése...")
    
    installed_count = 0
    for req in missing:
        try:
            print(f"    Telepítés: {req}...", end=" ", flush=True)
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', req],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("OK")
                installed_count += 1
            else:
                print("HIBA")
                print(f"      {result.stderr[:200]}")
        except Exception as e:
            print(f"HIBA: {e}")
    
    return installed_count, len(missing) - installed_count


def main():
    """Fő belépési pont."""
    print()
    print("=" * 50)
    print("  DubSync - Függőség Ellenőrző")
    print("=" * 50)
    print()
    
    root = get_project_root()
    requirements_files = find_requirements_files(root)
    
    if not requirements_files:
        print("[!] Nem található requirements.txt fájl.")
        return 1
    
    installed, failed = check_and_install(requirements_files, auto_install=True)
    
    print()
    if failed > 0:
        print(f"[!] {failed} csomag telepítése sikertelen.")
        return 1
    else:
        print("[OK] Minden függőség rendben.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
