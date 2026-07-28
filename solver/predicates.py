"""Frozen predicate inventory for the dual-granularity 1D-ARC solver.

Number roles (types — never cross-role arithmetic):
  value    — color symbols
  position — grid ordinals (pixel index)
  size     — cardinals (block lengths, counts)
  block_id — object ordinals
  rank     — length-rank ordinals (1 = longest)

Ladder levels for body_pred exposure:
  2 = block pixel-head
  3 = dual pixel-head
  4 = object-head (out_block); no pixel-paint priors
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
    # Ladder levels that expose this as a body_pred (2=block, 3=dual, 4=object)
    ladder_levels: FrozenSet[int]


PREDICATES: Tuple[Predicate, ...] = (
    # heads
    Predicate("out", 3, ("ex", "position", "value"), "head", frozenset()),
    Predicate("out_block", 4, ("ex", "position", "size", "value"), "head_object", frozenset()),
    # pixel
    Predicate("in", 3, ("ex", "position", "value"), "pixel", frozenset({3})),
    Predicate("empty", 2, ("ex", "position"), "pixel", frozenset({3})),
    Predicate("width", 2, ("ex", "position"), "pixel", frozenset({3})),
    # block — level 4 = tight object-head body set for searchability
    Predicate("block", 4, ("ex", "block_id", "size", "value"), "block", frozenset({2, 3, 4})),
    Predicate("empty_block", 3, ("ex", "block_id", "size"), "block", frozenset({2, 3})),
    Predicate("block_len", 3, ("ex", "block_id", "size"), "geometry", frozenset({3, 4})),
    Predicate("obj_index", 3, ("ex", "block_id", "rank"), "block", frozenset({2, 3})),
    # geometry
    Predicate("left_of", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("adjacent", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("gap", 4, ("ex", "block_id", "block_id", "size"), "geometry", frozenset({3})),
    Predicate("touches_edge", 3, ("ex", "block_id", "edge"), "geometry", frozenset({2, 3})),
    Predicate("block_succ", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("obj_succ", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({3})),
    # length comparison
    Predicate("shorter", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("longer", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("same_len", 3, ("ex", "block_id", "block_id"), "geometry", frozenset({2, 3})),
    Predicate("size_lt", 2, ("size", "size"), "geometry", frozenset({3})),
    # aggregation
    Predicate("largest", 2, ("ex", "block_id"), "agg", frozenset({2, 3})),
    Predicate("smallest", 2, ("ex", "block_id"), "agg", frozenset({2, 3})),
    Predicate("non_largest", 2, ("ex", "block_id"), "agg", frozenset({2, 3})),
    Predicate("block_count", 2, ("ex", "size"), "agg", frozenset({3})),
    Predicate("empty_block_count", 2, ("ex", "size"), "agg", frozenset({2, 3})),
    Predicate("color_count", 3, ("ex", "value", "size"), "agg", frozenset({3})),
    Predicate("unique_color", 2, ("ex", "value"), "agg", frozenset({2, 3})),
    Predicate("len_rank", 3, ("ex", "block_id", "rank"), "agg", frozenset({3})),
    # anchors
    Predicate("mid", 2, ("ex", "position"), "anchors", frozenset({3})),
    Predicate("mirror_index", 3, ("ex", "position", "position"), "anchors", frozenset({3})),
    Predicate("from_right", 3, ("ex", "position", "position"), "anchors", frozenset({3})),
    # arithmetic (position ordinals only — dual / pixel)
    Predicate("my_succ", 2, ("position", "position"), "arith", frozenset({3})),
    Predicate("lt", 2, ("position", "position"), "arith", frozenset({3})),
    Predicate("add", 3, ("position", "position", "position"), "arith", frozenset({3})),
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
    # Full paint of non-largest blocks (hollow prior baked in) — pixel-head stages only
    Predicate("solid_cell", 4, ("ex", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    Predicate("gap_cell", 5, ("ex", "block_id", "block_id", "position", "value"), "bridge", frozenset({2, 3})),
    # Marker-centered geometry (compositional tools — not precomputed outputs)
    # Level 4 = lean object-head set only
    Predicate("marker_block", 2, ("ex", "block_id"), "marker", frozenset({2, 3, 4})),
    Predicate("unit_block", 2, ("ex", "block_id"), "marker", frozenset({2, 3, 4})),
    Predicate("reflect_pos", 4, ("ex", "position", "position", "position"), "marker", frozenset({2, 3, 4})),
    Predicate(
        "reflect_end",
        4,
        ("ex", "block_id", "block_id", "position"),
        "marker",
        frozenset({2, 3, 4}),
    ),
    Predicate(
        "between_block_marker",
        4,
        ("ex", "block_id", "block_id", "position"),
        "marker",
        frozenset({2, 3}),
    ),
    Predicate(
        "block_marker_gap",
        4,
        ("ex", "block_id", "block_id", "size"),
        "marker",
        frozenset({2, 3, 4}),
    ),
    Predicate(
        "same_side_marker",
        3,
        ("ex", "block_id", "block_id"),
        "marker",
        frozenset({2, 3}),
    ),
    Predicate(
        "opp_side_marker",
        3,
        ("ex", "block_id", "block_id"),
        "marker",
        frozenset({2, 3}),
    ),
    Predicate("offset_pos", 3, ("position", "size", "position"), "marker", frozenset({2, 3, 4})),
    Predicate("size_add", 3, ("size", "size", "size"), "marker", frozenset({2, 3, 4})),
)


def by_layer(layer: str) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if p.layer == layer)


def body_preds_for_level(level: int) -> Tuple[Predicate, ...]:
    return tuple(p for p in PREDICATES if level in p.ladder_levels)


def head_pred() -> Predicate:
    return next(p for p in PREDICATES if p.layer == "head")


def head_pred_object() -> Predicate:
    return next(p for p in PREDICATES if p.layer == "head_object")
