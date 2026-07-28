"""Encode ARC JSON into dual pixel/block Popper facts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from solver.grid import flatten, segment_all_runs, segment_blocks

PathLike = Union[str, Path]


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
    test_path: Path  # test.pl: pos/neg + test BK (paper-style soft score)
    exs_path: Path  # pixel-head examples (alias of exs_pixel_path)
    exs_pixel_path: Path
    exs_object_path: Path
    bias_hint: str = "dual"
    color_maps: Dict[int, Dict[int, int]] = field(default_factory=dict)  # ex -> role->orig (unused unless canonicalize)
    inv_color_maps: Dict[int, Dict[int, int]] = field(default_factory=dict)


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


def _block_and_derived(ex: int, row: Sequence[int]) -> List[str]:
    """Emit searchable block facts + fully grounded bridges.

    All maximal runs (including color 0) share one left→right ``block_id`` space.
    Colored: ``block(Ex,Id,Len,Color)`` + ``obj_index(Ex,Bid,K)`` (dense nonempty ordinal).
    Empty: ``empty_block(Ex,Id,Len)`` — not ``block(...,0)``.
    Geometry over all run ids; aggregations / paint bridges over colored only.
    """
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

    facts.append(f"block_count({ex},{len(colored_ids)}).")
    facts.append(f"empty_block_count({ex},{len(empty_ids)}).")
    if w:
        facts.append(f"mid({ex},{w // 2}).")
    for i in range(w):
        facts.append(f"from_right({ex},{i},{w - 1 - i}).")
        facts.append(f"mirror_index({ex},{i},{w - 1 - i}).")

    lengths: List[int] = [0] * n_runs  # bid -> length
    colored_lengths: List[Tuple[int, int]] = []  # (len, id) for aggregations
    color_counts: Dict[int, int] = {}
    observed_sizes: set = set()
    obj_k = 0

    for bid, (s, e, c) in enumerate(runs):
        L = e - s + 1
        lengths[bid] = L
        observed_sizes.add(L)
        if s == 0:
            facts.append(f"touches_edge({ex},{bid},left).")
        if e == w - 1:
            facts.append(f"touches_edge({ex},{bid},right).")

        # Generic placement binders (input geometry only; all runs)
        facts.append(f"block_start({ex},{bid},{s}).")
        facts.append(f"block_end({ex},{bid},{e}).")
        if e + 1 < w:
            facts.append(f"after_block({ex},{bid},{e + 1}).")
        if s - 1 >= 0:
            facts.append(f"before_block({ex},{bid},{s - 1}).")

        if c == 0:
            facts.append(f"empty_block({ex},{bid},{L}).")
            for p in range(s, e + 1):
                facts.append(f"pixel_block({ex},{p},{bid}).")
            continue

        facts.append(f"block({ex},{bid},{L},{c}).")
        facts.append(f"block_len({ex},{bid},{L}).")
        facts.append(f"obj_index({ex},{bid},{obj_k}).")
        obj_k += 1
        colored_lengths.append((L, bid))
        color_counts[c] = color_counts.get(c, 0) + 1
        for p in range(s, e + 1):
            facts.append(f"in_block({ex},{bid},{p}).")
            facts.append(f"pixel_block({ex},{p},{bid}).")
            facts.append(f"block_cell({ex},{bid},{p},{c}).")
            if p == s or p == e:
                facts.append(f"block_edge({ex},{bid},{p}).")
                facts.append(f"edge_cell({ex},{bid},{p},{c}).")
            else:
                facts.append(f"interior_cell({ex},{bid},{p},{c}).")

    # Directed successors over runs / nonempty objects
    for i in range(n_runs - 1):
        facts.append(f"block_succ({ex},{i},{i + 1}).")
    for a, b in zip(colored_ids, colored_ids[1:]):
        facts.append(f"obj_succ({ex},{a},{b}).")

    # Length compares over all run ids (empty participates)
    for i in range(n_runs):
        for j in range(n_runs):
            if i == j:
                continue
            Li, Lj = lengths[i], lengths[j]
            if Li < Lj:
                facts.append(f"shorter({ex},{i},{j}).")
            elif Li > Lj:
                facts.append(f"longer({ex},{i},{j}).")
            else:
                facts.append(f"same_len({ex},{i},{j}).")

    # Geometry over all run pairs; gap_cell only when both endpoints colored
    for i in range(n_runs):
        for j in range(i + 1, n_runs):
            s1, e1, c1 = runs[i]
            s2, e2, c2 = runs[j]
            facts.append(f"left_of({ex},{i},{j}).")
            g = s2 - e1 - 1
            facts.append(f"gap({ex},{i},{j},{g}).")
            observed_sizes.add(g)
            if g == 0:
                facts.append(f"adjacent({ex},{i},{j}).")
                facts.append(f"adjacent({ex},{j},{i}).")
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
                facts.append(f"in_gap({ex},{i},{j},{p}).")
                if fill_c is not None:
                    facts.append(f"gap_cell({ex},{i},{j},{p},{fill_c}).")

    # Aggregations over colored runs only
    if colored_lengths:
        max_L = max(L for L, _ in colored_lengths)
        min_L = min(L for L, _ in colored_lengths)
        for L, bid in colored_lengths:
            if L == max_L:
                facts.append(f"largest({ex},{bid}).")
            else:
                facts.append(f"non_largest({ex},{bid}).")
                s, e, c = runs[bid]
                for p in range(s, e + 1):
                    facts.append(f"solid_cell({ex},{bid},{p},{c}).")
            if L == min_L:
                facts.append(f"smallest({ex},{bid}).")
        unique_lens = sorted({L for L, _ in colored_lengths}, reverse=True)
        rank = {L: r + 1 for r, L in enumerate(unique_lens)}
        for L, bid in colored_lengths:
            facts.append(f"len_rank({ex},{bid},{rank[L]}).")

    # Cardinal compares on sizes observed in this example (not position lt)
    sizes = sorted(observed_sizes | {len(colored_ids), len(empty_ids)})
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({a},{b}).")

    # Size addition table (compositional; mirrors position add for object stage).
    size_universe = sorted(set(sizes) | set(range(0, w + 1)))
    for a in size_universe:
        for b in size_universe:
            s = a + b
            if s <= w:
                facts.append(f"size_add({a},{b},{s}).")

    for c, n in color_counts.items():
        facts.append(f"color_count({ex},{c},{n}).")
        if n == 1:
            facts.append(f"unique_color({ex},{c}).")

    facts.extend(_marker_geometry_facts(ex, runs, w, colored_ids, color_counts))
    return facts


def _marker_geometry_facts(
    ex: int,
    runs: Sequence[Tuple[int, int, int]],
    w: int,
    colored_ids: Sequence[int],
    color_counts: Dict[int, int],
) -> List[str]:
    """Marker-centered geometry tools (no precomputed output blocks).

    ``reflect_pos(Ex, M, P, P2)`` uses reflection across marker index M:
    ``P2 = 2*M - P`` when in-bounds (1D-ARC mirror-across-delimiter).
    """
    facts: List[str] = []
    if w <= 0:
        return facts

    # Small offsets as sugar over add (object bias has no c*/add).
    for k in (1, 2, 3):
        for p in range(w):
            if p + k < w:
                facts.append(f"offset_pos({p},{k},{p + k}).")
            if p - k >= 0:
                facts.append(f"offset_pos({p},{k},{p - k}).")

    if not colored_ids:
        return facts

    # Marker = length-1 colored run whose color appears once (delimiter style).
    markers: List[int] = []
    for bid in colored_ids:
        s, e, c = runs[bid]
        if e == s and color_counts.get(c, 0) == 1:
            markers.append(bid)
            facts.append(f"marker_block({ex},{bid}).")

    if not markers:
        return facts

    for mbid in markers:
        ms, me, _mc = runs[mbid]
        # Single-cell marker: reflect across that cell index.
        mpos = ms
        for p in range(w):
            p2 = 2 * mpos - p
            if 0 <= p2 < w:
                facts.append(f"reflect_pos({ex},{mpos},{p},{p2}).")

        for bid in colored_ids:
            if bid == mbid:
                continue
            s, e, _c = runs[bid]
            if e < ms:
                facts.append(f"same_side_marker({ex},{bid},{mbid}).")
                g = ms - e - 1
                facts.append(f"block_marker_gap({ex},{bid},{mbid},{g}).")
                for p in range(e + 1, ms):
                    facts.append(f"between_block_marker({ex},{bid},{mbid},{p}).")
            elif s > me:
                facts.append(f"same_side_marker({ex},{bid},{mbid}).")
                g = s - me - 1
                facts.append(f"block_marker_gap({ex},{bid},{mbid},{g}).")
                for p in range(me + 1, s):
                    facts.append(f"between_block_marker({ex},{bid},{mbid},{p}).")

            if e < ms:
                for other in colored_ids:
                    if other == bid or other == mbid:
                        continue
                    os, oe, _ = runs[other]
                    if os > me:
                        facts.append(f"opp_side_marker({ex},{bid},{other}).")
                        facts.append(f"opp_side_marker({ex},{other},{bid}).")

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


def _bk_lines_for(
    examples: Sequence[ExampleGrids],
    *,
    include_pixels: bool,
    include_blocks: bool,
    include_aggregations: bool,
    max_w: int,
) -> List[str]:
    """Ground pixel/block facts for ``examples`` plus shared arithmetic tables."""
    lines: List[str] = []
    if include_pixels:
        for eg in examples:
            lines.extend(_pixel_facts(eg.ex_id, eg.inp))
    if include_blocks:
        for eg in examples:
            derived = _block_and_derived(eg.ex_id, eg.inp)
            if not include_aggregations:
                derived = [
                    f
                    for f in derived
                    if not any(f.startswith(n + "(") for n in _AGG_NAMES)
                ]
            lines.extend(derived)
    lines.extend(_arith_ground(max_w))
    return lines


def _exs_out_blocks(train: List[ExampleGrids], max_color: int = 9) -> List[str]:
    """Object-head examples: pos/neg ``out_block(Ex, Start, Len, Color)`` only.

    Negatives are compact: wrong color at each true (Start,Len), plus every
    other (Start,Len) paired with each train-output color (not the full
    Start×Len×Color cube — that stalls Popper on long 1D rows).
    """
    pos: List[str] = []
    neg: List[str] = []
    for eg in train:
        assert eg.out is not None
        w = len(eg.out)
        true_blocks: List[Tuple[int, int, int]] = []
        true_set: set = set()
        colors_used: set = set()
        for s, e, c in segment_blocks(eg.out):
            L = e - s + 1
            true_blocks.append((s, L, c))
            true_set.add((s, L, c))
            colors_used.add(c)
            pos.append(f"pos(out_block({eg.ex_id},{s},{L},{c})).")
        # Wrong color at a true span
        for s, L, c in true_blocks:
            for v in range(1, max_color + 1):
                if v != c:
                    neg.append(f"neg(out_block({eg.ex_id},{s},{L},{v})).")
        # Wrong spans using only colors that appear in this output
        if not colors_used:
            continue
        for s in range(w):
            for L in range(1, w - s + 1):
                for c in colors_used:
                    if (s, L, c) not in true_set:
                        neg.append(f"neg(out_block({eg.ex_id},{s},{L},{c})).")
    return pos + neg


def encode_instance(
    src: Union[PathLike, dict],
    out_dir: PathLike,
    *,
    canonicalize_colors: bool = False,
    include_aggregations: bool = True,
    include_blocks: bool = True,
    include_pixels: bool = True,
) -> EncodeResult:
    """Write train ``bk.pl``, test BK / ``test.pl``, and train exs under ``out_dir``.

    Matches the paper repo layout: learning BK is train-input only; test input
    facts live in ``test.pl`` (and ``test_bk.pl`` for apply).
    """
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

    if canonicalize_colors:
        from solver.colors import canonicalize_examples

        train, test, color_maps, inv_maps = canonicalize_examples(train, test)
    else:
        color_maps, inv_maps = {}, {}

    max_w = 1
    for eg in train + test:
        max_w = max(max_w, len(eg.inp))
        if eg.out is not None:
            max_w = max(max_w, len(eg.out))

    bk_kw = dict(
        include_pixels=include_pixels,
        include_blocks=include_blocks,
        include_aggregations=include_aggregations,
        max_w=max_w,
    )
    train_bk = _bk_lines_for(train, **bk_kw)
    test_bk = _bk_lines_for(test, **bk_kw)

    bk_path = out_dir / "bk.pl"
    test_bk_path = out_dir / "test_bk.pl"
    test_path = out_dir / "test.pl"
    exs_pixel_path = out_dir / "exs.pl"
    exs_object_path = out_dir / "exs_object.pl"

    bk_path.write_text("\n".join(train_bk) + "\n")
    test_bk_path.write_text("\n".join(test_bk) + "\n")

    labeled_test = [eg for eg in test if eg.out is not None]
    test_exs = _exs_pos_neg(labeled_test) if labeled_test else []
    # Original layout: pos/neg first, then test BK facts.
    test_path.write_text("\n".join(test_exs + test_bk) + "\n")

    exs_pixel_path.write_text("\n".join(_exs_pos_neg(train)) + "\n")
    exs_object_path.write_text("\n".join(_exs_out_blocks(train)) + "\n")

    # sidecar for harness
    meta = {
        "train": [{"id": e.ex_id, "input": e.inp, "output": e.out} for e in train],
        "test": [{"id": e.ex_id, "input": e.inp, "output": e.out} for e in test],
    }
    (out_dir / "grids.json").write_text(json.dumps(meta))

    return EncodeResult(
        train=train,
        test=test,
        out_dir=out_dir,
        bk_path=bk_path,
        test_bk_path=test_bk_path,
        test_path=test_path,
        exs_path=exs_pixel_path,
        exs_pixel_path=exs_pixel_path,
        exs_object_path=exs_object_path,
        color_maps=color_maps,
        inv_color_maps=inv_maps,
    )
