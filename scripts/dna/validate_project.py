"""DNA project profile validator.

Validates ``.dna/project.yaml`` — the per-repository setup DNA needs before
any feature run: tracker, team members, lane assignments (which spiral is
owned by whom), and the optional companion-tool declarations. See
``dna-bootstrap.md`` for the setup procedure and ``project.example.yaml``
for the template.

Usage:
    python scripts/dna/validate_project.py [--output PATH]

Exit codes:
    0 — profile valid (warnings allowed)
    1 — profile missing or invalid
    2 — environment error (unreadable file, invalid YAML)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    DNA_PROJECT_FILE,
    now_iso,
    write_json,
)

MEMBER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
LANES = ("spiral_a", "spiral_b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the JSON report.",
    )
    return parser.parse_args()


def parse_profile() -> tuple[dict, list[str]]:
    """Return (profile, errors). Empty profile means unreadable."""
    if not DNA_PROJECT_FILE.exists():
        return {}, [
            f"project profile missing at {DNA_PROJECT_FILE}; "
            "run the dna-bootstrap procedure (see dna-bootstrap.md)"
        ]
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return {}, ["PyYAML is not installed; pip install pyyaml"]

    try:
        data = yaml.safe_load(DNA_PROJECT_FILE.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, [f"project profile is not valid YAML: {exc}"]

    if not isinstance(data, dict):
        return {}, ["project profile must be a YAML mapping"]
    return data, []


def validate(profile: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the project profile."""
    errors: list[str] = []
    warnings: list[str] = []

    version = profile.get("version")
    if version != 1:
        errors.append(f"version must be 1, got {version!r}")

    tracker = profile.get("tracker") or {}
    kind = tracker.get("kind", "linear")
    if kind != "linear":
        errors.append(f"tracker.kind must be 'linear' (the only supported tracker), got {kind!r}")
    if not str(tracker.get("team") or "").strip():
        errors.append("tracker.team is required (Linear team key, e.g. CIT)")

    members = profile.get("members") or {}
    if not isinstance(members, dict) or not members:
        errors.append("members must be a non-empty mapping of member-id -> details")
        members = {}
    for member_id, details in members.items():
        if not MEMBER_ID_RE.match(str(member_id)):
            errors.append(f"member id {member_id!r} must match {MEMBER_ID_RE.pattern}")
        if not isinstance(details, dict):
            errors.append(f"member {member_id!r} must be a mapping with at least a name")
            continue
        if not str(details.get("name") or "").strip():
            errors.append(f"member {member_id!r} is missing a name")
        if not str(details.get("linear") or "").strip():
            warnings.append(
                f"member {member_id!r} has no linear username; "
                "assignment and closer detection will fall back to manual input"
            )

    lanes = profile.get("lanes") or {}
    for lane in LANES:
        cfg = lanes.get(lane)
        if not isinstance(cfg, dict):
            errors.append(f"lanes.{lane} is required (leader assignment for the parallel lane)")
            continue
        leader = cfg.get("leader")
        if not leader:
            errors.append(f"lanes.{lane}.leader is required")
        elif leader not in members:
            errors.append(f"lanes.{lane}.leader {leader!r} is not declared in members")
        executor = cfg.get("executor")
        if executor is not None and not isinstance(executor, str):
            errors.append(f"lanes.{lane}.executor must be a string (human or agent:<name>)")

    if lanes and set(lanes) - set(LANES):
        warnings.append(f"unknown lanes {sorted(set(lanes) - set(LANES))} are ignored")

    initiator = profile.get("initiator")
    if not initiator:
        errors.append("initiator is required (member id that drives dna-disco/dna-split)")
    elif initiator not in members:
        errors.append(f"initiator {initiator!r} is not declared in members")

    intelligence = profile.get("intelligence")
    if intelligence is not None:
        if not isinstance(intelligence, dict):
            errors.append("intelligence must be a mapping when present")
        else:
            known = {"graph_freshness_cmd", "graph_update_cmd", "call_graph_path"}
            for key, value in intelligence.items():
                if key not in known:
                    warnings.append(f"intelligence.{key} is not recognized and is ignored")
                elif not isinstance(value, str):
                    errors.append(f"intelligence.{key} must be a string")

    branching = profile.get("branching")
    if branching is not None:
        if not isinstance(branching, dict):
            errors.append("branching must be a mapping when present")
        elif not isinstance(branching.get("protected", []), list):
            errors.append("branching.protected must be a list of branch names")

    return errors, warnings


def main() -> int:
    args = parse_args()
    profile, errors = parse_profile()

    if errors and not profile:
        verdict = "fail"
        report = {
            "check": "validate_project",
            "verdict": verdict,
            "profile": str(DNA_PROJECT_FILE),
            "errors": errors,
            "warnings": [],
            "validated_at": now_iso(),
        }
    else:
        errors_found, warnings = validate(profile)
        verdict = "fail" if errors_found else "pass"
        report = {
            "check": "validate_project",
            "verdict": verdict,
            "profile": str(DNA_PROJECT_FILE),
            "errors": errors_found,
            "warnings": warnings,
            "validated_at": now_iso(),
        }

    if args.output:
        write_json(args.output, report)

    for warning in report["warnings"]:
        print(f"WARN: {warning}")
    for error in report["errors"]:
        print(f"ERROR: {error}")

    print(f"validate_project: {report['verdict']} ({DNA_PROJECT_FILE})")
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
