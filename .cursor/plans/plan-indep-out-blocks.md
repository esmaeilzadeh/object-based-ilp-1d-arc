# Plan: Independent output blocks (no input anchoring)

**Status:** APPROVED — user auto-confirmed implement; rewrite (not stepwise ladder).
**Branch:** `cursor/indep-out-blocks-ebb2` (from `main`)
**Direction:** `.cursor/rules/block-level-only.mdc` — uniform mechanical emit; no category gating; no answer-leaking BK; no marker/reflect hacks.
**Gate:** `.cursor/rules/soft-eval-regression.mdc` on first-3-per-cat (54 tasks, 120s).

## Goal

Replace input-anchored `out_block(E, Bid, Off, Len, Color)` with **independent output-run indices**:

```
out_block(E, Rank, Start, Len, Color)
```

| Arg | Meaning |
|---|---|
| `Rank` | ordinal index of the output run (incl. empty), left→right (`r0`, `r1`, …) |
| `Start` | absolute pixel start (size constant `sN`) |
| `Len` | run length (size) |
| `Color` | run color (**incl. `v0`** for empty) |

ILP must discover relations between **input** block indices/ranks/starts and **output** ranks/starts — nothing is pre-anchored to an input `Bid`.

No ladder, no dual head, no residual Bid/Off path.

## BK additions (lean, uniform, all instances)

- `block(E, Bid, Len, Color)` for **all** input runs including empty (`v0`)
- `in_start(E, Bid, Start)` — absolute start as size
- `in_rank(E, Bid, Rank)` — ordinal among all input runs
- `block_succ(E, Bi, Bj)` — consecutive run ids (all runs)
- `rank_rev(Ri, Rk)` — mechanical sugar `k = n-1-i` for observed run-count `n` (flip/mirror ordinal reverse)
- Keep existing: `gap` (between consecutive runs), `size_add`/`size_lt`/`size_sum3`, `obj_succ`/`obj_pair` on **colored** subset only, `component_*`, parity, `cardinal_ordinal`

No `out_*` answer facts in BK (would leak). Output structure appears only as head exs.

## Exs / decode / bias

- Positives: every output run via `segment_all_runs(out)` → `pos(out_block(E,rK,sStart,sLen,vC))`
- Negs: wrong Rank / Start / Len / Color families (deterministic, same spirit as before)
- Decode: paint at absolute `Start` (no `block_geometry` / Bid offset)
- Bias: drop “block must use head Bid (var 1)” — var 1 is now Rank; keep bidirectional `size_add` on Start/Len (vars 2/3)

## Files

`solver/predicates.py`, `encoder.py`, `decode.py`, `bias_gen.py`, `bias/object.pl`, `tests/test_encoder.py`, `tests/test_decode.py` (+ any fail tests that hardcode old shape).

## Eval

```bash
OUT=results/eval_indep_out JOBS=2 ./scripts/run_solver_eval_parallel.sh block_primary 120 0,1,2
```

Report vs S1′b / S6@120 baselines. Soft-gate KEEP/REVERT after report (user may still want the experiment kept for analysis even if net drops).

## Non-goals

- No SPEC edit without ask (`spec-sync.mdc`)
- No marker/reflect BK
- No category-named bias
- No pixel-head rescue
