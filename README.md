# Object-based ILP for 1D-ARC

Per-instance solver for 1D-ARC: encode grids as **color blocks (objects)**, induce rules with [Popper](https://github.com/logic-and-learning-lab/popper), decode to pixels for scoring.

**Sole path:** object-head / `block_primary` only. No pixel-head ILP, dual induction, or trivial closed-form stages.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./popper

./scripts/smoke_solver.sh

python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --timeout 60 --out pred.json --work-dir work/demo
```

Full setup, flags, and eval: [docs/06-RUNNING.md](docs/06-RUNNING.md).  
Walkthrough of what that run produces: [docs/03-TUTORIAL.md](docs/03-TUTORIAL.md).

## Docs

| Doc | Audience | Content |
|-----|----------|---------|
| [01 — Approach & Landscape](docs/01-ILP-1D-Method.md) | Researchers | Why blocks vs pixels; positioning vs Decom and ILPAR |
| [02 — Method](docs/02-SOLVER_PLAN.md) | Method readers | Encode → induce → verify → decode pipeline |
| [03 — Tutorial](docs/03-TUTORIAL.md) | New users | One full example from pixels to learned rule |
| [04 — Evaluation](docs/04-EVALUATION.md) | Empirical readers | Scoreboard vs pixel Relational Decomposition |
| [05 — Repository Guide](docs/05-REPO_STRUCTURE.md) | Developers | Folder map, data flow, where to change what |
| [06 — Running](docs/06-RUNNING.md) | Practitioners | Setup, CLI, smoke, 54-task eval |

Also: [block-level-only direction](.cursor/rules/block-level-only.mdc) · [solver package notes](solver/README.md) · [Decom paper (IJCAI 2025)](https://dl.acm.org/doi/10.24963/ijcai.2025/504) ([local PDF](docs/2408.12212v3.pdf))

## Eval (54-task slice)

```bash
JOBS=2 OUT=results/eval_local_120 \
  ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

Only mode: `block_primary`. Details → [docs/06-RUNNING.md](docs/06-RUNNING.md).

## Layout

- `solver/` — encode, bias, induce, verify, decode, harness
- `popper/` — vendored Popper
- `raw_data/onedarcraw/` — 1D-ARC JSON
- `scripts/` — smoke / eval wrappers
- `docs/` — numbered docs (`01`…`06`)
- `results/`, `work/` — generated eval/scratch
