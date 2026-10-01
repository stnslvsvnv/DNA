"""Common helpers for DNA service scripts.

This module is the shared foundation for `scripts/dna/*.py`. It centralises
filesystem layout, JSON I/O, and feature-state lookups so that every check
script can stay short and focused on its own logic.

The DNA manifest (`DNA.md`) and method documents
(`methods/dna-*.md`) describe what each check must verify; this
module describes only how to find and read the artifacts those checks
operate on.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


def _project_root() -> Path:
    """Resolve the host project root.

    The scripts may run from an installed copy outside the host repository
    (agent skill, cloned kit), so the script location is never the primary
    signal. Priority: ``DNA_PROJECT_ROOT`` env, then the git top-level of the
    current directory, then the current directory itself.
    """
    configured = os.environ.get("DNA_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        root = proc.stdout.strip()
        if root:
            return Path(root).resolve()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path.cwd().resolve()


PROJECT_ROOT = _project_root()


def _state_root() -> Path:
    """Return the DNA state root, overridable for host repositories."""
    configured = os.environ.get("DNA_STATE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return PROJECT_ROOT / ".dna"


DNA_STATE_DIR = _state_root()
DNA_ARCHIVE_DIR = DNA_STATE_DIR / "_archived"
DNA_PROJECT_FILE = DNA_STATE_DIR / "project.yaml"


def load_project() -> dict:
    """Load the project profile (`.dna/project.yaml`); {} when missing."""
    if not DNA_PROJECT_FILE.exists():
        return {}
    data = yaml.safe_load(DNA_PROJECT_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def feature_dir(feature_slug: str) -> Path:
    """Return the canonical state directory for a feature."""
    return DNA_STATE_DIR / feature_slug


def cycle_dir(feature_slug: str, cycle_number: int) -> Path:
    """Return the canonical state directory for one cycle of a feature."""
    return feature_dir(feature_slug) / "cycles" / f"cycle-{cycle_number}"


def checks_dir(feature_slug: str, cycle_number: int) -> Path:
    """Return the directory where Law 7 check JSON reports are stored."""
    return cycle_dir(feature_slug, cycle_number) / "checks"


def contract_path(feature_slug: str, cycle_number: int) -> Path:
    """Return the path to the frozen contract for a cycle."""
    return feature_dir(feature_slug) / "contract" / f"connector-{cycle_number}.yaml"


def issue_map_path(feature_slug: str) -> Path:
    """Return the path to the Linear issue map for a feature."""
    return feature_dir(feature_slug) / "linear" / "issue-map.json"


def shared_kernel_path(feature_slug: str) -> Path:
    """Return the path to the explicit Shared Kernel allowlist."""
    return feature_dir(feature_slug) / "shared-kernel.txt"


def now_iso() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    """Load JSON from disk; raise FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    """Atomically write JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def load_shared_kernel(feature_slug: str) -> set[str]:
    """Return the set of files explicitly declared as Shared Kernel.

    Files are stored one per line, comments allowed via leading '#'.
    Missing file means an empty set.
    """
    path = shared_kernel_path(feature_slug)
    if not path.exists():
        return set()
    out: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def git_diff_files(branch: str, base: str) -> list[str]:
    """Return the list of paths changed in `branch` relative to `base`.

    Uses `git diff --name-only base...branch`. Both branch refs must already
    exist locally (run `git fetch` before calling).
    """
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{branch}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


@dataclass
class CheckResult:
    """Common envelope for every Law 7 check JSON output."""

    check: str
    verdict: str
    feature_slug: str
    cycle_number: int
    timestamp: str = field(default_factory=now_iso)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "verdict": self.verdict,
            "feature_slug": self.feature_slug,
            "cycle_number": self.cycle_number,
            "timestamp": self.timestamp,
            "details": self.details,
        }
