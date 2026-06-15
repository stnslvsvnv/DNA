# DNA

**Manifesto of Parallel Engineering for Small Teams.**

Status: v2 (frozen). This document is the constitution of the DNA method
family. Methods that implement it live in `methods/dna-*.md`.
Service scripts live in `scripts/dna/`.

---

## Preamble

DNA is not management philosophy. It is a set of engineering laws that
hold architectural borders between people who work in parallel.

You stop planning tasks. You start planning the interfaces where the tasks
must meet.

This is a framework for teams that want a continuous, isolated flow of value
creation, not a daily simulation of activity on standups.

---

## 0. Glossary

| DNA term         | Engineering meaning                                        |
|------------------|------------------------------------------------------------|
| Spiral           | Isolated executor or work stream (one person or one squad).|
| Cycle (виток)    | Period of isolated work between two integration nodes.     |
| Amplitude        | Duration of a cycle. Recommended 5–10 working days.        |
| Node             | Integration point where spirals technically meet.          |
| Connector        | Slice of the contract verified at the current node.        |
| Hydrogen bonds   | Contracts between domains (OpenAPI, Protobuf, events).     |
| Double helix     | State of successful CI integration on a connector.         |
| Coupling point   | Place in the contract where spirals must technically meet. |

---

## 1. Applicability

DNA applies when all of the following hold:

1. Team size is between 2 and 6 people.
2. The feature decomposes into at least two weakly coupled business domains.
3. All participants can design APIs and contracts independently.
4. CI infrastructure exists for contract tests and integration tests.
5. Requirements are reasonably stable within a single cycle.

If any condition fails, DNA degrades into ordinary Kanban with
unnecessary ceremony. In that case do not use this method.

This check is enforced by an explicit applicability gate after `dna-disco`
(see method documentation).

---

## 2. Laws

### Law 1. Orthogonal Domain Demarcation (MECE)

- The product is cut along vertical business domains, not technological
  layers (no "backend person + frontend person" split).
- Borders follow the MECE rule: mutually exclusive, collectively exhaustive.
- No code ownership overlap. Nobody writes inside another spiral's domain.
- Demarcation procedure on Stage 0:
  1. List all use-cases of the feature.
  2. Group them by business invariants (what changes together lives together).
  3. Verify MECE: each use-case belongs to exactly one domain.
  4. Validate boundaries conceptually with a knowledge-graph report,
     compare Leiden communities to the human grouping, check god nodes
     for coupling-point candidates, and note surprising connections
     that cross the proposed boundary. Adjust if the graph contradicts
     the human grouping.
  5. Validate boundaries mechanically with a call graph:
     run `cross_domain_coupling.py` to detect real cross-boundary calls,
     cycles, and Shared Kernel candidates. Adjust boundaries if the
     call graph contradicts the human grouping.
  6. Build the dependency graph between domains.
  7. If the graph contains a cycle, revise the borders.
  8. Freeze the result in `DOMAINS.md` with one explicit owner per domain.

### Law 2. Contract-First with Versioning

- No production code is written for the current connector before its
  contract is frozen.
- Contracts are versioned (semantic or date-based).
- A minor or patch change requires notification to the partner spiral.
- A major change requires a synchronous session and re-signing by both
  spirals.
- Silent contract mutation is forbidden (see Antipattern 2).
- Contract tests for every connector are required in CI.
- After freeze, each spiral immediately raises a local mock of the partner
  side and works independently.

### Law 3. Isolation of Implementation, Transparency of Progress

- **Implementation is a black box.** Internal patterns, file structure,
  working hours, and reasoning are nobody else's business.
- **Progress is transparent through Linear.** Issue statuses are the
  synchronisation surface.
- A spiral must update its owned issues at least once per working day while
  the cycle is active.
- Daily standups are forbidden. Linear is the standup.

### Law 4. Cycles Are Determined by Contract Decomposition

This is the central law. It defines the topology of the method.

- The number of cycles N for a feature is decided during `dna-split`, not
  by calendar or budget.
- Decomposition algorithm:
  1. Enumerate all contact points between spirals (endpoints, events,
     shared data, shared events).
  2. Group them into **minimally integrable blocks**: sets of points that
     are meaningful to verify together.
  3. Order the blocks by dependency.
  4. Each block becomes one cycle and one integration node.
- Inside a cycle the spirals work on different files connected by exactly
  one shared connector. The node verifies only that connector, not the
  entire contract.
