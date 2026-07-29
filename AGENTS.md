# AGENTS.md

## Cursor Cloud specific instructions

This repo is a per-instance ILP solver for 1D-ARC (Python + Popper). It is a
CLI/library, not a web service — there is no server to start.

### Environment
- A Python venv lives at `.venv` (created by the startup update script). Activate
  it before running anything: `source .venv/bin/activate`.
- Requires **SWI-Prolog >= 9.1.12** on `PATH` (for `janus-swi`). The default
  Ubuntu `swi-prolog` (9.0.x) is too old; the newer build comes from the official
  `ppa:swi-prolog/stable` and is baked into the VM snapshot. If `swipl --version`
  reports < 9.1.12, `janus-swi` will fail to build/import.
- `clingo` is installed via pip (no system package needed).
- Popper is vendored under `popper/` and installed editable (`pip install -e ./popper`).

### Run the solver (hello world)
```bash
source .venv/bin/activate
python -m solver.cli raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 90 --out pred.json --work-dir work/smoke
```
A correct solve reports `"verified_train": true` and writes `predicted_grid` to
`pred.json`. Convenience wrapper: `./scripts/smoke_solver.sh`.

### Tests
```bash
source .venv/bin/activate
python -m pytest -q
```
`pytest` is a dev-only dependency (not in `requirements.txt`); the update script
installs it into the venv.

### Ablation harness
`./scripts/run_solver_eval.sh <mode> <timeout> <trials>` runs Popper over many
dataset instances and is **slow** (minutes to hours). Use `LIMIT=` and a small
trial list for quick checks, e.g. `LIMIT=1 ./scripts/run_solver_eval.sh dual 30 0`.

### Notes
- No linter is configured in the repo.
- Per-instance solves spawn Popper/Prolog subprocesses; the `--timeout` is a soft
  budget for the ILP ladder, so wall-clock can exceed it slightly.
- Scratch output dirs (`work/`, `results/`, `programs/`, `logs/`, `pred.json`)
  are git-ignored.
