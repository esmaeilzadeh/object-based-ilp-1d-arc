# Object-based ILP for 1D-ARC

Per-instance solver for 1D-ARC JSON: encode grids as **color blocks (objects)**,
induce `out_block/5` with [Popper](https://github.com/logic-and-learning-lab/popper),
decode to pixels for scoring.

**Sole path:** object-head / `block_primary` only. No pixel-head ILP, dual
induction, or trivial closed-form stages.

**Docs (read in order):**

| # | Doc | What it is |
|---|-----|------------|
| 1 | [ILP landscape](docs/01-ILP-1D-Method.md) | Where this work sits among ILP/1D-ARC methods; why we induce per task from scratch (not curriculum/transfer) |
| 2 | [Method plan](docs/02-SOLVER_PLAN.md) | Designed method: thesis, stages, allowed/forbidden paths, eval protocol, optional extensions |
| 3 | [Current method (as-built)](docs/03-CURRENT_METHOD.md) | What the code does *now*: pipeline, how to run, failure reasons, non-goals (trust this if plan and tip drift) |
| 4 | [vs Decom comparison](docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) | Exact/soft scoreboard vs pixel Relational Decomposition on the same 54-task slice |
| 5 | [Repo map](docs/05-REPO_STRUCTURE.md) | Folder/file roles and “where do I…?” pointers |

Also: [block-level-only direction](.cursor/rules/block-level-only.mdc) (mandatory research constraints) · [solver package notes](solver/README.md) · [Decom paper PDF](docs/2408.12212v3.pdf) (reference appendix)

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

Full folder/file map: [docs/05-REPO_STRUCTURE.md](docs/05-REPO_STRUCTURE.md).

- `solver/` — lean encode, mechanical object bias, induce, verify, decode, harness
- `popper/` — vendored Popper
- `raw_data/onedarcraw/` — 1D-ARC JSON (+ external Decom baselines)
- `scripts/` — eval / smoke wrappers
- `docs/` — method, comparison, structure
- `results/`, `work/` — generated eval/scratch (gitignored)
