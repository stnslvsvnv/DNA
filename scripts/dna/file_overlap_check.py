"""DNA Law 7, check 1: file overlap detection.

Runs at `dna-close` time. Compares the set of files modified by Spiral A on
its cycle branch against the set modified by Spiral B on its cycle branch
(both relative to the feature branch). Files explicitly listed in
`shared-kernel.txt` are exempt.

Verdict:
    pass  - no overlap (or overlap only inside Shared Kernel allowlist)
    fail  - real overlap detected; the responsible spiral is the one that
            wrote into foreign territory.

Identification of the responsible spiral is heuristic: the spiral that
modified more files in the intersection wins the responsibility. This is
deliberately simple; if both spirals modified the same files in the
intersection, the responsibility is `both` and the manifest demands a
mini-retrospective.

Usage:
    python scripts/dna/file_overlap_check.py \\
        --feature my-feature \\
        --cycle 1 \\
        --branch-a feat/my-feature/spiral-a/cycle-1 \\
        --branch-b feat/my-feature/spiral-b/cycle-1 \\
        --base feat/my-feature \\
        --output .dna/my-feature/cycles/cycle-1/checks/file_overlap.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    CheckResult,
    checks_dir,
    git_diff_files,
    load_shared_kernel,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True, help="Feature slug")
    parser.add_argument("--cycle", type=int, required=True, help="Cycle number")
    parser.add_argument("--branch-a", required=True, help="Spiral A cycle branch")
    parser.add_argument("--branch-b", required=True, help="Spiral B cycle branch")
    parser.add_argument(
        "--base",
        required=True,
        help="Feature branch (e.g. feat/<slug>) used as merge base",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for the JSON report. Default: standard checks dir.",
    )
    return parser.parse_args()


def run_check(
    feature: str,
    cycle: int,
    branch_a: str,
    branch_b: str,
    base: str,
) -> CheckResult:
    files_a = set(git_diff_files(branch_a, base))
    files_b = set(git_diff_files(branch_b, base))
    raw_intersection = files_a & files_b

    shared_kernel = load_shared_kernel(feature)
    real_intersection = sorted(raw_intersection - shared_kernel)
    exempt_intersection = sorted(raw_intersection & shared_kernel)

    if not real_intersection:
        verdict = "pass"
        responsible = None
    else:
        a_count = sum(1 for f in real_intersection if f in files_a)
        b_count = sum(1 for f in real_intersection if f in files_b)
        if a_count == b_count:
            responsible = "both"
        elif a_count > b_count:
            responsible = "a"
        else:
            responsible = "b"
        verdict = "fail"

    return CheckResult(
        check="file_overlap",
        verdict=verdict,
        feature_slug=feature,
        cycle_number=cycle,
        details={
            "spiral_a_files_changed": len(files_a),
            "spiral_b_files_changed": len(files_b),
            "intersection": real_intersection,
            "shared_kernel_exempt": exempt_intersection,
            "responsible_spiral": responsible,
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

    output = args.output or (checks_dir(args.feature, args.cycle) / "file_overlap.json")
    write_json(output, result.to_dict())

    print(f"[file_overlap] verdict={result.verdict} -> {output}")
    return 0 if result.verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
