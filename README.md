# Object-based ILP for 1D-ARC

Generic per-instance solver for 1D-ARC JSON problems. Encodes each grid as
**pixels + color blocks**, then learns an input→output logic program with
[Popper](https://github.com/logic-and-learning-lab/popper) via a cheap-first
ladder (trivial checks → block-only ILP → dual ILP).

Method details: [docs/SOLVER_PLAN.md](docs/SOLVER_PLAN.md).  
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
```

Or: `./scripts/smoke_solver.sh`

## Ablation harness

```bash
# modes: pixel_only | block_only | dual | dual_no_agg | dual_no_ladder | dual_full
./scripts/run_solver_eval.sh dual 60 0,1,2
# LIMIT=5 ./scripts/run_solver_eval.sh dual 60 0
```

## Layout

- `solver/` — encode, bias, induce, verify, ladder CLI, harness
- `raw_data/onedarcraw/` — 1D-ARC JSON dataset
- `popper/` — vendored Popper
- `docs/` — method plans
