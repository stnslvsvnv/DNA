---
description: DNA Cycle method - local cycle launch by spiral leader, per-spiral decomposition and execution
---

# Method DNA-CYCLE: Local Cycle Launch

Activation: spiral leader explicitly asks for `dna-cycle`, `/dna-cycle`,
`DNA cycle N`, `start cycle N for spiral A`, or `launch my cycle`.

`dna-cycle` is the third method of the DNA family. It runs N times per
spiral (once per cycle). It is the spiral's local method for decomposing the
connector task assigned to it for the current cycle into Linear issues,
creating the cycle branch, and launching isolated work.

This method is bound by the manifest in `DNA.md`. It must not violate
any law of that manifest.

---

## 1. Purpose

`dna-cycle` converts a frozen connector contract into an executable work plan
for one spiral. The plan consists of:

- A cycle-specific branch (Law 9).
- A set of Linear issues owned by the spiral, labelled with the cycle.
- Optional internal investigation via host architecture-index, call-graph, or
  read-only investigation tooling scoped to the spiral's domain.
- A clear stop condition: all Linear issues for this cycle are closed.

After `dna-cycle` finishes, the spiral works in isolation until the cycle
closes. The spiral does not coordinate with the other spiral during the
cycle except through the frozen contract.

---

## 2. Prerequisites

`dna-cycle` may run only when all of the following are true:

- `dna-split` has been completed for this `feature_slug`.
- The spiral leader has been assigned the spiral's sub-issue in Linear.
- The contract for the current cycle N is frozen (both `signed_by` fields
  in `contract/connector-N.yaml` are filled).
- The spiral leader has explicitly requested `dna-cycle N`.

If any prerequisite is missing, `dna-cycle` halts and asks the spiral
leader how to proceed.

---

## 3. Core Rules

Section ID: `DNA-CYCLE-CORE`

1. `dna-cycle` is run by the spiral leader only, not by the initiator or
   the other spiral.
2. `dna-cycle` is local to one spiral. It does not create issues, branches,
   or artifacts for the other spiral.
3. `dna-cycle` must load the frozen contract for cycle N before any
   planning. The contract is the source of truth for what must be delivered.
4. `dna-cycle` may run an architecture-index query in the context of the spiral's domain to
   gather codebase context. This is optional and decided by the spiral
   leader.
5. `dna-cycle` may run read-only investigation lanes for internal reconnaissance inside the
   spiral's domain. This is optional and decided by the spiral leader.
6. `dna-cycle` must create a cycle branch from `feat/<feature-slug>` and
   push it to origin.
7. `dna-cycle` must create Linear issues under the spiral's sub-issue,
   labelled with `dna:<feature-slug>`, `spiral:<a|b>`, `cycle:<N>`.
8. `dna-cycle` must not close the spiral's sub-issue. That happens only
   after all N cycles are complete.
9. `dna-cycle` uses the configured issue-tracker CLI and never reads or
   depends on private wrapper internals.
10. `dna-cycle` must not start implementation. It only plans and scaffolds.
    Implementation is the spiral's responsibility after `dna-cycle` exits.

---

## 4. Inputs

Required:

- `feature_slug` — must match the slug used in `dna-disco` and `dna-split`.
- `spiral_id` — `a` or `b`.
- `cycle_number` — integer, 1 to N.

Optional:

- `investigation_mode` — `none`, `index-only`, `index+callgraph` (default, recommended), `full-readonly`.
  Default: `index+callgraph`.

  **Guard on `none`.** `investigation_mode=none` is permitted ONLY when
  `.dna/<feature-slug>/cross-domain-coupling.json` exists AND
  its `mece_verdict` equals `"pure"`. Any other verdict (`soft`, `weak`)
  or a missing file forces minimum `index+callgraph`. The agent MUST read the file
  before honoring `none`. If `none` is requested but the guard fails, the
  mode is silently downgraded to `index+callgraph` and the downgrade reason is
  logged in `cycles/cycle-<N>/spiral-<spiral-id>/investigation.md` under
  section `Mode Downgrade`.

