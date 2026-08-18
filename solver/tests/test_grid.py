"""Unit tests for grid flatten and block segmentation."""

from solver.grid import (
    colored_blocks_with_left_margin,
    flatten,
    right_margins_from_left,
    segment_all_runs,
    segment_blocks,
)


def test_flatten_nested_and_flat():
    assert flatten([[1, 0, 2]]) == [1, 0, 2]
    assert flatten([1, 0, 2]) == [1, 0, 2]
    assert flatten([]) == []
    assert flatten([[]]) == []


def test_empty_row_no_blocks():
    assert segment_blocks([0, 0, 0]) == []
    assert segment_blocks([]) == []


def test_segment_all_runs_includes_background():
    assert segment_all_runs([0, 0, 0]) == [(0, 2, 0)]
    assert segment_all_runs([]) == []
    assert segment_all_runs([2, 2, 2, 0, 0, 9]) == [
        (0, 2, 2),
        (3, 4, 0),
        (5, 5, 9),
    ]


def test_segment_blocks_filters_zeros():
    assert segment_blocks([2, 2, 2, 0, 0, 9]) == [(0, 2, 2), (5, 5, 9)]


def test_single_pixel():
    assert segment_blocks([0, 5, 0]) == [(1, 1, 5)]
    assert segment_all_runs([0, 5, 0]) == [(0, 0, 0), (1, 1, 5), (2, 2, 0)]


def test_two_adjacent_different_colors():
    assert segment_blocks([2, 3]) == [(0, 0, 2), (1, 1, 3)]
    assert segment_all_runs([2, 3]) == [(0, 0, 2), (1, 1, 3)]


def test_background_gaps():
    assert segment_blocks([1, 1, 0, 0, 4, 4, 4, 0, 2]) == [
        (0, 1, 1),
        (4, 6, 4),
        (8, 8, 2),
    ]


def test_full_width_block():
    assert segment_blocks([7, 7, 7, 7]) == [(0, 3, 7)]
    assert segment_all_runs([7, 7, 7, 7]) == [(0, 3, 7)]


def test_colored_blocks_with_left_margin():
    assert colored_blocks_with_left_margin([2, 2, 2, 0, 5, 5]) == [
        (0, 3, 2, 0, 2),
        (1, 2, 5, 4, 5),
    ]
    assert colored_blocks_with_left_margin([0, 1, 1, 0, 0]) == [
        (1, 2, 1, 1, 2),
    ]
    assert colored_blocks_with_left_margin([0, 0, 0]) == []
    assert colored_blocks_with_left_margin([8, 8, 8, 4]) == [
        (0, 3, 8, 0, 2),
        (0, 1, 4, 3, 3),
    ]


def test_right_margin_equals_next_left():
    row = [2, 2, 2, 0, 5, 5]
    blocks = colored_blocks_with_left_margin(row)
    rights = right_margins_from_left(blocks, len(row))
    assert rights == [1, 0]  # next Left; trailing 0
    adj = colored_blocks_with_left_margin([8, 8, 8, 4])
    assert right_margins_from_left(adj, 4) == [0, 0]
    one = colored_blocks_with_left_margin([0, 1, 1, 0, 0])
    assert right_margins_from_left(one, 5) == [2]

