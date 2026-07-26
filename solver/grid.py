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


def segment_blocks(row: Sequence[int]) -> List[Block]:
    """Maximal runs of same non-zero color. Background (0) is not a block.

    Returns list of ``(start, end, color)`` with inclusive indices, ordered left→right.
    Block ids are implicit: index in the returned list.
    """
    blocks: List[Block] = []
    n = len(row)
    i = 0
    while i < n:
        c = int(row[i])
        if c == 0:
            i += 1
            continue
        j = i
        while j + 1 < n and int(row[j + 1]) == c:
            j += 1
        blocks.append((i, j, c))
        i = j + 1
    return blocks