---

## 5. Workflow

### 5.1 Load Contract

Read the frozen connector contract for the current cycle:

```
.dna/<feature-slug>/contract/connector-<N>.yaml
```

Verify both `signed_by.spiral_a_leader` and `signed_by.spiral_b_leader`
fields are filled. If either is empty, HALT (Law 2 forbids work on an
unsigned contract).

Recommended verification:

```bash
python scripts/dna/validate_contract.py --feature <feature-slug> --cycle <N>
```

Extract the following inputs for later steps:

- `connector_id` and `kind` (rest | event | shared-data | rpc)
- `spirals.producer` / `spirals.consumer` (own role for this cycle)
- `schema` (the frozen interface fragment)
- `contract_tests` (paths the cycle must satisfy)
- `mock.producer_mock` / `mock.consumer_mock` (stub paths for 5.6)
- `version` (used by the mid-cycle amendment protocol in 5.8)

### 5.2 Bootstrap Working Directory

Ensure the cycle directory exists:

```
.dna/<feature-slug>/cycles/cycle-<N>/spiral-<spiral-id>/
```

Initialise empty skeletons for:

- `investigation.md` — populated in 5.3 (or left empty if `investigation_mode=none`)
- `issues.json` — populated in 5.4

Do not create `result.md` at bootstrap. It is written by the spiral during
or after the cycle work, not at scaffold time.

### 5.3 Optional Investigation

If `investigation_mode` is `index-only`, `index+callgraph`, or `full-readonly`, run the
corresponding methods in the context of the spiral's domain.

If `investigation_mode` is `none`, first apply the guard described in
section 4: read `cross-domain-coupling.json` and verify
`mece_verdict == "pure"`. If the guard fails, downgrade to `index+callgraph` and
log the reason. The remainder of this section then applies to the
downgraded mode.

For a knowledge graph (optional, available in any investigation mode when a
knowledge graph is present):

If `<knowledge-graph-dir>/` exists, the spiral may run a single conceptual query
before diving into files. This is useful when the spiral is entering an
unfamiliar domain:

```bash
# Find the conceptual path between the domain's main entry point
# and the connector target
<knowledge-graph-tool> path "<domain-entry-concept>" "<connector-target-concept>"

# Ask how two concepts interact
<knowledge-graph-tool> query "how does <concept-A> connect to <concept-B>?"
```

The output is a 3-7 node path through the knowledge graph. It gives the
spiral a high-level map of which concepts to read about before `architecture-index` maps
them to exact files. This is optional and not the default — it is available
when the spiral wants faster orientation in new territory.

For architecture-index tooling (included in `index-only` and `index+callgraph`):

```
Query: "What modules and files are relevant to <domain-name> for implementing
<connector-id>?"
```

For call-graph tooling (included in `index+callgraph` — the default and recommended mode):

After the architecture index narrows the scope, the call graph mechanically narrows it further using
the call graph. This identifies the minimal set of files the spiral must
touch for the current connector:

```bash
# Find functions in this domain that are called from the partner domain
# (the connector surface)
<callers-query> "<connector-function>" --depth 2

# Find what breaks if the spiral changes connector-facing functions
<impact-query> "<connector-function>" --depth 2 --tests --json
```

The output gives the spiral:
- **The connector surface:** functions that the partner spiral calls.
- **The blast radius:** which domain-internal functions and tests are
  affected by connector changes.
- **The file subset:** instead of reading the entire domain, the spiral
  reads only files in the call chain of the connector.

This replaces guesswork with mechanical scope narrowing. It is the
recommended default because it saves reading time and reduces the risk of
the spiral touching files outside the connector scope.

For read-only investigation lanes:

Define lanes scoped to the spiral's domain. Example:

