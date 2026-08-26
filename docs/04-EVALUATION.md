# 04 — Evaluation: Hybrid vs Relational Decomposition

This document describes how we evaluate the **census-routed hybrid** solver (`hybrid_census`) against the pixel-level Relational Decomposition (Decom) baseline from Hocquette & Cropper (IJCAI 2025).

Both systems use the same ILP engine family (Popper) and the same 54-task slice (18 categories × trials `0,1,2`). The difference is the **system**: Decom is pixels-only; ours **routes** each instance to object-head or pixel-head induction via a train-grid census (see [02 — Method](02-SOLVER_PLAN.md)).

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
| **60 s (1 min)** | **19/54** | 32/54 | −13 |
| **600 s (10 min)** | **44/54** | 34/54 | **+10** |
| **3600 s (1 h)** | **45/54** | 37/54 | **+8** |

**Finding:** at **600 s** the hybrid already jumps past Decom (+10 exact). At **3600 s** the lead is **+8**. Short **60 s** is behind Decom (−13); most of the lift appears between 1 min and 10 min.

## Soft accuracy (%)

Soft accuracy is `(TP + TN) / (TP + FN + TN + FP)` over **each** Decom-style `pos(out(...))` / `neg(out(...))` label (not per example id, and not raw pixel Hamming). Near-miss grids can therefore score high because of many true-negative color labels. Implementation: `solver/lp/do_test.pl` + `solver/paper_score.py`; rescored artifacts stamp `soft_definition: "per_label_out_v1"`.

| Budget | Ours (hybrid_census) | Decom (paper) |
|--------|----------------------|---------------|
| 60 s | 97.5 | 59.3 |
| 600 s | 99.2 | 63.0 |
| 3600 s | 99.2 | 68.5 |

**Caveat:** Soft is inflated by true negatives (each cell contributes one positive and many negative color labels). Prefer **exact /54** as the headline. Soft values written before `per_label_out_v1` are **not comparable** (they collapsed to exact-or-nothing per test id).

## Protocol alignment

- **Slice:** first 3 instances of each of 18 categories → 54 tasks.
- **Learning:** from scratch per trial — no curriculum, no cross-task transfer.
- **Metrics:** exact match on the test grid; soft accuracy as above.
- **Mode for headline:** `hybrid_census`.
- **Hardware note:** Decom’s paper used a single Xeon Gold 6138 core, serial. Headline Ours campaigns below used `JOBS=3` on an 8-CPU host; parallelism speeds suite wall-clock but does not lengthen any single task’s timeout.

Campaign entrypoints:

```bash
# Compound 1m → 10m → mismatch@1h (JOBS=3)
./scripts/run_hybrid_campaign_1m_10m_mismatch1h_j3.sh

# Census-match 33 @ 1h (object road)
./scripts/run_census_match33_1h_j3.sh
```

## Why routing helps (qualitative)

Neither representation wins everywhere:

| Situation | Typical road | Why |
|-----------|--------------|-----|
| Train I/O preserve bulky/unit **counts** (move, flip, many recolors, …) | Object (`out_block`) | First-class blocks, sizes, succession, gaps |
| Train I/O change run inventory (many `pcopy_*`, some structure-changing transforms) | Pixel (`out`) | Can invent colors at new indices without anchoring only to existing input blocks |

The hybrid claim is that **choosing per instance** recovers both kinds of wins under one mechanical gate—not that object ILP alone matches Decom on duplication tasks, and not that pixel ILP alone matches object ILP on counting/recolor tasks.

### Per-category exact (x/3)

Census road is uniform within each first-3 category on this slice (`match` = object road, `mismatch` = pixel road).

