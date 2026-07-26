"""Encode ARC JSON into dual pixel/block Popper facts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from solver.grid import Block, flatten, segment_blocks

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
    bk_path: Path
    exs_path: Path
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
    facts: List[str] = []
    blocks = segment_blocks(row)
    w = len(row)
    facts.append(f"block_count({ex},{len(blocks)}).")
    if w:
        facts.append(f"mid({ex},{w // 2}).")
    for i in range(w):
        facts.append(f"from_right({ex},{i},{w - 1 - i}).")
        facts.append(f"mirror_index({ex},{i},{w - 1 - i}).")

    lengths: List[Tuple[int, int]] = []  # (len, id)
    color_counts: Dict[int, int] = {}
    for bid, (s, e, c) in enumerate(blocks):
        facts.append(f"block({ex},{bid},{s},{e},{c}).")
        L = e - s + 1
        facts.append(f"block_len({ex},{bid},{L}).")
        lengths.append((L, bid))
        color_counts[c] = color_counts.get(c, 0) + 1
        if s == 0:
            facts.append(f"touches_edge({ex},{bid},left).")
        if e == w - 1:
            facts.append(f"touches_edge({ex},{bid},right).")

    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            s1, e1, _ = blocks[i]
            s2, e2, _ = blocks[j]
            facts.append(f"left_of({ex},{i},{j}).")
            g = s2 - e1 - 1
            facts.append(f"gap({ex},{i},{j},{g}).")
            if g == 0:
                facts.append(f"adjacent({ex},{i},{j}).")
                facts.append(f"adjacent({ex},{j},{i}).")

    if lengths:
        max_L = max(L for L, _ in lengths)
        min_L = min(L for L, _ in lengths)
        for L, bid in lengths:
            if L == max_L:
                facts.append(f"largest({ex},{bid}).")
            if L == min_L:
                facts.append(f"smallest({ex},{bid}).")
        # dense rank by length descending
        unique_lens = sorted({L for L, _ in lengths}, reverse=True)
        rank = {L: r + 1 for r, L in enumerate(unique_lens)}
        for L, bid in lengths:
            facts.append(f"len_rank({ex},{bid},{rank[L]}).")

    for c, n in color_counts.items():
        facts.append(f"color_count({ex},{c},{n}).")
        if n == 1:
            facts.append(f"unique_color({ex},{c}).")
    return facts


def _arith_ground(max_w: int) -> List[str]:
    """Ground position arithmetic for 0..max_w inclusive (max_position)."""
    facts: List[str] = []
    # positions used are 0..max_w-1 for cells; allow max_w for width constants
    P = max(max_w, 1)
    facts.append(f"max_position({P}).")
    for i in range(P + 1):
        facts.append(f"position({i}).")
    for i in range(10):
        facts.append(f"value({i}).")
        facts.append(f"v{i}({i}).")
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
    # Bridge rules (keeps BK small)
    facts.append("span(S,T,P) :- position(S), position(T), position(P), S =< P, P =< T.")
    facts.append(
        "span_shift(S,T,K,P) :- add(S,K,S2), add(T,K,T2), span(S2,T2,P)."
    )
    return facts


def _exs_pos_neg(train: List[ExampleGrids], max_color: int = 9) -> List[str]:
    pos: List[str] = []
    neg: List[str] = []
    for eg in train:
        assert eg.out is not None
        for i, c in enumerate(eg.out):
            c = int(c)
            if c != 0:
                pos.append(f"pos(out({eg.ex_id},{i},{c})).")
            for v in range(0, max_color + 1):
                if v != c:
                    neg.append(f"neg(out({eg.ex_id},{i},{v})).")
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
    """Write ``bk.pl`` and ``exs.pl`` under ``out_dir``; return EncodeResult."""
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

    bk_lines: List[str] = []
    max_w = 1
    for eg in train + test:
        max_w = max(max_w, len(eg.inp))
        if eg.out is not None:
            max_w = max(max_w, len(eg.out))

    # Emit per-layer across all examples so predicates stay contiguous.
    if include_pixels:
        for eg in train + test:
            bk_lines.extend(_pixel_facts(eg.ex_id, eg.inp))
    if include_blocks:
        for eg in train + test:
            derived = _block_and_derived(eg.ex_id, eg.inp)
            if not include_aggregations:
                agg_names = (
                    "largest",
                    "smallest",
                    "block_count",
                    "color_count",
                    "unique_color",
                    "len_rank",
                )
                derived = [
                    f
                    for f in derived
                    if not any(f.startswith(n + "(") for n in agg_names)
                ]
            bk_lines.extend(derived)

    bk_lines.extend(_arith_ground(max_w))

    bk_path = out_dir / "bk.pl"
    exs_path = out_dir / "exs.pl"
    bk_path.write_text("\n".join(bk_lines) + "\n")
    exs_path.write_text("\n".join(_exs_pos_neg(train)) + "\n")

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
        exs_path=exs_path,
        color_maps=color_maps,
        inv_color_maps=inv_maps,
    )
