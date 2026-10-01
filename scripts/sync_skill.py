"""Sync the portable DNA kit into ``skills/dna/``.

The repository root is the single source of truth. This script mirrors the
kit files into the skill directory so that skill installers (`omp skill`,
`npx skills add`) ship a self-contained copy. ``tests/test_skill_sync.py``
fails when the mirror drifts, and ``--check`` performs the same comparison
without writing.

Usage:
    python scripts/sync_skill.py           # regenerate the mirror
    python scripts/sync_skill.py --check   # verify the mirror is in sync
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "dna"

KIT_FILES = [
    "VERSION",
    "DNA.md",
    "dna-bootstrap.md",
    "project.example.yaml",
]
KIT_DIRS = [
    "methods",
    "scripts/dna",
]
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")


def kit_relative_paths() -> list[Path]:
    """Return every canonical kit path relative to the repository root."""
    paths: list[Path] = [Path(name) for name in KIT_FILES]
    for dirname in KIT_DIRS:
        base = ROOT / dirname
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                paths.append(path.relative_to(ROOT))
    return paths


def sync() -> None:
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    for name in KIT_FILES:
        shutil.copy2(ROOT / name, SKILL_DIR / name)
    for dirname in KIT_DIRS:
        target = SKILL_DIR / dirname
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(ROOT / dirname, target, ignore=IGNORE)
    print(f"synced {len(kit_relative_paths())} files -> {SKILL_DIR}")


def check() -> int:
    drift: list[str] = []
    for rel in kit_relative_paths():
        source = ROOT / rel
        mirror = SKILL_DIR / rel
        if not mirror.exists():
            drift.append(f"missing in skill: {rel}")
        elif source.read_bytes() != mirror.read_bytes():
            drift.append(f"content differs: {rel}")
    if drift:
        for item in drift:
            print(f"DRIFT: {item}")
        return 1
    print(f"skill mirror in sync ({len(kit_relative_paths())} files)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without writing.")
    args = parser.parse_args()
    if args.check:
        return check()
    sync()
    return 0


if __name__ == "__main__":
    sys.exit(main())
