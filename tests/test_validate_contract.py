"""validate_contract.py: frozen contracts pass, unfrozen ones fail."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "dna" / "validate_contract.py"

CONTRACT_OK = """\
connector_id: cp-1
cycle: 1
kind: rest
version: 1.0.0
spirals: {producer: A, consumer: B}
schema:
  paths:
    /orders:
      get: {}
contract_tests:
  - path: tests/contracts/cp-1/producer_test.py
signed_by:
  spiral_a_leader: alice
  spiral_b_leader: bob
signed_at: "2026-01-01T00:00:00+00:00"
"""


def write_contract(repo: Path, text: str) -> None:
    target = repo / ".dna" / "demo" / "contract" / "connector-1.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def run(repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "DNA_PROJECT_ROOT": str(repo)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--feature", "demo", "--cycle", "1"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_frozen_contract_passes(tmp_path: Path) -> None:
    write_contract(tmp_path, CONTRACT_OK)
    proc = run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK" in proc.stdout


def test_unfrozen_contract_fails(tmp_path: Path) -> None:
    write_contract(tmp_path, CONTRACT_OK.replace("spiral_b_leader: bob", "spiral_b_leader:"))
    proc = run(tmp_path)
    assert proc.returncode == 1
    assert "not filled" in proc.stdout


def test_missing_contract_is_environment_error(tmp_path: Path) -> None:
    proc = run(tmp_path)
    assert proc.returncode == 2
