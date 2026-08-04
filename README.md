# Object-based ILP for 1D-ARC

Generic per-instance solver for 1D-ARC JSON problems. Research default:
**block-primary** — encode grids as color blocks, induce
`out_block(Ex, Bid, Off, Len, Color)` with one mechanical object bias, then
decode to pixels for scoring.

Direction (mandatory): [`.cursor/rules/block-level-only.mdc`](.cursor/rules/block-level-only.mdc).  
As-built method: [docs/CURRENT_METHOD.md](docs/CURRENT_METHOD.md).  
Historical / dual-ladder plan: [docs/SOLVER_PLAN.md](docs/SOLVER_PLAN.md).  
Package notes: [solver/README.md](solver/README.md).

## Setup

Requires Python 3.10+, SWI-Prolog (for `janus-swi`), and Clingo.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./popper
```

## Solve (research default)

```bash
python -m solver.harness --mode block_primary --timeout 60 --one \
  raw_data/onedarcraw/dataset/1d_recoloring_bmc/1d_recoloring_bmc_0.json
```

Or parallel / batch:

```bash
./scripts/run_solver_eval.sh block_primary 60 0,1,2
# JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

### Legacy CLI

`python -m solver.cli …` still runs the **legacy dual ladder** by default
(trivials → block/object/pixel/dual). Prefer `block_primary` for the block-lift
eval. Smoke: `./scripts/smoke_solver.sh` (CLI / dual path).

## Ablation harness

```bash
# Research default
./scripts/run_solver_eval.sh block_primary 60 0,1,2

# Pixel / dual ablations (not the block-lift claim)
# modes: pixel_only | block_only | block_primary | dual | dual_no_agg | dual_no_ladder | dual_full
./scripts/run_solver_eval.sh pixel_only 60 0,1,2
LIMIT=5 ./scripts/run_solver_eval.sh dual 60 0
```

## Layout

- `solver/` — encode, mechanical bias, induce, verify, decode, harness
- `raw_data/onedarcraw/` — 1D-ARC JSON dataset
- `popper/` — vendored Popper
- `docs/` — CURRENT_METHOD, SOLVER_PLAN, ILP-1D-Method
