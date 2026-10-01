"""DNA Law 7, check 2: dependency drift detection.

Runs at `dna-close` time. Inspects dependency manifests changed by Spiral A
and Spiral B on their cycle branches. Reports duplicates: dependencies
introduced by one spiral that are already declared by the other spiral
elsewhere in the repo.

This is deliberately a WARNING check, not a blocker: per Law 7 it
contributes to the Law 8 retrospective trigger evaluation but does not stop
`dna-close` on its own.

Supported manifest types (extend as the project grows):
    - api-adapter/pyproject.toml            (Poetry-style)
    - api-adapter/requirements*.txt
    - file_investigator/pyproject.toml
    - file_investigator/requirements*.txt
    - frontend/package.json
    - any pyproject.toml or requirements*.txt at the repo root

Usage:
    python scripts/dna/dependency_drift_check.py \\
        --feature my-feature \\
        --cycle 1 \\
        --branch-a feat/my-feature/spiral-a/cycle-1 \\
        --branch-b feat/my-feature/spiral-b/cycle-1 \\
        --base feat/my-feature
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    PROJECT_ROOT,
    CheckResult,
    checks_dir,
    git_diff_files,
    write_json,
)

DEP_FILE_PATTERNS = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
)


def is_dep_file(path: str) -> bool:
    name = Path(path).name
    return name in DEP_FILE_PATTERNS or name.startswith("requirements")


def list_changed_dep_files(branch: str, base: str) -> list[str]:
    return [p for p in git_diff_files(branch, base) if is_dep_file(p)]


def file_at_revision(path: str, ref: str) -> str:
    """Return file content at `ref` or an empty string if it does not exist."""
    try:
        proc = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout
    except subprocess.CalledProcessError:
        return ""


def parse_python_deps(content: str) -> set[str]:
    """Extract package names from pyproject.toml or requirements.txt content."""
    deps: set[str] = set()
    if not content:
        return deps

    # requirements.txt style: "package==1.0", "package>=1.0", "package"
    for raw in content.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if match:
            deps.add(match.group(1).lower())

    # pyproject.toml: very rough scan for "package" inside dependencies arrays.
    if "[" in content and "]" in content and "dependencies" in content:
        for match in re.finditer(r'"([A-Za-z0-9_.\-]+)\s*[<>=!~]', content):
            deps.add(match.group(1).lower())
        for match in re.finditer(r'"([A-Za-z0-9_.\-]+)"', content):
            name = match.group(1).lower()
            if not name.startswith(("python", "license", "name", "version")):
                deps.add(name)
    return deps


def parse_npm_deps(content: str) -> set[str]:
    if not content:
        return set()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return set()
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key) or {}
        if isinstance(section, dict):
            deps.update(name.lower() for name in section.keys())
    return deps


def extract_added_deps(path: str, branch: str, base: str) -> set[str]:
    """Return dependencies added in `branch` versus `base` for one file."""
    before = (
        parse_npm_deps(file_at_revision(path, base))
        if path.endswith(".json")
        else parse_python_deps(file_at_revision(path, base))
    )
    after = (
        parse_npm_deps(file_at_revision(path, branch))
        if path.endswith(".json")
        else parse_python_deps(file_at_revision(path, branch))
    )
    return after - before


def collect_added_deps(branch: str, base: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for path in list_changed_dep_files(branch, base):
        added = extract_added_deps(path, branch, base)
        if added:
            out[path] = added
    return out


def existing_deps_in_partner(partner_branch: str) -> set[str]:
    """Approximate set of dependencies already declared on the partner branch."""
    deps: set[str] = set()
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", partner_branch],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for path in files:
        if not is_dep_file(path):
            continue
        content = file_at_revision(path, partner_branch)
        if path.endswith(".json"):
            deps.update(parse_npm_deps(content))
        else:
            deps.update(parse_python_deps(content))
    return deps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--branch-a", required=True)
    parser.add_argument("--branch-b", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def run_check(
    feature: str,
    cycle: int,
    branch_a: str,
    branch_b: str,
    base: str,
) -> CheckResult:
    a_added = collect_added_deps(branch_a, base)
    b_added = collect_added_deps(branch_b, base)

    a_added_flat = {d for deps in a_added.values() for d in deps}
    b_added_flat = {d for deps in b_added.values() for d in deps}

    b_existing = existing_deps_in_partner(branch_b)
    a_existing = existing_deps_in_partner(branch_a)

    duplicates_a_into_b = sorted(a_added_flat & b_existing)
    duplicates_b_into_a = sorted(b_added_flat & a_existing)

    has_duplicates = bool(duplicates_a_into_b or duplicates_b_into_a)
    verdict = "warning" if has_duplicates else "pass"

    return CheckResult(
        check="dependency_drift",
        verdict=verdict,
        feature_slug=feature,
        cycle_number=cycle,
        details={
            "spiral_a_new_deps": sorted(a_added_flat),
            "spiral_b_new_deps": sorted(b_added_flat),
            "duplicates_a_already_in_b": duplicates_a_into_b,
            "duplicates_b_already_in_a": duplicates_b_into_a,
        },
    )


def main() -> int:
    args = parse_args()
    result = run_check(
        feature=args.feature,
        cycle=args.cycle,
        branch_a=args.branch_a,
        branch_b=args.branch_b,
        base=args.base,
    )

    output = args.output or (checks_dir(args.feature, args.cycle) / "dependency_drift.json")
    write_json(output, result.to_dict())

    print(f"[dependency_drift] verdict={result.verdict} -> {output}")
    # WARNING is non-blocking, exit 0 even on warning.
    return 0


if __name__ == "__main__":
    sys.exit(main())
