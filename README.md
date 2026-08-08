# Object-based ILP for 1D-ARC

Per-instance solver for 1D-ARC JSON: encode grids as **color blocks (objects)**,
induce `out_block/5` with [Popper](https://github.com/logic-and-learning-lab/popper),
decode to pixels for scoring.

**Sole path:** object-head / `block_primary` only. No pixel-head ILP, dual
induction, or trivial closed-form stages.

**Docs (read in order):**

1. **[ILP landscape](docs/01-ILP-1D-Method.md)** — Where this work sits among ILP /
   1D-ARC methods (pixel Decom, ILPAR, …). Explains the block-lift claim and
   **why we induce each trial from scratch** (few-shot program synthesis), not
   curriculum / transfer from simpler tasks.

2. **[Method plan](docs/02-SOLVER_PLAN.md)** — Living **design** doc: thesis,
   stages (representation → induction → paint-verify → eval), what is
   allowed/forbidden, optional extensions (e.g. cross-task library). Use when
   deciding *what the solver should be*; may look slightly ahead of the tip.

3. **[Current method (as-built)](docs/03-CURRENT_METHOD.md)** — Short
   **implementation** snapshot: claim, real `block_primary` pipeline, failure
   reasons, non-goals, how to run. Use for “what ships right now.” If plan and
   code disagree, **trust this** for behavior.

4. **[vs Decom comparison](docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md)** —
   Exact/soft scoreboard vs pixel Relational Decomposition on the same 54-task
   slice (protocol alignment, budgets, per-category strengths).

5. **[Repo map](docs/05-REPO_STRUCTURE.md)** — Folder/file roles, scripts table,
   and “where do I…?” pointers into the codebase.

6. **[Running guide](docs/06-RUNNING.md)** — Practical runbook: setup, CLI/harness
   flags, smoke scripts, sequential/parallel eval, stability protocol, result
   layout, troubleshooting — with concrete examples.

Also: [block-level-only direction](.cursor/rules/block-level-only.mdc) (mandatory
research constraints) · [solver package notes](solver/README.md) ·
[Decom / Relational Decomposition (IJCAI 2025)](https://dl.acm.org/doi/10.24963/ijcai.2025/504)
(Hocquette & Cropper; [local PDF](docs/2408.12212v3.pdf))

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

Full flags, scripts, and result layout: [docs/06-RUNNING.md](docs/06-RUNNING.md).

## Eval (first-3 trials)

```bash
./scripts/run_solver_eval.sh block_primary 60 0,1,2
# JOBS=4 OUT=results/eval_local_120 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

Only mode: `block_primary`. Details → [docs/06-RUNNING.md](docs/06-RUNNING.md).

## Layout

Full folder/file map: [docs/05-REPO_STRUCTURE.md](docs/05-REPO_STRUCTURE.md).

- `solver/` — lean encode, mechanical object bias, induce, verify, decode, harness
- `popper/` — vendored Popper
- `raw_data/onedarcraw/` — 1D-ARC JSON (+ external Decom baselines)
- `scripts/` — eval / smoke wrappers
- `docs/` — numbered method + running docs (`01`…`06`)
- `results/`, `work/` — generated eval/scratch (gitignored)
