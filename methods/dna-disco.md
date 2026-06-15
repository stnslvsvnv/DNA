---
description: DNA Discovery method - investigation and applicability gate before dna-split
---

# Method DNA-DISCO: Discovery for DNA

Activation: user explicitly asks for `dna-disco`, `/dna-disco`, `DNA discover`,
`запустить DNA discovery`, or "use DNA on this feature".

`dna-disco` is the first method of the DNA family. It runs once per
feature, before any planning or coding. Its job is to gather enough evidence
to decide whether DNA applies, and to produce a synthesised dossier that
`dna-split` can decompose into spirals and cycles.

This method is bound by the manifest in `DNA.md`. It must not violate
any law of that manifest.

---

## 1. Purpose

`dna-disco` exists to remove ambiguity from the moment a feature is requested.
A feature initiator says: "I want feature X on portal Y." Without `dna-disco`
the team would either improvise the split or argue about it. `dna-disco`
replaces both of those failure modes with a single evidence-backed dossier
and a binary applicability verdict.

It is read-only. It does not modify production code, does not freeze
contracts, does not create branches, and does not create Linear issues for
spirals. It only investigates.

---

## 2. When to Use

Use `dna-disco` when:

- The user has described a non-trivial feature that may decompose into ≥2
  business domains.
- The user has explicitly asked to consider DNA for this feature.
- The team has time to invest in proper Stage 0 before coding.

Do not use `dna-disco` when:

- The task is a single-domain bug fix or trivial change.
- The user already approved a smaller single-executor workflow or direct
  implementation.
- The feature has been previously processed by `dna-disco` and the dossier
  is still fresh (less than one week old, requirements unchanged).

---

## 3. Core Rules

Section ID: `DNA-DISCO-CORE`

1. `dna-disco` is launched only by explicit human request from the feature
   initiator.
2. `dna-disco` is read-only: no source code is modified, no Linear issues
   are created, no branches are pushed.
3. `dna-disco` may reuse host-provided architecture-index, call-graph,
   knowledge-graph, or read-only investigation tools instead of reimplementing
   investigation logic.
4. `dna-disco` produces two synthesis artifacts: `dossier.md` (human) and
   `dossier.json` (machine).
5. `dna-disco` ends with a mandatory human review (`REVIEW.md`) and a
   machine applicability gate. Both must pass before `dna-split` may run.
6. `dna-disco` must not propose final domain borders. It proposes a draft
   decomposition and lists alternatives. Final demarcation belongs to
   `dna-split`.
7. `dna-disco` must not skip ADR creation: at minimum the demarcation draft
   must be backed by `decisions/000-discovery-notes.md`.
8. `dna-disco` must respect the host repository's ticketing, security, and
   automation policies.

---

## 4. Inputs

Required:

- `feature_slug` — short kebab-case identifier (e.g. `autonomous-it-shop`).
- `feature_description` — raw description from the initiator. May be a
  ticket, structured prompt, or chat message.

Optional:

- `existing_linear_issue` — link to a Linear ticket if one already exists.
- `priority_constraints` — deadlines, regulatory constraints, dependencies.

If `feature_description` is below quality threshold (vague, ambiguous, or
too short), `dna-disco` recommends running `/tol` first to produce a
clearer prompt and stops. It does not attempt to investigate from a weak
input.

---

## 5. Workflow

### 5.1 Bootstrap

Create the working directory:

```
.dna/<feature-slug>/
  +-- decisions/
  +-- (other directories created later by dna-split)
```

Initialise an empty `dossier.md` skeleton and an empty `dossier.json`.

### 5.2 Conceptual Orientation (optional knowledge graph)

Before loading files, load concepts when the host repository provides a
knowledge graph. This is the cheapest operation in the funnel: one report and
2-3 graph queries against a pre-built graph.

**Freshness gate (HARD, mandatory when a graph is used):** Before relying on
knowledge-graph output, verify that the graph is fresh with the host
repository's graph freshness command.

- If the knowledge graph is stale, update it before continuing.
- If the knowledge graph is missing, skip this optional step or build the graph
  through the host repository's graph tooling.
- If the check still exits non-zero AND the invocation context does NOT set
  the `--accept-stale-graph` waiver, HALT and report the stale source. Do not
  proceed with stale graph data.
- If the waiver IS set, log `STALE-WAIVED: knowledge_graph` in `dossier.md`
  under section `Freshness Checks` and proceed. The waiver is opt-in per
  invocation and never the default.

1. **Read the graph report:**
   Read the host repository's knowledge-graph report.
   Key sections for DNA:
   - **God Nodes** — most-connected concepts. If a god node touches two
     candidate domains, it is a natural coupling point.
   - **Communities** — Leiden-detected clusters. These often map to
     bounded contexts and are the starting hypothesis for domain boundaries.
   - **Surprising Connections** — cross-file links that are not obvious
     from the code structure. These catch hidden coupling that the call
     graph would miss.

