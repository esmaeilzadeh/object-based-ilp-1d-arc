# 05 — Repository structure and file descriptions

**Reading order:** [01](01-ILP-1D-Method.md) → [02](02-SOLVER_PLAN.md) →
[03](03-CURRENT_METHOD.md) → [04](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md) →
**you are here**.

Map of this repo’s folders and important files. Method details live in
[03-CURRENT_METHOD.md](03-CURRENT_METHOD.md) and [02-SOLVER_PLAN.md](02-SOLVER_PLAN.md);
comparison numbers in
[04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md](04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md).

**Sole runtime path:** object-head / `block_primary` (`out_block/5` → paint decode).
Direction: [`.cursor/rules/block-level-only.mdc`](../.cursor/rules/block-level-only.mdc).

---

## Top-level tree

```text
object-based-ilp-1d-arc/
├── README.md                 # Setup, one-shot solve, eval entry points
├── LICENSE
├── requirements.txt          # Python deps (Clingo, janus-swi, NumPy, …)
├── pred.json                 # Optional CLI prediction dump (gitignored when present)
├── solver/                   # ★ Main package: encode → bias → induce → verify → decode
├── scripts/                  # Eval / smoke / stability shell wrappers
├── raw_data/onedarcraw/      # Vendored 1D-ARC JSON dataset (+ parser helpers)
├── popper/                   # Vendored Popper ILP system (editable install)
├── docs/                     # Numbered reading order: 01…05 (+ Decom PDF)
├── tests/fixtures/           # Hand fixtures for hard smokes (not full dataset)
├── results/                  # Eval outputs (gitignored)
├── work/                     # Scratch encode/induce dumps (gitignored)
├── .cursor/                  # Agent rules + plans (not product runtime)
├── .agents/                  # Optional agent skills
└── .venv/                    # Local virtualenv (gitignored)
```

---

## `solver/` — object-ILP pipeline (primary code)

Package notes: [solver/README.md](../solver/README.md).

```text
solver/
├── __init__.py          # Package version
├── __main__.py          # `python -m solver` → cli.main
├── cli.py               # Single-instance CLI
├── harness.py           # Multi-instance eval harness (block_primary only)
├── pipeline.py          # Orchestrates one instance end-to-end
├── encoder.py           # ARC JSON → lean typed BK + exs + geometry
├── bias_gen.py          # Mechanical per-instance bias_object.pl from BK/exs
├── predicates.py        # Frozen predicate inventory + typed roles
├── induce.py            # Popper child-process wrapper (honest timeout)
├── verify.py            # Paint-verify induced program on train
├── decode.py            # out_block facts → pixel grids
├── paper_score.py       # Soft (tp+tn)/total via do_test.pl (scoring only)
├── grid.py              # Flatten ARC grids; segment color runs/blocks
├── README.md
├── bias/
│   └── object.pl        # Static bias fallback/tests only (runtime uses generated)
├── lp/
│   └── do_test.pl       # Soft-score helper consulted by paper_score
└── tests/               # Unit tests for encoder/decode/grid/pipeline/…
```

| File | Role |
|---|---|
| `cli.py` | `python -m solver.cli path.json --timeout N [--out pred.json] [--work-dir D]` |
| `harness.py` | Discover `raw_data/.../dataset/*/*.json`, filter trials, write per-task JSON under `results/` |
| `pipeline.py` | `solve()`: encode → bias → induce → paint-verify → decode test → soft score → `SolveResult` |
| `encoder.py` | Segment runs; emit lean BK (`block`, typed `b*`/`s*`/`v*`/`r*`, gaps, `size_add`, …), pos/neg `out_block` exs, `block_geometry` for decode |
| `bias_gen.py` | Uniform mechanical bias: body preds/constants from **that instance’s** BK/exs only |
| `predicates.py` | Allowlists and type signatures (value / position / size / block_id / rank); no cross-role arithmetic |
| `induce.py` | Temp dir + Popper invoke; returns program text or timeout/exhaust failure |
| `verify.py` | Closed-world: decode program on train inputs; require exact gold outputs |
| `decode.py` | Bid+Off (+ Len, Color) → absolute paint; OOB/overlap fail |
| `paper_score.py` | Builds pixel `out/3` program from predicted grid for soft matrix only — **not** a pixel solver |
| `grid.py` | `flatten`, `segment_all_runs`, `segment_blocks` |

