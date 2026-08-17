"""Partition paint oracle: train gold in grids.json, not BK."""

from pathlib import Path

from solver.decode import apply_hybrid_program
from solver.encoder_hybrid import encode_hybrid_block
from solver.paint_check import partition_paint_ok, partition_rows_equal
from solver.verify import grids_equal

_SHIFTED = {
    "train": [
        {
            "input": [[0, 4, 8, 8, 8, 8, 8, 8, 8, 0]],
            "output": [[0, 8, 8, 8, 8, 8, 8, 8, 4, 0]],
        }
    ],
    "test": [
        {
            "input": [[0, 4, 8, 8, 8, 8, 8, 8, 8, 0]],
            "output": [[0, 8, 8, 8, 8, 8, 8, 8, 4, 0]],
        }
    ],
}

GOLD = [0, 8, 8, 8, 8, 8, 8, 8, 4, 0]
BULKY_ONLY = [0, 8, 8, 8, 8, 8, 8, 8, 0, 0]
UNIT_ONLY = [0, 0, 0, 0, 0, 0, 0, 0, 4, 0]


def test_full_row_gold_rejects_correct_bulky_only_paint():
    """Why we slice: a bar-only program leaves the unit as 0."""
    assert grids_equal(BULKY_ONLY, GOLD) is False
    assert partition_rows_equal(BULKY_ONLY, GOLD, "bulky") is True


def test_partition_unit_accepts_seed_and_rejects_bar_or_zero_paint():
    assert partition_rows_equal(UNIT_ONLY, GOLD, "unit") is True
    onto_bar = [0, 4, 0, 0, 0, 0, 0, 0, 4, 0]
    onto_zero = [9, 0, 0, 0, 0, 0, 0, 0, 4, 0]
    assert partition_rows_equal(onto_bar, GOLD, "unit") is False
    assert partition_rows_equal(onto_zero, GOLD, "unit") is False


def test_partition_bulky_rejects_overpaint_onto_unit_or_background():
    onto_unit = [0, 8, 8, 8, 8, 8, 8, 8, 8, 0]
    onto_bg = [8, 8, 8, 8, 8, 8, 8, 8, 0, 0]
    assert partition_rows_equal(onto_unit, GOLD, "bulky") is False
    assert partition_rows_equal(onto_bg, GOLD, "bulky") is False


def test_partition_paint_ok_matches_decode(tmp_path: Path):
    enc = encode_hybrid_block(_SHIFTED, tmp_path / "enc")
    grids = tmp_path / "enc" / "grids.json"
    bulky = "out_block(0,b0,sm1,s7,v8).\n"
    unit = "out_pixel(0,u0,s7,v4).\n"
    assert partition_paint_ok(bulky, enc.bk_path, grids, "bulky") is True
    assert partition_paint_ok(unit, enc.bk_path, grids, "unit") is True
    assert partition_paint_ok(bulky, enc.bk_path, grids, "unit") is False
    over = "out_block(0,b0,sm1,s8,v8).\n"
    assert partition_paint_ok(over, enc.bk_path, grids, "bulky") is False
    onto_bar = "out_pixel(0,u0,s0,v4).\n"
    assert partition_paint_ok(onto_bar, enc.bk_path, grids, "unit") is False
    preds = apply_hybrid_program(
        bulky,
        unit,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
        unit_geometry=enc.unit_geometry,
        extra_offs=enc.observed_offs,
    )
    assert preds[0] == GOLD
