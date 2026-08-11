# Eval run registry

Campaign index for **local** `results/` trees. Each campaign should have:

- `summary.json` — aggregate exact/soft
- `run_manifest.json` — provenance (`eval-run-meta/v1`)
- per-task `*.json` — preferably with `run_meta`

Cite a run as: **path + `git_sha` (from manifest) + exact n/N**.
Historical rows may have `git_sha: null` (`provenance: best_effort_historical`).

Off-repo backup (pre-tracking):
`../_backups/object-based-ilp-1d-arc/work-results-20260811T134411Z.tar.gz`

| Campaign dir | mode | timeout | jobs | n | exact | soft | git_sha |
|---|---|---|---|---|---|---|---|
| `results/eval_s6_60s/block_primary` | block_primary | 60 | 4 | 54 | 25/54 | 0.463 | `null` |
| `results/solver/baseline_block_primary_120/block_primary` | block_primary | 120 | 4 | 54 | 37/54 | 0.685 | `null` |
| `results/solver_block_primary/block_primary` | block_primary | 300 | None | 9 | 0/9 | 0.000 | `null` |
| `results/solver_block_unit/block_primary` | block_primary | 600 | None | 3 | 3/3 | 1.000 | `null` |
| `results/solver_lean_object/block_primary` | block_primary | 600 | None | 9 | 4/9 | 0.444 | `null` |
| `results/solver_marker_fix/dual` | dual | 600 | None | 9 | 4/9 | 0.444 | `null` |
| `results/solver_t345/block_primary` | block_primary | 120 | 4 | 54 | 39/54 | 0.722 | `null` |

## How new runs are stamped

`solver/run_meta.collect_run_meta` → harness / `run_solver_eval_parallel.sh`
write `run_manifest.json` and attach `run_meta` on `summary.json` (and slim
`run_meta` on per-task rows).

Do **not** treat prose in `docs/04-COMPARISON-…` as a substitute for these
artifacts; that doc is the scoreboard narrative and is left unchanged here.