- If a hidden coupling point appears mid-cycle, the cycle is stopped and a
  partial return to Stage 0 is performed for that point. Spirals must not
  agree on new contracts informally in chat.
- Recommended amplitude per cycle is 5–10 working days. A soft cap of 10
  days triggers an early warning, not an automatic stop.

### Law 5. Integration Node Equals Green CI on the Current Connector

- A node is closed only when all of the following are true:
  - Contract tests for the current connector are green on both sides.
  - The end-to-end test that exercises the current connector passes.
  - No TODO or FIXME markers remain in integration-layer code.
  - Both spirals sign off on the merge.
- A Linear cycle is not the same as a DNA node. A Linear cycle is a time
  container. A node is a technical event. The node is carried by a
  dedicated Linear issue labelled `integration-node`.

### Law 6. Shared Kernel — Three Strategies

Cross-cutting infrastructure (authentication, logging, shared UI primitives)
is a collision risk and must be handled explicitly during `dna-split`. One
of three strategies must be chosen and recorded as an ADR:

1. **Co-developed before split.** The kernel is built jointly before the
   spirals diverge.
2. **Delegated to one spiral.** One spiral owns the kernel; the other uses
   stubs until the kernel is ready.
3. **External package.** The kernel lives in its own repository or package
   with its own versioning. Both spirals are consumers, not contributors,
   except through PRs to a designated owner.

### Law 7. Fallback Protocol — Pre-Close Validation

Before any node closes, `dna-close` runs three machine checks. They define
responsibility automatically and remove subjective blame.

1. **File overlap check.**
   - Files modified by Spiral A in cycle N and files modified by Spiral B
     in cycle N must not intersect, except files explicitly declared as
     Shared Kernel.
   - On violation: STOP. The responsible spiral is the one that wrote into
     foreign territory.

2. **Dependency drift check.**
   - New dependencies introduced by one spiral must not duplicate
     dependencies already present in the other spiral.
   - On violation: WARNING. Not a blocker, but a question for the
     retrospective trigger.

3. **Contract conformance check.**
   - Contract tests for the current connector must pass.
   - The integration test for the current connector must pass.
   - If a contract test fails, the responsible spiral is the one whose
     implementation does not match its own declared contract.
   - If contract tests pass but the integration test fails, the contract
     itself is incomplete and both spirals enter a mini-retrospective.

The person who runs `dna-close` is the spiral member who closed the last
Linear issue of the current cycle.

### Law 8. Integration Gate with Retrospective Triggers

- Retrospective is machine-triggered, never scheduled.
- Triggers:
  - The contract changed two or more times during the cycle.
  - The integration node failed on the first attempt.
  - The cycle amplitude exceeded the 10-day soft cap.
  - The Heroic Integration honest flag is set to `Minor` or `Major`.
- When a trigger fires, `dna-close` auto-creates an ADR draft and blocks
  the start of the next cycle until both spirals sign off on the ADR.
- When no trigger fires, retrospective is skipped silently. A healthy
  cycle has no retrospective. This is intentional and is the protection
  against ceremony creep.

### Law 9. Branch Topology

```
main
 └── feat/<feature-slug>                              (created by dna-split)
      ├── feat/<feature-slug>/spiral-a/cycle-N
      └── feat/<feature-slug>/spiral-b/cycle-N
```

- `main` and `feat/<feature-slug>` are protected branches.
- Cycle branches merge into `feat/<feature-slug>` only through `dna-close`.
- `feat/<feature-slug>` merges into `main` only on the final `dna-close`
  of the last cycle.
- Direct push to protected branches is forbidden.

---

## 3. Antipatterns

1. **Contraband business logic.** A spiral implements logic that belongs to
   the other domain "for convenience". Detected by Law 7 file-overlap check.

2. **Silent contract mutation.** A spiral unilaterally renames a field or
   changes a schema during the cycle without re-signing. Detected by
   contract tests at the node.

3. **Synchronous deadlock.** Circular dependencies between domains are
   committed to on Stage 0. Detected by knowledge graph (surprising connections),
   call graph (`cross_domain_coupling.py`), and the dependency graph
   step of the demarcation procedure.

4. **Heroic integration.** The node does not converge on time and one
   spiral hand-patches both sides in panic. Detected only by an honest
   flag on the Integration Issue: `[No / Minor / Major]`. The flag is a
   mandatory field at node closure. A `Minor` or `Major` flag triggers
   retrospective via Law 8.

---

## 4. Health Metrics

