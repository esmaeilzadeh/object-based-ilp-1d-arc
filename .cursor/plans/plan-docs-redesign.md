# Plan: Redesign all docs for readability and publishability

**Goal:** Turn the current internal working notes (`01`–`06` + `README`) into a coherent, human-readable documentation set suitable for public release or as a basis for a paper.

## Current problems

1. **Cryptic density** — “lean typed-role BK”, “mechanical exs”, “Bid+Off anchoring”, “soft % TN-padded” appear without definition.
2. **Audience confusion** — Docs mix “how to run this” (06) with “what we designed” (02) with “what actually ships” (03) with “how we beat Decom” (04), all in the same register.
3. **Duplication** — 02 (plan) and 03 (as-built) overlap heavily; 01 (landscape) and 04 (comparison) repeat the same Decom description.
4. **No narrative flow** — The reader never gets a simple story: “ARC is hard because it’s relational → we encode as objects → we learn rules about objects → we paint back to pixels → here is one full example.”

## New architecture (6 documents, clear audiences)

| Doc | New title | Audience | Purpose |
|-----|-----------|----------|---------|
| `01` | **Approach & Landscape** | Researchers, reviewers | Where this sits among ILP/ARC work; why blocks vs pixels; the Decom baseline context. |
| `02` | **Method (Encode–Induce–Decode)** | Implementers, method readers | The pipeline as a story: segmentation → BK → bias → Popper → paint-verify → decode. This absorbs current 02 (design) and 03 (as-built) into one definitive method doc. |
| `03` | **Tutorial: A Full Example** | New users, educators | The `1d_denoising_1c_0` walkthrough (currently `07-DEMO-ENCODING.md`). Show one task from pixels to Prolog to painted output, in plain language. |
| `04` | **Evaluation vs Decom** | Empirical readers | The 54-task comparison, budgets, scoreboards. Keep numbers but add prose explaining *why* the difference matters (object vs pixel representations). |
| `05` | **Repository Guide** | Developers | File map, API surface, how to extend (bias, predicates, new heads). Current 05 is fine but needs prose, not just tables. |
| `06` | **Running & Reproducing** | Practitioners | Setup, CLI, eval harness, smoke tests. Current 06 is close; needs clearer “first 5 minutes” path. |

Delete `07-DEMO-ENCODING.md` (moves to `03`). Update `README.md` to be a 1-page “quick start” pointing to `06` and `03`.

## Style guide (apply to all)

1. **Sentence before code.** Never show a Prolog atom or bash flag without explaining it in English first.
2. **Define acronyms at first use.** Write “background knowledge (BK)” once, then use BK.
3. **One concept per section.** Don’t mix “what Popper expects” with “how to run Popper” in the same paragraph.
4. **Tables for comparison only.** Use prose for explanation; tables for side-by-side data (e.g., “Ours vs Decom @60s”).
5. **Active voice, present tense.** “The encoder segments the grid…” not “The grid is segmented by…”.

## Per-document rewrite notes

### 01 — Approach & Landscape
- Remove the internal “reading order” boilerplate at the top.
- Add a 2-paragraph “Why objects?” motivation before the method comparison.
- Move the detailed Decom protocol alignment to 04; keep 01 as high-level positioning.
- Add a simple diagram: `[Pixels] → [Blocks] → [ILP] → [Paint] → [Pixels]`.

### 02 — Method (Encode–Induce–Decode)
- Merge current 02 and 03. Kill the “as-built vs plan” split; describe the method as it actually works.
- Structure:
  1. **Input:** ARC JSON (3 train pairs, 1 test input).
  2. **Encoding:** Grids → maximal runs → typed atoms (`block`, `largest`, `gap`, …).
  3. **Learning:** Popper with `out_block/5` head, mechanical bias from that instance.
  4. **Verification:** Paint-verify on train (Python checks exact match).
  5. **Application:** Test BK + learned rules → paint to pixels.
- Explain *why* we use typed roles (`b*`, `s*`, `v*`) with a concrete example of what would go wrong without them.
- Move the “negative results / ablations” (independent-out failure) to a short section here, not in 04.

### 03 — Tutorial: A Full Example
- Rename `07-DEMO-ENCODING.md` to this.
- Rewrite as narrative: “Here is a 1D-ARC task. The input looks like this… The output looks like this… What changed?… Here is how we teach the computer to see it…”
- Show the four grids, then show the segmentation as a diagram (ASCII art), then show the Prolog facts with English translations.
- Explain the induced rule: “Keep the largest block, delete the rest.”

### 04 — Evaluation vs Decom
- Keep the scoreboard tables but add a “How to read this” paragraph.
- Explain the soft vs exact distinction clearly.
- Add a short “Hardware fairness” section (laptop vs Xeon) with a table.

### 05 — Repository Guide
- Turn the file tree into prose: “The `solver/` package contains…”
- Explain the flow: `cli.py` → `pipeline.py` → `encoder.py` → `induce.py` → `decode.py`.
- Add a “Where to change what” section (e.g., “To add a new bias predicate, edit `predicates.py` and `bias_gen.py`”).

### 06 — Running & Reproducing
- Add a “5-minute quick start” at the very top: venv → install → solve one JSON.
- Move the long eval-provenance section to the end.
- Clarify that `test.pl` is for scoring only, not learning.

## Implementation order

1. **01** (Approach) — sets the stage.
2. **02** (Method) — the core intellectual contribution.
3. **03** (Tutorial) — makes it concrete.
4. **04** (Evaluation) — empirical results.
5. **05** (Repo guide) — for developers.
6. **06** (Running) — for practitioners.
7. **README** — slim down to quick links.

## Non-goals

- Do not add new method content (no new predicates, no new ablations).
- Do not change the code or the eval numbers; only the prose.
- Do not write the full paper here; this is documentation that *supports* the paper.

## Deliverables

- Six rewritten `.md` files in `docs/`.
- Updated `README.md`.
- Deleted `07-DEMO-ENCODING.md` (content moved to `03`).