| Lane | Focus                                         |
|------|-----------------------------------------------|
| A    | Existing code in the domain                   |
| B    | Data model changes needed                     |
| C    | Test coverage gaps                            |

Lanes are read-only and write results to
`.dna/tmp/investigation/<run_id>/<lane>/result.md`.

Aggregate investigation results into
`.dna/<feature-slug>/cycles/cycle-<N>/spiral-<id>/investigation.md`.

### 5.4 Decomposition

The spiral leader decomposes the connector task into Linear issues. The
decomposition is the spiral's internal decision and is not reviewed by the
other spiral or the initiator.

Recommended decomposition (non-binding):

- One issue per contract test (producer-side, consumer-side).
- One issue per mock implementation.
- One issue per integration test contribution.
- One or more issues for the domain logic that backs the connector.

Each issue must have:

- Title: `[Cycle N] <short-description>`
- Labels: `dna:<feature-slug>`, `spiral:<a|b>`, `cycle:<N>`
- Parent: the spiral's sub-issue from `linear/issue-map.json`
- Assignee: a member of the spiral (may be the leader or another member)

Create the issues via `linear` CLI:

```bash
linear create \
  --title "[Cycle 1] Implement GET /products/{id}" \
  --parent CIT-124 \
  --labels dna:autonomous-it-shop,spiral:a,cycle:1 \
  --assignee alice \
  --execute
```

Persist the created issue IDs to
`.dna/<feature-slug>/cycles/cycle-<N>/spiral-<id>/issues.json`:

```json
{
  "cycle": 1,
  "spiral": "a",
  "issues": [
    {"id": "CIT-130", "title": "..."},
    {"id": "CIT-131", "title": "..."}
  ]
}
```

### 5.5 Branch Creation

Create the cycle branch from `feat/<feature-slug>`:

```bash
git fetch origin
git checkout feat/<feature-slug>
git pull --ff-only
git checkout -b feat/<feature-slug>/spiral-<id>/cycle-<N>
git push -u origin feat/<feature-slug>/spiral-<id>/cycle-<N>
```

Do not mark this branch as protected. It will merge into
`feat/<feature-slug>` via `dna-close`.

### 5.6 Mock Scaffolding

If the contract specifies mock paths, create stub files at those paths:

```bash
mkdir -p stubs/cp-1/
echo '{}' > stubs/cp-1/producer.json
echo '{}' > stubs/cp-1/consumer.json
```

Commit the stubs to the cycle branch:

```bash
git add stubs/
git commit -m "dna-cycle: scaffold mocks for cycle <N>"
git push
```

This satisfies Law 2: "After freeze, each spiral immediately raises a local
mock of the partner side."

### 5.7 Handover

When all steps succeed, emit a final handover message:

```
dna-cycle <N> ready for spiral <id>.

Branch: feat/<feature-slug>/spiral-<id>/cycle-<N>
Issues created: <count>
Contract: contract/connector-<N>.yaml
Mock paths: <list>

Next step: work on the issues. When all issues are closed, the last closer
runs /dna-close <N>.
```

### 5.8 Mid-Cycle Contract Amendment

Law 2 forbids silent contract mutation. When a spiral discovers a hidden
coupling point, a missing field, or any other gap in the frozen connector
during cycle work, the spiral MUST follow this protocol instead of patching
the contract informally.

**Trigger.** Any one of:

- A spiral cannot satisfy `contract_tests` without changing the schema.
- A spiral discovers a cross-boundary call that is not represented in the
  frozen connector.
- The partner spiral reports a required field change.

**Procedure.**

1. **Pause the cycle.** Stop committing code that depends on the un-signed
   change.
2. **Edit `contract/connector-<N>.yaml`.** Update `schema` and bump
   `version` per semver:
   - additive / backward-compatible change → minor bump (e.g. 1.0.0 → 1.1.0)
   - breaking change → major bump (e.g. 1.0.0 → 2.0.0)
3. **Clear both `signed_by` fields and update `signed_at`** to indicate
   the contract has been amended and requires re-signing.
