# DNA Bootstrap

One-time setup of a repository before the first `dna-disco`. Produces the
project profile `.dna/project.yaml` (tracker, members, lane assignments,
optional companion tooling), verifies prerequisites, and protects the
long-lived branches. Run this once per repository; features then go through
`dna-disco` → `dna-split` → `dna-cycle` → `dna-close`.

This document is not one of the four DNA methods; it prepares the ground
they run on.

---

## 1. Prerequisites

| Requirement | Why |
|---|---|
| Git repository with an `origin` remote | DNA branches merge through PRs. |
| Python 3.10+ | All service scripts. |
| `pyyaml` (`pip install pyyaml`) | Contract and profile parsing. |
| `linear` CLI with workspace access | Issue hierarchy, assignment, closer detection. |
| `gh` or `glab` (optional) | Automated branch protection. Without it the script prints manual steps. |

Check the environment:

```bash
python3 --version
python3 -c "import yaml; print('pyyaml ok')"
git remote -v
linear --version
```

---

## 2. Install the kit

Three equivalent ways to get `scripts/dna/` onto the machine:

1. **Repository checkout** — clone this repository and run scripts from it:

   ```bash
   git clone https://github.com/stnslvsvnv/DNA.git .dna-kit
   ```

2. **Agent skill (recommended)** — install through the OMP registry or a
   cross-agent skill installer:

   ```bash
   omp skill install @stnslvsvnv/dna
   # or
   npx skills add stnslvsvnv/DNA@dna -g -y
   ```

3. **Vendor into the host repository** — copy `scripts/dna/` into the host
   repository under `scripts/dna/` and invoke it as `python scripts/dna/...`.

The scripts run against the **host repository**, not against the kit
location. The host project root resolves from `DNA_PROJECT_ROOT`, then the
git top-level of the current working directory, then the current directory.
When running the scripts from an installed skill, execute them from the host
repository:

```bash
python <skill-dir>/scripts/dna/validate_project.py
# or, inside an agent that resolves skill:// paths:
python skill://dna/scripts/dna/validate_project.py
```

---

## 3. Create `.dna/project.yaml`

Copy `project.example.yaml` and fill it in:

```bash
mkdir -p .dna
cp project.example.yaml .dna/project.yaml
```

The profile answers the two initial setup questions: **where** parallel
work hangs (Linear team, branches) and **who** owns each lane.

```yaml
version: 1
tracker:
  kind: linear
  team: CIT           # Linear team key
members:              # every human or agent that can own a lane
  alice: {name: Alice, linear: alice@example.com}
  bob:   {name: Bob,   linear: bob@example.com}
lanes:                # the parallel lanes (spirals) and their leaders
  spiral_a: {leader: alice, executor: human}
  spiral_b: {leader: bob,   executor: agent:worker-2}
initiator: alice      # drives dna-disco/dna-split and approves REVIEW.md
```

Field notes:

- `members.<id>.linear` — Linear username or email; used for sub-issue
  assignment and closer detection.
- `lanes.spiral_*.leader` — the contract signer (`signed_by`) and the
  Linear assignee for that lane; the operator of `dna-cycle`.
- `lanes.spiral_*.executor` — free-form: `human` or `agent:<name>`. This is
  the hook for running lanes with agent workers.
- `initiator` — the single member that runs `dna-disco`/`dna-split`.

Validate the profile:

```bash
python scripts/dna/validate_project.py
```

Missing profile is a hard stop: `dna-disco` and `dna-split` will not run
without it.

---

## 4. Protect the long-lived branches

Manifest Law 9 requires `main` and `feat/<feature-slug>` to be protected;
direct pushes are forbidden. Feature branches are protected later, by
`dna-split`; protect `main` now:

```bash
python scripts/dna/protect_branch.py --branch main
python scripts/dna/protect_branch.py --branch main --check
```

The script applies protection through `gh`/`glab` when available (require
pull request, block force pushes and deletions) and prints manual
instructions otherwise. Verify the result in the host settings before
starting the first feature.

---

## 5. Contract and integration test wiring

Each connector contract (`contract/connector-N.yaml`, produced later by
`dna-split`) lists its own tests:

```yaml
contract_tests:
  - path: tests/contracts/cp-1/producer_test.yaml
integration_tests:
  - path: tests/integration/cp-1_e2e.py
```

`dna-close` runs these paths with `pytest` (`.py`) or `npm test`
(`.js`/`.ts`). There is nothing to configure globally — bootstrap only
confirms that the repository has a working test runner and CI:

```bash
python3 -m pytest --version   # or npm test --dry-run
```

---

## 6. Optional companions (3A and friends)

DNA works standalone. Optional companion tooling makes it sharper:

| Companion | Layer | Used by |
|---|---|---|
| 3A skill | architecture index, call graph, concept graph | `dna-disco` §5.2–5.5, `dna-split` §5.4–5.5, `dna-cycle` §5.3 |
| Any graph tooling | freshness-checked knowledge graph | boundary validation |

Declare the available commands in the profile; DNA checks presence and makes
only the *freshness gates* hard. Absence never blocks a run:

```yaml
intelligence:
  graph_freshness_cmd: "python scripts/check_graph_freshness.py"
  graph_update_cmd: "python scripts/update_graphify_no_viz.py ."
  call_graph_path: "context/index/call_graph.json"
```

If the 3A skill is installed in the agent runtime, its instructions remain
the source of truth for those phases; DNA never duplicates them.

---

## 7. Commit and start

```bash
git add .dna/project.yaml
git commit -m "chore(dna): add project profile"
```

Then start the first feature with `dna-disco`. Checklist:

- [ ] `python scripts/dna/validate_project.py` → `pass`
- [ ] `main` protection verified (`protect_branch.py --check`)
- [ ] Test runner available for contract/integration tests
- [ ] Optional companions declared (or consciously omitted)
- [ ] `.dna/project.yaml` committed

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `ERROR: project profile missing` | Run this bootstrap; create `.dna/project.yaml`. |
| Script writes to the wrong directory | Run from the host repo or set `DNA_PROJECT_ROOT`. |
| State lands outside the repo | Check `DNA_STATE_ROOT`; unset it to use `<root>/.dna`. |
| `Branch not protected` stays after apply | The host plan may not support protection (GitHub Free for private repos); apply manually per the printed instructions. |
| `linear` CLI missing | Install it or rely on the documented manual fallback in `dna-close`. |
