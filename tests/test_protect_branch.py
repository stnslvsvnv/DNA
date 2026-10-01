"""protect_branch.py: manual fallback, dry-run, and missing-branch handling."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "dna" / "protect_branch.py"

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


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "host"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "remote", "add", "origin", "https://github.com/example/dna-host.git")
    (repo / "README.md").write_text("host\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "init")
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DNA_PROJECT_ROOT": str(repo)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )


def test_manual_provider_prints_instructions(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    proc = run(repo, "--branch", "main", "--provider", "manual")
    assert proc.returncode == 0, proc.stderr
    assert "main: manual" in proc.stdout
    assert "GitHub UI" in proc.stdout


def test_feature_flag_expands_and_missing_branch_warns(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    proc = run(repo, "--feature", "demo", "--provider", "manual")
    assert proc.returncode == 0
    assert "main: manual" in proc.stdout
    assert "feat/demo: warning" in proc.stdout


def test_dry_run_reports_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    proc = run(repo, "--branch", "main", "--provider", "github", "--dry-run")
    assert proc.returncode == 0
    assert "main:" in proc.stdout


def test_not_a_git_repo_is_environment_error(tmp_path: Path) -> None:
    bare = tmp_path / "plain"
    bare.mkdir()
    proc = run(bare, "--branch", "main", "--provider", "manual")
    assert proc.returncode == 2
