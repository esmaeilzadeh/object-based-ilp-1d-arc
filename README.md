# Object-based ILP for 1D-ARC

Per-instance solver for 1D-ARC JSON: encode grids as **color blocks (objects)**,
induce `out_block/5` with [Popper](https://github.com/logic-and-learning-lab/popper),
decode to pixels for scoring.

**Sole path:** object-head / `block_primary` only. No pixel-head ILP, dual
induction, or trivial closed-form stages.

As-built: [docs/CURRENT_METHOD.md](docs/CURRENT_METHOD.md).  
Method plan: [docs/SOLVER_PLAN.md](docs/SOLVER_PLAN.md).  
ILP landscape: [docs/ILP-1D-Method.md](docs/ILP-1D-Method.md).  
Direction: [`.cursor/rules/block-level-only.mdc`](.cursor/rules/block-level-only.mdc).  
Package notes: [solver/README.md](solver/README.md).

## Setup

Requires Python 3.10+, SWI-Prolog (for `janus-swi`), and Clingo.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./popper
```

## Solve one instance

```bash
python -m solver.cli raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json

# or harness
python -m solver.harness --mode block_primary --timeout 60 --one \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json

./scripts/smoke_solver.sh
```

## Eval (first-3 trials)

```bash
./scripts/run_solver_eval.sh block_primary 60 0,1,2
# JOBS=4 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

Only mode: `block_primary`.

## Layout

- `solver/` — lean encode, mechanical object bias, induce, verify, decode, harness
- `popper/` — vendored Popper
- `raw_data/onedarcraw/` — 1D-ARC JSON (+ external Decom baselines)
