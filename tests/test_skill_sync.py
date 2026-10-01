"""The skill mirror under skills/dna/ must match the canonical kit at the root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_mirror_in_sync() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_skill.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_skill_frontmatter_has_name_and_description() -> None:
    text = (ROOT / "skills" / "dna" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    frontmatter = text.split("---", 2)[1]
    assert "\nname: dna" in frontmatter
    description_line = [
        line for line in frontmatter.splitlines() if line.startswith("description:")
    ]
    assert description_line, "SKILL.md must declare a description"
    assert "dna-disco" in description_line[0]
