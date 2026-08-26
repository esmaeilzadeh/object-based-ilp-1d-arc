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
    unit_geometry: Dict[int, Dict[int, int]] = field(default_factory=dict)
    observed_offs: List[int] = field(default_factory=list)
    exs_unit_path: Optional[Path] = None
    bias_unit_path: Optional[Path] = None
    road: str = "object"
    exs_pixel_path: Optional[Path] = None
    bias_pixel_path: Optional[Path] = None


def block_geometry_for_row(row: Sequence[int]) -> Dict[int, Tuple[int, int]]:
    """Map all-run id → inclusive (start, end)."""
    return {bid: (s, e) for bid, (s, e, _c) in enumerate(segment_all_runs(row))}


def colored_block_geometry_for_row(row: Sequence[int]) -> Dict[int, Tuple[int, int]]:
    """Map dense colored rank → inclusive (start, end). Matches lean ``block/4`` ids."""
    geo: Dict[int, Tuple[int, int]] = {}
    k = 0
    for s, e, c in segment_all_runs(row):
        if c == 0:
            continue
        geo[k] = (s, e)
        k += 1
    return geo


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
    if not typed:
        return str(i)
    if i < 0:
        return f"sm{abs(i)}"
    return f"s{i}"


def _uid(i: int, typed: bool) -> str:
    return f"u{i}" if typed else str(i)


def _col(i: int, typed: bool) -> str:
    return f"v{i}" if typed else str(i)


def _load_json(src: Union[PathLike, dict]) -> dict:
    if isinstance(src, dict):
        return src
    return json.loads(Path(src).read_text())


def _block_and_derived(ex: int, row: Sequence[int]) -> List[str]:
    """Emit searchable object BK for one input row.

    Colored runs only, dense ranks ``0..n-1`` so ``OutBid`` can unify with
    ``InBid``. Typed atoms ``b*`` / ``p*`` / ``s*`` / ``v*`` keep roles apart.
    Facts are the object-body allowlist: ``block``, ``bind``, ``obj_succ``,
    ``gap``, ``size_sum3``, ``size_add``, ``size_lt``, ``cardinal_ordinal``.
    Pixel starts live in Python ``block_geometry`` for decode, not in BK.
    """
    t = True
    facts: List[str] = []
    runs = segment_all_runs(row)
    w = len(row)
    n_runs = len(runs)
    colored_ids: List[int] = []
    for bid, (_s, _e, c) in enumerate(runs):
        if c != 0:
            colored_ids.append(bid)

    dense_of: Dict[int, int] = {rid: k for k, rid in enumerate(colored_ids)}

    def _id(all_run: int) -> str:
        return _bid(dense_of[all_run], t)

    lengths: List[int] = [0] * n_runs
    observed_sizes: set = set()

    for bid, (_s, _e, c) in enumerate(runs):
        L = _e - _s + 1
        lengths[bid] = L
        observed_sizes.add(L)
        if c == 0:
            continue
        facts.append(f"block({ex},{_id(bid)},{_sz(L, t)},{_col(c, t)}).")

    for a, b in zip(colored_ids, colored_ids[1:]):
        facts.append(f"obj_succ({ex},{_id(a)},{_id(b)}).")
    for i in range(len(colored_ids)):
        facts.append(f"bind({ex},{_bid(i, t)},{_bid(i, t)}).")

    for a, b in zip(colored_ids, colored_ids[1:]):
        _s1, e1, _c1 = runs[a]
        s2, _e2, _c2 = runs[b]
        g = s2 - e1 - 1
        facts.append(f"gap({ex},{_id(a)},{_id(b)},{_sz(g, t)}).")
        observed_sizes.add(g)
        La, Lb = lengths[a], lengths[b]
        total = La + g + Lb
        if total <= w:
            facts.append(
                f"size_sum3({_sz(La, t)},{_sz(g, t)},{_sz(Lb, t)},{_sz(total, t)})."
            )
        for x, y in ((La, g), (1, g)):
            s = x + y
            if s <= w and x >= 0 and y >= 0:
                facts.append(f"size_add({_sz(x, t)},{_sz(y, t)},{_sz(s, t)}).")
                observed_sizes.add(s)
    for bid in colored_ids:
        L = lengths[bid]
        if L >= 2 and L <= w:
            facts.append(f"size_add({_sz(1, t)},{_sz(L - 1, t)},{_sz(L, t)}).")
            observed_sizes.add(L - 1)
    sizes = sorted(s for s in observed_sizes if s >= 0)
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({_sz(a, t)},{_sz(b, t)}).")
    for i in sizes:
        if 0 <= i < w:
            facts.append(f"cardinal_ordinal({_sz(i, t)},{_pos(i, t)}).")

    facts = [
        f
        for f in facts
        if any(f.startswith(n + "(") for n in _LEAN_EMIT_ALLOW)
    ]
    return facts


