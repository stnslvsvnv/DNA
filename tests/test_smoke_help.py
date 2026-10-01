"""Every service script must answer --help with exit code 0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts" / "dna"
NON_CLI = {"common.py", "__init__.py"}


def script_paths() -> list[Path]:
    return sorted(p for p in SCRIPTS_DIR.glob("*.py") if p.name not in NON_CLI)


def test_scripts_are_discovered() -> None:
    assert len(script_paths()) >= 10


def test_help_smoke() -> None:
    failures = []
    for script in script_paths():
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or "usage" not in proc.stdout.lower():
            failures.append(f"{script.name}: rc={proc.returncode} {proc.stderr.strip()}")
    assert not failures, "\n".join(failures)
