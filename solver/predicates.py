"""Frozen predicate inventory for the object-only 1D-ARC solver.

Number roles (types — never cross-role arithmetic):
  value    — color symbols
  position — grid ordinals (pixel index / binders)
  size     — cardinals (block lengths, counts)
  block_id — object ordinals
  rank     — length-rank ordinals (1 = longest)

Runtime bias uses object-head exposure only (`body_preds_for_level(4)`).
Entries tagged with other levels are unused legacy inventory and are not a
second solver path.
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
    # Historical exposure tags; runtime object bias filters level 4 only.
    ladder_levels: FrozenSet[int]


PREDICATES: Tuple[Predicate, ...] = (
    # heads
    Predicate("out", 3, ("ex", "position", "value"), "head", frozenset()),
    # Object head: anchor input block id + output length/color (pixel start is decode-only).
    Predicate("out_block", 5, ("ex", "block_id", "size", "size", "value"), "head_object", frozenset()),
    # out_block(E, Bid, Off, Len, Color): paint at start(Bid)+Off.
    # pixel
    Predicate("in", 3, ("ex", "position", "value"), "pixel", frozenset({3})),
    Predicate("empty", 2, ("ex", "position"), "pixel", frozenset({3})),
    Predicate("width", 2, ("ex", "position"), "pixel", frozenset({3})),
    # block / object-head core
    Predicate("block", 4, ("ex", "block_id", "size", "value"), "block", frozenset({2, 3, 4})),
    Predicate("empty_block", 3, ("ex", "block_id", "size"), "block", frozenset({2, 3, 4})),
    Predicate("block_len", 3, ("ex", "block_id", "size"), "geometry", frozenset({3, 4})),
    Predicate("obj_index", 3, ("ex", "block_id", "rank"), "block", frozenset({2, 3, 4})),
    # geometry (object–object)
    Predicate("left_of", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("adjacent", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("gap", 4, ("ex", "block_id", "block_id", "size"), "geometry", frozenset({3, 4})),
    Predicate("touches_edge", 3, ("ex", "block_id", "edge"), "geometry", frozenset({2, 3, 4})),
    Predicate("block_succ", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("obj_succ", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({3, 4})),
    # length comparison
    Predicate("shorter", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("longer", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("same_len", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3, 4})),
    Predicate("size_lt", 2, ("size", "size"), "geometry", frozenset({3, 4})),
    # aggregation
    Predicate("largest", 2, ("ex", "block_id"), "agg", frozenset({2, 3, 4})),
    Predicate("smallest", 2, ("ex", "block_id"), "agg", frozenset({2, 3, 4})),
    Predicate("non_largest", 2, ("ex", "block_id"), "agg", frozenset({2, 3, 4})),
    Predicate("block_count", 2, ("ex", "size"), "agg", frozenset({3})),
    Predicate("empty_block_count", 2, ("ex", "size"), "agg", frozenset({2, 3, 4})),
    Predicate("color_count", 3, ("ex", "value", "size"), "agg", frozenset({3})),
    Predicate("unique_color", 2, ("ex", "value"), "agg", frozenset({2, 3, 4})),
    Predicate("len_rank", 3, ("ex", "block_id", "rank"), "agg", frozenset({3})),
    # anchors
    Predicate("mid", 2, ("ex", "position"), "anchors", frozenset({3})),
    Predicate("mirror_index", 3, ("ex", "position", "position"), "anchors", frozenset({3})),
    Predicate("from_right", 3, ("ex", "position", "position"), "anchors", frozenset({3})),
    # arithmetic (position ordinals — unused on object path unless level 4)
    Predicate("my_succ", 2, ("position", "position"), "arith", frozenset({3})),
    Predicate("lt", 2, ("position", "position"), "arith", frozenset({3})),
    Predicate("add", 3, ("position", "position", "position"), "arith", frozenset({3})),
    # Generic size/position sugar for object stage (not task-shaped transforms)
    Predicate("offset_pos", 3, ("position", "size", "position"), "arith", frozenset({2, 3, 4})),
    Predicate("size_add", 3, ("size", "size", "size"), "arith", frozenset({2, 3, 4})),
    # Ternary size sum for object-head (typed path); not a block-merge prior.
    Predicate("size_sum3", 4, ("size", "size", "size", "size"), "arith", frozenset({4})),
    # Parity on size values — block-neutral, no answer leak.
    Predicate("size_even", 1, ("size",), "arith", frozenset({4})),
    Predicate("size_odd", 1, ("size",), "arith", frozenset({4})),
    # Every-other colored succession (padded-fill pairing); input geometry only.
    Predicate("obj_pair", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({4})),
    # Maximal contiguous non-zero component: leftmost block + pixel span length.
    Predicate("component_start", 2, ("ex", "block_id"), "geometry", frozenset({4})),
    Predicate("component_len", 3, ("ex", "block_id", "size"), "geometry", frozenset({4})),
    # bridges — grounded; hide naked Start/End constants
    Predicate("pixel_block", 3, ("ex", "position", "block_id"), "bridge", frozenset({2, 3})),
    Predicate("in_block", 3, ("ex", "block_id", "position"), "bridge", frozenset({2, 3})),
    Predicate("block_edge", 3, ("ex", "block_id", "position"), "bridge", frozenset({2, 3})),
    Predicate("block_start", 3, ("ex", "block_id", "position"), "bridge", frozenset({3, 4})),
    Predicate("block_end", 3, ("ex", "block_id", "position"), "bridge", frozenset({3, 4})),
    Predicate("after_block", 3, ("ex", "block_id", "position"), "bridge", frozenset({3})),
    Predicate("before_block", 3, ("ex", "block_id", "position"), "bridge", frozenset({3})),
    Predicate("in_gap", 4, ("ex", "block_id", "block_id", "position"), "bridge", frozenset({2, 3})),
    Predicate("block_cell", 4, ("ex", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    Predicate("edge_cell", 4, ("ex", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    Predicate("interior_cell", 4, ("ex", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    # Full paint of non-largest blocks (legacy inventory; not object-head)
    Predicate("solid_cell", 4, ("ex", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    Predicate("gap_cell", 5, ("ex", "block_id", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
)


def by_layer(layer: str) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if p.layer == layer)


def body_preds_for_level(level: int) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if level in p.ladder_levels)


def head_pred() -> Predicate:
    return next(p for p in PREDICATES if p.layer == "head")


def head_pred_object() -> Predicate:
    return next(p for p in PREDICATES if p.layer == "head_object")


# Block-primary / object-head: single lean BK emit vocabulary (no per-category sets).
OBJECT_BODY_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        "block",
        "obj_succ",
        "obj_pair",
        "gap",
        "size_sum3",
        "size_add",
        "size_lt",
        "largest",
        "non_largest",
        "component_start",
        "component_len",
        "size_even",
        "size_odd",
    }
)