def _typed_constant_unaries(max_w: int) -> List[str]:
    """Emit ``b*`` / ``s*`` / ``v*`` / ``sm*`` unary tables once per ``bk.pl``."""
    facts: List[str] = []
    for i in range(10):
        facts.append(f"v{i}(v{i}).")
    for i in range(max_w + 1):
        facts.append(f"s{i}(s{i}).")
        facts.append(f"b{i}(b{i}).")
    for i in range(1, max_w + 1):
        facts.append(f"sm{i}(sm{i}).")
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


def _bk_lines_for(examples: Sequence[ExampleGrids], *, max_w: int) -> List[str]:
    """Typed-role block facts for ``examples`` (object path only)."""
    lines: List[str] = []
    for eg in examples:
        lines.extend(_block_and_derived(eg.ex_id, eg.inp))
    lines.extend(_typed_constant_unaries(max_w))
    return lines


def _colored_input_starts(inp: Sequence[int]) -> List[int]:
    return [s for s, _e, c in segment_all_runs(inp) if c != 0]


def _colored_input_bids(inp: Sequence[int]) -> List[int]:
    """Dense colored ranks ``0..n-1`` (same space as lean ``block/4`` and OutBid)."""
    return list(range(len(_colored_input_starts(inp))))


def _out_block_gold(
    inp: Sequence[int], out: Sequence[int]
) -> List[Tuple[int, int, int, int]]:
    """``(OutBid, Off, Len, Color)`` for each gold colored output object.

    ``OutBid`` is L→R output colored rank (mechanical). ``Off`` is ``out_s``
    minus the start of the same-rank colored *input* (zip for the displacement
    number only — not spatial argmax, and the input id is not in the tuple).
    Decode paints at ``start(InBid)+Off`` for the ``InBid`` the clause binds.
    """
    in_starts = _colored_input_starts(inp)
    labels: List[Tuple[int, int, int, int]] = []
    for out_bid, (s, e, c) in enumerate(segment_blocks(out)):
        L = e - s + 1
        if out_bid >= len(in_starts):
            continue
        off = int(s) - int(in_starts[out_bid])
        labels.append((out_bid, off, L, int(c)))
    return labels


