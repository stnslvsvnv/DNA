---
description: DNA Split method - finalize demarcation, freeze contracts, create N-cycle plan and Linear/branch scaffolding
---

# Method DNA-SPLIT: Demarcation and Contract Freeze

Activation: user explicitly asks for `dna-split`, `/dna-split`,
`DNA split`, or `freeze DNA contracts`.

`dna-split` is the second method of the DNA family. It runs once per
feature, after `dna-disco` has produced a passed applicability gate. Its job
is to convert the dossier into a frozen, signed plan that two spirals can
execute in isolation.

This method is bound by the manifest in `DNA.md`. It must not violate
any law of that manifest.

---

## 1. Purpose

`dna-split` converts a discovery dossier into an executable plan. The plan
consists of:

- A final domain demarcation with named owners (Law 1).
- A frozen contract per coupling point (Law 2).
- An ordered list of N cycles, each with one connector (Law 4).
- A chosen Shared Kernel strategy (Law 6).
- A protected feature branch and per-cycle scaffolding (Law 9).
- A Linear master issue with two spiral sub-issues and N Integration Issue
  placeholders.

After `dna-split` finishes, spirals are free to diverge and run
`dna-cycle` independently.

---

## 2. Prerequisites

`dna-split` may run only when all of the following are true:

- `dna-disco` has been completed for this `feature_slug`.
- `dossier.md`, `dossier.json`, and `REVIEW.md` exist with all human
  checks marked `yes`.
- `applicability-gate-report.json` has verdict `pass`.
- The initiator has explicitly requested `dna-split`.

If any prerequisite is missing, `dna-split` halts and asks the user how
to proceed.

---

## 3. Core Rules

Section ID: `DNA-SPLIT-CORE`

1. `dna-split` is run by the feature initiator only.
2. `dna-split` finalises decisions; it does not reopen the discovery.
   New investigation, if needed, is performed by re-running `dna-disco`.
3. `dna-split` must produce signed ADRs for: domain split, coupling
   points (and thus N cycles), Shared Kernel strategy.
4. `dna-split` freezes contracts per connector. Each frozen connector is
   stored as a versioned file in `contract/`.
5. `dna-split` creates the protected feature branch and the Linear
   structure in a single atomic operation. If any step fails, all
   side-effects must be rolled back.
6. `dna-split` must not start `dna-cycle` automatically. Cycle launch is
   the spiral leader's responsibility.
7. `dna-split` uses the configured issue-tracker CLI and never reads or
   depends on private wrapper internals.

---

## 4. Inputs

- `feature_slug` — must match the slug used in `dna-disco`.
- All artifacts produced by `dna-disco` under
  `.dna/<feature_slug>/`.

---

## 5. Workflow

### 5.1 Final Demarcation

The initiator reviews the candidate domains in `dossier.json` and selects
the final split. The result is written to `DOMAINS.md`:

```markdown
# Domains — <feature-slug>

## Spiral A: <domain-name-1>

Owner: <name>
Linear sub-issue: <id>

What is inside this sovereignty:
- ...

What is explicitly outside:
- ...

Connectors to Spiral B:
- Cycle 1: <connector-id>
- Cycle 2: <connector-id>
- ...

Recommended internal lanes (non-binding):
- ...

## Spiral B: <domain-name-2>

(symmetrical)

## Shared Kernel

Strategy: <co-developed | delegated | external>
Owner during cycles: <name>
Components:
- ...
```

The "What is explicitly outside" section is mandatory. Without explicit
exclusions, contraband business logic (Antipattern 1) becomes likely.

### 5.1.1 Write `shared-kernel.txt`

After `DOMAINS.md` is finalised, extract every file path listed under
`## Shared Kernel / Components` (one path per line, relative to repo root,
no globs) and write them to:

```
.dna/<feature-slug>/shared-kernel.txt
```

This file is the authoritative allowlist consumed by
`scripts/dna/file_overlap_check.py` at `dna-close` (Law 7, check 1). Without
it the overlap check sees every Shared Kernel file as a violation.

If no Shared Kernel components exist, write an empty file. Presence of the
file is mandatory; emptiness is allowed.

### 5.2 ADR Production

Three ADRs must be created, signed by the initiator and noted by both
spiral leaders:

| ID  | Title                  | Purpose                                          |
|-----|------------------------|--------------------------------------------------|
| 001 | Domain split           | Why the borders are where they are.              |
| 002 | Coupling points and N  | Why N cycles, why this grouping of connectors.   |
| 003 | Shared Kernel strategy | Why this strategy, and what alternatives lost.   |

ADRs follow the manifest's mandatory structure:

```
Context
Considered Alternatives (>=2)
Decision
Rationale
Consequences
Reversibility
```

### 5.3 Contract Freeze

For each coupling point a contract artifact is produced under
`contract/connector-N.yaml`:

