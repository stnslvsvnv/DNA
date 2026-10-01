"""DNA Law 8: retrospective trigger evaluation.

Runs at `dna-close` time after Law 7 checks and after honest-flag
collection. Evaluates whether the cycle had any condition severe enough to
demand a retrospective + ADR.

Triggers:
    1. Contract changed >= 2 times during the cycle.
    2. Integration node failed first attempt (any Law 7 check failed and
       was retried before this final run).
    3. Cycle amplitude exceeded 10 working days.
    4. Heroic-integration honest flag is Minor or Major.

If any trigger fires, the next cycle is blocked until both spirals sign
off on the auto-created ADR draft.

This script does not create the ADR file itself (that is a `dna-close`
orchestration step); it only emits the verdict and the list of triggers
that fired so the orchestrator knows what to do.

Usage:
    python scripts/dna/retrospective_trigger.py \\
        --feature my-feature \\
        --cycle 1 \\
        --honest-flag Minor \\
        --contract-changes 2 \\
        --first-attempt-failed \\
        --amplitude-days 11
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    cycle_dir,
    now_iso,
    write_json,
)

CYCLE_AMPLITUDE_SOFT_CAP_DAYS = 10
HONEST_FLAG_TRIGGER_VALUES = {"Minor", "Major"}
CONTRACT_CHANGE_TRIGGER_THRESHOLD = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument(
        "--honest-flag",
        choices=["No", "Minor", "Major"],
        required=True,
        help="Heroic Integration honest flag from Integration Issue",
    )
    parser.add_argument(
        "--contract-changes",
        type=int,
        default=0,
        help="Number of contract changes during the cycle",
    )
    parser.add_argument(
        "--first-attempt-failed",
        action="store_true",
        help="Set if the integration node failed on first attempt",
    )
    parser.add_argument(
        "--amplitude-days",
        type=int,
        required=True,
        help="Actual cycle amplitude in working days",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    triggers: list[str] = []

    if args.contract_changes >= CONTRACT_CHANGE_TRIGGER_THRESHOLD:
        triggers.append(f"contract_changed_x{args.contract_changes}")

    if args.first_attempt_failed:
        triggers.append("first_attempt_failed")

    if args.amplitude_days > CYCLE_AMPLITUDE_SOFT_CAP_DAYS:
        triggers.append(f"amplitude_exceeded_{args.amplitude_days}d")

    if args.honest_flag in HONEST_FLAG_TRIGGER_VALUES:
        triggers.append(f"heroic_integration_{args.honest_flag.lower()}")

    report = {
        "feature_slug": args.feature,
        "cycle_number": args.cycle,
        "timestamp": now_iso(),
        "triggers_fired": triggers,
        "retrospective_required": bool(triggers),
        "inputs": {
            "honest_flag": args.honest_flag,
            "contract_changes": args.contract_changes,
            "first_attempt_failed": args.first_attempt_failed,
            "amplitude_days": args.amplitude_days,
        },
    }

    output = args.output or (cycle_dir(args.feature, args.cycle) / "retrospective-trigger.json")
    write_json(output, report)

    print(
        f"[retrospective_trigger] required={report['retrospective_required']} "
        f"triggers={triggers or 'none'} -> {output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
