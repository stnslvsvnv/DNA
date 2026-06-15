"""DNA contract validator.

Validates a frozen connector contract (`contract/connector-N.yaml`) against
`schemas/contract.schema.json`. Used by `dna-cycle` to confirm that the
contract is fully signed before launching cycle work.

Also supports recording contract amendments via `--record-change`. Each
amendment is appended to
`.dna/<feature-slug>/contract/changelog.json` so that
`retrospective_trigger.py` at `dna-close` can count amendments per cycle
deterministically (Law 8 trigger: >= 2 amendments).

Usage:
    # Validate the current contract for a cycle
    python scripts/dna/validate_contract.py --feature my-feature --cycle 1

    # Record a mid-cycle amendment
    python scripts/dna/validate_contract.py --feature my-feature --cycle 1 \\
        --record-change "hidden coupling on field X" \\
        --version-before 1.0.0 --version-after 1.1.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from common import (  # type: ignore[import-not-found]
    contract_path,
    feature_dir,
    now_iso,
)

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"


def changelog_path(feature_slug: str) -> Path:
    return feature_dir(feature_slug) / "contract" / "changelog.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument(
        "--record-change",
        metavar="REASON",
        default=None,
        help=(
            "Record a contract amendment with the given reason. Switches the "
            "script from validate mode to record mode. Requires "
            "--version-before and --version-after."
        ),
    )
    parser.add_argument(
        "--version-before",
        default=None,
        help="Connector version before the amendment (e.g. 1.0.0).",
    )
    parser.add_argument(
        "--version-after",
        default=None,
        help="Connector version after the amendment (e.g. 1.1.0).",
    )
    return parser.parse_args()


def basic_validate(contract: dict) -> list[str]:
    """Schema-light validation that does not require jsonschema package.

    Returns a list of error strings; empty list means valid.
    """
    errors: list[str] = []
    required_top = [
        "connector_id",
        "cycle",
        "kind",
        "version",
        "spirals",
        "schema",
        "contract_tests",
        "signed_by",
        "signed_at",
    ]
    for key in required_top:
        if key not in contract:
            errors.append(f"missing top-level key: {key}")

    spirals = contract.get("spirals") or {}
    for role in ("producer", "consumer"):
        if role not in spirals:
            errors.append(f"spirals.{role} missing")

    signed_by = contract.get("signed_by") or {}
    for role in ("spiral_a_leader", "spiral_b_leader"):
        if not signed_by.get(role):
            errors.append(f"signed_by.{role} not filled (contract is not frozen)")

    contract_tests = contract.get("contract_tests") or []
    if len(contract_tests) == 0:
        errors.append("contract_tests is empty (Law 2 demands contract tests)")

    return errors


def record_change(
    feature: str,
    cycle: int,
    reason: str,
    version_before: str,
    version_after: str,
) -> int:
    """Append an amendment entry to the cycle's contract changelog."""
    path = contract_path(feature, cycle)
    if not path.exists():
        print(f"ERROR: contract not found: {path}", file=sys.stderr)
        return 2

    with path.open(encoding="utf-8") as fh:
        contract = yaml.safe_load(fh) or {}

    entry = {
        "connector_id": contract.get("connector_id", f"cp-{cycle}"),
        "cycle": cycle,
        "version_before": version_before,
        "version_after": version_after,
        "reason": reason,
        "timestamp": now_iso(),
        "signed_by": contract.get("signed_by", {}),
    }

    log_path = changelog_path(feature)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if log_path.exists():
        with log_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            data = []
    else:
        data = []

    data.append(entry)

    with log_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(
        f"[validate_contract] recorded change cycle={cycle} "
        f"{version_before} -> {version_after} reason={reason!r} "
        f"({len(data)} total entries) -> {log_path}"
    )
    return 0


def main() -> int:
    args = parse_args()

    # Record mode: append to changelog and exit.
    if args.record_change is not None:
        if not args.version_before or not args.version_after:
            print(
                "ERROR: --record-change requires both --version-before and --version-after",
                file=sys.stderr,
            )
            return 2
        return record_change(
            feature=args.feature,
            cycle=args.cycle,
            reason=args.record_change,
            version_before=args.version_before,
            version_after=args.version_after,
        )

    # Validate mode (default).
    path = contract_path(args.feature, args.cycle)
    if not path.exists():
        print(f"ERROR: contract not found: {path}", file=sys.stderr)
        return 2

    with path.open(encoding="utf-8") as fh:
        contract = yaml.safe_load(fh) or {}

    errors = basic_validate(contract)

    if errors:
        print(f"[validate_contract] FAIL ({len(errors)} errors):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(
        f"[validate_contract] OK contract={args.feature}/cycle-{args.cycle} "
        f"signed_at={contract.get('signed_at')} (verified at {now_iso()})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
