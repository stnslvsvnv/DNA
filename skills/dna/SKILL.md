---
name: dna
description: DNA contract-first method for parallel engineering in small teams (dna-disco, dna-split, dna-cycle, dna-close). Use when asked to run DNA on a feature, to bootstrap DNA in a repository, to split work into parallel lanes/spirals with frozen contracts and integration nodes, or when the user mentions dna-disco, dna-split, dna-cycle, or dna-close.
license: CC BY-ND 4.0
compatibility: Requires git, Python 3.10+, pyyaml, and the Linear CLI. Optional gh/glab (branch protection) and the 3A companion skill.
---

# DNA — contract-first parallel engineering

DNA synchronizes interfaces, not people. A feature is cut into two weakly
coupled domains (spirals), their connectors are frozen as versioned
contracts, and work proceeds in isolation until a machine-validated
integration node merges it. Four methods form the lifecycle:

```
dna-disco -> dna-split -> dna-cycle (xN, both spirals) -> dna-close (xN)
investigate   freeze        isolate & execute               integrate & merge
```

The manifest (`DNA.md`) is the constitution of the method and is frozen at
v2. Read it before acting; method documents must not contradict it.

## What this skill ships

| Path | Purpose |
|---|---|
| `DNA.md` | Manifest: laws, antipatterns, metrics, artifact layout. |
| `methods/dna-*.md` | The four method documents. |
| `scripts/dna/` | Mechanical gates: applicability, contract validation, Law 7 checks, metrics, branch protection, project validation. |
| `scripts/dna/schemas/` | JSON Schemas for dossier, connector contract, project profile. |
| `dna-bootstrap.md` | One-time repository setup before the first feature. |
| `project.example.yaml` | Template for `.dna/project.yaml`. |
| `VERSION` | Kit version. |

## First run in a repository

1. Read `dna-bootstrap.md` and complete it: prerequisites, `.dna/project.yaml`
   (tracker, members, lane leaders), branch protection, optional companions.
2. Validate the profile:

   ```bash
   SKILL_DIR=$(realpath skill://dna)
   python "$SKILL_DIR/scripts/dna/validate_project.py"
   ```

3. Start the first feature with the `dna-disco` method.

The scripts run against the **host repository**: the project root resolves
from `DNA_PROJECT_ROOT`, then the git top-level of the current directory,
then the current directory. The state root is `<host>/.dna/` (override:
`DNA_STATE_ROOT`). Feature state (contracts, ADRs, checks, reports) is
committed into the feature branch.

## Running the methods

Trigger the methods by name: `dna-disco`, `dna-split`, `dna-cycle`,
`dna-close`, `use DNA on this feature`, `DNA discovery`. Each method reads
the previous method's artifacts under `.dna/<feature-slug>/`.

Useful script invocations (run from the host repository):

```bash
python "$SKILL_DIR/scripts/dna/validate_project.py"
python "$SKILL_DIR/scripts/dna/protect_branch.py" --feature <slug>
python "$SKILL_DIR/scripts/dna/applicability_gate.py" --feature <slug>
python "$SKILL_DIR/scripts/dna/validate_contract.py" --feature <slug> --cycle 1
python "$SKILL_DIR/scripts/dna/file_overlap_check.py" --feature <slug> --cycle 1 --branch-a <a> --branch-b <b>
python "$SKILL_DIR/scripts/dna/detect_closer.py" --feature <slug> --cycle 1
python "$SKILL_DIR/scripts/dna/metrics.py" --feature <slug> --cycle 1
```

Exit codes: `0` pass/warning, `1` blocking failure, `2` environment error.

## Tracker

Linear is the supported issue tracker (the initial setup question "where do
the lanes hang" is answered in `.dna/project.yaml`: Linear team key, member
usernames, lane leaders). `detect_closer.py` uses the `linear` CLI and
degrades to a documented deterministic fallback when Linear data is
unavailable.

## Optional companions

DNA works standalone. Companion tooling (for example the 3A skill:
concept graph, architecture index, call graph) is *presence-checked* and
declared in `.dna/project.yaml` under `intelligence`. Presence makes the
corresponding freshness gate hard; absence never blocks a run.

## Using DNA from other flows

- Reference this skill directly (`skill://dna`) or via `/skill:dna`.
- Subagents can autoload it (`autoloadSkills: [dna]`).
- The scripts are CI-friendly: `validate_project.py`, `protect_branch.py`,
  and the Law 7 checks run standalone with JSON reports.
- Method phases are ordinary markdown steps: an orchestrator can call
  `dna-disco`/`dna-split` as a design phase and `dna-close` as a merge gate.
