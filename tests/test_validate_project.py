"""validate_project.py: profile validation semantics."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "dna" / "validate_project.py"

VALID = """\
version: 1
tracker:
  kind: linear
  team: CIT
members:
  alice:
    name: Alice
    linear: alice@example.com
  bob:
    name: Bob
    linear: bob@example.com
lanes:
  spiral_a:
    leader: alice
    executor: human
  spiral_b:
    leader: bob
    executor: agent:worker-2
initiator: alice
"""


def run(project_root: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "DNA_PROJECT_ROOT": str(project_root)}
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
    )


def write_profile(root: Path, text: str) -> None:
    target = root / ".dna" / "project.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def test_missing_profile_fails(tmp_path: Path) -> None:
    proc = run(tmp_path)
    assert proc.returncode == 1
    assert "dna-bootstrap" in proc.stdout


def test_valid_profile_passes(tmp_path: Path) -> None:
    write_profile(tmp_path, VALID)
    proc = run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "pass" in proc.stdout


def test_leader_must_be_member(tmp_path: Path) -> None:
    write_profile(tmp_path, VALID.replace("leader: bob", "leader: carol"))
    proc = run(tmp_path)
    assert proc.returncode == 1
    assert "carol" in proc.stdout


def test_missing_initiator_fails(tmp_path: Path) -> None:
    write_profile(tmp_path, VALID.replace("initiator: alice\n", ""))
    proc = run(tmp_path)
    assert proc.returncode == 1
    assert "initiator" in proc.stdout


def test_malformed_yaml_fails(tmp_path: Path) -> None:
    write_profile(tmp_path, "version: [1\n")
    proc = run(tmp_path)
    assert proc.returncode == 1