| Metric                                            | Healthy   | Alarm signal         |
|---------------------------------------------------|-----------|----------------------|
| Contract changes per cycle                        | ≤1 minor  | ≥1 major or ≥3 minor |
| Time from contract frozen to mock running         | <1 day    | >2 days              |
| Integration-node duration                         | <10% cycle| >25% cycle           |
| Cross-domain PRs (PR into foreign domain)         | 0         | ≥1 unsanctioned      |

These metrics are emitted by `scripts/dna/metrics.py` after each `dna-close`.

---

## 5. Method Family

DNA is implemented as four explicit methods. Each method has its own
document in `methods/`. The manifest is the contract those methods
must satisfy.

| Method      | Triggered by                                    | Frequency           |
|-------------|-------------------------------------------------|---------------------|
| `dna-disco` | Feature initiator                               | Once per feature    |
| `dna-split` | Feature initiator                               | Once per feature    |
| `dna-cycle` | Spiral leader (each spiral, independently)      | N per spiral        |
| `dna-close` | Person who closed the last Linear issue of cycle| N; last call finalises feature |

---

## 6. Intelligence Stack

DNA can use three optional intelligence layers as a funnel. Each layer narrows
scope for the next:

```
knowledge graph     -> "What concepts exist? What communities?"
architecture index  -> "Where are those concepts? Which files?"
call graph          -> "What calls what? What breaks?"
DNA                 -> "How do we split and run in parallel?"
                       Frozen connectors, N cycles, Law 7 gates.
```

Each layer is optional if its data source is absent, but together they
shrink the reading set from ~500 files to ~7-12 files before any
implementation begins. See `methods/dna-disco.md` for the exact
order of operations.

---

## 7. Lifecycle Overview

```
[Initiator] feature idea
   |
   v
dna-disco        --> dossier.md + dossier.json
   |
   v
[HUMAN GATE]     --> REVIEW.md (initiator approves demarcation, N, kernel)
   |
   v
[APPLICABILITY]  --> machine check (Section 1)
   |
   v
dna-split        --> DOMAINS.md, ADRs, contract/connector-N.yaml,
                     feat/<slug> branch, Linear master+sub-issues,
                     Integration Issue placeholders
   |
   v
+--------------------------------+
| For each cycle N (in parallel):|
|                                |
| Spiral A: dna-cycle N          |
| Spiral B: dna-cycle N          |
|                                |
| isolated work in branches      |
|                                |
| last Linear-issue closer:      |
|   dna-close N                  |
|     - Law 7 checks             |
|     - retrospective if needed  |
|     - merge into feat/<slug>   |
+--------------------------------+
   |
   v
Final dna-close
   - merge feat/<slug> into main/dev
   - close Linear master-issue
   - archive state
```

---

## 8. Artifact Layout

```
.dna/<feature-slug>/
|-- dossier.md
|-- dossier.json
|-- REVIEW.md
|-- DOMAINS.md
|-- contract/
|   |-- connector-1.yaml
|   |-- connector-2.yaml
|-- decisions/
|   |-- 001-domain-split.md
|   |-- 002-coupling-points.md
|   |-- 003-shared-kernel.md
|   |-- NNN-*.md
|-- cycles/
|   |-- cycle-N/
|       |-- spiral-a/result.md
|       |-- spiral-b/result.md
|       |-- close-report.md
|       |-- retrospective.md   (only if triggered)
|-- linear/
    |-- issue-map.json
```

---

## 9. Style Invariants

- ADRs are mandatory for every architectural decision (domain split,
  coupling-point grouping, Shared Kernel strategy, contract changes).
- ADR template: `Context / Considered Alternatives / Decision / Rationale
  / Consequences / Reversibility`.
- ADRs from completed features should be indexed by the host repository's
  documentation or architecture-index tooling so future features reuse precedent.
- Documents are written in dry engineering register. No marketing language.
  No emojis.

---

## 10. Constraints on Method Evolution

- A method document must not contradict the manifest.
- A method change that requires loosening any law in this manifest is
  treated as a manifest change and must be reviewed explicitly.
- The four method names are reserved: `dna-disco`, `dna-split`,
  `dna-cycle`, `dna-close`.
- Adding a fifth method is allowed only if it implements a law that none
  of the four currently implements.

---

## 11. References

- `methods/dna-disco.md`
- `methods/dna-split.md`
- `methods/dna-cycle.md`
- `methods/dna-close.md`
- `scripts/dna/` — service scripts.

End of manifest.
