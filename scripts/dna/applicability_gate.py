"""DNA applicability gate.

Runs between `dna-disco` and `dna-split`. Verifies that the feature
described by the dossier qualifies for DNA per manifest Section 1
(applicability conditions). Produces a binary verdict.

Verdict:
    pass - all conditions met; `dna-split` may proceed
    fail - one or more conditions failed; DNA does not apply, fallback to
           sequential execution or single-executor work

Usage:
    python scripts/dna/applicability_gate.py --feature my-feature
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    PROJECT_ROOT,
    feature_dir,
    load_json,
    now_iso,
    write_json,
)


def check_team_size(dossier: dict) -> tuple[bool, str]:
    team = dossier.get("team") or {}
    size = team.get("size")
    if not isinstance(size, int):
        return False, "team.size not declared"
    if 2 <= size <= 6:
        return True, f"team size = {size}"
    return False, f"team size {size} outside DNA range (2-6)"


def check_two_domains(dossier: dict) -> tuple[bool, str]:
    domains = dossier.get("domains_candidates") or []
    if len(domains) >= 2:
        return True, f"{len(domains)} candidate domains"
    return False, f"only {len(domains)} domain(s) declared"


def check_owners(dossier: dict) -> tuple[bool, str]:
    domains = dossier.get("domains_candidates") or []
    missing = [d.get("id", "?") for d in domains if not d.get("potential_owner")]
    if missing:
        return False, f"missing potential_owner on: {missing}"
    return True, "all domains have a potential_owner"


def check_ci_present() -> tuple[bool, str]:
    indicators = [
        ".github/workflows",
        "Makefile",
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
    ]
    found = [p for p in indicators if (PROJECT_ROOT / p).exists()]
    if found:
        return True, f"CI indicator found: {found[0]}"
    return False, "no CI infrastructure indicator found"


def check_stability(dossier: dict) -> tuple[bool, str]:
    if dossier.get("requirements_stable_for_cycle") is True:
        return True, "requirements declared stable for >=1 cycle"
    if dossier.get("requirements_stable_for_cycle") is False:
        return False, "requirements declared NOT stable for >=1 cycle"
    # Default to True if not declared, with a note (initiator-driven check).
    return True, "stability not explicitly declared; assumed acceptable"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fdir = feature_dir(args.feature)
    dossier_path = fdir / "dossier.json"
    if not dossier_path.exists():
        print(f"ERROR: dossier.json missing at {dossier_path}", file=sys.stderr)
        return 2

    dossier = load_json(dossier_path)

    checks = [
        ("team_size", check_team_size(dossier)),
        ("two_or_more_domains", check_two_domains(dossier)),
        ("owners_present", check_owners(dossier)),
        ("ci_present", check_ci_present()),
        ("requirements_stable", check_stability(dossier)),
    ]

    failed = [(name, msg) for name, (ok, msg) in checks if not ok]
    verdict = "pass" if not failed else "fail"

    report = {
        "feature_slug": args.feature,
        "verdict": verdict,
        "timestamp": now_iso(),
        "checks": {name: {"ok": ok, "detail": msg} for name, (ok, msg) in checks},
        "failed": [name for name, _ in failed],
    }

    output = args.output or (fdir / "applicability-gate-report.json")
    write_json(output, report)

    print(f"[applicability_gate] verdict={verdict} -> {output}")
    if failed:
        for name, msg in failed:
            print(f"  - FAILED: {name}: {msg}")
    return 0 if verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
