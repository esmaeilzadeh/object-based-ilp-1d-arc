"""Per-example color-role canonicalization."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

from solver.encoder import ExampleGrids


def _role_map(row_in: List[int], row_out: Optional[List[int]]) -> Dict[int, int]:
    counts: Counter = Counter()
    for c in row_in:
        if c:
            counts[c] += 1
    if row_out is not None:
        for c in row_out:
            if c:
                counts[c] += 1
    ordered = sorted(counts.keys(), key=lambda c: (-counts[c], c))
    return {c: i + 1 for i, c in enumerate(ordered)}


def _apply(row: List[int], mapping: Dict[int, int]) -> List[int]:
    return [0 if c == 0 else mapping[c] for c in row]


def canonicalize_examples(
    train: List[ExampleGrids],
    test: List[ExampleGrids],
) -> Tuple[
    List[ExampleGrids],
    List[ExampleGrids],
    Dict[int, Dict[int, int]],
    Dict[int, Dict[int, int]],
]:
    color_maps: Dict[int, Dict[int, int]] = {}
    inv_maps: Dict[int, Dict[int, int]] = {}
    new_train: List[ExampleGrids] = []
    for eg in train:
        m = _role_map(eg.inp, eg.out)
        inv = {r: c for c, r in m.items()}
        color_maps[eg.ex_id] = m
        inv_maps[eg.ex_id] = inv
        new_train.append(
            ExampleGrids(eg.ex_id, _apply(eg.inp, m), _apply(eg.out, m) if eg.out else None)
        )
    new_test: List[ExampleGrids] = []
    for eg in test:
        m = _role_map(eg.inp, eg.out)
        inv = {r: c for c, r in m.items()}
        color_maps[eg.ex_id] = m
        inv_maps[eg.ex_id] = inv
        new_test.append(
            ExampleGrids(
                eg.ex_id,
                _apply(eg.inp, m),
                _apply(eg.out, m) if eg.out is not None else None,
            )
        )
    return new_train, new_test, color_maps, inv_maps