| Category | Road | Ours @60 | Ours @600 | Ours @3600 | Decom @60 | Decom @600 | Decom @3600 |
|----------|------|----------|-----------|------------|-----------|------------|-------------|
| denoising_1c | mismatch | 3 | 3 | 3 | 3 | 3 | 3 |
| denoising_mc | mismatch | 3 | 3 | 3 | 3 | 3 | 3 |
| fill | mismatch | 3 | 3 | 3 | 3 | 3 | 3 |
| flip | match | 0 | 3 | 3 | 0 | 0 | 2 |
| hollow | mismatch | 3 | 3 | 3 | 3 | 2 | 3 |
| mirror | match | 0 | 2 | 3 | 1 | 3 | 3 |
| move_1p | match | 0 | 3 | 3 | 3 | 3 | 3 |
| move_2p | match | 0 | 3 | 3 | 3 | 3 | 3 |
| move_2p_dp | match | 0 | 3 | 3 | 1 | 2 | 2 |
| move_3p | match | 0 | 3 | 3 | 3 | 3 | 3 |
| move_dp | match | 0 | 3 | 3 | 0 | 0 | 0 |
| padded_fill | mismatch | 0 | 0 | 0 | 0 | 0 | 0 |
| pcopy_1c | mismatch | 3 | 3 | 3 | 3 | 3 | 3 |
| pcopy_mc | mismatch | 3 | 3 | 3 | 3 | 3 | 3 |
| recolor_cmp | match | 0 | 0 | 0 | 0 | 0 | 0 |
| recolor_cnt | match | 1 | 3 | 3 | 0 | 0 | 0 |
| recolor_oe | match | 0 | 0 | 0 | 0 | 0 | 0 |
| scale_dp | match | 0 | 3 | 3 | 3 | 3 | 3 |
| **Total** | | **19** | **44** | **45** | **32** | **34** | **37** |

Decom cells are from the published paper tables for this slice (120 s / 2 min column omitted); re-check against the artifact repo if you need machine-verified digits.

## Road-split ablations (same campaigns)

| Slice | @600 s | @3600 s |
|-------|--------|---------|
| Census-match 33 (object road) | 26/33 | 27/33 |
| Census-mismatch 21 (pixel road) | 18/21 | 18/21 |

Persistent exact zeros on this slice: `padded_fill` (pixel road), `recolor_cmp`, `recolor_oe` (object road).

## Ablations (optional, not the headline)

Useful controls once numbers exist:

| Ablation | Mode / setup | Question it answers |
|----------|--------------|---------------------|
| Object-only | `block_primary` | How much does the pixel road add? |
| Pixel-only subset | tasks with `census_match=false` | Is the pixel road healthy on its own slice? |
| Match-only subset | tasks with `census_match=true` | Is the object road healthy on its own slice? |

Historical `block_primary` scoreboards (e.g. old 40/54 @60 s) are **not** the hybrid headline; keep them in `results/RUN_REGISTRY.md` if needed for provenance, not as “current Ours.”

## Search / timeout caveats

Popper’s timeout is a **search budget**. A longer budget can replace an early train-good program with a later compressed one that verifies or generalizes worse. If a longer timeout looks worse than a shorter one on the same commit, treat it as an infra / search-selection issue until per-task `failure_reason` and joblogs say otherwise (see project eval-hygiene rules).

## Data provenance

| Claim | Source |
|-------|--------|
| Decom results | `programs/relational/{60,600,3600}/1d/*/popper/*/results.pl` in the IJCAI 2025 artifact repo |
| Ours @60 s | `results/eval_60s_hybrid_all54_j3/hybrid_census/summary.json` — **19/54** exact, soft 0.9749 — `git_sha` `1084793…` (jobs=3) |
| Ours @600 s | `results/eval_600s_hybrid_all54_j3/hybrid_census/summary.json` — **44/54** exact, soft 0.9918 — `git_sha` `0306ca0…` (jobs=3) |
| Ours @3600 s match 33 | `results/eval_3600s_census_match33_j3/hybrid_census/summary.json` — **27/33** exact — `git_sha` `35eb2c1…` (jobs=3) |
| Ours @3600 s mismatch 21 | `results/eval_3600s_census_mismatch21_j3/hybrid_census/summary.json` — **18/21** exact — `git_sha` `4b4f808…` (jobs=3) |
| Ours @3600 s /54 | Match 33 + mismatch 21 → **45/54** |
| Host / JOBS | Each campaign’s `run_manifest.json` |

Cite a finished run as **directory + git SHA + exact n/N**. Local campaign index: `results/RUN_REGISTRY.md`.
