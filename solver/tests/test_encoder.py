"""Unit tests for block encoding (typed roles + grounded bridges)."""

from pathlib import Path

from solver.bias_gen import render_bias
from solver.encoder import _block_and_derived, encode_instance


def _facts(row):
    return set(_block_and_derived(0, row))


def test_block_atom_is_id_len_color():
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "block(0,0,3,2)." in facts
    assert "block(0,1,2,5)." in facts
    assert "block(0,0,0,2,2)." not in facts


def test_length_comparisons_and_size_lt():
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "shorter(0,1,0)." in facts
    assert "longer(0,0,1)." in facts
    assert "size_lt(2,3)." in facts


def test_pixel_block_embedding():
    facts = _facts([0, 7, 7, 7, 0])
    assert "pixel_block(0,1,0)." in facts
    assert "pixel_block(0,2,0)." in facts
    assert "pixel_block(0,3,0)." in facts
    assert "pixel_block(0,0,0)." not in facts


def test_non_largest_and_interior():
    facts = _facts([2, 2, 2, 2, 0, 5, 5])
    assert "largest(0,0)." in facts
    assert "non_largest(0,1)." in facts
    assert "solid_cell(0,1,5,5)." in facts
    assert "solid_cell(0,1,6,5)." in facts
    assert not any(f.startswith("solid_cell(0,0,") for f in facts)
    assert "interior_cell(0,0,1,2)." in facts
    assert "edge_cell(0,0,0,2)." in facts


def test_in_gap_and_gap_cell():
    facts = _facts([2, 2, 2, 0, 0, 5, 5])
    assert "left_of(0,0,1)." in facts
    assert "in_gap(0,0,1,3)." in facts
    assert "gap_cell(0,0,1,3,5)." in facts  # shorter is block 1 color 5


def test_block_bias_omits_position_and_size_constants():
    text = render_bias(2, max_vars=8, max_body=12)
    assert "constant(v0, value)." in text
    assert "constant(c0, position)." not in text
    assert "constant(s0, size)." not in text
    assert "body_pred(pixel_block,3)." in text
    assert "body_pred(non_largest,2)." in text
    assert "body_pred(interior_cell,4)." in text
    assert "body_pred(solid_cell,4)." in text


def test_dual_bias_keeps_position_arith_and_rank():
    text = render_bias(3, max_vars=9, max_body=16)
    assert "constant(c0, position)." in text
    assert "constant(r1, rank)." in text
    assert "body_pred(size_lt,2)." in text
    assert "type(len_rank,('ex', 'block_id', 'rank'))." in text


def test_encode_instance_writes_new_schema(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[1, 1, 0, 2]], "output": [[1, 1, 2, 2]]},
            {"input": [[3, 0, 4, 4]], "output": [[3, 4, 4, 4]]},
            {"input": [[5, 5, 5, 0, 6]], "output": [[5, 5, 5, 6, 6]]},
        ],
        "test": [{"input": [[7, 7, 0, 0, 8]], "output": [[7, 7, 8, 8, 8]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    assert "pixel_block(" in bk
    assert "non_largest(" in bk or "largest(" in bk
    assert "size_lt(" in bk
    assert "span(" not in bk
