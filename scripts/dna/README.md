# scripts/dna/

Service scripts for the DNA method family. These scripts are invoked
by the four DNA methods (`dna-disco`, `dna-split`, `dna-cycle`,
`dna-close`) and by CI hooks.

The manifest lives in `DNA.md` at the repo root. The methods live in
`methods/dna-*.md`. This directory contains only mechanical
checks; it is never the source of truth.

## Inventory

| Script                            | Used by      | Purpose                                                      |
|-----------------------------------|--------------|--------------------------------------------------------------|
| `common.py`                       | (library)    | Shared helpers: paths, JSON/YAML I/O, git helpers.            |
| `applicability_gate.py`           | `dna-disco`  | Verifies manifest Section 1 conditions on dossier.json.       |
| `validate_contract.py`            | `dna-cycle`  | Confirms a connector contract is fully signed and well-formed.|
| `file_overlap_check.py`           | `dna-close`  | Law 7 check 1: spiral-A files ∩ spiral-B files == ∅.         |
| `dependency_drift_check.py`       | `dna-close`  | Law 7 check 2: warns on duplicated dependencies.              |
| `contract_conformance_check.py`   | `dna-close`  | Law 7 check 3: runs contract + integration tests.             |
| `retrospective_trigger.py`        | `dna-close`  | Law 8: evaluates retrospective triggers.                      |
| `detect_closer.py`                | `dna-close`  | Identifies the responsible runner (last issue closer).        |
| `metrics.py`                      | `dna-close`  | Emits Section 4 health metrics for the closed cycle.          |
| `cross_domain_coupling.py`        | `dna-disco`, `dna-split` | Analyses architecture index call graph for domain coupling, MECE validation, coupling-point detection. |
| `schemas/dossier.schema.json`     | (data)       | JSON Schema for `dossier.json`.                               |
| `schemas/contract.schema.json`    | (data)       | JSON Schema for `contract/connector-N.yaml`.                  |

## Conventions

- Every check writes a JSON report. The default location follows the
  artifact layout in the manifest.
- Every script supports `--output PATH` to override the default location.
- Exit code semantics:
  - `0` — pass (or warning, for non-blocking checks)
  - `1` — fail (blocking)
  - `2` — environment error (missing prerequisite, malformed input)
- All scripts use the shared `common.py` for paths, time, JSON I/O, and
  git helpers. Do not duplicate these utilities in individual scripts.

## Dependencies

- Python 3.10+ (for `tuple[T, ...]` and `int | None` syntax).
- `pyyaml` for contract YAML parsing.
- `linear` CLI (through the configured issue-tracker policy) for `detect_closer.py`. Falls back to
  manual mode if the CLI is unavailable.

## Smoke Test

After any change to a script in this directory, run:

```bash
python scripts/dna/file_overlap_check.py --help
python scripts/dna/dependency_drift_check.py --help
python scripts/dna/contract_conformance_check.py --help
python scripts/dna/applicability_gate.py --help
python scripts/dna/validate_contract.py --help
python scripts/dna/retrospective_trigger.py --help
python scripts/dna/detect_closer.py --help
python scripts/dna/metrics.py --help
python scripts/dna/cross_domain_coupling.py --help
```

All nine invocations must exit 0 and print usage.
