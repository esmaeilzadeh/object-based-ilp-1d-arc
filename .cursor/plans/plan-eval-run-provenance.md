# Plan: Eval run provenance (trackable results)

## Goal

Make every solver/eval run **referable**: bind scores to `git` SHA/branch, config,
host, and timestamp. Stop treating `results/` as disposable-only. Keep comparison
**reports** (`docs/04-COMPARISON-…`) unchanged.

## Non-goals

- Do **not** edit `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md` or rewrite
  historical scoreboards.
- Do **not** invent missing SHAs for old remote runs; mark historical manifests
  `provenance: best_effort` / `git_sha: null` when unknown.

## Steps

1. **Backup** current `work/` and `results/` off-repo (compressed archive under
   `../_backups/object-based-ilp-1d-arc/`). Leave in-repo copies in place.
2. **Branch** `cursor/eval-run-provenance` from current `main`.
3. **`.gitignore`**: remove `work/` and `results/` entries only (leave other
   ignores; do not add/change a `reports/` policy).
4. **Code**: add `solver/run_meta.py` (`collect_run_meta`) writing:
   - `git_sha`, `git_branch`, `git_dirty`, `git_describe` (best-effort)
   - `started_at` / `finished_at` (UTC ISO)
   - `hostname`, `platform`
   - `mode`, `timeout`, `jobs`, `trials`, `dataset`, `out`
   Stamp into:
   - `results/.../run_manifest.json` (campaign-level)
   - `summary.json` field `run_meta`
   - per-task result JSON field `run_meta` (sha + mode + timeout at least)
5. **Wire** `solver/harness.py` + `scripts/run_solver_eval_parallel.sh` (+
   sequential path via harness).
6. **Registry**: add `results/RUN_REGISTRY.md` listing known local campaigns and
   how to cite a run (path + sha + summary). Best-effort manifests beside
   existing `summary.json` files.
7. **Docs**: short subsection in `docs/06-RUNNING.md` only (how provenance is
   recorded). No changes to comparison report docs.
8. **Tests**: unit test for `collect_run_meta` shape / keys.
9. **Skill** (personal, cross-project):
   `~/.cursor/skills/eval-run-provenance/SKILL.md` — reusable protocol for CS
   experiment recording (manifest schema, backup, do-not-gitignore results,
   cite SHA+artifact).
10. **Commits** (one per step cluster): backup note N/A; then gitignore; then
    code+scripts+tests; then registry+06; skill is outside repo (no commit) or
    copy under `.agents/skills/` if we want repo-visible too — **both**: personal
    skill for other projects + project `.agents/skills/eval-run-provenance/`
    for this repo.

## Done when

- Off-repo backup archive exists and is readable.
- `work/` / `results/` no longer gitignored.
- A smoke/harness summarize path writes `run_manifest.json` + `run_meta` on
  summary.
- Skill installed for reuse on other CS experiments.
- Comparison report files untouched.
