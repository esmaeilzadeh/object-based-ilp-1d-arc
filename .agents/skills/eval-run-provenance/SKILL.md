---
name: eval-run-provenance
description: >-
  Record and cite CS experiment / eval runs with solid provenance (git SHA,
  branch, config, host, timestamps, artifact paths). Use when running evals,
  benchmarks, ablations, or when the user asks how to track, backup, or refer
  to experiment results across machines.
disable-model-invocation: false
---

# Eval / experiment run provenance

## Goal

Every meaningful run must be **referable**: a reviewer can go from a reported
score to (1) code SHA, (2) config, (3) artifact files. Do not report scores
alone when artifacts or SHAs are missing — say so explicitly.

## Mandatory protocol (any CS project)

1. **Do not gitignore result trees** you will cite (or mirror slim copies under
   `artifacts/evals/<run-id>/`). Scratch dumps may stay ignored; **summaries and
   manifests must be versioned or released**.
2. **Before a long run**, note: branch, `git rev-parse HEAD`, dirty or clean,
   timeout/jobs/seeds, host (`hostname`, CPU/RAM), output directory.
3. **At run start**, write `run_manifest.json` (`eval-run-meta/v1`) with at least:
   - `git_sha`, `git_branch`, `git_dirty`
   - `started_at` (UTC ISO)
   - `hostname`, `platform`
   - knobs: mode/timeout/jobs/trials/seeds/dataset/`out`
4. **At run end**, set `finished_at`; attach the same object as `run_meta` on
   `summary.json`. Per-task rows get a slim `run_meta` (sha + mode + timeout).
5. **Backup** large trees off-repo (tar.gz) *and* keep citable summaries in git
   or a release tarball. Never assume a remote machine auto-pushed results.
6. **Cite** as: `path + git_sha + exact metric (e.g. 40/54)`. If `git_sha` is
   null (historical), label `provenance: best_effort_historical` — do not invent
   a SHA.
7. When the user asks “what did run X score?”, lead with **provenance strength**:
   committed artifact / local-only / prose-only — then the number.

## Schema (`eval-run-meta/v1`)

```json
{
  "schema": "eval-run-meta/v1",
  "started_at": "2026-08-11T13:44:11+00:00",
  "finished_at": "2026-08-11T14:10:00+00:00",
  "git_sha": "…",
  "git_branch": "…",
  "git_dirty": false,
  "git_describe": "…",
  "hostname": "…",
  "platform": "…",
  "mode": "…",
  "timeout": 60,
  "jobs": 2,
  "trials": "0,1,2",
  "dataset": "…",
  "out": "results/…"
}
```

## This repo (object-based-ilp-1d-arc)

- Collector: `solver/run_meta.py`
- Wired from: `solver/harness.py`, `scripts/run_solver_eval_parallel.sh`
- Index: `results/RUN_REGISTRY.md`
- Docs: `docs/06-RUNNING.md` § provenance
- Comparison narrative in `docs/04-EVALUATION.md` is **not** the artifact store;
  do not silently rewrite report numbers when fixing provenance.

## Anti-patterns

- Reporting soft/exact from chat memory without a path + SHA
- Assuming `results/` on a Cloud Agent was pushed because the code was
- Inventing SHAs for old runs
- Overwriting campaign `run_manifest.json` from parallel workers