**Runtime artifacts** (under `--work-dir` or harness out): typically `bk.pl`, `exs.pl`,
`bias_object.pl`, Popper logs, predicted grid JSON. Soft `out/3` appears only in
scoring `test.pl`, never as the induction head.

---

## `scripts/` — eval and smoke wrappers

| Script | Purpose |
|---|---|
| `smoke_solver.sh` | Ensure venv + deps; run harness `--one` on a default denoising JSON |
| `smoke_block_hard.sh` | Three fixtures under `tests/fixtures/` (fill / move / hollow) via CLI |
| `run_solver_eval.sh` | Sequential harness: `MODE TIMEOUT TRIALS` (default `block_primary 60 0,1,2`) |
| `run_solver_eval_parallel.sh` | Parallel suite; env: `JOBS`, `DELAY`, `OUT`, `DATASET`, `OMP_NUM_THREADS=1` |
| `run_stability_protocol.sh` | `R` repeats @ JOBS=1 for stability of exact counts |

Example:

```bash
JOBS=4 OUT=results/eval_s6_60s ./scripts/run_solver_eval_parallel.sh block_primary 60 0,1,2
```

---

## `raw_data/onedarcraw/` — dataset

Vendored 1D-ARC (Xu et al. / LLM4ARC lineage). See package `README.md`.

```text
raw_data/onedarcraw/
├── README.md
├── __init__.py
├── decompo_parser.py          # Helpers related to Decom-style parsing (not our solver path)
└── dataset/
    ├── 1d_denoising_1c/
    ├── 1d_denoising_mc/
    ├── 1d_fill/
    ├── 1d_flip/
    ├── 1d_hollow/
    ├── 1d_mirror/
    ├── 1d_move_1p/ … 1d_move_dp/ …
    ├── 1d_padded_fill/
    ├── 1d_pcopy_1c/ 1d_pcopy_mc/
    ├── 1d_recolor_oe/ _cnt/ _cmp/
    └── 1d_scale_dp/
```

Each category folder holds instance JSON files, e.g.
`1d_flip/1d_flip_0.json` … `_2.json` (and often more). Standard paper slice:
**18 categories × trials `0,1,2` = 54 tasks**.

Instance shape (standard ARC): `train` (3 I/O pairs) + `test` (input; gold
output used only for scoring).

---

## `popper/` — vendored ILP engine

Upstream Popper (Logic & Learning Lab), installed editable: `pip install -e ./popper`.

```text
popper/
├── README.md, LICENSE, setup.py, solvers.md
├── popper.py                 # Entry
└── popper/                   # Core package
    ├── loop.py, generate.py, gen2.py, gen3.py
    ├── combine.py, maxsat.py, tester.py, bkcons.py, util.py
    └── lp/                   # alan.pl, test.pl, …
```

Our solver does **not** fork Popper logic for the claim; it supplies BK/exs/bias
and consumes the induced program.

---

## `docs/` — human documentation (read in number order)

| File | Contents |
|---|---|
| `01-ILP-1D-Method.md` | ILP / 1D-ARC landscape; why per-task scratch induction |
| `02-SOLVER_PLAN.md` | Living method plan / stage design |
| `03-CURRENT_METHOD.md` | As-built encode–induce–decode snapshot |
| `04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md` | Exact/soft scoreboard vs pixel Decom |
| `05-REPO_STRUCTURE.md` | This file — folders and file roles |
| `2408.12212v3.pdf` | Decom paper PDF (local copy; not in the numbered sequence) |

---

## `tests/` — fixtures (outside `solver/tests`)

```text
tests/fixtures/
├── fill_gap_with_shorter.json
├── hollow_largest_keep_rest.json
└── move_left_block_past_pivot.json
```

Used by `scripts/smoke_block_hard.sh`. Unit tests live under `solver/tests/`.

