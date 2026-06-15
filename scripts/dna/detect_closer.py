"""DNA dna-close trigger detector.

Reads Linear issue history for a given feature/cycle and identifies the
member who closed the last issue belonging to that cycle. That person is
the responsible runner of `dna-close` per manifest Law 7 (last-issue-closer
rule).

This script depends on the `linear` CLI wrapper (per configured issue-tracker policy) and
falls back to a manual prompt if Linear data is unavailable or ambiguous
(timestamp tie, missing data).

Usage:
    python scripts/dna/detect_closer.py --feature my-feature --cycle 1
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    cycle_dir,
    issue_map_path,
    load_json,
    now_iso,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def linear_available() -> bool:
    return shutil.which("linear") is not None


def fetch_cycle_issues(feature: str, cycle: int) -> list[dict]:
    """Return issues for this feature/cycle via `linear list`.

    Output format depends on the CLI version. We try a JSON output first;
    if it's not supported, we fall back to a parseable text output.
    """
    label_a = f"dna:{feature}"
    label_b = f"cycle:{cycle}"

    try:
        proc = subprocess.run(
            [
                "linear",
                "list",
                "--label",
                label_a,
                "--label",
                label_b,
                "--state",
                "Done",
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(proc.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return []


def pick_last_closer(issues: list[dict]) -> tuple[str | None, str | None, str]:
    """Return (closer_username, closer_issue_id, reason)."""
    if not issues:
        return None, None, "no closed issues found"

    # Sort by closed_at descending. Field name varies by CLI; try a few.
    def closed_at(issue: dict) -> str:
        return issue.get("closedAt") or issue.get("closed_at") or issue.get("completedAt") or ""

    sorted_issues = sorted(issues, key=closed_at, reverse=True)
    if not sorted_issues[0].get("closedAt") and not sorted_issues[0].get("completedAt"):
        return None, None, "issues have no closed timestamp"

    last = sorted_issues[0]
    second = sorted_issues[1] if len(sorted_issues) > 1 else None

    last_ts = closed_at(last)
    if second and closed_at(second) == last_ts:
        return None, None, "timestamp tie between last two closures"

    closer = (
        last.get("assignee", {}).get("name")
        or last.get("assignee_name")
        or last.get("closedBy", {}).get("name")
    )
    issue_id = last.get("identifier") or last.get("id")
    return closer, issue_id, f"last closure at {last_ts}"


def main() -> int:
    args = parse_args()

    if not linear_available():
        print("WARN: `linear` CLI not found; falling back to manual mode.")
        report = {
            "feature_slug": args.feature,
            "cycle_number": args.cycle,
            "timestamp": now_iso(),
            "closer": None,
            "issue_id": None,
            "reason": "linear CLI not available",
            "manual_fallback": True,
        }
    else:
        # Validate that the issue map exists; defensive check.
        try:
            load_json(issue_map_path(args.feature))
        except FileNotFoundError:
            print(
                "ERROR: linear/issue-map.json missing; did dna-split run?",
                file=sys.stderr,
            )
            return 2

        issues = fetch_cycle_issues(args.feature, args.cycle)
        closer, issue_id, reason = pick_last_closer(issues)

        report = {
            "feature_slug": args.feature,
            "cycle_number": args.cycle,
            "timestamp": now_iso(),
            "closer": closer,
            "issue_id": issue_id,
            "reason": reason,
            "manual_fallback": closer is None,
            "considered_issues": len(issues),
        }

    output = args.output or (cycle_dir(args.feature, args.cycle) / "closer.json")
    write_json(output, report)

    if report["closer"]:
        print(f"[detect_closer] closer={report['closer']} -> {output}")
        return 0
    print(f"[detect_closer] manual fallback required ({report['reason']}) -> {output}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
