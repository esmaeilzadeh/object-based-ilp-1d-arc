# Plan: Human-readable rewrite of the demo encoding doc

**Scope:** `docs/07-DEMO-ENCODING.md` only. Target: a reader who knows ARC but not Popper/ILP internals. Tone: clear, narrative, precise.

## Current problems

1. **Front-loaded jargon** — “exs”, “BK”, “bias”, “lean”, “typed roles” appear before definition.
2. **Fact dumping** — grids and Prolog atoms are shown raw instead of explained.
3. **No narrative flow** — sections are labeled lists, not a story of “grid → objects → logic → learned rule → paint”.
4. **Missing motivation** — why we split colored vs empty, why we need offsets, why geometry is Python-side.
5. **Compact tables** — useful for coders, hard to read as prose.

## Rewrite outline (proposed structure)

### 1. The task (plain language)
- Show the four 32-pixel rows visually (colored vs background).
- One sentence: “The rule seems to be: keep the longest same-color stretch, delete the rest.”

### 2. From pixels to objects (the encoding)
- Explain maximal runs (maximal = can’t extend either side).
- Show how each row becomes a list of runs (colored blocks and empty gaps).
- Introduce `block(Example, Id, Length, Color)` for colored runs and explain why background runs get a different predicate (`empty_block`) even though they share the same id space.
- Explain `block_geometry`: the Python-side map `example → block_id → [start, end]` that lets us paint later.

### 3. Teaching the learner (BK + examples)
- What Popper needs: Background Knowledge (facts), Examples (pos/neg), Bias (grammar).
- BK: list the `block` facts for the three training examples in plain English first, then show the Prolog.
- Examples: explain that `pos` means “this is the correct output block” and `neg` means “don’t choose this”. Show one full positive example and explain what `Off=0` means.

### 4. The search space (bias)
- Explain `max_body(6)` etc. in words: “rules can have at most 6 conditions”.
- Explain typed roles (`b1`, `s10`, `v4`) as “different kinds of things that can’t be mixed”.

### 5. What Popper finds (the induced rule)
- Show the actual clause: `out_block(Ex, Bid, s0, Len, Color) :- largest(Ex, Bid), block(Ex, Bid, Len, Color)`.
- Translate to English: “For every example, if a block is the largest, paint it at offset 0 (unchanged position) with its own length and color.”

### 6. Testing and scoring
- Explain that the test example gets its own BK (`test_bk.pl`), we ask “which `out_block` atoms are true?”, and Python paints pixels using `block_geometry`.
- Explain `test.pl` briefly: pixel-level gold for scoring, not for learning.

## Style rules for the rewrite

- **Sentence first, code second.** Every Prolog snippet gets an English gloss before or after.
- **No unexplained abbreviations.** Write “background knowledge (BK)” once, then use BK.
- **Use the demo grid as running example.** Show the actual row of 32 numbers, then show how it becomes blocks.
- **Tables become prose or bullet lists.** Keep tables only for side-by-side comparisons (e.g., train 0 vs train 1).
- **Define “lean” once** or drop the term entirely in favor of “minimal set of facts”.

## Implementation steps

1. Draft new sections 1–6 in the new style (replace existing file content).
2. Keep all existing factual content (same grids, same Prolog atoms) but rephrase explanations.
3. Add a “Summary: the pipeline in one paragraph” at the end.
4. Verify that every Prolog atom in the doc has an English translation within ±2 sentences.

## Deliverable

Updated `docs/07-DEMO-ENCODING.md` that reads like a tutorial, not a code dump.
