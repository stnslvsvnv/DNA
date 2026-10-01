---
description: DNA Close method - integration gate, Law 7 validation, retrospective triggering, merge into feature branch (or main on final cycle)
---

# Method DNA-CLOSE: Integration Gate

Activation: triggered by the spiral member who closed the **last open
Linear issue** for the current cycle. Activation may also be manual:
`dna-close N`, `/dna-close N`, or `close DNA cycle N`.

`dna-close` is the fourth and final method of the DNA family. It runs
N times per feature (one call per integration node). The last call also
finalises the feature: it merges the feature branch into `main` and closes
the Linear master issue.

This method is bound by the manifest in `DNA.md`. It must not violate
any law of that manifest.

---

## 1. Purpose

`dna-close` is the only place where DNA permits the technical meeting
of two spirals. It performs three machine validations from Law 7, gathers
the honest flag for Antipattern 4, fires retrospective triggers from Law 8,
and merges the cycle branches into the feature branch (Law 9).

If the cycle is the final one (`N == total_cycles`), `dna-close` also
merges the feature branch into `main`, closes the Linear master issue, and
archives the feature state.

---

## 2. Prerequisites

`dna-close` may run only when all of the following are true:

- `dna-split` has been completed for this `feature_slug`.
- Both spirals have completed `dna-cycle` for the current cycle N.
- All Linear issues with labels `dna:<feature-slug>` and `cycle:<N>` (for
  both `spiral:a` and `spiral:b`) are closed.
- Both cycle branches `cycle/<feature-slug>/spiral-{a,b}/cycle-<N>` exist
  on origin.

If any prerequisite is missing, `dna-close` halts and reports which
condition is unmet.

---

## 3. Core Rules

Section ID: `DNA-CLOSE-CORE`

1. `dna-close` is run by the spiral member who closed the last cycle issue
   in Linear. Detection is automated by `scripts/dna/detect_closer.py`,
   which reads Linear issue history.
2. `dna-close` runs three machine checks (Law 7) before merging anything.
3. `dna-close` collects the Heroic Integration honest flag and the
   "Lesson learned" one-liner from each spiral.
4. `dna-close` fires retrospective triggers (Law 8) and creates an ADR
   draft when triggered. The next cycle is blocked until both spirals
   sign off on the ADR.
5. `dna-close` merges cycle branches into `feat/<feature-slug>` only when
   all checks pass.
