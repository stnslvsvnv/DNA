"""DNA cross-domain coupling detector.

Analyses a call graph JSON file to mechanically identify coupling between two
candidate domains. Used by `dna-disco` to validate MECE demarcation (Law 1)
and by `dna-split` to auto-detect coupling points for connector contracts
(Law 4).

Produces a JSON report:
    - a_calls_b: list of cross-boundary calls from domain A into domain B
    - b_calls_a: reverse direction
    - bidirectional: calls going both ways (MECE violation signal)
    - cycles_detected: whether a cycle exists between domains
    - shared_kernel_candidates: files called from both domains
    - coupling_points_auto: auto-detected connector candidates

Usage:
    python scripts/dna/cross_domain_coupling.py \
        --domain-a "catalog/**" \
        --domain-b "logistics/**" \
        --output .dna/<slug>/cross-domain-coupling.json
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from collections import defaultdict
from pathlib import Path

from common import (  # type: ignore[import-not-found]
    PROJECT_ROOT,
    now_iso,
    write_json,
)

CALL_GRAPH_PATH = PROJECT_ROOT / "call_graph.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain-a",
        required=True,
        help='Glob pattern for domain A files (e.g. "api-adapter/integration/**")',
    )
    parser.add_argument(
        "--domain-b",
        required=True,
        help="Glob pattern for domain B files",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--call-graph",
        type=Path,
        default=CALL_GRAPH_PATH,
        help=f"Path to call_graph.json. Default: {CALL_GRAPH_PATH}",
    )
    return parser.parse_args()


def load_call_graph(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: call graph not found at {path}", file=sys.stderr)
        print("Provide a call graph with --call-graph PATH.", file=sys.stderr)
        sys.exit(2)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def files_in_domain(def_index: dict[str, list[dict]], pattern: str) -> set[str]:
    """Return set of files matching the domain glob pattern."""
    files: set[str] = set()
    for defs in def_index.values():
        for d in defs:
            f = d.get("file", "")
            if f and fnmatch.fnmatch(f, pattern):
                files.add(f)
    return files


def fqns_in_domain(def_index: dict[str, list[dict]], pattern: str) -> set[str]:
    """Return set of FQNs defined in files matching the domain pattern."""
    fqns: set[str] = set()
    for defs in def_index.values():
        for d in defs:
            f = d.get("file", "")
            if f and fnmatch.fnmatch(f, pattern):
                fqn = d.get("fqn", "")
                if fqn:
                    fqns.add(fqn)
    return fqns


def find_cross_calls(
    callers_of: dict[str, list[str]],
    callee_fqns: set[str],
    caller_fqns: set[str],
) -> list[dict]:
    """Find calls from `caller_fqns` into `callee_fqns`."""
    crosses: list[dict] = []
    for callee in sorted(callee_fqns):
        callers = callers_of.get(callee, [])
        for caller in callers:
            if caller in caller_fqns:
                crosses.append({"caller": caller, "callee": callee})
    return crosses


def find_cycles(
    a_calls_b: list[dict],
    b_calls_a: list[dict],
) -> bool:
    """Simple cycle detection: any call in both directions."""
    return bool(a_calls_b and b_calls_a)


def find_shared_kernel_candidates(
    def_index: dict[str, list[dict]],
    a_fqns: set[str],
    b_fqns: set[str],
    callers_of: dict[str, list[str]],
) -> list[str]:
    """Files whose definitions are called from BOTH domain A and domain B."""
    score: dict[str, set[str]] = defaultdict(set)  # file -> set of caller domains

    for callee_fqn, callers in callers_of.items():
        for caller in callers:
            if caller in a_fqns:
                # find the file of callee
                for name, defs in def_index.items():
                    for d in defs:
                        if d.get("fqn") == callee_fqn:
                            score[d["file"]].add("a")
            elif caller in b_fqns:
                for name, defs in def_index.items():
                    for d in defs:
                        if d.get("fqn") == callee_fqn:
                            score[d["file"]].add("b")

    return sorted(f for f, domains in score.items() if "a" in domains and "b" in domains)


def extract_fqn(def_obj: dict) -> str:
    return def_obj.get("fqn", "")


def main() -> int:
    args = parse_args()
    cg = load_call_graph(args.call_graph)

    def_index: dict[str, list[dict]] = cg.get("definitionIndex", {})
    callers_of: dict[str, list[str]] = cg.get("callersOf", {})

    a_files = files_in_domain(def_index, args.domain_a)
    b_files = files_in_domain(def_index, args.domain_b)
    a_fqns = fqns_in_domain(def_index, args.domain_a)
    b_fqns = fqns_in_domain(def_index, args.domain_b)

    a_calls_b = find_cross_calls(callers_of, b_fqns, a_fqns)
    b_calls_a = find_cross_calls(callers_of, a_fqns, b_fqns)

    bidirectional = [
        pair
        for pair in a_calls_b
        if any(p["caller"] == pair["callee"] and p["callee"] == pair["caller"] for p in b_calls_a)
    ]

    cycles = find_cycles(a_calls_b, b_calls_a)

    # Group coupling points by callee domain file for connector grouping
    coupling_points: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    for cross in a_calls_b + b_calls_a:
        key = (cross["caller"], cross["callee"])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        direction = "a→b" if cross in a_calls_b else "b→a"
        caller_file = ""
        callee_file = ""
        for name, defs in def_index.items():
            for d in defs:
                if d.get("fqn") == cross["caller"]:
                    caller_file = d.get("file", "")
                if d.get("fqn") == cross["callee"]:
                    callee_file = d.get("file", "")

        coupling_points.append(
            {
                "direction": direction,
                "caller": cross["caller"],
                "callee": cross["callee"],
                "caller_file": caller_file,
                "callee_file": callee_file,
            }
        )

    shared_kernel = find_shared_kernel_candidates(def_index, a_fqns, b_fqns, callers_of)

    meece_ok = len(a_calls_b) == 0 and len(b_calls_a) == 0
    meece_soft_ok = len(bidirectional) == 0 and not cycles and len(a_calls_b) <= 7

    report = {
        "timestamp": now_iso(),
        "domain_a": {"pattern": args.domain_a, "files": len(a_files), "fqns": len(a_fqns)},
        "domain_b": {"pattern": args.domain_b, "files": len(b_files), "fqns": len(b_fqns)},
        "a_calls_b": a_calls_b,
        "b_calls_a": b_calls_a,
        "bidirectional_calls": bidirectional,
        "cycles_detected": cycles,
        "coupling_points_auto": coupling_points,
        "shared_kernel_candidates": shared_kernel,
        "mece_verdict": "pure" if meece_ok else "soft" if meece_soft_ok else "weak",
        "mece_notes": (
            "No cross-boundary calls; domains are strictly independent."
            if meece_ok
            else (
                "Acceptable cross-boundary coupling; no cycles or bidirectional calls."
                if meece_soft_ok
                else (
                    "Weak MECE: bidirectional calls or >7 cross-calls detected. "
                    "Review demarcation or prepare connectors."
                )
            )
        ),
    }

    write_json(args.output, report)
    print(
        f"[cross_domain_coupling] {len(a_files)}A/{len(b_files)}B files, "
        f"{len(a_calls_b)} A→B, {len(b_calls_a)} B→A, "
        f"mece={report['mece_verdict']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
