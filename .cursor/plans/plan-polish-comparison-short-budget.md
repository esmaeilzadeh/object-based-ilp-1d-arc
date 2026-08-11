# Plan: Polish comparison report — short-budget win + host fairness

## Goal

Update `docs/04-COMPARISON-vs-Hocquette-Cropper-IJCAI25.md` only (no code). Fold in
the Cloud Agent vs paper-host fairness discussion, and polish the narrative so the
**short-budget lead** (especially @60s) is the front-and-center claim.

## Claims to add / sharpen

1. **Short-budget dominance:** Ours leads at 60 / 120 / 600 s (+8 / +9 / +7 exact).
   Headline: **40/54 @60s already exceeds Decom’s best paper exact (37/54 @3600s)**.
2. **Host fairness (per-task):** Paper = 1× Xeon Gold 6138 core, serial. Ours @60s =
   `JOBS=2` on 4 KVM vCPUs / 15 GiB. Same 60 s wall timeout; our per-task CPU is
   **not stronger** (likely weaker virtual core). Parallelism caveat only — not a
   fatter single-core.
3. Soft story aligned: ours 74.1% @60s > Decom paper soft 59.3% @60s and even their
   68.5% @3600s.

## Edit scope (one file)

| Section | Change |
|---------|--------|
| §0 TL;DR | Lead with short-budget win; mention 40@1min > their 37@1h; host one-liner |
| §1 | New **§1a Host / machine fairness** table + per-task vs aggregate |
| §2 Reading | Tighten “lesser time limits” framing; cross-link §1a |
| §2a | Replace thin fairness caveat with pointer to §1a; keep per-cat table |
| §2c Trend | Emphasize 60–600 lead; 3600 regression secondary |
| §5 Conclusions | Bullet 1 → short-budget story; optional soft @60 vs their @3600 |
| Appendix A | Add paper host + our VPS provenance rows |

## Out of scope

- Re-running evals; changing `JOBS` defaults in scripts
- SPEC / other docs (06 already has §6.0 host profile — only link)
- Applying until user approves after reviewing the proposed diff

## Apply gate

Show unified diff vs current `docs/04-…` **before** writing the real file.
Wait for explicit go-ahead (`approved` / `apply` / `implement`).
