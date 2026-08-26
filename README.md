# Census-routed hybrid ILP for 1D-ARC

Per-instance solver for [1D-ARC](raw_data/onedarcraw/): a **train-grid census** chooses whether to induce rules over **color blocks (objects)** or over **pixels**, then [Popper](https://github.com/logic-and-learning-lab/popper) learns a program and we decode to pixels for scoring.

**Default path:** `hybrid_census` — if every training pair keeps the same count of bulky runs (length ≥ 2) and unit runs (length 1), use the object head (`out_block`); otherwise use the pixel head (`out`). Mode `block_primary` forces the object road only (ablation / debug).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ./popper

./scripts/smoke_solver.sh

python -m solver.cli \
  raw_data/onedarcraw/dataset/1d_denoising_1c/1d_denoising_1c_0.json \
  --mode hybrid_census --timeout 60 --out pred.json --work-dir work/demo
```

Full setup, flags, and eval: [docs/06-RUNNING.md](docs/06-RUNNING.md).  
Worked examples of both roads: [docs/03-TUTORIAL.md](docs/03-TUTORIAL.md).

## Docs

| Doc | Summary |
|-----|---------|
| [01 — Approach & Landscape](docs/01-ILP-1D-Method.md) | For researchers. Explains the 1D-ARC few-shot setting, compares pixel Relational Decomposition (Decom) and ILPAR to this repo, and states the claim: **routing** each instance to object-level or pixel-level induction via a name-free census—not “blocks always beat pixels.” |
| [02 — Method](docs/02-SOLVER_PLAN.md) | For method readers. Walks through `solve_hybrid`: the census gate, the object road (encode → induce → paint-verify → decode), the pixel road (Decom-style `out/3` encode → induce → soft-score → decode), and how modes `hybrid_census` vs `block_primary` differ. |
| [03 — Tutorial](docs/03-TUTORIAL.md) | For newcomers. Two end-to-end walks: a census-match flip task on the object road, and a census-fail structure-changing task on the pixel road, including grids, work-dir artifacts, and how to read the result JSON. |
| [04 — Evaluation](docs/04-EVALUATION.md) | For empirical readers. Protocol for the 54-task slice vs Decom, metric definitions, and the hybrid scoreboard (**19/54** @60 s, **44/54** @600 s, **45/54** @3600 s exact; +10 vs Decom at 10 min). |
| [05 — Repository Guide](docs/05-REPO_STRUCTURE.md) | For developers. Folder map, which module owns census / object encode / pixel encode / harness, dual-path dataflow, and “where to change what.” |
| [06 — Running](docs/06-RUNNING.md) | For practitioners. Install, CLI `--mode`, smoke scripts, parallel 54-task eval with `hybrid_census`, reading `summary.json`, and troubleshooting common failure reasons. |

Also: [solver package notes](solver/README.md) · [Decom paper (IJCAI 2025)](https://dl.acm.org/doi/10.24963/ijcai.2025/504) ([local PDF](docs/2408.12212v3.pdf))

## Eval (54-task slice)

Headline exact match (`hybrid_census` vs paper Decom on the same 54-task slice):

| Budget | Ours | Decom |
|--------|------|-------|
| 60 s | **19/54** | 32/54 |
| 600 s | **44/54** | 34/54 |
| 3600 s | **45/54** | 37/54 |

Provenance and per-category tables → [docs/04-EVALUATION.md](docs/04-EVALUATION.md).

```bash
JOBS=2 OUT=results/eval_local_600 \
  ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2
```

Object-only control: use mode `block_primary` instead. Details → [docs/06-RUNNING.md](docs/06-RUNNING.md).

## Layout

- `solver/` — census gate, object/pixel encode, bias, induce, verify, decode, CLI, harness
- `popper/` — vendored Popper
- `raw_data/onedarcraw/` — 1D-ARC JSON
- `scripts/` — smoke / eval wrappers
- `docs/` — numbered docs (`01`…`06`)
- `results/`, `work/` — generated eval/scratch
