"""Census gate: grids only (in and out). No filenames."""

from solver.census import bulky_runs, census_match, unit_runs, zip_offsets
from solver.grid import segment_blocks


def test_match_one_bar_one_unit_both_sides():
    train = [([4, 8, 8, 8, 8, 8, 8, 8], [8, 8, 8, 8, 8, 8, 8, 4])]
    assert census_match(train) is True


def test_match_despite_coloured_pixel_mass_change():
    """Bar grows; bulky and unit counts still 1↔1."""
    train = [([4, 8, 8, 8], [4, 8, 8, 8, 8, 8])]
    assert len(bulky_runs(train[0][0])) == 1
    assert len(bulky_runs(train[0][1])) == 1
    assert census_match(train) is True


def test_false_when_output_drops_units():
    train = [([4, 0, 8, 8, 8, 8, 0, 4], [0, 0, 8, 8, 8, 8, 0, 0])]
    assert census_match(train) is False


def test_false_when_output_gains_a_bar():
    train = [([4, 8, 8, 8], [8, 8, 8, 0, 8, 8, 8])]
    assert census_match(train) is False


def test_all_run_tie_is_not_enough():
    """Seed+bar → two bars: all-runs 2→2, bulky 1→2."""
    inp, out = [4, 8, 8, 8], [8, 8, 8, 0, 8, 8, 8]
    assert len(segment_blocks(inp)) == len(segment_blocks(out)) == 2
    assert len(bulky_runs(inp)) == 1
    assert len(bulky_runs(out)) == 2
    assert census_match([(inp, out)]) is False


def test_false_when_output_splits_bar_into_units():
    train = [([8, 8, 8, 8, 8], [8, 0, 0, 0, 8])]
    assert census_match(train) is False


def test_false_when_output_merges_units_into_a_bar():
    train = [([8, 0, 0, 0, 8], [8, 8, 8, 8, 8])]
    assert census_match(train) is False


def test_false_when_a_unit_appears_on_output():
    train = [([8, 8, 8, 8], [8, 8, 8, 8, 0, 4])]
    assert census_match(train) is False


def test_true_zero_units_both_sides():
    train = [([8, 8, 8, 8, 0, 0], [0, 8, 8, 8, 8, 0])]
    assert unit_runs(train[0][0]) == []
    assert unit_runs(train[0][1]) == []
    assert census_match(train) is True


def test_zip_off_can_be_negative():
    zipped = zip_offsets([(1, 7, 8)], [(0, 6, 8)])
    assert zipped == [(0, -1, 7, 8)]


def test_all_pairs_must_match():
    train = [
        ([4, 8, 8, 8], [8, 8, 8, 4]),
        ([4, 0, 8, 8, 8], [8, 8, 8, 0, 0]),
    ]
    assert census_match(train) is False
