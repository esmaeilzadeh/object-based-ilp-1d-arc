# 04 — Evaluation: Hybrid vs Relational Decomposition

This document describes how we evaluate the **census-routed hybrid** solver (`hybrid_census`) against the pixel-level Relational Decomposition (Decom) baseline from Hocquette & Cropper (IJCAI 2025).

Both systems use the same ILP engine family (Popper) and the same 54-task slice (18 categories × trials `0,1,2`). The difference is the **system**: Decom is pixels-only; ours **routes** each instance to object-head or pixel-head induction via a train-grid census (see [02 — Method](02-SOLVER_PLAN.md)).

> **Numbers pending.** Exact / soft figures for **Ours** below are placeholders (`TBD`) until the current experiment finishes. Qualitatively, at the **10-minute (600 s)** budget the hybrid system already shows a **clear performance jump** relative to the older single-representation / block-only scoreboard narrative. Fill tables from `results/.../hybrid_census/summary.json` + git SHA when ready.

## What “Ours” means

| Label | Meaning |
|-------|---------|
| **Ours (hybrid_census)** | Default system: `solve_hybrid` with census routing |
| **Ours (block_primary)** | Ablation: object road only (no pixel road). Not the headline claim |
| **Decom** | Published pixel Relational Decomposition results on the same slice |

Do **not** report a pixel-road solve as a “block-only win.” Use `failure_detail.road` when discussing which path succeeded.

## Headline scoreboard (exact match /54)

| Budget | Ours (hybrid_census) | Decom (pixel, paper) | Margin |
|--------|----------------------|----------------------|--------|
| **60 s** | TBD/54 | 32/54 | +TBD |
| **120 s** | TBD/54 | 30/54 | +TBD |
| **600 s (10 min)** | TBD/54 | 34/54 | +TBD |
| **3600 s** | TBD/54 | 37/54 | +TBD |

**Pending finding (qualitative):** at **600 s**, hybrid shows a clear jump; replace this sentence with the measured TBD/54 and margin after the experiment lands.

## Soft accuracy (%)

Soft accuracy is `(TP + TN) / (TP + FN + TN + FP)` over **each** Decom-style `pos(out(...))` / `neg(out(...))` label (not per example id, and not raw pixel Hamming). Near-miss grids can therefore score high because of many true-negative color labels. Implementation: `solver/lp/do_test.pl` + `solver/paper_score.py`; rescored artifacts stamp `soft_definition: "per_label_out_v1"`.

| Budget | Ours (hybrid_census) | Decom (paper) |
|--------|----------------------|---------------|
| 60 s | TBD | 59.3 |
| 120 s | TBD | 55.6 |
| 600 s | TBD | 63.0 |
| 3600 s | TBD | 68.5 |

**Caveat:** Soft is inflated by true negatives (each cell contributes one positive and many negative color labels). Prefer **exact /54** as the headline. Soft values written before `per_label_out_v1` are **not comparable** (they collapsed to exact-or-nothing per test id).

## Protocol alignment

- **Slice:** first 3 instances of each of 18 categories → 54 tasks.
- **Learning:** from scratch per trial — no curriculum, no cross-task transfer.
- **Metrics:** exact match on the test grid; soft accuracy as above.
- **Mode for headline:** `hybrid_census`.
- **Hardware note:** Decom’s paper used a single Xeon Gold 6138 core, serial. Our parallel evals typically use `JOBS=2` on a small multi-vCPU host; parallelism speeds the suite wall-clock but does not lengthen any single task’s timeout.

Example command (fill `OUT` when you run the campaign):

```bash
JOBS=2 OUT=results/eval_hybrid_600s \
  ./scripts/run_solver_eval_parallel.sh hybrid_census 600 0,1,2
```

## Why routing helps (qualitative)

Neither representation wins everywhere:

| Situation | Typical road | Why |
|-----------|--------------|-----|
| Train I/O preserve bulky/unit **counts** (move, flip, many recolors, …) | Object (`out_block`) | First-class blocks, sizes, “largest,” gaps |
| Train I/O change run inventory (many `pcopy_*`, some structure-changing transforms) | Pixel (`out`) | Can invent colors at new indices without anchoring only to existing input blocks |

The hybrid claim is that **choosing per instance** recovers both kinds of wins under one mechanical gate—not that object ILP alone matches Decom on duplication tasks, and not that pixel ILP alone matches object ILP on counting/recolor tasks.

After the experiment, replace the rows below with measured exact x/3 (or delete if you prefer only the aggregate table).

### Per-category exact (x/3) — placeholders

| Category | Ours @60 | Ours @120 | Ours @600 | Ours @3600 | Decom @60 | Decom @120 | Decom @600 | Decom @3600 |
|----------|----------|-----------|-----------|------------|-----------|------------|------------|-------------|
| denoising_1c | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| denoising_mc | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| fill | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| flip | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 2 |
| hollow | TBD | TBD | TBD | TBD | 3 | 3 | 2 | 3 |
| mirror | TBD | TBD | TBD | TBD | 1 | 0 | 3 | 3 |
| move_1p | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| move_2p | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| move_2p_dp | TBD | TBD | TBD | TBD | 1 | 0 | 2 | 2 |
| move_3p | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| move_dp | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 0 |
| padded_fill | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 0 |
| pcopy_1c | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| pcopy_mc | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| recolor_cmp | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 0 |
| recolor_cnt | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 0 |
| recolor_oe | TBD | TBD | TBD | TBD | 0 | 0 | 0 | 0 |
| scale_dp | TBD | TBD | TBD | TBD | 3 | 3 | 3 | 3 |
| **Total** | **TBD** | **TBD** | **TBD** | **TBD** | **32** | **30** | **34** | **37** |

Decom cells above are from the published paper tables for this slice; re-check against the artifact repo if you need machine-verified digits.

## Ablations (optional, not the headline)

Useful controls once numbers exist:

| Ablation | Mode / setup | Question it answers |
|----------|--------------|---------------------|
| Object-only | `block_primary` | How much does the pixel road add? |
| Pixel-only subset | tasks with `census_match=false` | Is the pixel road healthy on its own slice? |
| Match-only subset | tasks with `census_match=true` | Is the object road healthy on its own slice? |

Leave measured ablation tables TBD until you decide which campaigns to cite. Historical `block_primary` scoreboards (e.g. old 40/54 @60 s) are **not** the hybrid headline; keep them in `results/RUN_REGISTRY.md` if needed for provenance, not as “current Ours.”

## Search / timeout caveats

Popper’s timeout is a **search budget**. A longer budget can replace an early train-good program with a later compressed one that verifies or generalizes worse. If a longer timeout looks worse than a shorter one on the same commit, treat it as an infra / search-selection issue until per-task `failure_reason` and joblogs say otherwise (see project eval-hygiene rules).

## Data provenance (fill after experiment)

| Claim | Source (to fill) |
|-------|------------------|
| Decom results | `programs/relational/{60,600,3600}/1d/*/popper/*/results.pl` in the IJCAI 2025 artifact repo |
| Ours @60 s | `results/<campaign>/hybrid_census/summary.json` + git SHA — **TBD** |
| Ours @120 s | **TBD** |
| Ours @600 s | **TBD** (priority fill for the 10-minute jump claim) |
| Ours @3600 s | **TBD** |
| Host / JOBS | Record in `run_manifest.json` for each campaign |

Cite a finished run as **directory + git SHA + exact n/N**. Local campaign index: `results/RUN_REGISTRY.md`.