2. **Query for feature-relevant concepts:**
   Use the host graph query/path tooling to ask how feature concepts connect.
   Use these results to understand the conceptual neighbourhood before the
   architecture index maps concepts to files.

3. **Capture into dossier:**
   - Add section `Conceptual Map` to `dossier.md`.
   - List god nodes relevant to the feature.
   - List communities that overlap with the feature's domain.
   - Flag surprising connections that cross candidate boundaries.
   - If no knowledge graph is available, record `knowledge_graph: unavailable`
     in the dossier and continue with the architecture index.

This step narrows the conceptual search space from the entire project to
the relevant conceptual cluster before any file is read.

### 5.3 Codebase Context (architecture index)

Run the host repository's architecture-index query in the context of the
feature description. When a knowledge graph was available, use its concept names
as query input instead of raw natural language.

The architecture index produces:

- Index freshness check.
- ARCHITECTURE_SNAPSHOT excerpt for relevant areas.
- Bounded-context candidates that may be touched by the feature.

Capture architecture-index output into `dossier.md` under section `Codebase Context`.

If the architecture index is stale, refresh it before proceeding.

### 5.4 Parallel Investigation (read-only lanes)

Launch four read-only investigation lanes. Each lane writes its result into
`.dna/tmp/investigation/<run_id>/<lane>/result.md`.

Mandatory lanes:

| Lane | Focus                                         |
|------|-----------------------------------------------|
| A    | Business invariants and use-cases of the feature |
| B    | Existing modules and their current borders   |
| C    | External dependencies and integrations        |
| D    | Risks, NFRs, security, performance constraints |

Optional lanes (added when the feature requires them):

| Lane | Focus                                         |
|------|-----------------------------------------------|
| E    | Data model and migrations                     |
| F    | UX flows and user-facing surfaces             |
| G    | Compliance, regulatory, contractual constraints |

Each lane is independent. Lanes do not communicate during execution.
Lanes are read-only and may not modify the repository.

### 5.5 Call Graph Validation

After read-only lanes produce candidate domains, use a call graph to
mechanically validate the proposed boundaries before synthesis.

**Freshness gate (HARD, mandatory when a call graph is used):** Before running
call graph validation, verify that the call graph is fresh.

- If the call graph is stale, rebuild it before continuing.
- If `Call graph` is **missing**: build the index before continuing.
- If the check still exits non-zero AND the agent invocation context does
  NOT set the `--accept-stale-graph` waiver, HALT and report the stale
  source. Domain boundary validation against a stale call graph is
  unreliable and is forbidden by default.
- If the waiver IS set, log `STALE-WAIVED: call_graph` in `dossier.md`
  under section `Freshness Checks` and proceed. The waiver is opt-in per
  invocation and never the default.

Call graph validation answers four questions without reading source code:

1. **MECE validation.** Are the candidate domains truly independent?
   ```bash
   python scripts/dna/cross_domain_coupling.py \
     --domain-a "<candidate-domain-a-glob>" \
     --domain-b "<candidate-domain-b-glob>" \
     --output .dna/<feature-slug>/cross-domain-coupling.json
   ```
   If `mece_verdict` is `pure`, the domains have zero cross-calls and the
   split is mechanically confirmed. If `weak`, reconsider the demarcation.

2. **Coupling point auto-detection.** The `coupling_points_auto` list in the
   report is the raw input for defining connector contracts in `dna-split`.
   Every cross-boundary call is a candidate coupling point.

3. **Cycle detection.** `cycles_detected: true` means domains are mutually
   dependent (Antipattern 3: Synchronous deadlock). Rerun architecture-index with
   narrower scope and reconsider boundaries.

4. **Shared Kernel candidates.** The `shared_kernel_candidates` list shows
   files called from both domains. These are candidates for the Shared
   Kernel strategy decision (Law 6).

Capture the call graph validation results into `dossier.md` under section
`Call Graph Validation`. Include the `mece_verdict`, cycle status, and the
raw `cross-domain-coupling.json` path.

If no call graph exists, the freshness gate above HALTs unless
`--accept-stale-graph` waiver is set. With waiver, the human gate
(Section 5.8) will decide whether to proceed.

### 5.6 Aggregation

After all lanes finish and call graph validation is captured, the
orchestrator (the agent that activated `dna-disco`) reads every `result.md`
and synthesises them into:

- `dossier.md` — human-readable narrative.
- `dossier.json` — structured data following `dossier-schema.json` (see
  Section 7).

The orchestrator does not delegate aggregation to a worker. Synthesis is
the core deliverable of `dna-disco` and must remain with the orchestrator.

### 5.7 Draft Decomposition

The orchestrator produces a **draft** decomposition based on the dossier:

- Candidate domain split (≥2 spirals).
- Candidate coupling points between domains.
- Candidate number of cycles N (estimate, not final).
- Candidate Shared Kernel components.

These are recorded as `decisions/000-discovery-notes.md` (an ADR draft, not
yet signed). The draft must include at least two alternative splits when
they exist; if only one viable split exists, that fact is stated explicitly.