def _exs_out_blocks(
    train: List[ExampleGrids],
    max_color: int = 9,
    *,
    typed_roles: bool = False,
) -> List[str]:
    """Object-head examples: pos/neg ``out_block(Ex, OutBid, Off, Len, Color)``.

    ``OutBid`` is output colored rank. No input Bid in the positive.
    """
    t = typed_roles
    pos: List[str] = []
    neg: List[str] = []
    for eg in train:
        assert eg.out is not None
        runs = segment_all_runs(eg.inp)
        colored_bids = _colored_input_bids(eg.inp)
        true_blocks = _out_block_gold(eg.inp, eg.out)
        true_set: set = set(true_blocks)
        colors_used: set = {c for _b, _o, _L, c in true_blocks}
        observed_sizes: set = set([0])
        for bid, (s, e, c) in enumerate(runs):
            if c == 0:
                continue
            L = e - s + 1
            observed_sizes.add(L)
        for a, b in zip(colored_bids, colored_bids[1:]):
            La = runs[a][1] - runs[a][0] + 1
            Lb = runs[b][1] - runs[b][0] + 1
            g = runs[b][0] - runs[a][1] - 1
            observed_sizes.add(g)
            observed_sizes.add(La + g + Lb)
            observed_sizes.add(La + g)
            observed_sizes.add(g + Lb)
            if g >= 0:
                observed_sizes.add(1 + g)  # common unit+gap offset
        for bid, off, L, c in true_blocks:
            observed_sizes.add(L)
            observed_sizes.add(abs(off))
            pos.append(
                f"pos(out_block({eg.ex_id},{_bid(bid, t)},"
                f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)}))."
            )
        for bid, off, L, c in true_blocks:
            for v in range(1, max_color + 1):
                if v != c:
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off, t)},{_sz(L, t)},{_col(v, t)}))."
                    )
        if not colors_used or not true_blocks:
            continue
        n_out = len(true_blocks)
        if typed_roles:
            w = len(eg.out)
            len_cands = sorted(set(observed_sizes) | set(range(1, min(w, 12) + 1)))
            # Wrong offsets: full -w..w (zip Off can be negative).
            off_cands = list(range(-w, w + 1))
            for bid, off, L, c in true_blocks:
                for L2 in len_cands:
                    if L2 < 1 or L2 == L:
                        continue
                    if (bid, off, L2, c) in true_set:
                        continue
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                        f"{_sz(off, t)},{_sz(L2, t)},{_col(c, t)}))."
                    )
                for off2 in off_cands:
                    if off2 == off:
                        continue
                    if (bid, off2, L, c) in true_set:
                        continue
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                        f"{_sz(off2, t)},{_sz(L, t)},{_col(c, t)}))."
                    )
            # Wrong OutBid for a true (Off,Len,Color), plus leftover input ids.
            all_bids = sorted(set(range(n_out)) | set(colored_bids))
            for bid in all_bids:
                for _tb, off, L, c in true_blocks:
                    if (bid, off, L, c) in true_set:
                        continue
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                        f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)}))."
                    )
            # Cross mix: true OutBid with another object's (Len, Color).
            input_lc: List[Tuple[int, int]] = []
            for _bid2, (s2, e2, c2) in enumerate(runs):
                if c2 == 0:
                    continue
                input_lc.append((e2 - s2 + 1, c2))
            for bid, off, L, c in true_blocks:
                for L2, C2 in input_lc:
                    if (bid, off, L2, C2) in true_set:
                        continue
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                        f"{_sz(off, t)},{_sz(L2, t)},{_col(C2, t)}))."
                    )
                for _b2, _o2, L2, C2 in true_blocks:
                    if (bid, off, L2, C2) in true_set:
                        continue
                    neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                        f"{_sz(off, t)},{_sz(L2, t)},{_col(C2, t)}))."
                    )
        else:
            w = len(eg.out)
            for bid in range(n_out):
                for off in sorted(observed_sizes):
                    if off < -w or off > w:
                        continue
                    for L in range(1, w + 1):
                        for c in colors_used:
                            if (bid, off, L, c) not in true_set:
                                neg.append(
                                    f"neg(out_block({eg.ex_id},{_bid(bid, t)},"
                                    f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)}))."
                                )
    seen: set = set()
    out: List[str] = []
    for line in pos + neg:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def _paint_constraint_bk(
    train: List[ExampleGrids],
    *,
    typed_roles: bool = True,
) -> List[str]:
    """SWI paint checker for stock Popper ``functional_test`` (append to exs).

    Not bias body preds and not ``bk.pl`` (Clingo recall deduction cannot parse
    SWI rules). Facts: ``gold`` / ``need_block`` / ``paint_start`` /
    ``rank_origin`` / ``sz_int``. Paint origin is the body's ``block/4`` InBid
    (facts fall back to same-rank input via ``rank_origin``).
    Dup/extra fire even when the hypothesis is still incomplete (``eff8e50``).
    """
    t = typed_roles
    lines: List[str] = []
    max_w = 1
    for eg in train:
        max_w = max(max_w, len(eg.inp))
        if eg.out is not None:
            max_w = max(max_w, len(eg.out))
    for i in range(max_w + 1):
        lines.append(f"sz_int({_sz(i, t)},{i}).")
    for i in range(1, max_w + 1):
        lines.append(f"sz_int({_sz(-i, t)},{-i}).")

    paint_starts: List[str] = []
    rank_origins: List[str] = []
    golds: List[str] = []
    needs: List[str] = []
    for eg in train:
        assert eg.out is not None
        k = 0
        for s, _e, c in segment_all_runs(eg.inp):
            if c == 0:
                continue
            # Integer canvas start for start(InBid)+Off cover (checker-only).
            paint_starts.append(f"paint_start({eg.ex_id},{_bid(k, t)},{int(s)}).")
            rank_origins.append(
                f"rank_origin({eg.ex_id},{_bid(k, t)},{_bid(k, t)})."
            )
            k += 1
        for p, c in enumerate(eg.out):
            golds.append(f"gold({eg.ex_id},{int(p)},{_col(int(c), t)}).")
        for bid, off, L, c in _out_block_gold(eg.inp, eg.out):
            needs.append(
                f"need_block({eg.ex_id},{_bid(bid, t)},"
                f"{_sz(off, t)},{_sz(L, t)},{_col(int(c), t)})."
            )
    lines.extend(paint_starts)
    lines.extend(rank_origins)
    lines.extend(golds)
    lines.extend(needs)

    lines.extend(
        [
            "first_block((A,B), Ex, InBid) :- "
            "(first_block(A, Ex, InBid) -> true ; first_block(B, Ex, InBid)).",
            "first_block(block(Ex, InBid, _, _), Ex, InBid) :- nonvar(InBid).",
            "origin_inbid(Ex, OutBid, Off, Len, C, InBid) :- "
            "clause(out_block(Ex, OutBid, Off, Len, C), Body), Body \\== true, "
            "call(Body), first_block(Body, Ex, InBid), !.",
            "origin_inbid(Ex, OutBid, _, _, _, InBid) :- "
            "rank_origin(Ex, OutBid, InBid).",
            "painted(E,P,OutBid,C) :- out_block(E,OutBid,Off,Len,C), "
            "origin_inbid(E,OutBid,Off,Len,C,InBid), paint_start(E,InBid,S), "
            "sz_int(Off,Oi), sz_int(Len,Li), Start is S+Oi, End is Start+Li-1, "
            "between(Start, End, P).",
            "overlap(E,P) :- painted(E,P,B1,_), painted(E,P,B2,_), B1 \\= B2.",
            "uncovered(E,P) :- gold(E,P,C), C \\= v0, \\+ painted(E,P,_,_).",
            "extra(E,P) :- painted(E,P,_,_), gold(E,P,v0).",
            "wrong(E,P) :- painted(E,P,_,C), gold(E,P,G), G \\= C.",
            "block_oob :- out_block(E,OutBid,Off,Len,C), "
            "origin_inbid(E,OutBid,Off,Len,C,InBid), paint_start(E,InBid,S), "
            "sz_int(Off,Oi), sz_int(Len,Li), End is S+Oi+Li-1, "
            "(S+Oi < 0 ; \\+ gold(E,End,_)).",
            "dup_bid :- out_block(E,B,O1,L1,C1), out_block(E,B,O2,L2,C2), "
            "(O1 \\= O2 ; L1 \\= L2 ; C1 \\= C2).",
            "extra_head :- out_block(E,B,O,L,C), \\+ need_block(E,B,O,L,C).",
            "missing_head :- need_block(E,B,O,L,C), \\+ out_block(E,B,O,L,C).",
            # Dup/extra always reject (timeout leftovers that double-paint a Bid).
            "non_functional(_Atom) :- dup_bid.",
            "non_functional(_Atom) :- extra_head.",
            # Full paint once every gold need_block is proved.
            "non_functional(_Atom) :- \\+ missing_head, overlap(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, uncovered(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, extra(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, wrong(_,_).",
            "non_functional(_Atom) :- \\+ missing_head, block_oob.",
        ]
    )
    return lines


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
    # Bias + Clingo recalls from input BK only. Paint checker is SWI-only and
    # must not sit in bk.pl (Clingo cannot parse ``:-`` / ``\+`` / ``between``).
    input_bk_text = "\n".join(train_bk) + "\n"
    paint_bk = _paint_constraint_bk(train, typed_roles=True)

    bk_path = out_dir / "bk.pl"
    test_bk_path = out_dir / "test_bk.pl"
    test_path = out_dir / "test.pl"
    exs_object_path = out_dir / "exs_object.pl"

    bk_path.write_text(input_bk_text)
    test_bk_path.write_text("\n".join(test_bk) + "\n")

    labeled_test = [eg for eg in test if eg.out is not None]
    test_exs = _exs_pos_neg(labeled_test) if labeled_test else []
    test_path.write_text("\n".join(test_exs + test_bk) + "\n")

    exs_lines = _exs_out_blocks(train, typed_roles=True)
    # Tester consults exs then bk; keep paint checker with examples (SWI).
    exs_object_path.write_text(
        "\n".join(exs_lines) + "\n" + "\n".join(paint_bk) + "\n"
    )

    from solver.bias_gen import render_object_bias_from_bk

    bias_object_path = out_dir / "bias_object.pl"
    bias_object_path.write_text(
        render_object_bias_from_bk(
            input_bk_text,
            exs_text="\n".join(exs_lines) + "\n",
        )
    )

    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = {}
    for eg in train + test:
        block_geometry[eg.ex_id] = colored_block_geometry_for_row(eg.inp)

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
