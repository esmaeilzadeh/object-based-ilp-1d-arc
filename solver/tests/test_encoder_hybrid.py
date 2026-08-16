"""Hybrid encode labels: zip-within-sort, no filenames."""

from pathlib import Path

from solver.census import census_match
from solver.encoder_hybrid import encode_hybrid_block


def test_zip_labels_shifted_bar_and_seed(tmp_path: Path):
    inst = {
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
    assert census_match(inst["train"]) is True
    enc = encode_hybrid_block(inst, tmp_path / "enc")
    block_exs = enc.exs_object_path.read_text()
    unit_exs = enc.exs_unit_path.read_text()
    assert "pos(out_block(0,b0,sm1,s7,v8))." in block_exs
    assert "pos(out_pixel(0,u0,s7,v4))." in unit_exs
    assert "neg(out_block(0,b0," in block_exs and ",s1," in block_exs
    bias_u = enc.bias_unit_path.read_text()
    assert "head_pred(out_pixel,4)." in bias_u
    assert "head_pred(out,3)." not in bias_u
    assert "head_pred(out_block,5)." in enc.bias_object_path.read_text()
    bk = enc.bk_path.read_text()
    assert "block(0,b0,s7,v8)." in bk
    assert "unit(0,u0,v4)." in bk
    assert "sm1(sm1)." in bk
    assert "neg(out_block(0,b0,s0,s7,v8))." in block_exs
    assert "neg(out_pixel(0,u0,s0,v4))." in unit_exs


def test_bk_defines_sm_unaries_for_full_width(tmp_path: Path):
    """Unit negs use Off in [-w,w]; BK must define smK/1 or Popper crashes."""
    row_in = [2, 2, 2] + [0] * 16 + [3]
    row_out = [2] * 18 + [0] + [3]
    inst = {
        "train": [{"input": [row_in], "output": [row_out]}],
        "test": [{"input": [row_in], "output": [row_out]}],
    }
    enc = encode_hybrid_block(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    unit_exs = enc.exs_unit_path.read_text()
    assert "sm16(sm16)." in bk
    assert "sm16" in unit_exs or "s0" in unit_exs
