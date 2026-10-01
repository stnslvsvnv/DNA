"""applicability_gate.py: pass and fail verdicts on synthetic dossiers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "dna" / "applicability_gate.py"

DOSSIER_OK = {
    "feature_slug": "demo",
    "created_at": "2026-01-01T00:00:00+00:00",
    "team": {"size": 2, "members": ["alice", "bob"]},
    "domains_candidates": [
        {"name": "orders", "potential_owner": "alice"},
        {"name": "billing", "potential_owner": "bob"},
    ],
    "requirements_stable_for_cycle": True,
}


def make_project(tmp_path: Path, dossier: dict) -> Path:
    repo = tmp_path / "host"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    fdir = repo / ".dna" / "demo"
    fdir.mkdir(parents=True)
    (fdir / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    return repo


def run(repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "DNA_PROJECT_ROOT": str(repo)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--feature", "demo"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_passing_dossier(tmp_path: Path) -> None:
    repo = make_project(tmp_path, DOSSIER_OK)
    proc = run(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((repo / ".dna" / "demo" / "applicability-gate-report.json").read_text())
    assert report["verdict"] == "pass"


def test_team_too_large_fails(tmp_path: Path) -> None:
    dossier = json.loads(json.dumps(DOSSIER_OK))
    dossier["team"]["size"] = 7
    proc = run(make_project(tmp_path, dossier))
    assert proc.returncode == 1


def test_single_domain_fails(tmp_path: Path) -> None:
    dossier = json.loads(json.dumps(DOSSIER_OK))
    dossier["domains_candidates"] = [{"name": "orders", "potential_owner": "alice"}]
    proc = run(make_project(tmp_path, dossier))
    assert proc.returncode == 1


def test_missing_ci_indicator_fails(tmp_path: Path) -> None:
    repo = make_project(tmp_path, DOSSIER_OK)
    shutil.rmtree(repo / ".github")
    proc = run(repo)
    assert proc.returncode == 1
