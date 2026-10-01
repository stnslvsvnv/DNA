# DNA

**Stop syncing people. Start syncing interfaces.**

[![CI](https://github.com/stnslvsvnv/DNA/actions/workflows/ci.yml/badge.svg)](https://github.com/stnslvsvnv/DNA/actions/workflows/ci.yml)
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

This repository ships the method in three forms:

- **the kit** — manifest, four method documents, mechanical gate scripts, schemas;
- **an agent skill** (`skills/dna/`) — the same kit packaged for agent runtimes
  (`omp skill`, `npx skills add`, `.agents/skills`);
- **a bootstrap procedure** (`dna-bootstrap.md`) — one-time repository setup:
  project profile, branch protection, optional companion tooling.

---

## Quick Start

### 1. Get the kit

As an agent skill (recommended):

```bash
omp skill install @stnslvsvnv/dna        # OMP registry (skills.omp.sh)
# or, cross-agent:
npx skills add stnslvsvnv/DNA@dna -g -y
```

Or clone and use the scripts directly:

```bash
git clone https://github.com/stnslvsvnv/DNA.git
```

### 2. Bootstrap the host repository

Full procedure: `dna-bootstrap.md`. Short version:

```bash
mkdir -p .dna
cp project.example.yaml .dna/project.yaml     # tracker, members, lanes
python <kit>/scripts/dna/validate_project.py
python <kit>/scripts/dna/protect_branch.py --branch main
```

### 3. Run the first feature

Trigger `dna-disco`, then `dna-split`, then `dna-cycle` per spiral, then
`dna-close` per integration node. See `methods/` for the exact steps.

---

## Team and Lane Setup

`.dna/project.yaml` is the initial setup of a DNA deployment. It answers the
two questions every parallel run depends on: **where** lanes hang and **who**
owns and executes each one.

```yaml
version: 1
tracker:
  kind: linear
  team: CIT                 # Linear team key hosting DNA issues
members:                    # every human or agent that can own a lane
  alice: {name: Alice, linear: alice@example.com}
  bob:   {name: Bob,   linear: bob@example.com}
lanes:                      # the parallel lanes (spirals)
  spiral_a: {leader: alice, executor: human}
  spiral_b: {leader: bob,   executor: agent:worker-2}
initiator: alice            # drives dna-disco/dna-split, approves REVIEW.md
```

| Field | Consumed by |
|---|---|
| `tracker.team` | Linear hierarchy created by `dna-split` |
| `members.<id>.linear` | sub-issue assignees, closer detection |
| `lanes.spiral_*.leader` | contract `signed_by`, Linear assignee, `dna-cycle` operator |
| `lanes.spiral_*.executor` | free-form (`human` or `agent:<name>`) — the hook for agent-run lanes |
| `initiator` | `dna-disco` / `dna-split` runs |

Schema: `scripts/dna/schemas/project.schema.json`. Validator:
`scripts/dna/validate_project.py`. Feature runs refuse to start without a
valid profile.

---

## Prerequisites

| Requirement | Needed for |
|---|---|
| Git repository with an `origin` remote | branches, Law 9 protection, merges |
| Python 3.10+ | all service scripts |
| `pyyaml` | contract and profile parsing |
| `linear` CLI with workspace access | issue hierarchy, assignment, closer detection (manual fallback exists) |
| `gh` or `glab` (optional) | automated branch protection |
| 3A skill or other graph tooling (optional) | concept graph, architecture index, call graph layers |

The scripts run against the **host repository**: the project root resolves from
`DNA_PROJECT_ROOT`, then the git top-level of the current directory, then the
current directory. The state root is `<host>/.dna/` (`DNA_STATE_ROOT`
overrides). Feature state — contracts, ADRs, checks, reports — is committed
into the feature branch; only caches and `*.tmp` are ignored.

---

## Connecting to Agent Runtimes

- **Skill discovery**: place or install the skill at `.agents/skills/dna/`
  (project) or `~/.agents/skills/dna/` (user). Runtimes that support the
  Agent Skills layout resolve `SKILL.md` from there; OMP exposes it as
  `skill://dna` and `/skill:dna`.
- **Autoload in subagents**: add `autoloadSkills: [dna]` to the agent
  frontmatter.
- **Registry**: maintainers publish with `omp skill publish ./skills/dna`;
  users install `omp skill install @stnslvsvnv/dna`.
- **Other flows**: the four methods are ordinary markdown steps and the gate
  scripts are CI-friendly (exit codes `0` pass, `1` blocking failure,
  `2` environment error). Any orchestrator can call `dna-disco`/`dna-split`
  as a design phase and `dna-close` as a merge gate.

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

The manifest (`DNA.md`) is the constitution: laws, antipatterns, health
metrics, artifact layout. Method documents must not contradict it.

## Optional Companions

DNA works standalone. Optional companion tooling — for example the 3A skill
(concept graph, architecture index, call graph) — is declared in
`.dna/project.yaml` under `intelligence`:

```yaml
intelligence:
  graph_freshness_cmd: "python scripts/check_graph_freshness.py"
  graph_update_cmd: "python scripts/update_graphify_no_viz.py ."
  call_graph_path: "context/index/call_graph.json"
```

DNA presence-checks the declared tooling. Presence makes the corresponding
freshness gate hard; absence never blocks a run.

---

## Scripts

The scripts under `scripts/dna/` are the mechanical gates: applicability,
contract validation, Law 7 checks (file overlap, dependency drift, contract
conformance), retrospective triggers, closer detection, metrics, branch
protection, project validation. See [`scripts/dna/README.md`](scripts/dna/README.md)
for the inventory, conventions, and the smoke test.

```bash
python scripts/dna/validate_project.py
python scripts/dna/protect_branch.py --feature <slug>
python scripts/dna/applicability_gate.py --feature <slug>
python scripts/dna/validate_contract.py --feature <slug> --cycle 1
```

---

## Repository Layout

```text
DNA.md                  # Manifest and laws
dna-bootstrap.md        # One-time repository setup
project.example.yaml    # Template for .dna/project.yaml
methods/                # Four method documents
scripts/dna/            # Mechanical checks and helpers
scripts/dna/schemas/    # JSON Schemas (dossier, contract, project)
scripts/sync_skill.py   # Regenerates the skill mirror
skills/dna/             # Self-contained agent skill (mirror + SKILL.md)
tests/                  # pytest suite
.github/workflows/      # CI
CHANGELOG.md, VERSION   # Kit versioning
```

---

## Contributing

Found a bug or have an idea? [Open an issue](https://github.com/stnslvsvnv/DNA/issues).

For method changes, please discuss in an issue first — the manifest (`DNA.md`)
is frozen at v2. Run `python scripts/sync_skill.py` and `pytest -q` before
proposing a change; CI enforces both.

---

## License

This work is licensed under the [Creative Commons Attribution-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nd/4.0/).

You are free to share and redistribute this material in any medium or format, provided you give appropriate credit and do not distribute modified versions.

---

## Status

This repository is the standalone extraction of the DNA method, packaged as an
agent skill and a bootstrapable kit. Host-specific tools stay abstract or
optional: knowledge graphs, architecture indexes, and call graphs are
integration points supplied by the adopting repository, and the supported
issue tracker is Linear (fork and adapt for other trackers).
