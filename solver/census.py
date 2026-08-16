"""Train-grid census for the hybrid encoding gate (no task names)."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union

from solver.grid import flatten, segment_blocks

Grid = Union[Sequence[int], Sequence[Sequence[int]]]
Span = Tuple[int, int, int]  # start, end, color (inclusive)
Pair = Tuple[Sequence[int], Sequence[int]]


def bulky_runs(row: Sequence[int]) -> List[Span]:
    """Coloured runs with length ≥ 2, left to right."""
    return [(s, e, c) for s, e, c in segment_blocks(row) if (e - s + 1) >= 2]


def unit_runs(row: Sequence[int]) -> List[Span]:
    """Coloured runs with length 1, left to right."""
    return [(s, e, c) for s, e, c in segment_blocks(row) if (e - s + 1) == 1]


def zip_offsets(
    in_spans: Sequence[Span], out_spans: Sequence[Span]
) -> List[Tuple[int, int, int, int]]:
    """Left-to-right zip: ``(in_id, off, out_len, out_color)``.

    ``off = out_start - in_start``. Lengths may differ; counts must match.
    """
    if len(in_spans) != len(out_spans):
        raise ValueError("zip_offsets requires equal span counts")
    out: List[Tuple[int, int, int, int]] = []
    for i, ((in_s, _in_e, _in_c), (out_s, out_e, out_c)) in enumerate(
        zip(in_spans, out_spans)
    ):
        out.append((i, out_s - in_s, out_e - out_s + 1, int(out_c)))
    return out


def _pair_rows(pair: Union[Pair, dict]) -> Pair:
    if isinstance(pair, dict):
        return flatten(pair["input"]), flatten(pair["output"])
    return pair[0], pair[1]


def census_match(train: Iterable[Union[Pair, dict]]) -> bool:
    """True iff every train pair has equal bulky counts and equal unit counts."""
    any_pair = False
    for pair in train:
        any_pair = True
        inp, out = _pair_rows(pair)
        if len(bulky_runs(inp)) != len(bulky_runs(out)):
            return False
        if len(unit_runs(inp)) != len(unit_runs(out)):
            return False
    return any_pair
