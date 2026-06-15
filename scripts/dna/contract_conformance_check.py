"""DNA Law 7, check 3: contract conformance.

Runs at `dna-close` time. Executes contract tests and integration tests for
the current connector. Determines responsibility when tests fail.

Verdict:
    pass                    - all tests green
    contract_test_fail      - contract test failed; responsible spiral is
                              the one whose implementation does not match
                              its own declared contract
    integration_test_fail   - integration test failed while contract tests
                              passed; contract is incomplete; both spirals
                              enter mini-retrospective

Test discovery:
    Contract tests are listed in `contract/connector-N.yaml` under
    `contract_tests`. Integration tests are listed under `integration_tests`.

    Each test path is relative to PROJECT_ROOT. The script runs them via
    pytest (for Python) or npm test (for JS/TS). If a test path does not
    exist, the check fails immediately.

Usage:
    python scripts/dna/contract_conformance_check.py \\
        --feature my-feature \\
        --cycle 1 \\
        --output .dna/my-feature/cycles/cycle-1/checks/contract_conformance.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from common import (  # type: ignore[import-not-found]
    PROJECT_ROOT,
    CheckResult,
    checks_dir,
    contract_path,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature", required=True)
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def load_contract(feature: str, cycle: int) -> dict:
    path = contract_path(feature, cycle)
    if not path.exists():
        raise FileNotFoundError(f"Contract not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def run_test(test_path: str) -> tuple[bool, str]:
    """Run a single test file. Return (success, stderr_snippet)."""
    abs_path = PROJECT_ROOT / test_path
    if not abs_path.exists():
        return False, f"Test file not found: {test_path}"

    if test_path.endswith(".py"):
        cmd = ["pytest", "-xvs", str(abs_path)]
    elif test_path.endswith((".js", ".ts")):
        cmd = ["npm", "test", "--", str(abs_path)]
    else:
        return False, f"Unknown test type: {test_path}"

    try:
        subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr[:500]
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 60s"


def run_check(feature: str, cycle: int) -> CheckResult:
    contract = load_contract(feature, cycle)
    contract_tests = contract.get("contract_tests") or []
    integration_tests = contract.get("integration_tests") or []

    contract_results = {}
    for test_spec in contract_tests:
        if isinstance(test_spec, dict):
            path = test_spec.get("path")
        else:
            path = test_spec
        if not path:
            continue
        success, err = run_test(path)
        contract_results[path] = {"success": success, "error": err}

    integration_results = {}
    for test_spec in integration_tests:
        if isinstance(test_spec, dict):
            path = test_spec.get("path")
        else:
            path = test_spec
        if not path:
            continue
        success, err = run_test(path)
        integration_results[path] = {"success": success, "error": err}

    contract_pass = all(r["success"] for r in contract_results.values())
    integration_pass = all(r["success"] for r in integration_results.values())

    if contract_pass and integration_pass:
        verdict = "pass"
        responsible = None
    elif not contract_pass:
        verdict = "contract_test_fail"
        # Heuristic: responsible spiral is the producer if producer test fails,
        # consumer if consumer test fails. If both fail, "both".
        producer_fail = any(
            not r["success"] for p, r in contract_results.items() if "producer" in p
        )
        consumer_fail = any(
            not r["success"] for p, r in contract_results.items() if "consumer" in p
        )
        if producer_fail and consumer_fail:
            responsible = "both"
        elif producer_fail:
            responsible = contract.get("spirals", {}).get("producer", "unknown")
        elif consumer_fail:
            responsible = contract.get("spirals", {}).get("consumer", "unknown")
        else:
            responsible = "unknown"
    else:
        verdict = "integration_test_fail"
        responsible = "both"

    return CheckResult(
        check="contract_conformance",
        verdict=verdict,
        feature_slug=feature,
        cycle_number=cycle,
        details={
            "contract_tests": contract_results,
            "integration_tests": integration_results,
            "responsible_spiral": responsible,
        },
    )


def main() -> int:
    args = parse_args()
    result = run_check(feature=args.feature, cycle=args.cycle)

    output = args.output or (checks_dir(args.feature, args.cycle) / "contract_conformance.json")
    write_json(output, result.to_dict())

    print(f"[contract_conformance] verdict={result.verdict} -> {output}")
    return 0 if result.verdict == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