6. `dna-close` for the final cycle additionally merges `feat/<feature-slug>`
   into `main` (or `dev`, depending on the repo's flow), closes the Linear
   master issue, and archives the feature state.
7. `dna-close` uses the configured issue-tracker CLI and never reads or
   depends on private wrapper internals.
8. `dna-close` must produce `close-report.md` in the cycle directory
   regardless of pass or fail.

---

## 4. Inputs

Required:

- `feature_slug` — must match the slug used in the previous methods.
- `cycle_number` — the cycle being closed.

Optional:

- `force_run` — set when manual override is requested. Subject to user
  confirmation; not the default path.

---

## 5. Workflow

### 5.1 Detect Closer

Run `scripts/dna/detect_closer.py` against the Linear issue history. It
returns the user who closed the last open issue for cycle N. That user is
the responsible runner of `dna-close`. When the Linear lookup is ambiguous,
member identity resolves through `.dna/project.yaml`
(`members.<id>.linear`).

If the script cannot determine the unique closer (timestamp tie, missing
data, Linear API error), apply this deterministic fallback in order:

1. **Timestamp tie within 60 seconds.** Closer = spiral with
   alphabetically smaller `spiral_id`. Practically: `spiral_a` wins over
   `spiral_b`.
2. **Linear data unreachable or ambiguous.** Closer = `spiral_a` by
   default.
3. **Explicit override.** If the invocation sets `--force-closer <a|b>`
   (CLI flag) or `DNA_FORCE_CLOSER=a|b` (environment variable), that
   value wins over rules 1 and 2.

The closer logs which rule fired in `close-report.md` under the section
`Closer Detection` (one line, e.g. `Detection: deterministic_fallback
rule_1 alphabetical_tiebreak`).

The fallback is machine-deterministic by design. No path ends in "ask a
human to decide" — `dna-close` must always be able to proceed.

### 5.2 Confirm Cycle Completion

Before any check, confirm that all cycle issues are closed:

```bash
linear list --label dna:<feature-slug> --label cycle:<N>
```

If any issue is open, halt and report.

### 5.3 Law 7 Validation Suite

Run the three machine checks via service scripts. All checks must produce
a JSON report in `cycles/cycle-<N>/checks/`.

#### 5.3.1 File Overlap Check

```bash
python scripts/dna/file_overlap_check.py \
  --feature <feature-slug> \
  --cycle <N> \
  --branch-a cycle/<feature-slug>/spiral-a/cycle-<N> \
  --branch-b cycle/<feature-slug>/spiral-b/cycle-<N> \
  --base feat/<feature-slug> \
  --output cycles/cycle-<N>/checks/file_overlap.json
```

The script reads `shared-kernel.txt` automatically from
`.dna/<feature-slug>/shared-kernel.txt` (created by `dna-split`).
No explicit `--shared-kernel-list` flag is needed.

Output:

```json
{
  "check": "file_overlap",
  "verdict": "pass | fail",
  "intersection": ["..."],
  "shared_kernel_exempt": ["..."],
  "responsible_spiral": "a|b|null"
}
```

On `fail`: `dna-close` halts. The responsible spiral must clean up before
re-running.

#### 5.3.2 Dependency Drift Check

```bash
python scripts/dna/dependency_drift_check.py \
  --feature <feature-slug> \
  --cycle <N> \
  --output cycles/cycle-<N>/checks/dependency_drift.json
```

Output:

```json
{
  "check": "dependency_drift",
  "verdict": "pass | warning",
  "duplicated_deps": ["..."],
  "spiral_a_new_deps": ["..."],
  "spiral_b_new_deps": ["..."]
}
```

On `warning`: `dna-close` continues. The drift becomes a question for the
retrospective trigger evaluation.

#### 5.3.3 Contract Conformance Check

```bash
python scripts/dna/contract_conformance_check.py \
  --feature <feature-slug> \
  --cycle <N> \
  --output cycles/cycle-<N>/checks/contract_conformance.json
```

Output:

```json
{
  "check": "contract_conformance",
  "verdict": "pass | contract_test_fail | integration_test_fail",
  "responsible_spiral": "a|b|both|null",
  "details": "..."
}
```

On `contract_test_fail`: the responsible spiral fixes its implementation.
`dna-close` halts.

On `integration_test_fail` while contract tests pass: contract is
incomplete. Both spirals enter mini-retrospective. `dna-close` halts and
the connector contract is reopened (a partial Stage 0 return).

### 5.4 Honest Flag Collection

Update the Integration Issue in Linear with mandatory fields:

```
Heroic Integration?            [No / Minor / Major]
Contract changes during cycle? [None / Minor / Major]
Lesson learned (Spiral A):     <one line>
Lesson learned (Spiral B):     <one line>
```

`dna-close` blocks until all four fields are filled. The closer prompts
both spirals to fill their respective fields.

### 5.5 Retrospective Trigger Evaluation

Run `scripts/dna/retrospective_trigger.py` with the collected data. It
evaluates Law 8 triggers:

- Contract changed >= 2 times during the cycle.
- Integration node failed first attempt (any check returned non-pass on
  this run before re-running).
- Cycle amplitude exceeded 10 working days.
- Heroic-integration flag is `Minor` or `Major`.

**Contract-change count source.** The `--contract-changes <int>` flag of
`retrospective_trigger.py` MUST be derived mechanically from the
amendment changelog, not from hand-filled fields:

```bash
CHANGES=$(python -c "
import json, pathlib
p = pathlib.Path('.dna/<feature-slug>/contract/changelog.json')
if not p.exists():
    print(0)
else:
    data = json.load(p.open())
    print(sum(1 for e in data if e.get('cycle') == <N>))
")

python scripts/dna/retrospective_trigger.py \
  --feature <feature-slug> --cycle <N> \
  --honest-flag <No|Minor|Major> \
  --contract-changes "$CHANGES" \
  --amplitude-days <days> \
  [--first-attempt-failed]
```

If `changelog.json` is absent, the count is 0 (no amendments occurred).
This makes the Law 8 trigger fully deterministic — humans cannot
under- or over-report contract changes.

Output:

```json
{
  "triggers_fired": ["heroic_integration_minor", "amplitude_exceeded"],
  "retrospective_required": true | false
}
```

If `retrospective_required` is `true`:

- Auto-create `cycles/cycle-<N>/retrospective.md` from the template.
- Auto-create an ADR draft `decisions/<NNN>-cycle-<N>-retrospective.md`.
- Mark next cycle as `blocked` in `linear/issue-map.json` until both
  spirals sign off on the ADR.
- Notify both spiral leaders via Linear comment.

If `retrospective_required` is `false`, no retrospective document is
created. Skip silently. Healthy cycles do not produce retrospectives.

### 5.6 Merge

When all checks pass and the retrospective gate (if triggered) is
honoured, merge cycle branches into `feat/<feature-slug>`:

```bash
git fetch origin
git checkout feat/<feature-slug>
git pull --ff-only

# Merge spiral A
git merge --no-ff origin/cycle/<feature-slug>/spiral-a/cycle-<N> \
  -m "dna-close: cycle <N> spiral A"

# Merge spiral B
git merge --no-ff origin/cycle/<feature-slug>/spiral-b/cycle-<N> \
  -m "dna-close: cycle <N> spiral B"

git push origin feat/<feature-slug>
```

If a merge produces conflicts, classify them before acting:

- **Substantive conflicts** — changes to business logic, API contracts, or
  data models in overlapping files. These are Law 7 violations (the file
  overlap check should have caught them; if it didn't, the Shared Kernel
  list is wrong). Halt, fix the Shared Kernel list, and re-run the file
  overlap check.

- **Cosmetic conflicts** — import reordering, `__init__.py` additions,
  whitespace, formatting, or generated file changes that do not affect
  behaviour. These are NOT Law 7 violations. Resolve them manually and
  document every resolved cosmetic conflict in `close-report.md` under the
  `Resolved Cosmetic Conflicts` section. Do NOT halt for cosmetic conflicts;
  resolve them and continue.

The classification is a human judgement call by the closer. When in doubt,
treat a conflict as substantive rather than cosmetic.

### 5.7 Close Linear Cycle Artifacts

Close the Integration Issue for cycle N:

```bash
linear done --issue <integration-issue-id> \
  --comment "DNA cycle <N> closed. Verdicts: file_overlap=pass, dependency_drift=<v>, contract_conformance=pass, heroic_flag=<f>."
```

Update `linear/issue-map.json` to reflect the closed state.

### 5.8 Final Cycle Special Path

If `cycle_number == total_cycles` (read from
`decisions/002-coupling-points.md`), do the following additional steps:

1. Merge `feat/<feature-slug>` into `main` (or `dev` per the repo flow):

   ```bash
   git checkout main
   git pull --ff-only
   git merge --no-ff feat/<feature-slug> \
     -m "dna-close: feature <feature-slug> finalised"
   git push origin main
   ```

2. Close the Linear master issue:

   ```bash
   linear done --issue <master-issue-id> \
     --comment "DNA feature <feature-slug> complete. <N> cycles closed."
   ```

3. Archive the feature state:

   ```bash
   mv .dna/<feature-slug> \
      .dna/_archived/<feature-slug>-$(date +%Y%m%d)
   ```

4. Optionally delete the feature branch:

   ```bash
   git push origin --delete feat/<feature-slug>
   ```

5. Emit the final report:

   ```
   DNA feature <feature-slug> complete.

   Cycles: <N>
   Retrospectives triggered: <count>
   Heroic integrations: <count>
   Final merge: main <commit-sha>
   Linear master closed: <id>
   Archive: .dna/_archived/<feature-slug>-<date>/
   ```

### 5.9 Close Report

Before composing the report, generate health metrics. The closer derives
`--contract-changes` from `changelog.json` (same logic as section 5.5) and
fills the remaining metric inputs from cycle observations:

```bash
python scripts/dna/metrics.py \
  --feature <feature-slug> --cycle <N> \
  --contract-changes "$CHANGES" \
  --mock-time-hours <h> \
  --node-duration-percent <p> \
  --cross-domain-prs <n>
```

The script writes `cycles/cycle-<N>/metrics.json`. The close report
embeds the result.

Regardless of pass or fail, produce
`cycles/cycle-<N>/close-report.md`:

```markdown
# DNA-Close Report — <feature-slug> cycle <N>

Date: ...
Closer: <name>
Closer Detection: <detect_closer | deterministic_fallback rule_<n> | force_override>

## Law 7 Checks

- File overlap: <pass | fail>
- Dependency drift: <pass | warning>
- Contract conformance: <pass | contract_test_fail | integration_test_fail>

## Honest Flags

- Heroic Integration: <No | Minor | Major>
- Contract changes during cycle: <None | Minor | Major>

## Health Metrics

Generated by `scripts/dna/metrics.py`; source file:
`cycles/cycle-<N>/metrics.json`.

- contract_changes_per_cycle: value=<n> status=<healthy|warning|alarm>
- time_to_mock_hours: value=<h> status=<healthy|warning|alarm>
- node_duration_percent_of_cycle: value=<p> status=<healthy|warning|alarm>
- cross_domain_prs: value=<n> status=<healthy|alarm>
- overall: <healthy|warning|alarm>

## Retrospective

Triggered: <yes | no>
Triggers fired: <list>
ADR: <path or n/a>

## Merge

Spiral A merged: <commit-sha or skipped>
Spiral B merged: <commit-sha or skipped>
Feature branch state: <ready-for-next-cycle | finalised>

## Resolved Cosmetic Conflicts

(Only if cosmetic conflicts occurred during merge; omit section if none)

- `path/to/file.py`: <brief description of the cosmetic conflict and resolution>
- ...

## Final Cycle Actions

(only on last cycle)

- Main merge: <commit-sha>
- Linear master closed: <id>
- Archive: <path>
```

---

## 6. Outputs

Produced files (under `.dna/<feature-slug>/cycles/cycle-<N>/`):

| File                              | Owner       | Purpose                              |
|-----------------------------------|-------------|--------------------------------------|
| `checks/file_overlap.json`        | script      | Law 7 check 1 result                 |
| `checks/dependency_drift.json`    | script      | Law 7 check 2 result                 |
| `checks/contract_conformance.json`| script      | Law 7 check 3 result                 |
| `close-report.md`                 | dna-close   | Human-readable close report          |
| `retrospective.md`                | dna-close   | Only if triggered                    |

Side-effects:

- Cycle branches merged into `feat/<feature-slug>`.
- Integration Issue closed in Linear.
- On final cycle: feature branch merged into `main`; master issue closed;
  state archived.

---

## 7. Failure Modes

- **Closer cannot be detected.** Fall back to manual activation by either
  spiral leader.
- **File overlap check fails.** Halt; responsible spiral cleans up.
- **Contract conformance fails.** Halt; responsible spiral fixes.
- **Integration test fails while contract tests pass.** Halt; contract
  reopens for partial Stage 0.
- **Honest flag fields incomplete.** Halt until both spirals fill them.
- **Merge produces conflicts.** Treat as Law 7 violation; halt and revise
  Shared Kernel list.
- **Final-cycle main merge fails.** Halt; do not archive state until the
  merge is resolved.

If any unexpected blocker appears, stop, state options, and wait for direction.

---

## 8. What dna-close Is Not

- It is not `dna-cycle`. It does not create branches or issues.
- It is not implementation. It only validates and merges.
- It is not retrospective theatre. Retrospective is created only on
  trigger.
- It is not a substitute for human review of the integration. The closer
  remains responsible for confirming that the merge is sane.

---

## 9. Approval Gate

`dna-close` is complete only when:

- All three Law 7 checks have produced JSON reports.
- Honest flag fields are filled.
- Retrospective document exists if triggered (and ADR draft exists).
- Cycle branches are merged into `feat/<feature-slug>`.
- Integration Issue is closed in Linear.
- `close-report.md` exists for the cycle.

For the final cycle, additionally:

- `feat/<feature-slug>` is merged into `main`.
- Linear master issue is closed.
- Feature state is archived.

If any of those is missing, `dna-close` is incomplete and the next cycle
(or the feature finalisation) is forbidden to start.

End of method.