| Test module | Focus |
|---|---|
| `test_grid.py` | Flatten / segmentation |
| `test_encoder.py` | BK/exs emission |
| `test_decode.py` | Paint from `out_block` |
| `test_pipeline_object_only.py` | Object-only orchestration invariants |
| `test_paper_score.py` | Soft matrix helpers |
| `test_failure_reason.py` | Failure taxonomy / bias detail |

Run: `pytest solver/tests` (from repo root with venv active).

---

## `results/` and `work/` — generated (gitignored)

| Path | Typical use |
|---|---|
| `results/solver/` | Default harness / parallel-eval out dirs |
| `results/eval_s6_60s/` (etc.) | Named eval campaigns (`OUT=…`) |
| `results/logs/` | Optional log dumps |
| `work/` | Ad-hoc probe dirs (`encode/`, `popper/`, hand experiments) |

A typical eval tree:

```text
results/<campaign>/
├── block_primary/            # or flat per-task dirs depending on harness version
│   └── <category>_<trial>/   # pred JSON, maybe work artifacts
├── summary.json              # Aggregate exact / soft (when produced)
└── …
```

Do not commit these; recreate via scripts.

---

## `.cursor/` — agent workflow (not runtime)

```text
.cursor/
├── rules/                    # Always-on project rules (block-level-only, plan gates, …)
└── plans/                    # Saved design/publishing plans (e.g. plan-publishing-paper.md)
```

| Rule (examples) | Intent |
|---|---|
| `block-level-only.mdc` | Uniform mechanical language; no category BK; object-head only |
| `plan-approval-gate.mdc` | Plans propose-only until explicit implement approval |
| `plan-implementation.mdc` | Clean tree, new branch, one commit per step |
| `store-plans.mdc` | Write plans under `.cursor/plans/` |
| `spec-sync.mdc` | SPEC edits only after user confirmation |
| `build-locally.mdc` | Prefer local run/verify |

`.agents/skills/` — optional coding/process skills for agents; not imported by `solver`.

---

## Root config / env

| Path | Role |
|---|---|
| `requirements.txt` | Runtime Python deps for solver + Popper stack |
| `.gitignore` | Ignores `.venv/`, `work/`, `results/`, `pred.json`, caches |
| `.env` | Local secrets (e.g. API keys); **do not commit** |
| `.cursorignore` | Paths excluded from Cursor indexing |
| `LICENSE` | Project license |

---

## Data flow (one instance)

```text
raw_data/.../<task>.json
        │
        ▼
  encoder.encode_instance ──► bk.pl, exs.pl, block_geometry, typed_roles
        │
        ▼
  bias_gen.render_object_bias ──► bias_object.pl
        │
        ▼
  induce (Popper) ──► program text (out_block/5)  or failure_reason
        │
        ▼
  verify_object_on_train ──► accept / paint_verify_failed
        │
        ▼
  decode.apply_object_program (test) ──► predicted pixel row
        │
        ▼
  paper_score (optional soft) + harness JSON under results/
```

---

## External baselines (not in this tree by default)

Pixel Relational Decomposition (Hocquette & Cropper) programs and paper-style
evals typically live in a sibling checkout such as `../1d-arc/programs/relational/{60,120,600,3600}/`.
This repo’s `docs/04-COMPARISON-…` references those paths; they are **not** a solver
mode here.

---

## Quick “where do I…?”

| Task | Location |
|---|---|
| Change BK / head / bias generation | `solver/encoder.py`, `predicates.py`, `bias_gen.py` |
| Change decode / Bid+Off paint | `solver/decode.py`, `verify.py` |
| Change Popper invoke / timeout | `solver/induce.py` |
| Run one JSON | `python -m solver.cli …` or `scripts/smoke_solver.sh` |
| Run 54-task slice | `scripts/run_solver_eval_parallel.sh` |
| Read method claim | `docs/03-CURRENT_METHOD.md` |
| Read vs-Decom numbers | `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md` |
| Publishing / venue plan | `.cursor/plans/plan-publishing-paper.md` |
