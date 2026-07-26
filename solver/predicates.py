"""Frozen predicate inventory for the dual-granularity 1D-ARC solver.

Layers:
  pixel   — raw cells
  block   — maximal same-color runs
  geometry / agg / anchors — derived (precomputed, not learned)
  arith   — successor / order / addition
  bridge  — paint block spans onto pixels
  head    — induction target
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Tuple


@dataclass(frozen=True)
class Predicate:
    name: str
    arity: int
    types: Tuple[str, ...]
    layer: str
    # Ladder levels that expose this as a body_pred (1=trivial unused, 2=block, 3=dual)
    ladder_levels: FrozenSet[int]


PREDICATES: Tuple[Predicate, ...] = (
    # head
    Predicate("out", 3, ("ex", "position", "value"), "head", frozenset()),
    # pixel
    Predicate("in", 3, ("ex", "position", "value"), "pixel", frozenset({3})),
    Predicate("empty", 2, ("ex", "position"), "pixel", frozenset({3})),
    Predicate("width", 2, ("ex", "position"), "pixel", frozenset({2, 3})),
    # block
    Predicate("block", 5, ("ex", "block_id", "position", "position", "value"), "block", frozenset({2, 3})),
    # geometry
    Predicate("block_len", 3, ("ex", "block_id", "position"), "geometry", frozenset({2, 3})),
    Predicate("left_of", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("adjacent", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("gap", 4, ("ex", "block_id", "block_id", "position"), "geometry", frozenset({2, 3})),
    Predicate("touches_edge", 3, ("ex", "block_id", "edge"), "geometry", frozenset({2, 3})),
    # aggregation
    Predicate("largest", 2, ("ex", "block_id"), "agg", frozenset({2, 3})),
    Predicate("smallest", 2, ("ex", "block_id"), "agg", frozenset({2, 3})),
    Predicate("block_count", 2, ("ex", "position"), "agg", frozenset({2, 3})),
    Predicate("color_count", 3, ("ex", "value", "position"), "agg", frozenset({2, 3})),
    Predicate("unique_color", 2, ("ex", "value"), "agg", frozenset({2, 3})),
    Predicate("len_rank", 3, ("ex", "block_id", "position"), "agg", frozenset({2, 3})),
    # anchors
    Predicate("mid", 2, ("ex", "position"), "anchors", frozenset({2, 3})),
    Predicate("mirror_index", 3, ("ex", "position", "position"), "anchors", frozenset({2, 3})),
    Predicate("from_right", 3, ("ex", "position", "position"), "anchors", frozenset({2, 3})),
    # arithmetic
    Predicate("my_succ", 2, ("position", "position"), "arith", frozenset({2, 3})),
    Predicate("lt", 2, ("position", "position"), "arith", frozenset({2, 3})),
    Predicate("add", 3, ("position", "position", "position"), "arith", frozenset({2, 3})),
    # bridges
    Predicate("span", 3, ("position", "position", "position"), "bridge", frozenset({2, 3})),
    Predicate("span_shift", 4, ("position", "position", "position", "position"), "bridge", frozenset({2, 3})),
)


def by_layer(layer: str) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if p.layer == layer)


def body_preds_for_level(level: int) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if level in p.ladder_levels)


def head_pred() -> Predicate:
    return next(p for p in PREDICATES if p.layer == "head")
