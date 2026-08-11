# 05 — Repository Guide

A map of the codebase: where things live, what they do, and how to extend them.

## Top-level layout

```
object-based-ilp-1d-arc/
├── solver/              # Main package: encode → bias → induce → verify → decode
├── scripts/             # Shell wrappers for eval and smoke tests
├── raw_data/onedarcraw/ # Vendored 1D-ARC JSON dataset
├── popper/              # Vendored Popper ILP engine (editable install)
├── docs/                # This documentation set
├── tests/fixtures/      # Hand-written fixtures for smoke tests
├── results/             # Eval outputs (gitignored)
├── work/                # Scratch encode/induce dumps (gitignored)
├── README.md            # Quick start
└── requirements.txt     # Python dependencies
```

## The `solver/` package

This is the core pipeline. Each module handles one stage:

| File | What it does |
|------|--------------|
| `cli.py` | Command-line entry point: `python -m solver.cli <task.json> --timeout N` |
| `harness.py` | Multi-instance eval: discovers JSON files, runs `solve()` on each, writes results |
| `pipeline.py` | Orchestrates one instance: encode → bias → induce → verify → decode → score |
| `encoder.py` | Segments grids into maximal runs, writes `bk.pl`, `exs_object.pl`, `block_geometry` |
| `bias_gen.py` | Generates `bias_object.pl` from the instance’s own facts (no hand-tuning) |
| `predicates.py` | Frozen inventory of predicates and their type signatures |
| `induce.py` | Runs Popper in a child process, returns the learned program or failure reason |
| `verify.py` | Paint-verify: checks that the learned program reproduces all training outputs exactly |
| `decode.py` | Converts `out_block` atoms to pixel grids using `block_geometry` |
| `paper_score.py` | Computes soft accuracy `(TP+TN)/total` via a Prolog helper |
| `grid.py` | Utilities: flatten grids, segment runs |

### How data flows through the pipeline

```
raw_data/.../<task>.json
        ↓
  encoder.encode_instance
        ↓
  bk.pl, exs_object.pl, bias_object.pl, block_geometry
        ↓
  induce (Popper)
        ↓
  program.pl  (or failure: timeout / exhausted / error)
        ↓
  verify_object_on_train
        ↓
  accept  →  decode test  →  predicted pixels
  reject  →  fallback_identity (return test input unchanged)
        ↓
  paper_score (soft accuracy) + harness JSON result
```

### Where to change what

| Goal | Files to edit |
|------|---------------|
| Add a new background predicate | `predicates.py` (declare it), `encoder.py` (emit it), `bias_gen.py` (allow it in bias) |
| Change the head predicate | `encoder.py` (generate examples), `decode.py` (paint it), `verify.py` (check it) |
| Change Popper timeout behavior | `induce.py` |
| Change acceptance criteria | `verify.py` |
| Add a new eval script | `scripts/` + `harness.py` |

## The `scripts/` directory

| Script | Purpose |
|--------|---------|
| `smoke_solver.sh` | Quick check: solve one denoising task end-to-end |
| `smoke_block_hard.sh` | Solve three hand-written fixtures (fill, move, hollow) |
| `run_solver_eval.sh` | Sequential eval: `MODE TIMEOUT TRIALS` |
| `run_solver_eval_parallel.sh` | Parallel eval: set `JOBS=N`, `OUT=results/<name>` |
| `run_stability_protocol.sh` | Repeat eval multiple times to check variance |

Example:

```bash
JOBS=2 OUT=results/my_eval ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

## The `raw_data/onedarcraw/` directory

Vendored 1D-ARC dataset. Each category is a folder of JSON files:

```
raw_data/onedarcraw/dataset/
├── 1d_denoising_1c/
│   ├── 1d_denoising_1c_0.json
│   ├── 1d_denoising_1c_1.json
│   └── ...
├── 1d_flip/
├── 1d_hollow/
├── ...
```

Each JSON has `train` (3 input/output pairs) and `test` (1 input; gold output used only for scoring).

## The `popper/` directory

Vendored Popper ILP system. Install with `pip install -e ./popper`. We do not modify Popper’s logic; we only supply `bk.pl`, `exs_object.pl`, and `bias_object.pl` and consume the learned program.

## The `docs/` directory

| File | Audience | Content |
|------|----------|---------|
| `01-ILP-1D-Method.md` | Researchers | Why blocks vs pixels, positioning vs Decom/ILPAR |
| `02-SOLVER_PLAN.md` | Method readers | The encode–induce–decode pipeline |
| `03-TUTORIAL.md` | New users | Walkthrough of one full example |
| `04-EVALUATION.md` | Empirical readers | Scoreboard vs Decom, per-category breakdown |
| `05-REPO_STRUCTURE.md` | Developers | This file |
| `06-RUNNING.md` | Practitioners | Setup, CLI, eval harness, troubleshooting |

## The `tests/` directory

- `tests/fixtures/` — hand-written JSON fixtures for smoke tests
- `solver/tests/` — unit tests for encoder, decode, pipeline, etc.

Run tests: `pytest solver/tests`

## Generated directories (gitignored)

| Path | Content |
|------|---------|
| `results/` | Eval outputs, summaries, logs |
| `work/` | Scratch encode/induce dumps (e.g., `work/demo/` for CLI inspection) |

Do not commit these.

## Agent workflow files (`.cursor/`, `.agents/`)

- `.cursor/rules/` — Project rules (e.g., block-level-only direction, plan approval gates)
- `.cursor/plans/` — Saved design and publishing plans
- `.agents/skills/` — Optional agent skills

These are not part of the runtime solver.
