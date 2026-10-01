"""file_overlap_check.py: real git history overlap detection and Shared Kernel exemption."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "dna" / "file_overlap_check.py"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


def git(repo: Path, *args: str) -> None:
    env = {**os.environ, **GIT_ENV}
    subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=env
    )


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)


def make_history(tmp_path: Path) -> Path:
    repo = tmp_path / "host"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    (repo / "README.md").write_text("host\n", encoding="utf-8")
    commit(repo, "init")

    git(repo, "checkout", "-b", "feat/demo")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    commit(repo, "feature base")

    git(repo, "checkout", "-b", "cycle/demo/spiral-a/cycle-1")
    (repo / "a-only.txt").write_text("a\n", encoding="utf-8")
    (repo / "common.txt").write_text("from a\n", encoding="utf-8")
    commit(repo, "spiral a")

    git(repo, "checkout", "feat/demo")
    git(repo, "checkout", "-b", "cycle/demo/spiral-b/cycle-1")
    (repo / "b-only.txt").write_text("b\n", encoding="utf-8")
    (repo / "common.txt").write_text("from b\n", encoding="utf-8")
    commit(repo, "spiral b")
    return repo


def run(repo: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "DNA_PROJECT_ROOT": str(repo)}
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--feature",
            "demo",
            "--cycle",
            "1",
            "--branch-a",
            "cycle/demo/spiral-a/cycle-1",
            "--branch-b",
            "cycle/demo/spiral-b/cycle-1",
            "--base",
            "feat/demo",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_overlap_is_detected(tmp_path: Path) -> None:
    repo = make_history(tmp_path)
    proc = run(repo)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    report = json.loads(
        (repo / ".dna" / "demo" / "cycles" / "cycle-1" / "checks" / "file_overlap.json").read_text()
    )
    assert report["verdict"] == "fail"
    assert "common.txt" in report["details"]["intersection"]


def test_shared_kernel_exempts_overlap(tmp_path: Path) -> None:
    repo = make_history(tmp_path)
    kernel = repo / ".dna" / "demo" / "shared-kernel.txt"
    kernel.parent.mkdir(parents=True, exist_ok=True)
    kernel.write_text("common.txt\n", encoding="utf-8")
    proc = run(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