### 5.8 Human Gate

Create `REVIEW.md` with the following structure:

```markdown
# DNA Discovery Review — <feature-slug>

Date: ...
Initiator: ...

## Verdicts

- Domain demarcation acceptable?     [ ] yes [ ] no
- Cycle count estimate acceptable?   [ ] yes [ ] no
- Shared-kernel borders acceptable?  [ ] yes [ ] no
- Coupling points complete?          [ ] yes [ ] no

## Comments

(initiator writes here)

## Decision

[ ] Proceed to applicability gate
[ ] Re-run dna-disco with refined inputs
[ ] Abandon DNA for this feature
```

`dna-disco` halts here until the initiator fills `REVIEW.md` and signals
completion. The orchestrator must not advance past this point on its own.

### 5.9 Applicability Gate

Once all human checks are `yes`, the orchestrator runs the machine gate
(`scripts/dna/applicability_gate.py`). The gate verifies:

1. Team size declared, between 2 and 6.
2. Dossier identifies at least two weakly coupled domains.
3. Each candidate domain has a designated potential owner.
4. CI presence is confirmed (presence of `.github/workflows/`,
   `Makefile`, or equivalent).
5. The dossier shows that requirements are stable for at least one cycle.

The gate output is binary: `pass` or `fail`. On `fail` the gate writes a
list of failed conditions into `REVIEW.md` under `Gate Results` and
`dna-disco` exits.

On `pass` the orchestrator marks `dna-disco` complete and instructs the
initiator that `dna-split` may now run.

---

## 6. Outputs

Produced files (under `.dna/<feature-slug>/`):

| File                                  | Owner            | Purpose                          |
|---------------------------------------|------------------|----------------------------------|
| `dossier.md`                          | orchestrator     | Human narrative of investigation |
| `dossier.json`                        | orchestrator     | Machine view of investigation    |
| `REVIEW.md`                           | initiator        | Human gate verdict               |
| `decisions/000-discovery-notes.md`    | orchestrator     | ADR draft of demarcation options |
| `applicability-gate-report.json`      | gate script      | Machine gate verdict             |

---

## 7. dossier.json Schema (Summary)

A canonical machine view used by `dna-split`:

```json
{
  "feature_slug": "autonomous-it-shop",
  "created_at": "ISO-8601",
  "team": {
    "size": 2,
    "members": ["alice", "bob"]
  },
  "domains_candidates": [
    {
      "id": "catalog",
      "summary": "...",
      "use_cases": ["..."],
      "potential_owner": "alice"
    },
    {
      "id": "logistics",
      "summary": "...",
      "use_cases": ["..."],
      "potential_owner": "bob"
    }
  ],
  "coupling_points_candidates": [
    {
      "id": "cp-1",
      "from": "catalog",
      "to": "logistics",
      "kind": "rest|event|shared-data",
      "description": "..."
    }
  ],
  "shared_kernel_candidates": [
    {
      "id": "auth",
      "strategy_proposal": "delegated|co-developed|external"
    }
  ],
  "estimated_cycles": 3,
  "risks": ["..."],
  "nfrs": ["..."],
  "lane_results": [
    {"lane": "A", "path": ".dna/tmp/investigation/<run_id>/A/result.md"}
  ]
}
```

The full JSON Schema lives in `scripts/dna/schemas/dossier.schema.json`
once Step 3 of the implementation plan is delivered.

---

## 8. Failure Modes

- **Stale architecture index.** Refresh before continuing; do not investigate
  against a stale snapshot.
- **Read-only lane stalls.** Apply read-only lane stall handling (kill, retry,
  re-decompose). Do not block `dna-disco` indefinitely.
- **Dossier reveals only one viable domain.** Stop. Recommend a smaller
  single-executor workflow or direct implementation. DNA does not apply.
- **Initiator rejects the human gate.** Treat as normal: re-run `dna-disco`
  with refined inputs. Do not silently advance.
- **Applicability gate fails.** Stop. Do not run `dna-split`. Recommend
  fallback methods.

If any unexpected blocker appears, stop, state options, and wait for direction.

---

## 9. What dna-disco Is Not

- It is not `dna-split`. It does not freeze contracts, create branches, or
  open Linear issues for spirals.
- It is not a read-only investigation runner. It is the orchestrator that uses read-only lanes as a tool.
- It is not an architecture index. It loads architecture-index output to gather codebase context, but that is
  one of many inputs.
- It is not implementation. No source code is modified.

---

## 10. Approval Gate

`dna-disco` is complete only when:

- `dossier.md` and `dossier.json` exist and are non-empty.
- `REVIEW.md` is filled and all human checks are `yes`.
- `applicability-gate-report.json` exists with verdict `pass`.
- `decisions/000-discovery-notes.md` exists.

If any of those is missing, `dna-disco` is incomplete regardless of how
much investigation was performed.

End of method.
