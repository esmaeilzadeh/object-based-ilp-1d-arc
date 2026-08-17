"""Hybrid block-road encode: bulky Bids + unit Pids, zip-within-sort labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple, Union

from solver.bias_gen import render_object_bias_from_bk, render_unit_bias_from_bk
from solver.census import bulky_runs, unit_runs, zip_offsets
from solver.encoder import (
    EncodeResult,
    ExampleGrids,
    _bid,
    _col,
    _exs_pos_neg,
    _load_json,
    _sz,
    _uid,
)
from solver.grid import flatten

PathLike = Union[str, Path]


def _hybrid_input_facts(
    ex: int,
    row: Sequence[int],
    *,
    extra_offs: Sequence[int] = (),
) -> List[str]:
    """Bulky ``block/4`` with dense ids; ``unit/3`` for length-1 runs."""
    t = True
    facts: List[str] = []
    bulky = bulky_runs(row)
    units = unit_runs(row)
    w = len(row)
    observed: Set[int] = set([0, 1])
    lengths: List[int] = []

    for bid, (s, e, c) in enumerate(bulky):
        L = e - s + 1
        lengths.append(L)
        observed.add(L)
        facts.append(f"block({ex},{_bid(bid, t)},{_sz(L, t)},{_col(c, t)}).")

    for pid, (_s, _e, c) in enumerate(units):
        facts.append(f"unit({ex},{_uid(pid, t)},{_col(c, t)}).")

    for a in range(len(bulky) - 1):
        b = a + 1
        facts.append(f"obj_succ({ex},{_bid(a, t)},{_bid(b, t)}).")
        _s1, e1, _ = bulky[a]
        s2, _e2, _ = bulky[b]
        g = s2 - e1 - 1
        observed.add(g)
        facts.append(f"gap({ex},{_bid(a, t)},{_bid(b, t)},{_sz(g, t)}).")
        La, Lb = lengths[a], lengths[b]
        total = La + g + Lb
        if total <= w:
            facts.append(
                f"size_sum3({_sz(La, t)},{_sz(g, t)},{_sz(Lb, t)},{_sz(total, t)})."
            )
        for x, y in ((La, g), (1, g)):
            ssum = x + y
            if ssum <= w and x >= 0 and y >= 0:
                facts.append(f"size_add({_sz(x, t)},{_sz(y, t)},{_sz(ssum, t)}).")
                observed.add(ssum)

    for L in lengths:
        if L >= 2 and L <= w:
            facts.append(f"size_add({_sz(1, t)},{_sz(L - 1, t)},{_sz(L, t)}).")
            observed.add(L - 1)

    for off in extra_offs:
        observed.add(abs(off))
        if off < 0:
            k = abs(off)
            facts.append(f"{_sz(off, t)}({_sz(off, t)}).")
            facts.append(f"size_add({_sz(off, t)},{_sz(k, t)},{_sz(0, t)}).")
            facts.append(f"size_add({_sz(k, t)},{_sz(off, t)},{_sz(0, t)}).")

    sizes = sorted(s for s in observed if s >= 0)
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({_sz(a, t)},{_sz(b, t)}).")
    for i in sizes:
        if 0 <= i < w:
            facts.append(f"cardinal_ordinal({_sz(i, t)},p{i}).")

    for i in range(10):
        facts.append(f"v{i}(v{i}).")
    for i in range(w + 1):
        facts.append(f"s{i}(s{i}).")
    # Same width-uniform unaries as s{i}: bias can mention smK from exs negs.
    for i in range(1, w + 1):
        facts.append(f"sm{i}(sm{i}).")
    return facts


def _gold_bar_cells(out_row: Sequence[int]) -> Set[int]:
    cells: Set[int] = set()
    for s, e, _c in bulky_runs(out_row):
        cells.update(range(s, e + 1))
    return cells


def _dedupe(lines: List[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def _exs_hybrid_blocks(
    train: List[ExampleGrids],
    max_color: int = 9,
) -> Tuple[List[str], List[str], List[int]]:
    """Partitioned pos/neg for ``out_block/5`` and ``out_pixel/4``."""
    t = True
    block_pos: List[str] = []
    block_neg: List[str] = []
    unit_pos: List[str] = []
    unit_neg: List[str] = []
    all_offs: List[int] = [0]

    for eg in train:
        assert eg.out is not None
        in_b, out_b = bulky_runs(eg.inp), bulky_runs(eg.out)
        in_u, out_u = unit_runs(eg.inp), unit_runs(eg.out)
        w = len(eg.out)
        true_b: Set[Tuple[int, int, int, int]] = set()
        true_u: Set[Tuple[int, int, int]] = set()
        bar_cells = _gold_bar_cells(eg.out)

        for bid, off, L, c in zip_offsets(in_b, out_b):
            all_offs.append(off)
            true_b.add((bid, off, L, c))
            block_pos.append(
                f"pos(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off, t)},{_sz(L, t)},{_col(c, t)}))."
            )
        for pid, off, _L, c in zip_offsets(in_u, out_u):
            all_offs.append(off)
            true_u.add((pid, off, c))
            unit_pos.append(
                f"pos(out_pixel({eg.ex_id},{_uid(pid, t)},{_sz(off, t)},{_col(c, t)}))."
            )

        for bid in range(len(in_b)):
            for off in sorted(set(all_offs) | set(range(0, min(w, 8) + 1))):
                for c in range(1, max_color + 1):
                    if (bid, off, 1, c) not in true_b:
                        block_neg.append(
                            f"neg(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off, t)},{_sz(1, t)},{_col(c, t)}))."
                        )

        off_cands = sorted(set(range(0, w + 1)) | {o for o in all_offs})
        for bid, off, L, c in true_b:
            for v in range(1, max_color + 1):
                if v != c:
                    block_neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off, t)},{_sz(L, t)},{_col(v, t)}))."
                    )
            for L2 in range(2, min(w, 12) + 1):
                if L2 != L and (bid, off, L2, c) not in true_b:
                    block_neg.append(
                        f"neg(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off, t)},{_sz(L2, t)},{_col(c, t)}))."
                    )
            for off2 in off_cands:
                if off2 == off:
                    continue
                if (bid, off2, L, c) in true_b:
                    continue
                block_neg.append(
                    f"neg(out_block({eg.ex_id},{_bid(bid, t)},{_sz(off2, t)},{_sz(L, t)},{_col(c, t)}))."
                )
        for pid, off, c in true_u:
            for off2 in off_cands:
                if off2 == off:
                    continue
                if (pid, off2, c) in true_u:
                    continue
                unit_neg.append(
                    f"neg(out_pixel({eg.ex_id},{_uid(pid, t)},{_sz(off2, t)},{_col(c, t)}))."
                )

        for pid, off, c in true_u:
            for v in range(1, max_color + 1):
                if v != c:
                    unit_neg.append(
                        f"neg(out_pixel({eg.ex_id},{_uid(pid, t)},{_sz(off, t)},{_col(v, t)}))."
                    )

        for pid, (us, _ue, _uc) in enumerate(in_u):
            for off2 in range(-w, w + 1):
                paint = us + off2
                if paint in bar_cells:
                    for c in range(1, max_color + 1):
                        if (pid, off2, c) not in true_u:
                            unit_neg.append(
                                f"neg(out_pixel({eg.ex_id},{_uid(pid, t)},{_sz(off2, t)},{_col(c, t)}))."
                            )

    offs = sorted(set(all_offs))
    return _dedupe(block_pos + block_neg), _dedupe(unit_pos + unit_neg), offs


def encode_hybrid_block(
    src: Union[PathLike, dict],
    out_dir: PathLike,
) -> EncodeResult:
    """Encode the census-match road: bulky zip + unit zip."""
    obj = _load_json(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train: List[ExampleGrids] = []
    for i, pair in enumerate(obj["train"]):
        train.append(ExampleGrids(i, flatten(pair["input"]), flatten(pair["output"])))
    test: List[ExampleGrids] = []
    base = len(train)
    for j, pair in enumerate(obj["test"]):
        out = (
            flatten(pair["output"])
            if "output" in pair and pair["output"] is not None
            else None
        )
        test.append(ExampleGrids(base + j, flatten(pair["input"]), out))

    block_lines, unit_lines, offs = _exs_hybrid_blocks(train)

    def bk_for(examples: Sequence[ExampleGrids]) -> List[str]:
        lines: List[str] = []
        for eg in examples:
            lines.extend(_hybrid_input_facts(eg.ex_id, eg.inp, extra_offs=offs))
        return sorted(set(lines))

    train_bk = bk_for(train)
    test_bk = bk_for(test)
    bk_path = out_dir / "bk.pl"
    test_bk_path = out_dir / "test_bk.pl"
    bk_path.write_text("\n".join(train_bk) + "\n")
    test_bk_path.write_text("\n".join(test_bk) + "\n")

    exs_object_path = out_dir / "exs_object.pl"
    exs_unit_path = out_dir / "exs_unit.pl"
    exs_object_path.write_text("\n".join(block_lines) + "\n")
    exs_unit_path.write_text("\n".join(unit_lines) + "\n")

    bias_object_path = out_dir / "bias_object.pl"
    bias_unit_path = out_dir / "bias_unit.pl"
    bias_object_path.write_text(
        render_object_bias_from_bk(
            bk_path.read_text(), exs_text=exs_object_path.read_text()
        )
    )
    bias_unit_path.write_text(
        render_unit_bias_from_bk(bk_path.read_text(), exs_text=exs_unit_path.read_text())
    )

    labeled_test = [eg for eg in test if eg.out is not None]
    test_path = out_dir / "test.pl"
    test_exs = _exs_pos_neg(labeled_test) if labeled_test else []
    test_path.write_text("\n".join(test_exs + test_bk) + "\n")

    block_geometry: Dict[int, Dict[int, Tuple[int, int]]] = {}
    unit_geometry: Dict[int, Dict[int, int]] = {}
    for eg in train + test:
        block_geometry[eg.ex_id] = {
            i: (s, e) for i, (s, e, _c) in enumerate(bulky_runs(eg.inp))
        }
        unit_geometry[eg.ex_id] = {
            i: s for i, (s, _e, _c) in enumerate(unit_runs(eg.inp))
        }

    meta = {
        "train": [{"id": e.ex_id, "input": e.inp, "output": e.out} for e in train],
        "test": [{"id": e.ex_id, "input": e.inp, "output": None} for e in test],
        "typed_roles": True,
        "block_geometry": {
            str(eid): {str(b): [s, e] for b, (s, e) in geo.items()}
            for eid, geo in block_geometry.items()
        },
        "unit_geometry": {
            str(eid): {str(u): s for u, s in geo.items()}
            for eid, geo in unit_geometry.items()
        },
        "observed_offs": list(offs),
        "road": "hybrid_block",
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
        unit_geometry=unit_geometry,
        observed_offs=offs,
        exs_unit_path=exs_unit_path,
        bias_unit_path=bias_unit_path,
        road="hybrid_block",
    )
