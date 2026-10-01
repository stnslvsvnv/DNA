# Changelog

## 1.0.0 — 2026-10-01

First packaged release of the standalone DNA kit.

- **Agent skill packaging**: `skills/dna/` mirror with `SKILL.md`,
  `scripts/sync_skill.py`, and `tests/test_skill_sync.py`; installable via
  `omp skill` or `npx skills add`.
- **`dna-bootstrap.md`**: one-time repository setup — prerequisites,
  project profile, branch protection, contract-test wiring, optional
  companions.
- **Project profile** (`.dna/project.yaml`): tracker, members, and lane
  assignments (leader + executor per spiral) — the initial setup of where
  and to whom parallel lanes are attached. Validated by
  `scripts/dna/validate_project.py`; schema in
  `scripts/dna/schemas/project.schema.json`; template in
  `project.example.yaml`.
- **`scripts/dna/protect_branch.py`**: Law 9 branch protection via
  `gh`/`glab` with manual instructions as fallback.
- **Host-agnostic project root resolution**: `DNA_PROJECT_ROOT` → git
  top-level of the current directory → current directory, so the kit works
  when installed outside the host repository.
- **Optional companion tooling** (3A skill, knowledge graph, call graph):
  presence-checked and declared under `intelligence`; absence never blocks
  a DNA run, presence makes the freshness gates hard.
- **State conventions**: `.dna/` artifacts are committed into the feature
  branch; only caches and `*.tmp` are ignored.
- **Optional `linear` CLI dependency** documented with the existing manual
  fallback for closer detection.
- **Tests** (pytest) and **CI** (GitHub Actions) for scripts, the skill
  mirror, and the core gates.
