# Block-level 1D-ARC ILP

Object-head induction: output is a set of spans painted from input runs, not a pixel array.

## Language

**Output span**:
A maximal consecutive non-zero run in an output grid.
_Avoid_: block (ambiguous with input runs), copy, blob

**Bid-parent**:
The input run id used as `out_block`’s `Bid` for one output span. Decode paints at `start(Bid)+Offset`.
_Avoid_: heuristic, anchor (the procedure), mapping

**Anchor ranking**:
An ordered, instance-uniform choice of Bid-parent. Unique `(length, color)` on the input wins at any Offset. Otherwise same-color runs are scored before different-color: `1 / (3|ΔL| + |Offset| + 1)`.
_Avoid_: family heuristic, pcopy rule, copy heuristic

**Offset**:
Pixels from the Bid-parent’s start to the output span’s start. Decode paints at `start(Bid)+Offset`. Negative values are size constants `smK` meaning −K, emitted only when that Offset appears on a train Bid-parent (same mechanical rule as novel color constants).
_Avoid_: Off (code argument), negative index, s-1 (illegal Prolog)
