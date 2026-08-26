# 05 — Repository Guide

A map of the codebase as it exists today: where the **census-routed hybrid** lives, what each module does, and where to change things.

## Top-level layout

```
object-based-ilp-1d-arc/
├── solver/              # Census gate, object/pixel roads, CLI, harness
├── scripts/             # Smoke + eval wrappers
├── raw_data/onedarcraw/ # Vendored 1D-ARC JSON (+ Decom parser helpers)
├── popper/              # Vendored Popper ILP engine (editable install)
├── docs/                # Numbered human docs (01…06)
├── tests/fixtures/      # Hand-written smoke fixtures
├── results/             # Eval outputs (gitignored)
├── work/                # Scratch encode/induce dumps (gitignored)
├── archive/             # Retired experiments (e.g. old two-head hybrid)
├── README.md            # Quick start + doc summaries
└── requirements.txt
```

`archive/hybrid-two-head/` is **not** the current system. Today’s match road is a single `out_block/5` object head (same as `solve`), not parallel bulky/unit heads.

## The `solver/` package

| File | What it does |
|------|----------------|
| `cli.py` | Single-instance entry: `--mode hybrid_census` (default) or `block_primary` |
| `harness.py` | Batch eval; same modes; writes per-task JSON + `summary.json` |
| `pipeline.py` | `solve` (object only) and `solve_hybrid` (census → object or pixel) |
| `census.py` | `census_match`: bulky/unit run-count gate on train grids |
| `encoder.py` | Object segmentation, `bk.pl`, `exs_object.pl`, `block_geometry` |
| `bias_gen.py` | Mechanical object bias from that instance’s BK/exs |
| `predicates.py` | Frozen object predicate inventory / types |
| `pixel_encode.py` | Decom-style pixel BK/exs/bias for `out/3` |
| `induce.py` | Popper child process, timeouts, literal caps |
| `verify.py` | Object paint-verify on train |
| `decode.py` | Paint `out_block` or apply pixel programs |
| `paper_score.py` | Soft accuracy helper |
| `grid.py` | Flatten grids, segment runs |
| `run_meta.py` | Eval provenance metadata |

### Dual-path dataflow

```
JSON instance
      │
      ▼
census_match(train)?
      │
      ├─ true ──► encode object ──► Popper out_block ──► paint-verify
      │              │                                    │
      │              └──────── decode test ◄──────────────┘
      │
      └─ false ─► encode pixel ──► Popper out/3 ──► soft-score / apply
                         │
                         └──────── predicted pixels
      │
      ▼
exact + soft vs gold  (harness)
```

### Where to change what

| Goal | Start here |
|------|------------|
| Change the routing rule | `census.py` (keep it name-free and mechanical) |
| Add/change object BK facts | `predicates.py` → `encoder.py` → `bias_gen.py` |
| Change object head / painting | `encoder.py`, `decode.py`, `verify.py` |
| Change pixel encoding | `pixel_encode.py` (+ Decom templates under `raw_data/onedarcraw/`) |
| Timeout / literal budgets | `induce.py`, constants in `pipeline.py` / `bias_gen.py` |
| CLI or batch modes | `cli.py`, `harness.py` (`MODES`) |
| Soft metric | `paper_score.py` |

## The `scripts/` directory

| Script | Purpose |
|--------|---------|
| `smoke_solver.sh` | One dataset JSON via harness `hybrid_census` |
| `smoke_block_hard.sh` | Three fixtures via CLI `hybrid_census` |
| `run_solver_eval.sh` | Sequential eval: `MODE TIMEOUT TRIALS` |
| `run_solver_eval_parallel.sh` | Parallel eval: set `JOBS`, `OUT` |
| `run_stability_protocol.sh` | Repeat eval to check variance |

Example:

```bash
JOBS=2 OUT=results/my_eval \
  ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2
```

## The dataset

```
raw_data/onedarcraw/dataset/
├── 1d_denoising_1c/
├── 1d_flip/
├── 1d_pcopy_1c/
└── ...
```

Each file is typically three train pairs + one test. The hybrid **does not** branch on these folder names; only on train-grid geometry.

## Docs map

| Doc | Audience |
|-----|----------|
| `01-ILP-1D-Method.md` | Why hybrid routing vs Decom / ILPAR |
| `02-SOLVER_PLAN.md` | Method: census + both roads |
| `03-TUTORIAL.md` | Flip (object) + pcopy (pixel) walkthroughs |
| `04-EVALUATION.md` | Protocol + hybrid vs Decom scoreboard |
| `05-REPO_STRUCTURE.md` | This file |
| `06-RUNNING.md` | Install, CLI, eval, troubleshooting |

## Agent / direction notes

Project rules under `.cursor/rules/` describe the allowed scientific claim (block representation plus Decom-family size arith on the object road, census-routed hybrid as the /54 system, no task-name vocabulary switches, no answer-leaking BK, no marker/mirror hacks). Keep docs and code aligned with that claim.
