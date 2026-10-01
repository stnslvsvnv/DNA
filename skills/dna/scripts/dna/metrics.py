"""DNA health metrics emitter.

Runs at every `dna-close`. Aggregates Section 4 metrics from the manifest
across the closed cycle and writes a metrics report. Useful for retros and
for spotting unhealthy patterns over time.

Usage:
    python scripts/dna/metrics.py --feature my-feature --cycle 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    cycle_dir,
    load_json,
    now_iso,
    write_json,
)


def safe_load(path: Path) -> dict:
    try:
        return load_json(path)
    except FileNotFoundError:
        return {}


def assess(value: float | int, healthy_max: float, alarm_min: float) -> str:
    if value <= healthy_max:
        return "healthy"
    if value >= alarm_min:
        return "alarm"
    return "warning"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument(
        "--contract-changes",
        type=int,
        default=0,
        help="Number of contract changes during this cycle",
    )
    parser.add_argument(
        "--mock-time-hours",
        type=float,
        default=0.0,
        help="Hours from contract freeze to mock running",
    )
    parser.add_argument(
        "--node-duration-percent",
        type=float,
        default=0.0,
        help="Integration-node duration as %% of cycle duration",
    )
    parser.add_argument(
        "--cross-domain-prs",
        type=int,
        default=0,
        help="Count of unsanctioned cross-domain PRs detected",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    metrics = {
        "contract_changes_per_cycle": {
            "value": args.contract_changes,
            "status": assess(args.contract_changes, healthy_max=1, alarm_min=3),
        },
        "time_to_mock_hours": {
            "value": args.mock_time_hours,
            "status": assess(args.mock_time_hours, healthy_max=24, alarm_min=48),
        },
        "node_duration_percent_of_cycle": {
            "value": args.node_duration_percent,
            "status": assess(args.node_duration_percent, healthy_max=10, alarm_min=25),
        },
        "cross_domain_prs": {
            "value": args.cross_domain_prs,
            "status": "healthy" if args.cross_domain_prs == 0 else "alarm",
        },
    }

    overall = (
        "alarm"
        if any(m["status"] == "alarm" for m in metrics.values())
        else "warning"
        if any(m["status"] == "warning" for m in metrics.values())
        else "healthy"
    )

    report = {
        "feature_slug": args.feature,
        "cycle_number": args.cycle,
        "timestamp": now_iso(),
        "overall": overall,
        "metrics": metrics,
    }

    output = args.output or (cycle_dir(args.feature, args.cycle) / "metrics.json")
    write_json(output, report)

    print(f"[metrics] overall={overall} -> {output}")
    for name, payload in metrics.items():
        print(f"  {name}: value={payload['value']} status={payload['status']}")

    return 0 if overall != "alarm" else 1


if __name__ == "__main__":
    sys.exit(main())
