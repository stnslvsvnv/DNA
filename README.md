# DNA

**Stop syncing people. Start syncing interfaces.**

[![License: CC BY-ND 4.0](https://img.shields.io/badge/License-CC%20BY--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nd/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

DNA is a contract-first method for parallel engineering in small teams.

Most software methods try to synchronize people. DNA synchronizes interfaces.
It is designed for 2-6 engineers working on a feature that can be split into
at least two weakly coupled business domains. The team stops planning tasks as
the primary unit of coordination and starts planning the connectors where those
tasks must meet.

---

## The DNA Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  dna-disco  │────▶│  dna-split  │────▶│  dna-cycle  │────▶│  dna-close  │
│             │     │             │     │             │     │             │
│  Investigate│     │   Freeze    │     │   Execute   │     │  Integrate  │
│  & decide   │     │  contracts  │     │  in spiral  │     │  & merge    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                    │                    │                    │
       ▼                    ▼                    ▼                    ▼
   Dossier             Frozen plan         Cycle branch        Merged code
   + verdict           + contracts         + issues            + retrospective
```

DNA keeps implementation work isolated inside domain-owned spirals. Spirals meet
only at explicit integration nodes, and a node closes only when contract tests,
integration tests, and ownership checks pass.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/stnslvsvnv/DNA.git
cd DNA

# Check if DNA applies to your feature
python scripts/dna/applicability_gate.py --feature "your-feature-name"

# Validate a contract
python scripts/dna/validate_contract.py --contract path/to/contract.json
```

Runtime feature state defaults to `.dna/<feature-slug>/`. Override it with:

```bash
export DNA_STATE_ROOT=/path/to/dna-state
```

---

## When To Use DNA

| Use DNA when... | Don't use DNA when... |
|-----------------|----------------------|
| Team size is 2-6 people | Working solo or team > 6 |
| Feature splits into 2+ weakly coupled domains | Single-domain bug fix or small task |
| Team can design APIs/contracts independently | No API design experience |
| CI can run contract + integration tests | No CI infrastructure |
| Requirements stable for one cycle (5-10 days) | Requirements change daily |

In cases where DNA doesn't apply, it adds ceremony without adding safety.

---

## Methods

DNA consists of four sequential methods:

| Method | Purpose | When it runs |
|--------|---------|--------------|
| [**dna-disco**](methods/dna-disco.md) | Gather evidence, decide if DNA applies | Once per feature, before any planning |
| [**dna-split**](methods/dna-split.md) | Freeze domains, contracts, branches, issues | Once per feature, after disco passes |
| [**dna-cycle**](methods/dna-cycle.md) | Scaffold local cycle from frozen contract | N times per spiral (once per cycle) |
| [**dna-close**](methods/dna-close.md) | Run integration gate, merge, trigger retro | N times per feature (once per node) |

---

## Repository Layout

```text
DNA.md                  # Manifest and laws
methods/                # Four method documents
  dna-disco.md          # Discovery and applicability
  dna-split.md          # Demarcation and contract freeze
  dna-cycle.md          # Local cycle execution
  dna-close.md          # Integration gate and merge
scripts/dna/            # Mechanical checks and helpers
scripts/dna/schemas/    # JSON Schemas for method artifacts
```

---

## Scripts

The scripts under `scripts/dna/` are mechanical gates for the method:

| Script | Purpose |
|--------|---------|
| `applicability_gate.py` | Checks whether DNA fits a feature |
| `cross_domain_coupling.py` | Detects cross-domain calls from a call graph |
| `validate_contract.py` | Validates connector contracts and records amendments |
| `file_overlap_check.py` | Detects ownership violations before merge |
| `dependency_drift_check.py` | Warns on duplicated dependencies |
| `contract_conformance_check.py` | Runs contract and integration checks |
| `retrospective_trigger.py` | Decides whether a retrospective is required |
| `detect_closer.py` | Identifies who should run `dna-close` |
| `metrics.py` | Emits cycle health metrics |

---

## Contributing

Found a bug or have an idea? [Open an issue](https://github.com/stnslvsvnv/DNA/issues).

For method changes, please discuss in an issue first — the manifest (`DNA.md`) is frozen at v2.

---

## License

This work is licensed under the [Creative Commons Attribution-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nd/4.0/).

You are free to share and redistribute this material in any medium or format, provided you give appropriate credit and do not distribute modified versions.

---

## Status

This repository is the standalone extraction of the DNA method. It intentionally
keeps host-specific tools abstract: knowledge graphs, architecture indexes,
call graphs, issue trackers, and CI systems are integration points supplied by
the adopting repository.