```yaml
connector_id: cp-1
cycle: 1
kind: rest        # rest | event | shared-data | rpc
version: 1.0.0
spirals:
  producer: A
  consumer: B
schema:
  # OpenAPI fragment, Protobuf reference, or event schema
  ...
contract_tests:
  - path: tests/contracts/cp-1/producer_test.yaml
  - path: tests/contracts/cp-1/consumer_test.yaml
mock:
  producer_mock: stubs/cp-1/producer.json
  consumer_mock: stubs/cp-1/consumer.json
signed_by:
  spiral_a_leader: <name>
  spiral_b_leader: <name>
signed_at: ISO-8601
```

A connector is frozen only when both `signed_by` fields are filled. Until
then `dna-cycle` may not start for that cycle.

### 5.4 Knowledge-Graph Community Verification

After contracts are frozen but before the call-graph check, compare the
proposed domain boundaries against the conceptual graph. This is the
cheapest validation — one file read, no computation.

**Freshness gate (HARD, mandatory when a graph is used):** Before relying on a
knowledge graph, verify that it is fresh with the host repository's graph
freshness command.

- If the knowledge graph is stale, update it before continuing.
- If the knowledge graph is missing, skip this advisory step or build it through
  host tooling.
- If the check still exits non-zero AND the invocation context does NOT set
  the `--accept-stale-graph` waiver, HALT and report. Conceptual boundary
  validation against stale graph data is forbidden by default.
- If the waiver IS set, log `STALE-WAIVED: knowledge_graph` in the
  verification ADR and proceed. The waiver is opt-in per invocation.

1. **Read the current graph report** when one exists.

2. **Compare communities to domains:**
   - For each domain in `DOMAINS.md`, find the Leiden community (or
     communities) that overlap with it.
   - If a domain maps cleanly to one community → the boundary is
     conceptually sound.
   - If a domain spans multiple communities → the boundary may be cutting
     across a natural cluster. This is not a blocker, but it is a risk
     that should be noted in the ADR.
   - If a community spans both domains → there is conceptual coupling that
     the contract must handle explicitly.

3. **Flag surprises:**
   - Any "surprising connection" in the report that crosses the proposed
     domain boundary is a candidate coupling point that the frozen
     contracts must cover. If not covered, note the gap.

4. **Record the verdict:**
   - Add section `Knowledge-Graph Community Verification` to
     `decisions/004-call-graph-verification.md` (or create a new
     `decisions/005-knowledge-graph-verification.md` if the file already exists).
   - The verdict is advisory, not a gate. Even if the knowledge graph disagrees
     with the human grouping, `dna-split` may proceed. The disagreement is a
     documented risk, not a stop condition.

If no knowledge graph exists, record `knowledge_graph: unavailable` and continue
to call graph verification.

### 5.5 Call Graph Verification

After all connectors are frozen, run call graph validation to mechanically verify that the
contracts cover every real cross-boundary call. This catches gaps between
the human-written contracts and the actual code coupling.

**Freshness gate (HARD, mandatory when a call graph is used):** Before running
call graph validation, verify that the call graph is fresh.

- If the call graph is stale, rebuild it before continuing.
- If `Call graph` is **missing**: build the index before continuing.
- If the check still exits non-zero AND the agent invocation context does
  NOT set the `--accept-stale-graph` waiver, HALT and report. Contract
  coverage verification against a stale call graph is forbidden by default.
- If the waiver IS set, log `STALE-WAIVED: call_graph` in the verification
  ADR and proceed. The waiver is opt-in per invocation.

```bash
python scripts/dna/cross_domain_coupling.py \
  --domain-a "<spiral-a-domain-glob>" \
  --domain-b "<spiral-b-domain-glob>" \
  --output .dna/<feature-slug>/cross-domain-coupling-verified.json
```

Three checks:

1. **Coverage gap detection.**
   Compare the `coupling_points_auto` list against the frozen connectors.
   Every auto-detected coupling point must map to at least one connector.
   Unmapped points mean the contract is incomplete.

2. **Overlap prediction.**
   The `coupling_points_auto` list shows which files call which. Use this
   to predict potential file overlap before `dna-cycle` starts:
   ```bash
   python scripts/dna/cross_domain_coupling.py \
     --domain-a "..." --domain-b "..." \
     --output ... \
     | python -c "
   import json, sys
   r = json.load(open(sys.argv[1]))
   for cp in r['coupling_points_auto']:
       print(f\"OVERLAP RISK: {cp['caller_file']} vs {cp['callee_file']}\")
   "
   ```
   This is an early warning, not a blocker. The real check runs at `dna-close`.

3. **Shared Kernel verification.**
   If `dna-disco` proposed Shared Kernel candidates, verify with the
   call graph: files in `shared_kernel_candidates` that are called from
   both domains should be included in the Shared Kernel declaration.

Capture results in `decisions/004-call-graph-verification.md` (a brief ADR
draft).

If the call graph is stale or missing, the freshness gate above HALTs
unless `--accept-stale-graph` waiver is set.

### 5.6 Branch Topology

Create the feature branch:

```bash
git checkout main
git pull --ff-only
git checkout -b feat/<feature-slug>
git push -u origin feat/<feature-slug>
```

Mark `feat/<feature-slug>` as protected through repository settings or a
branch-protection script (see `scripts/dna/protect_branch.py`).

Cycle branches are not created here. They are created by `dna-cycle`.

### 5.7 Linear Structure

Create the Linear hierarchy via the `linear` CLI:

```
Master Issue: "[DNA] <feature-slug>"
  |-- Sub-issue: "[Spiral A] <feature-slug>" -> assignee = Spiral A leader
  |-- Sub-issue: "[Spiral B] <feature-slug>" -> assignee = Spiral B leader
  |
  |-- Integration Issue: "[DNA Node 1] <feature-slug>"  label: integration-node
  |-- Integration Issue: "[DNA Node 2] <feature-slug>"  label: integration-node
  |-- Integration Issue: "[DNA Node N] <feature-slug>"  label: integration-node
```

Required labels on every issue: `dna:<feature-slug>`.

Integration Issues are placeholders. Their description includes:

- Connector reference (path to `contract/connector-N.yaml`).
- Mandatory honest-flag field for cycle closure (`No`, `Minor`, `Major`).
- Mandatory "Lesson learned" one-liner from each spiral.
- Checkboxes for Law 7 outcomes.

Persist the Linear hierarchy to `linear/issue-map.json`:

```json
{
  "master": "CIT-123",
  "spirals": {"A": "CIT-124", "B": "CIT-125"},
  "integration_nodes": {
    "1": "CIT-126",
    "2": "CIT-127",
    "3": "CIT-128"
  }
}
```

### 5.8 Atomicity

The branch creation, Linear hierarchy creation, ADR signing, and contract
freeze form a single logical operation. If any step fails:

- Delete created Linear issues via `linear` CLI.
- Delete the feature branch (local and remote).
- Mark all created ADRs as `draft-rolled-back`.
- Leave `dossier.md` and `REVIEW.md` intact.
- Report the failure to the initiator and halt.

The orchestrator must not leave the system in a partial state.

### 5.9 Handover

When all steps succeed, emit a final handover message:

```
dna-split complete for <feature-slug>.

Feature branch: feat/<feature-slug>
Linear master: <id>
Spiral A leader: <name>, sub-issue: <id>
Spiral B leader: <name>, sub-issue: <id>
Cycles: N = <number>
Next step: each spiral leader runs /dna-cycle 1 independently.
```

---

## 6. Outputs

Produced files (under `.dna/<feature-slug>/`):

| File                                  | Owner       | Purpose                                |
|---------------------------------------|-------------|----------------------------------------|
| `DOMAINS.md`                          | initiator   | Final demarcation                      |
| `decisions/001-domain-split.md`       | initiator   | Signed ADR                             |
| `decisions/002-coupling-points.md`    | initiator   | Signed ADR with N cycles               |
| `decisions/003-shared-kernel.md`      | initiator   | Signed ADR                             |
| `contract/connector-N.yaml`           | initiator   | Frozen contract per cycle              |
| `shared-kernel.txt`                   | initiator   | File allowlist for Law 7 overlap check |
| `linear/issue-map.json`               | initiator   | Linear hierarchy index                 |

Side-effects:

- Git branch `feat/<feature-slug>` created and protected.
- Linear master + sub-issues + N integration issues created.

---

## 7. Failure Modes

- **Initiator cannot finalise demarcation.** Halt and return to
  `dna-disco` with new questions. Do not freeze a half-thought split.
- **A connector cannot be specified concretely.** Treat as a cycle that
  is not ready; reduce N until only fully specifiable connectors remain.
  The remaining work becomes a future feature.
- **Linear creation fails partially.** Run the rollback procedure in 5.8
  and report.
- **Branch protection cannot be applied.** Halt; protection is a Law 9
  invariant.

If any unexpected blocker appears, stop, state options, and wait for direction.

---

## 8. What dna-split Is Not

- It is not `dna-disco`. It does not investigate; it acts on the dossier.
- It is not `dna-cycle`. It does not create cycle branches or Linear
  decomposition inside a spiral.
- It is not implementation. No production code is modified.
- It is not Linear automation alone. It is an architecture decision.

---

## 9. Approval Gate

`dna-split` is complete only when:

- `DOMAINS.md` exists and lists explicit "inside" and "outside" for both
  spirals.
- All three ADRs (001, 002, 003) are signed.
- All N `contract/connector-*.yaml` files have both `signed_by` fields
  filled.
- `shared-kernel.txt` exists under `.dna/<feature-slug>/`
  (may be empty if no Shared Kernel components).
- Feature branch exists, is protected, and is pushed to origin.
- `linear/issue-map.json` exists and references the master issue, two
  sub-issues, and N integration issues.

If any of those is missing, `dna-split` is incomplete and the next method
(`dna-cycle`) is forbidden to start.

End of method.
