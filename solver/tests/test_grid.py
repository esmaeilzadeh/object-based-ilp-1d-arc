"""Unit tests for grid flatten and block segmentation."""

from solver.grid import flatten, segment_blocks


def test_flatten_nested_and_flat():
    assert flatten([[1, 0, 2]]) == [1, 0, 2]
    assert flatten([1, 0, 2]) == [1, 0, 2]
    assert flatten([]) == []
    assert flatten([[]]) == []


def test_empty_row_no_blocks():
    assert segment_blocks([0, 0, 0]) == []
    assert segment_blocks([]) == []


def test_single_pixel():
    assert segment_blocks([0, 5, 0]) == [(1, 1, 5)]


def test_two_adjacent_different_colors():
    assert segment_blocks([2, 3]) == [(0, 0, 2), (1, 1, 3)]


def test_background_gaps():
    assert segment_blocks([1, 1, 0, 0, 4, 4, 4, 0, 2]) == [
        (0, 1, 1),
        (4, 6, 4),
        (8, 8, 2),
    ]


def test_full_width_block():
    assert segment_blocks([7, 7, 7, 7]) == [(0, 3, 7)]
