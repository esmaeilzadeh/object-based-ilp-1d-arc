"""Encode ARC JSON into lean block Popper facts (object-head)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from solver.grid import flatten, segment_all_runs, segment_blocks
from solver.predicates import OBJECT_BODY_ALLOWLIST

PathLike = Union[str, Path]

# Predicates lean BK may emit (bias allowlist + no side tables).
_LEAN_EMIT_ALLOW = OBJECT_BODY_ALLOWLIST


@dataclass
class ExampleGrids:
    ex_id: int
    inp: List[int]
    out: Optional[List[int]]  # None for unlabeled test


@dataclass
class EncodeResult:
    train: List[ExampleGrids]
    test: List[ExampleGrids]
    out_dir: Path
    bk_path: Path  # train-input BK only (learning)
    test_bk_path: Path  # test-input BK only (apply / decode)
    test_path: Path  # test.pl: pos/neg out/3 + test BK (soft score only)
    exs_object_path: Path
    bias_object_path: Optional[Path] = None  # mechanical object bias from this BK/exs
    # Hard role isolation: atoms b*/p*/s*/v* instead of raw ints.
    typed_roles: bool = True
    # Python-only Bid → (start, end) for object decode; not written as searchable BK.
    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = field(default_factory=dict)


def block_geometry_for_row(row: Sequence[int]) -> Dict[int, Tuple[int, int]]:
    """Map input run id → inclusive (start, end)."""
    return {bid: (s, e) for bid, (s, e, _c) in enumerate(segment_all_runs(row))}


def anchor_input_block(inp: Sequence[int], out_s: int, out_e: int) -> Optional[int]:
    """Choose input run id that anchors an output colored span (Off=0 case)."""
    r = anchor_input_block_offset(inp, out_s, out_e)
    return None if r is None else r[0]


def anchor_input_block_offset(
    inp: Sequence[int], out_s: int, out_e: int
) -> Optional[Tuple[int, int]]:
    """Return ``(bid, offset)`` for an output span.

    Prefer a colored input run with the same start (offset 0). Otherwise use the
    rightmost colored input start at or left of ``out_s`` so ILP can learn a
    neutral size offset (no marker_block / reflect_* BK).
    """
    del out_e  # length checked by caller via out span
    runs = segment_all_runs(inp)
    for bid, (s, _e, c) in enumerate(runs):
        if c != 0 and s == out_s:
            return bid, 0
    best: Optional[Tuple[int, int]] = None  # (start, bid)
    for bid, (s, _e, c) in enumerate(runs):
        if c != 0 and s <= out_s:
            if best is None or s > best[0]:
                best = (s, bid)
    if best is None:
        return None
    s, bid = best
    return bid, out_s - s


def _bid(i: int, typed: bool) -> str:
    return f"b{i}" if typed else str(i)


def _pos(i: int, typed: bool) -> str:
    return f"p{i}" if typed else str(i)


def _sz(i: int, typed: bool) -> str:
    return f"s{i}" if typed else str(i)


def _col(i: int, typed: bool) -> str:
    return f"v{i}" if typed else str(i)


def _rank(i: int, typed: bool) -> str:
    return f"r{i}" if typed else str(i)


def _load_json(src: Union[PathLike, dict]) -> dict:
    if isinstance(src, dict):
        return src
    return json.loads(Path(src).read_text())


def _pixel_facts(ex: int, row: Sequence[int]) -> List[str]:
    facts = []
    w = len(row)
    facts.append(f"width({ex},{w}).")
    for i, c in enumerate(row):
        c = int(c)
        if c == 0:
            facts.append(f"empty({ex},{i}).")
        else:
            facts.append(f"in({ex},{i},{c}).")
    return facts


def _block_and_derived(
    ex: int,
    row: Sequence[int],
    *,
    typed_roles: bool = False,
    include_cell_bridges: bool = True,
    include_pixel_anchors: bool = True,
) -> List[str]:
    """Emit searchable block facts + optional cell/pixel bridges.

    All maximal runs (including color 0) share one left→right ``block_id`` space.
    Colored: ``block(Ex,Id,Len,Color)`` + ``obj_index(Ex,Bid,K)`` (dense nonempty ordinal).
    Empty: ``empty_block(Ex,Id,Len)`` — not ``block(...,0)``.
    Geometry over all run ids; aggregations over colored only.

    When ``typed_roles`` is True (block-primary), numeric roles are distinct atoms
    ``b*`` / ``p*`` / ``s*`` / ``v*`` so block_id cannot unify with position/size/value.

    ``include_cell_bridges`` (False on block-primary): omit per-cell / paint bridges.
    ``include_pixel_anchors`` (False on block-primary): omit ``block_start`` / ``block_end``
    / ``mid`` — pixel starts live in Python ``block_geometry`` for decode only.

    On ``typed_roles`` (block-primary): lean geometry only — ``obj_succ``-only
    ``gap``, ``size_sum3`` for obj_succ triples (no width² ``size_add``), and
    bias-allowlisted preds only (``OBJECT_BODY_ALLOWLIST``).
    """
    t = typed_roles
    cell = include_cell_bridges
    anchors = include_pixel_anchors
    lean = typed_roles
    facts: List[str] = []
    runs = segment_all_runs(row)
    w = len(row)
    n_runs = len(runs)
    colored_ids: List[int] = []
    empty_ids: List[int] = []
    for bid, (_s, _e, c) in enumerate(runs):
        if c == 0:
            empty_ids.append(bid)
        else:
            colored_ids.append(bid)

    if not lean:
        facts.append(f"block_count({ex},{_sz(len(colored_ids), t)}).")
        facts.append(f"empty_block_count({ex},{_sz(len(empty_ids), t)}).")
    if w and anchors:
        facts.append(f"mid({ex},{_pos(w // 2, t)}).")
    if cell:
        for i in range(w):
            facts.append(f"from_right({ex},{_pos(i, t)},{_pos(w - 1 - i, t)}).")
            facts.append(f"mirror_index({ex},{_pos(i, t)},{_pos(w - 1 - i, t)}).")

    lengths: List[int] = [0] * n_runs  # bid -> length
    colored_lengths: List[Tuple[int, int]] = []  # (len, id) for aggregations
    color_counts: Dict[int, int] = {}
    observed_sizes: set = set()
    obj_k = 0

    for bid, (s, e, c) in enumerate(runs):
        L = e - s + 1
        lengths[bid] = L
        observed_sizes.add(L)
        bb = _bid(bid, t)
        if not lean:
            if s == 0:
                facts.append(f"touches_edge({ex},{bb},left).")
            if e == w - 1:
                facts.append(f"touches_edge({ex},{bb},right).")

        if anchors:
            facts.append(f"block_start({ex},{bb},{_pos(s, t)}).")
            facts.append(f"block_end({ex},{bb},{_pos(e, t)}).")
        if cell:
            if e + 1 < w:
                facts.append(f"after_block({ex},{bb},{_pos(e + 1, t)}).")
            if s - 1 >= 0:
                facts.append(f"before_block({ex},{bb},{_pos(s - 1, t)}).")

        if c == 0:
            if lean:
                # Independent-out rewrite: empty runs are first-class blocks (v0).
                facts.append(f"block({ex},{bb},{_sz(L, t)},{_col(0, t)}).")
                facts.append(f"in_start({ex},{bb},{_sz(s, t)}).")
                facts.append(f"in_rank({ex},{bb},{_rank(bid, t)}).")
                observed_sizes.add(s)
            else:
                facts.append(f"empty_block({ex},{bb},{_sz(L, t)}).")
            if cell:
                for p in range(s, e + 1):
                    facts.append(f"pixel_block({ex},{_pos(p, t)},{bb}).")
            continue

        facts.append(f"block({ex},{bb},{_sz(L, t)},{_col(c, t)}).")
        if lean:
            facts.append(f"in_start({ex},{bb},{_sz(s, t)}).")
            facts.append(f"in_rank({ex},{bb},{_rank(bid, t)}).")
            observed_sizes.add(s)
        if not lean:
            facts.append(f"block_len({ex},{bb},{_sz(L, t)}).")
            facts.append(f"obj_index({ex},{bb},{_rank(obj_k, t)}).")
        obj_k += 1
        colored_lengths.append((L, bid))
        color_counts[c] = color_counts.get(c, 0) + 1
        if cell:
            for p in range(s, e + 1):
                facts.append(f"in_block({ex},{bb},{_pos(p, t)}).")
                facts.append(f"pixel_block({ex},{_pos(p, t)},{bb}).")
                facts.append(f"block_cell({ex},{bb},{_pos(p, t)},{_col(c, t)}).")
                if p == s or p == e:
                    facts.append(f"block_edge({ex},{bb},{_pos(p, t)}).")
                    facts.append(f"edge_cell({ex},{bb},{_pos(p, t)},{_col(c, t)}).")
                else:
                    facts.append(f"interior_cell({ex},{bb},{_pos(p, t)},{_col(c, t)}).")

    if lean:
        for i in range(n_runs - 1):
            facts.append(f"block_succ({ex},{_bid(i, t)},{_bid(i + 1, t)}).")
        # Ordinal reverse sugar for this example's run count.
        if n_runs >= 1:
            for i in range(n_runs):
                k = n_runs - 1 - i
                facts.append(f"rank_rev({_rank(i, t)},{_rank(k, t)}).")
    else:
        for i in range(n_runs - 1):
            facts.append(f"block_succ({ex},{_bid(i, t)},{_bid(i + 1, t)}).")
    for a, b in zip(colored_ids, colored_ids[1:]):
        facts.append(f"obj_succ({ex},{_bid(a, t)},{_bid(b, t)}).")
    # Every-other colored pair (o0-o1, o2-o3, ...): neutral pairing geometry.
    for i in range(0, len(colored_ids) - 1, 2):
        a, b = colored_ids[i], colored_ids[i + 1]
        facts.append(f"obj_pair({ex},{_bid(a, t)},{_bid(b, t)}).")

    # Maximal contiguous non-zero components → start block + span length.
    # A component is a maximal sequence of consecutive colored runs with no
    # empty run between them (pixel-adjacent colored blocks).
    if colored_ids:
        comp_start = colored_ids[0]
        prev = colored_ids[0]
        for cid in colored_ids[1:]:
            # empty run between prev and cid?
            if cid != prev + 1:
                # close previous component
                s0, _, _ = runs[comp_start]
                _, e1, _ = runs[prev]
                span = e1 - s0 + 1
                facts.append(f"component_start({ex},{_bid(comp_start, t)}).")
                facts.append(
                    f"component_len({ex},{_bid(comp_start, t)},{_sz(span, t)})."
                )
                observed_sizes.add(span)
                comp_start = cid
            prev = cid
        s0, _, _ = runs[comp_start]
        _, e1, _ = runs[prev]
        span = e1 - s0 + 1
        facts.append(f"component_start({ex},{_bid(comp_start, t)}).")
        facts.append(f"component_len({ex},{_bid(comp_start, t)},{_sz(span, t)}).")
        observed_sizes.add(span)

    if not lean:
        for i in range(n_runs):
            for j in range(n_runs):
                if i == j:
                    continue
                Li, Lj = lengths[i], lengths[j]
                bi, bj = _bid(i, t), _bid(j, t)
                if Li < Lj:
                    facts.append(f"shorter({ex},{bi},{bj}).")
                elif Li > Lj:
                    facts.append(f"longer({ex},{bi},{bj}).")
                else:
                    facts.append(f"same_len({ex},{bi},{bj}).")

    if lean:
        # Gaps between consecutive runs (all runs, incl. empty) — independent-out geometry.
        for i in range(n_runs - 1):
            _s1, e1, _c1 = runs[i]
            s2, _e2, _c2 = runs[i + 1]
            bi, bj = _bid(i, t), _bid(i + 1, t)
            g = s2 - e1 - 1
            facts.append(f"gap({ex},{bi},{bj},{_sz(g, t)}).")
            observed_sizes.add(g)
        # Ternary length sum for each colored succession (arithmetic only).
        for a, b in zip(colored_ids, colored_ids[1:]):
            La, Lb = lengths[a], lengths[b]
            _s1, e1, _ = runs[a]
            s2, _e2, _ = runs[b]
            g = s2 - e1 - 1
            total = La + g + Lb
            if total <= w:
                facts.append(
                    f"size_sum3({_sz(La, t)},{_sz(g, t)},{_sz(Lb, t)},{_sz(total, t)})."
                )
            # Binary size_add over observed succession lengths/gaps (uniform).
            for x, y in ((La, g), (1, g)):
                s = x + y
                if s <= w and x >= 0 and y >= 0:
                    facts.append(f"size_add({_sz(x, t)},{_sz(y, t)},{_sz(s, t)}).")
                    observed_sizes.add(s)
        # size_add(1, L-1, L) for each run length (uniform arith closure).
        for bid in range(n_runs):
            L = lengths[bid]
            if L >= 2 and L <= w:
                facts.append(
                    f"size_add({_sz(1, t)},{_sz(L - 1, t)},{_sz(L, t)})."
                )
                observed_sizes.add(L - 1)
        # Within-type cardinal comparison over observed sizes (lean).
        sizes = sorted(s for s in observed_sizes if s >= 0)
        for a in sizes:
            for b in sizes:
                if a < b:
                    facts.append(f"size_lt({_sz(a, t)},{_sz(b, t)}).")
        # Bridge: observed cardinal equals valid position index (uniform).
        for i in sizes:
            if 0 <= i < w:
                facts.append(f"cardinal_ordinal({_sz(i, t)},{_pos(i, t)}).")
    else:
        for i in range(n_runs):
            for j in range(i + 1, n_runs):
                s1, e1, c1 = runs[i]
                s2, e2, c2 = runs[j]
                bi, bj = _bid(i, t), _bid(j, t)
                facts.append(f"left_of({ex},{bi},{bj}).")
                g = s2 - e1 - 1
                facts.append(f"gap({ex},{bi},{bj},{_sz(g, t)}).")
                observed_sizes.add(g)
                if g == 0:
                    facts.append(f"adjacent({ex},{bi},{bj}).")
                    facts.append(f"adjacent({ex},{bj},{bi}).")
                if not cell:
                    continue
                both_colored = c1 != 0 and c2 != 0
                if both_colored:
                    if lengths[i] < lengths[j]:
                        fill_c: Optional[int] = c1
                    elif lengths[j] < lengths[i]:
                        fill_c = c2
                    else:
                        fill_c = None
                else:
                    fill_c = None
                for p in range(e1 + 1, s2):
                    facts.append(f"in_gap({ex},{bi},{bj},{_pos(p, t)}).")
                    if fill_c is not None:
                        facts.append(
                            f"gap_cell({ex},{bi},{bj},{_pos(p, t)},{_col(fill_c, t)})."
                        )

    if colored_lengths:
        max_L = max(L for L, _ in colored_lengths)
        min_L = min(L for L, _ in colored_lengths)
        for L, bid in colored_lengths:
            bb = _bid(bid, t)
            if L == max_L:
                facts.append(f"largest({ex},{bb}).")
            else:
                facts.append(f"non_largest({ex},{bb}).")
                if cell:
                    s, e, c = runs[bid]
                    for p in range(s, e + 1):
                        facts.append(f"solid_cell({ex},{bb},{_pos(p, t)},{_col(c, t)}).")
            if not lean and L == min_L:
                facts.append(f"smallest({ex},{bb}).")
        if not lean:
            unique_lens = sorted({L for L, _ in colored_lengths}, reverse=True)
            rank = {L: r + 1 for r, L in enumerate(unique_lens)}
            for L, bid in colored_lengths:
                facts.append(f"len_rank({ex},{_bid(bid, t)},{_rank(rank[L], t)}).")

    if not lean:
        sizes = sorted(observed_sizes | {len(colored_ids), len(empty_ids)})
        for a in sizes:
            for b in sizes:
                if a < b:
                    facts.append(f"size_lt({_sz(a, t)},{_sz(b, t)}).")

        size_universe = sorted(set(sizes) | set(range(0, w + 1)))
        for a in size_universe:
            for b in size_universe:
                s = a + b
                if s <= w:
                    facts.append(f"size_add({_sz(a, t)},{_sz(b, t)},{_sz(s, t)}).")

    if cell:
        for k in (1, 2, 3):
            for p in range(w):
                if p + k < w:
                    facts.append(f"offset_pos({_pos(p, t)},{_sz(k, t)},{_pos(p + k, t)}).")
                if p - k >= 0:
                    facts.append(f"offset_pos({_pos(p, t)},{_sz(k, t)},{_pos(p - k, t)}).")

    if not lean:
        for c, n in color_counts.items():
            facts.append(f"color_count({ex},{_col(c, t)},{_sz(n, t)}).")
            if n == 1:
                facts.append(f"unique_color({ex},{_col(c, t)}).")

    if lean:
        for sz in sorted(observed_sizes):
            if sz % 2 == 0:
                facts.append(f"size_even({_sz(sz, t)}).")
            else:
                facts.append(f"size_odd({_sz(sz, t)}).")
        # Belt-and-suspenders: BK emit == bias allowlist (drop stray preds).
        facts = [
            f
            for f in facts
            if any(f.startswith(n + "(") for n in _LEAN_EMIT_ALLOW)
        ]
        # Typed constant unary facts so Popper can resolve body_pred(C,1).
        for i in range(10):
            facts.append(f"v{i}(v{i}).")
        for i in range(w + 1):
            facts.append(f"s{i}(s{i}).")
        for i in range(max(n_runs, 1)):
            facts.append(f"r{i}(r{i}).")
    return facts


def _arith_ground(max_w: int) -> List[str]:
    """Ground position arithmetic + typed constant tables."""
    facts: List[str] = []
    P = max(max_w, 1)
    facts.append(f"max_position({P}).")
    for i in range(P + 1):
        facts.append(f"position({i}).")
    for i in range(10):
        facts.append(f"value({i}).")
        facts.append(f"v{i}({i}).")
    for i in range(10):
        facts.append(f"s{i}({i}).")
    for i in range(1, 10):
        facts.append(f"r{i}({i}).")
    for i in range(min(P + 1, 33)):
        facts.append(f"c{i}({i}).")
        facts.append(f"x{i}({i}).")
    lts: List[str] = []
    succs: List[str] = []
    adds: List[str] = []
    for a in range(P + 1):
        for b in range(P + 1):
            if a < b:
                lts.append(f"lt({a},{b}).")
            if b == a + 1:
                succs.append(f"my_succ({a},{b}).")
            s = a + b
            if s <= P:
                adds.append(f"add({a},{b},{s}).")
    facts.extend(lts)
    facts.extend(succs)
    facts.extend(adds)
    return facts


def _exs_pos_neg(examples: List[ExampleGrids], max_color: int = 9) -> List[str]:
    """Pixel-head examples: pos/neg ``out(Ex, Pos, Color)`` (nonzero pos only)."""
    pos: List[str] = []
    neg: List[str] = []
    for eg in examples:
        assert eg.out is not None
        for i, c in enumerate(eg.out):
            c = int(c)
            if c != 0:
                pos.append(f"pos(out({eg.ex_id},{i},{c})).")
            for v in range(0, max_color + 1):
                if v != c:
                    neg.append(f"neg(out({eg.ex_id},{i},{v})).")
    return pos + neg


_AGG_NAMES = (
    "largest",
    "smallest",
    "non_largest",
    "block_count",
    "empty_block_count",
    "color_count",
    "unique_color",
    "len_rank",
)


def _bk_lines_for(examples: Sequence[ExampleGrids], *, max_w: int) -> List[str]:
    """Lean typed-role block facts for ``examples`` (object path only)."""
    lines: List[str] = []
    for eg in examples:
        lines.extend(
            _block_and_derived(
                eg.ex_id,
                eg.inp,
                typed_roles=True,
                include_cell_bridges=False,
                include_pixel_anchors=False,
            )
        )
    del max_w  # width used inside lean emit via row length
    return lines


def _exs_out_blocks(
    train: List[ExampleGrids],
    max_color: int = 9,
    *,
    typed_roles: bool = False,
) -> List[str]:
    """Object-head examples: pos/neg ``out_block(Ex, Rank, Start, Len, Color)``.

    ``Rank`` is the left→right index of an output run (incl. empty).
    ``Start`` is the absolute pixel start. Decode paints ``[Start, Start+Len)``.
    """
    t = typed_roles
    pos: List[str] = []
    neg: List[str] = []
    for eg in train:
        assert eg.out is not None
        out_runs = segment_all_runs(eg.out)
        w = len(eg.out)
        true_blocks: List[Tuple[int, int, int, int]] = []  # rank, start, L, c
        true_set: set = set()
        colors_used: set = set()
        observed_sizes: set = set([0])
        for rank, (s, e, c) in enumerate(out_runs):
            L = e - s + 1
            true_blocks.append((rank, s, L, c))
            true_set.add((rank, s, L, c))
            colors_used.add(c)
            observed_sizes.add(L)
            observed_sizes.add(s)
            pos.append(
                f"pos(out_block({eg.ex_id},{_rank(rank, t)},{_sz(s, t)},{_sz(L, t)},{_col(c, t)}))."
            )
        if not true_blocks:
            continue
        # Wrong color at true (Rank, Start, Len).
        for rank, start, L, c in true_blocks:
            for v in range(0, max_color + 1):
                if v == c:
                    continue
                neg.append(
                    f"neg(out_block({eg.ex_id},{_rank(rank, t)},{_sz(start, t)},{_sz(L, t)},{_col(v, t)}))."
                )
        if not typed_roles:
            continue
        len_cands = sorted(set(observed_sizes) | set(range(1, min(w, 12) + 1)))
        start_cands = list(range(0, w + 1))
        rank_cands = list(range(0, max(len(out_runs) + 2, 1)))
        for rank, start, L, c in true_blocks:
            for L2 in len_cands:
                if L2 < 1 or L2 == L:
                    continue
                if (rank, start, L2, c) in true_set:
                    continue
                neg.append(
                    f"neg(out_block({eg.ex_id},{_rank(rank, t)},{_sz(start, t)},{_sz(L2, t)},{_col(c, t)}))."
                )
            for s2 in start_cands:
                if s2 == start:
                    continue
                if (rank, s2, L, c) in true_set:
                    continue
                neg.append(
                    f"neg(out_block({eg.ex_id},{_rank(rank, t)},{_sz(s2, t)},{_sz(L, t)},{_col(c, t)}))."
                )
            for r2 in rank_cands:
                if r2 == rank:
                    continue
                if (r2, start, L, c) in true_set:
                    continue
                neg.append(
                    f"neg(out_block({eg.ex_id},{_rank(r2, t)},{_sz(start, t)},{_sz(L, t)},{_col(c, t)}))."
                )
        # Identity / loose overpaint killers: wrong Len at (rank, start) with same color.
        for rank, (s, e, c) in enumerate(out_runs):
            Lin = e - s + 1
            for L0 in range(1, min(w, Lin + 3) + 1):
                if (rank, s, L0, c) in true_set:
                    continue
                neg.append(
                    f"neg(out_block({eg.ex_id},{_rank(rank, t)},{_sz(s, t)},{_sz(L0, t)},{_col(c, t)}))."
                )
    seen: set = set()
    out: List[str] = []
    for line in pos + neg:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def encode_instance(
    src: Union[PathLike, dict],
    out_dir: PathLike,
) -> EncodeResult:
    """Write lean object BK, ``exs_object.pl``, bias, and soft-score ``test.pl``."""
    obj = _load_json(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train: List[ExampleGrids] = []
    for i, pair in enumerate(obj["train"]):
        inp = flatten(pair["input"])
        out = flatten(pair["output"])
        train.append(ExampleGrids(i, inp, out))

    test: List[ExampleGrids] = []
    base = len(train)
    for j, pair in enumerate(obj["test"]):
        inp = flatten(pair["input"])
        out = flatten(pair["output"]) if "output" in pair and pair["output"] is not None else None
        test.append(ExampleGrids(base + j, inp, out))

    max_w = 1
    for eg in train + test:
        max_w = max(max_w, len(eg.inp))
        if eg.out is not None:
            max_w = max(max_w, len(eg.out))

    train_bk = sorted(_bk_lines_for(train, max_w=max_w), key=lambda f: f.split("(", 1)[0])
    test_bk = sorted(_bk_lines_for(test, max_w=max_w), key=lambda f: f.split("(", 1)[0])

    bk_path = out_dir / "bk.pl"
    test_bk_path = out_dir / "test_bk.pl"
    test_path = out_dir / "test.pl"
    exs_object_path = out_dir / "exs_object.pl"

    bk_path.write_text("\n".join(train_bk) + "\n")
    test_bk_path.write_text("\n".join(test_bk) + "\n")

    labeled_test = [eg for eg in test if eg.out is not None]
    test_exs = _exs_pos_neg(labeled_test) if labeled_test else []
    test_path.write_text("\n".join(test_exs + test_bk) + "\n")

    exs_object_path.write_text(
        "\n".join(_exs_out_blocks(train, typed_roles=True)) + "\n"
    )

    from solver.bias_gen import render_object_bias_from_bk

    bias_object_path = out_dir / "bias_object.pl"
    bias_object_path.write_text(
        render_object_bias_from_bk(
            bk_path.read_text(),
            exs_text=exs_object_path.read_text(),
        )
    )

    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = {}
    for eg in train + test:
        block_geometry[eg.ex_id] = block_geometry_for_row(eg.inp)

    meta = {
        "train": [{"id": e.ex_id, "input": e.inp, "output": e.out} for e in train],
        "test": [{"id": e.ex_id, "input": e.inp, "output": e.out} for e in test],
        "typed_roles": True,
        "block_geometry": {
            str(eid): {str(b): [s, e] for b, (s, e) in geo.items()}
            for eid, geo in block_geometry.items()
        },
    }
    (out_dir / "grids.json").write_text(json.dumps(meta))

    return EncodeResult(
        train=train,
        test=test,
        out_dir=out_dir,
        bk_path=bk_path,
        test_bk_path=test_bk_path,
        test_path=test_path,
        exs_object_path=exs_object_path,
        bias_object_path=bias_object_path,
        typed_roles=True,
        block_geometry=block_geometry,
    )
