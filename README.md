# DNA

DNA is a contract-first method for parallel engineering in small teams.

Most software methods try to synchronize people. DNA synchronizes interfaces.
It is designed for 2-6 engineers working on a feature that can be split into
at least two weakly coupled business domains. The team stops planning tasks as
the primary unit of coordination and starts planning the connectors where those
tasks must meet.

## Core Idea

```text
domains -> contracts -> isolated cycles -> machine integration gates
```

DNA keeps implementation work isolated inside domain-owned spirals. Spirals meet
only at explicit integration nodes, and a node closes only when contract tests,
integration tests, and ownership checks pass.

## Lifecycle

1. `dna-disco` gathers evidence and decides whether DNA applies.
2. `dna-split` freezes domains, connectors, contracts, branches, and issue shape.
3. `dna-cycle` lets each spiral scaffold its local cycle from the frozen contract.
4. `dna-close` runs the integration gate, merges cycle branches, and triggers a
   retrospective only when machine checks say one is needed.

## When To Use DNA

Use DNA when all conditions hold:

- team size is 2-6 people;
- the feature splits into at least two weakly coupled business domains;
- participants can design and honor API or event contracts independently;
- CI can run contract tests and integration tests;
- requirements are stable enough for one cycle.

Do not use DNA for a single-domain bug fix or a small sequential task. In that
case it adds ceremony without adding safety.

## Repository Layout

```text
DNA.md                  # Manifest and laws
methods/                # Four method documents
scripts/dna/            # Mechanical checks and helpers
scripts/dna/schemas/    # JSON Schemas for method artifacts
```

Runtime feature state defaults to `.dna/<feature-slug>/`. Override it with:

```bash
export DNA_STATE_ROOT=/path/to/dna-state
```

## Scripts

The scripts under `scripts/dna/` are mechanical gates for the method:

- `applicability_gate.py` checks whether DNA fits a feature.
- `cross_domain_coupling.py` detects cross-domain calls from a call graph.
- `validate_contract.py` validates connector contracts and records amendments.
- `file_overlap_check.py` detects ownership violations before merge.
- `dependency_drift_check.py` warns on duplicated dependencies.
- `contract_conformance_check.py` runs contract and integration checks.
- `retrospective_trigger.py` decides whether a retrospective is required.
- `detect_closer.py` identifies who should run `dna-close`.
- `metrics.py` emits cycle health metrics.

## Status

This repository is the standalone extraction of the DNA method. It intentionally
keeps host-specific tools abstract: knowledge graphs, architecture indexes,
call graphs, issue trackers, and CI systems are integration points supplied by
the adopting repository.
