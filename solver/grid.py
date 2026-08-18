"""1D grid helpers: flatten ARC nested lists and segment color blocks."""

from __future__ import annotations

from typing import List, Sequence, Tuple, Union

Grid = Union[Sequence[int], Sequence[Sequence[int]]]
Block = Tuple[int, int, int]  # start, end, color (inclusive indices)


def flatten(grid: Grid) -> List[int]:
    """Accept ``[[...]]`` or ``[...]`` and return a flat 1D row of ints."""
    if not grid:
        return []
    first = grid[0]
    if isinstance(first, (list, tuple)):
        if len(grid) != 1:
            # 1D-ARC uses a single row wrapped as [[...]]; if multiple rows, flatten row-major
            row: List[int] = []
            for r in grid:
                row.extend(int(x) for x in r)  # type: ignore[arg-type]
            return row
        return [int(x) for x in first]  # type: ignore[arg-type]
    return [int(x) for x in grid]  # type: ignore[arg-type]


def segment_all_runs(row: Sequence[int]) -> List[Block]:
    """Maximal runs of the same color, including background 0.

    Returns list of ``(start, end, color)`` with inclusive indices, ordered left→right.
    Run ids are implicit: index in the returned list (shared with empty + colored).
    """
    blocks: List[Block] = []
    n = len(row)
    i = 0
    while i < n:
        c = int(row[i])
        j = i
        while j + 1 < n and int(row[j + 1]) == c:
            j += 1
        blocks.append((i, j, c))
        i = j + 1
    return blocks


def segment_blocks(row: Sequence[int]) -> List[Block]:
    """Maximal runs of same non-zero color. Background (0) is not a colored block.

    Returns list of ``(start, end, color)`` with inclusive indices, ordered left→right.
    """
    return [b for b in segment_all_runs(row) if b[2] != 0]


# left_margin, length, color, start, end (inclusive)
MarginBlock = Tuple[int, int, int, int, int]


def colored_blocks_with_left_margin(row: Sequence[int]) -> List[MarginBlock]:
    """Colored runs as ``(left_margin, length, color, start, end)``, L→R.

    ``left_margin`` is the number of background cells immediately to the left of
    the run: the leading pad for the first object, otherwise the gap to the
    previous colored run. Trailing zeros are not stored; they are the unpainted
    canvas remainder at decode time.
    """
    out: List[MarginBlock] = []
    prev_end = -1
    for s, e, c in segment_blocks(row):
        left = s - prev_end - 1
        length = e - s + 1
        out.append((left, length, int(c), s, e))
        prev_end = e
    return out
