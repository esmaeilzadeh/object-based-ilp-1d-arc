"""Unit tests for block encoding (typed roles + grounded bridges)."""

from pathlib import Path

from solver.bias_gen import render_bias, render_object_bias
from solver.encoder import _block_and_derived, encode_instance


def _facts(row):
    return set(_block_and_derived(0, row))


def test_block_atom_is_id_len_color():
    # [2,2,2, 0, 5,5] → colored ids 0 and 2; empty id 1
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "block(0,0,3,2)." in facts
    assert "block(0,2,2,5)." in facts
    assert "empty_block(0,1,1)." in facts
    assert "block(0,1,1,0)." not in facts
    assert "obj_index(0,0,0)." in facts
    assert "obj_index(0,2,1)." in facts
    assert "block_count(0,2)." in facts
    assert "empty_block_count(0,1)." in facts


def test_succ_and_after_block():
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "block_succ(0,0,1)." in facts
    assert "block_succ(0,1,2)." in facts
    assert "obj_succ(0,0,2)." in facts
    assert "after_block(0,0,3)." in facts
    assert "block_start(0,0,0)." in facts
    assert "block_end(0,0,2)." in facts


def test_length_comparisons_and_size_lt():
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "shorter(0,2,0)." in facts
    assert "longer(0,0,2)." in facts
    assert "size_lt(2,3)." in facts


def test_pixel_block_embedding():
    # [0, 7,7,7, 0] → empty 0, colored 1, empty 2
    facts = _facts([0, 7, 7, 7, 0])
    assert "pixel_block(0,1,1)." in facts
    assert "pixel_block(0,2,1)." in facts
    assert "pixel_block(0,3,1)." in facts
    assert "pixel_block(0,0,0)." in facts
    assert "pixel_block(0,4,2)." in facts
    assert "empty_block(0,0,1)." in facts
    assert "empty_block(0,2,1)." in facts


def test_non_largest_and_interior():
    # [2,2,2,2, 0, 5,5] → colored 0 and 2
    facts = _facts([2, 2, 2, 2, 0, 5, 5])
    assert "largest(0,0)." in facts
    assert "non_largest(0,2)." in facts
    assert "solid_cell(0,2,5,5)." in facts
    assert "solid_cell(0,2,6,5)." in facts
    assert not any(f.startswith("solid_cell(0,0,") for f in facts)
    assert "interior_cell(0,0,1,2)." in facts
    assert "edge_cell(0,0,0,2)." in facts


def test_in_gap_and_gap_cell():
    # [2,2,2, 0,0, 5,5] → ids 0 colored, 1 empty, 2 colored
    facts = _facts([2, 2, 2, 0, 0, 5, 5])
    assert "left_of(0,0,2)." in facts
    assert "in_gap(0,0,2,3)." in facts
    assert "gap_cell(0,0,2,3,5)." in facts  # shorter colored endpoint is id 2 color 5
    assert "adjacent(0,0,1)." in facts
    assert "adjacent(0,1,2)." in facts


def test_block_bias_omits_position_and_size_constants():
    text = render_bias(2, max_vars=8, max_body=12)
    assert "constant(v0, value)." in text
    assert "constant(c0, position)." not in text
    assert "constant(s0, size)." not in text
    assert "body_pred(pixel_block,3)." in text
    assert "body_pred(non_largest,2)." in text
    assert "body_pred(interior_cell,4)." in text
    assert "body_pred(solid_cell,4)." in text
    assert "body_pred(empty_block,3)." in text
    assert "body_pred(obj_index,3)." in text
    assert "body_pred(empty_block_count,2)." in text
    assert "body_pred(block_succ,3)." in text
    assert "body_pred(obj_succ,3)." not in text  # object/dual only; keep block bias lean


def test_object_bias_head_and_no_paint_priors():
    text = render_object_bias()
    assert "head_pred(out_block,4)." in text
    assert "head_pred(out,3)." not in text
    assert "body_pred(obj_succ,3)." in text
    assert "body_pred(after_block,3)." in text
    assert "body_pred(block_start,3)." in text
    assert "body_pred(smallest,2)." in text
    assert "body_pred(gap_cell,5)." not in text
    assert "body_pred(solid_cell,4)." not in text
    assert "body_pred(left_of,3)." not in text
    assert "constant(c0, position)." not in text
    assert "constant(v0, value)." not in text


def test_dual_bias_keeps_position_arith_and_rank():
    text = render_bias(3, max_vars=9, max_body=16)
    assert "constant(c0, position)." in text
    assert "constant(r1, rank)." in text
    assert "body_pred(size_lt,2)." in text
    assert "type(len_rank,('ex', 'block_id', 'rank'))." in text
    assert "type(obj_index,('ex', 'block_id', 'rank'))." in text


def test_encode_instance_writes_pixel_and_object_exs(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[0, 0, 9, 2]]},
            {"input": [[5, 0, 1]], "output": [[0, 1, 5]]},
            {"input": [[8, 8, 0, 3]], "output": [[0, 0, 3, 8]]},
        ],
        "test": [{"input": [[7, 7, 7, 0, 4]], "output": [[0, 0, 0, 4, 7]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    assert "pixel_block(" in bk
    assert "empty_block(" in bk
    assert "obj_index(" in bk
    assert "block_succ(" in bk
    assert "after_block(" in bk
    assert "span(" not in bk

    pix = enc.exs_pixel_path.read_text()
    assert "pos(out(" in pix
    assert "out_block(" not in pix

    obj = enc.exs_object_path.read_text()
    assert "pos(out_block(0,2,1,9))." in obj
    assert "pos(out_block(0,3,1,2))." in obj
    assert "pos(out(" not in obj
    assert "block_succ(" not in obj
