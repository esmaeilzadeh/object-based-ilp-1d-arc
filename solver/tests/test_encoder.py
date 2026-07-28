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
    assert "max_vars(12)." in text
    assert "max_body(8)." in text
    assert "max_clauses(2)." in text
    assert ":- not body_var(_,1)." in text
    assert "body_pred(block_start,3)." in text
    assert "body_pred(block_end,3)." in text
    assert "body_pred(block_len,3)." in text
    assert "body_pred(size_add,3)." in text
    assert "body_pred(left_of,3)." in text
    assert "body_pred(adjacent,3)." in text
    assert "body_pred(gap,4)." in text
    assert "body_pred(block_succ,3)." in text
    assert "body_pred(obj_succ,3)." in text
    assert "body_pred(empty_block,3)." in text
    assert "constant(s1, size)." in text
    # Lean: length/agg noise not on object bias for this experiment
    assert "body_pred(shorter,3)." not in text
    assert "body_pred(largest,2)." not in text
    assert "body_pred(offset_pos,3)." not in text
    # No marker/mirror hacks; no pixel-paint bridges
    assert "body_pred(marker_block" not in text
    assert "body_pred(unit_block" not in text
    assert "body_pred(reflect_pos" not in text
    assert "body_pred(reflect_end" not in text
    assert "body_pred(block_marker_gap" not in text
    assert "body_pred(after_block,3)." not in text
    assert "body_pred(gap_cell,5)." not in text
    assert "body_pred(solid_cell,4)." not in text
    assert "constant(c0, position)." not in text
    assert "constant(s0, size)." not in text
    assert "mirrored_out_block" not in text


def test_no_marker_geometry_hacks_in_bk():
    # Former mirror-style row: must not emit banned marker/reflect facts
    row = [4, 4, 4, 4, 4, 0, 9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    facts = _facts(row)
    assert "left_of(0,0,2)." in facts
    assert "block_end(0,0,4)." in facts
    assert "offset_pos(0,2,2)." in facts
    assert "size_add(5,1,6)." in facts
    assert not any(f.startswith("marker_block(") for f in facts)
    assert not any(f.startswith("unit_block(") for f in facts)
    assert not any(f.startswith("reflect_pos(") for f in facts)
    assert not any(f.startswith("reflect_end(") for f in facts)
    assert not any(f.startswith("block_marker_gap(") for f in facts)
    assert not any(f.startswith("between_block_marker(") for f in facts)
    assert not any(f.startswith("same_side_marker(") for f in facts)
    assert not any("mirrored_out_block(" in f for f in facts)
    assert not any("extended_out_block(" in f for f in facts)
    assert not any("shifted_out_block(" in f for f in facts)


def test_pixel_bias_paper_parity():
    from solver.bias_gen import _pixel_only_bias

    text = _pixel_only_bias()
    assert "max_body(20)." in text
    assert ":- not body_var(_,1)." in text
    assert ":- not body_var(_,2)." in text
    assert "body_pred(marker_block" not in text
    assert "body_pred(reflect_pos" not in text


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
    # Train-only learning BK: train ex 0 present, test ex 3 absent.
    assert "in(0," in bk or "empty(0," in bk or "block(0," in bk
    assert "in(3," not in bk
    assert "empty(3," not in bk
    assert "block(3," not in bk
    assert "pixel_block(3," not in bk

    test_bk = enc.test_bk_path.read_text()
    assert "in(3," in test_bk or "empty(3," in test_bk or "block(3," in test_bk
    assert "in(0," not in test_bk
    assert "block(0," not in test_bk

    test_pl = enc.test_path.read_text()
    assert "pos(out(3," in test_pl or "neg(out(3," in test_pl
    assert "in(3," in test_pl or "empty(3," in test_pl or "block(3," in test_pl

    pix = enc.exs_pixel_path.read_text()
    assert "pos(out(" in pix
    assert "out_block(" not in pix

    obj = enc.exs_object_path.read_text()
    assert "pos(out_block(0,2,1,9))." in obj
    assert "pos(out_block(0,3,1,2))." in obj
    assert "pos(out(" not in obj
    assert "block_succ(" not in obj