4. **Record the amendment** in the persistent changelog:

   ```bash
   python scripts/dna/validate_contract.py \
     --feature <feature-slug> --cycle <N> \
     --record-change "<short reason>" \
     --version-before <old-version> --version-after <new-version>
   ```

   This appends an entry to
   `.dna/<feature-slug>/contract/changelog.json`. The Law 8
   trigger evaluator at `dna-close` reads this file to count amendments
   per cycle (threshold: >= 2 amendments → retrospective required).
5. **Re-sign.** Both spiral leaders fill `signed_by.spiral_a_leader` and
   `signed_by.spiral_b_leader` in the YAML.
6. **Validate.** Run `python scripts/dna/validate_contract.py --feature
   <feature-slug> --cycle <N>` and confirm exit 0.
7. **Resume the cycle.** Both spirals update their mocks and resume work
   against the new version.

**Scope.** Amendments are allowed only on the CURRENT cycle's connector
(`connector-<N>.yaml` where `<N>` equals the active cycle). Amending a
future cycle's contract requires re-running `dna-split` for that cycle
only — `dna-cycle` does not have the authority to mutate other cycles.

**Linear.** Add a comment to the Integration Issue for cycle N noting the
amendment (one line: reason + version bump). The Integration Issue
remains open until `dna-close` runs.

---

## 6. Outputs

Produced files (under `.dna/<feature-slug>/cycles/cycle-<N>/spiral-<id>/`):

| File                  | Owner         | Purpose                                |
|-----------------------|---------------|----------------------------------------|
| `investigation.md`    | spiral leader | Optional investigation synthesis       |
| `issues.json`         | spiral leader | List of created Linear issues          |
| `result.md`           | spiral        | Final result after cycle work (written later) |

Side-effects:

- Git branch `feat/<feature-slug>/spiral-<id>/cycle-<N>` created and pushed.
- N Linear issues created under the spiral's sub-issue.
- Mock stubs committed to the cycle branch.

---

## 7. Autonomy and Flexibility

`dna-cycle` is the spiral's local method. The spiral leader has full
autonomy over:

- Whether to run architecture-index or read-only investigation tooling.
- How to decompose the connector task into issues.
- How many issues to create.
- How to assign issues within the spiral.
- Whether to create additional internal branches or work directly on the
  cycle branch.

The only invariants are:

- The contract must be satisfied by the end of the cycle.
- No files outside the spiral's sovereignty may be modified (Law 1, Law 7).
- All issues must be labelled correctly for `dna-close` to detect cycle
  completion.

---

## 8. Failure Modes

- **Contract not frozen.** Halt; the spiral cannot start work without a
  signed contract.
- **Branch creation fails.** Halt; the cycle cannot proceed without a
  branch.
- **Linear issue creation fails partially.** Halt and report. Do not leave
  a partial issue set.
- **Investigation stalls.** Apply the host investigation-tool stall handling. Do
  not block `dna-cycle` indefinitely.

If any unexpected blocker appears, stop, state options, and wait for direction.

---

## 9. What dna-cycle Is Not

- It is not `dna-split`. It does not freeze contracts or create the
  feature branch.
- It is not `dna-close`. It does not merge branches or verify integration.
- It is not implementation. It only plans and scaffolds.
- It is not the other spiral's concern. Each spiral runs `dna-cycle`
  independently.

---

## 10. Approval Gate

`dna-cycle` is complete only when:

- The cycle branch exists and is pushed to origin.
- At least one Linear issue exists for this cycle, labelled correctly.
- `issues.json` exists and lists all created issues.
- Mock stubs (if specified in the contract) are committed to the cycle
  branch.
- If any mid-cycle amendment occurred (section 5.8),
  `contract/changelog.json` reflects every version bump and both spirals
  have re-signed the latest `connector-<N>.yaml`.

If any of those is missing, `dna-cycle` is incomplete and the spiral must
not start implementation.

End of method.
