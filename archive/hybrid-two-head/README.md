# Archived: census-match two-head (`out_block` + `out_pixel`)

Not a live solver path. Census-match now calls `solve()` (single `out_block/5`), same as `block_primary`.

## What this was

On `census_match=True`, `solve_hybrid` encoded bulky runs as `out_block/5` and unit runs as `out_pixel/4`, induced both heads in parallel (`ThreadPoolExecutor`, `paint_test=True`), then paint-verified the combined program.

## Why it was archived

That language is not the previous object solver. At 120s `JOBS=2` first-3 it scored **16/33** on census-match vs **23/33** for `block_primary` on the same families (−7: `recolor_cnt` 3→0, `scale_dp` 3→0, `move_dp` 1→0). Pixel census-fail stayed 18/21, so the whole system was 34/54 instead of the 41/54 routing estimate (23+18).

Citable two-head full 54: `results/eval_120s_allcats_j2/hybrid_census/summary.json` at `21c78a59c9bb9157d7fc3b3894fdcbc98d2e24f7` (**34/54**).

## Files

- `encoder_hybrid.py` — partitioned bulky/unit examples
- `test_encoder_hybrid.py` / `test_paint_check.py` — tests for that encoder
