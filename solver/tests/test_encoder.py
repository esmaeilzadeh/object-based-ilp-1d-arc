"""Unit tests for block encoding (typed roles + grounded bridges)."""

from pathlib import Path

from solver.bias_gen import render_bias, render_object_bias
from solver.encoder import _block_and_derived, encode_instance


def _facts(row, *, typed_roles: bool = False):
    return set(_block_and_derived(0, row, typed_roles=typed_roles))


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
    assert "constant(v0, 'value')." in text
    assert "constant(c0, 'position')." not in text
    assert "constant(s0, 'size')." not in text
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
    assert "max_vars(10)." in text
    assert "max_body(5)." in text
    assert "max_clauses(1)." in text
    assert ":- not body_var(_,1)." in text
    # Datalog-safe: head vars must appear in body (no Len-unbound junk).
    assert "non_datalog." not in text
    assert "body_pred(block,4)." in text
    assert "body_pred(size_sum3,4)." in text
    assert "body_pred(size_add,3)." not in text
    assert "body_pred(left_of,3)." not in text
    assert "body_pred(gap,4)." in text
    assert "body_pred(obj_succ,3)." in text
    # Fill bias omits largest (denoise stage uses object_denoise.pl).
    assert "body_pred(largest,2)." not in text
    assert "body_pred(block_len,3)." not in text
    assert "body_pred(adjacent,3)." not in text
    assert "body_pred(block_succ,3)." not in text
    assert "body_pred(empty_block,3)." not in text
    assert "constant(s1, 'size')." not in text
    assert "body_pred(C,1)" not in text
    assert "type(out_block,('ex', 'block_id', 'size', 'value'))." in text
    # Pixel starts are decode metadata only
    assert "body_pred(block_start,3)." not in text
    assert "body_pred(block_end,3)." not in text
    # Lean: length/agg noise not on object bias for this experiment
    assert "body_pred(shorter,3)." not in text
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
    assert "constant(c0, 'position')." not in text
    assert "constant(s0, 'size')." not in text
    assert "mirrored_out_block" not in text


def test_object_denoise_bias_is_block_plus_largest():
    from solver.bias_gen import render_object_denoise_bias

    text = render_object_denoise_bias()
    assert "head_pred(out_block,4)." in text
    assert "body_pred(block,4)." in text
    assert "body_pred(largest,2)." in text
    assert "body_pred(component_start,2)." in text
    assert "body_pred(component_len,3)." in text
    assert "body_pred(size_sum3,4)." not in text
    assert "body_pred(gap,4)." not in text
    assert "non_datalog." not in text
    assert "max_clauses(1)." in text
    assert "max_body(4)." in text

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
    assert "constant(c0, 'position')." in text
    assert "constant(r1, 'rank')." in text
    assert "body_pred(size_lt,2)." in text
    assert "type(len_rank,('ex', 'block_id', 'rank'))." in text
    assert "type(obj_index,('ex', 'block_id', 'rank'))." in text


def test_encode_instance_writes_pixel_and_object_exs(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]},
            {"input": [[5, 0, 1]], "output": [[5, 0, 1]]},
            {"input": [[8, 8, 0, 3]], "output": [[8, 8, 0, 3]]},
        ],
        "test": [{"input": [[7, 7, 7, 0, 4]], "output": [[7, 7, 7, 0, 4]]}],
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
    # bid0 len2 color2; bid2 len1 color9
    assert "pos(out_block(0,0,2,2))." in obj
    assert "pos(out_block(0,2,1,9))." in obj
    assert "pos(out(" not in obj
    assert "block_succ(" not in obj
    assert 0 in enc.block_geometry and 0 in enc.block_geometry[0]


def test_typed_roles_on_block_primary_encode(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[7, 0, 7]], "output": [[7, 7, 7]]},
        ],
        "test": [{"input": [[4, 0, 4]], "output": [[4, 4, 4]]}],
    }
    enc = encode_instance(
        inst, tmp_path / "enc", include_pixels=False, include_blocks=True
    )
    assert enc.typed_roles is True
    bk = enc.bk_path.read_text()
    assert "block(0,b0,s1,v7)." in bk
    assert "gap(0,b0,b2,s1)." in bk
    assert "size_sum3(s1,s1,s1,s3)." in bk
    assert "obj_succ(0,b0,b2)." in bk
    assert "largest(0,b0)." in bk
    assert "largest(0,b2)." in bk
    assert "size_add(" not in bk
    assert "left_of(" not in bk
    assert "size_lt(" not in bk
    assert "block(0,0,1,7)." not in bk
    # Lean allowlist only — no empty/run-neighbor clutter
    assert "empty_block(" not in bk
    assert "block_len(" not in bk
    assert "block_succ(" not in bk
    assert "adjacent(" not in bk
    assert "size_atom(" not in bk
    assert "value_atom(" not in bk
    # Neighbor-only gap between empty runs must not appear (obj_succ-only).
    assert "gap(0,b0,b1," not in bk
    assert "gap(0,b1,b2," not in bk
    # No per-cell / paint bridges on block-primary BK
    assert "pixel_block(" not in bk
    assert "in_block(" not in bk
    assert "in_gap(" not in bk
    assert "gap_cell(" not in bk
    assert "block_cell(" not in bk
    assert "offset_pos(" not in bk
    assert "mirror_index(" not in bk
    assert "from_right(" not in bk
    # Pixel starts are Python metadata only
    assert "block_start(" not in bk
    assert "block_end(" not in bk
    assert "mid(" not in bk
    assert "position_atom(" not in bk
    obj = enc.exs_object_path.read_text()
    # Anchor left block b0, merged length 3
    assert "pos(out_block(0,b0,s3,v7))." in obj
    assert "pos(out_block(0,p0,s3,v7))." not in obj
    # Compact negs: wrong color + identity input + wrong observed lens
    assert "neg(out_block(0,b0,s3,v1))." in obj
    assert "neg(out_block(0,b0,s1,v7))." in obj  # identity / wrong len
    assert enc.block_geometry[0][0] == (0, 0)


def test_lean_block_facts_obj_succ_only_gaps():
    facts = _facts([2, 2, 0, 0, 5, 5], typed_roles=True)
    assert "obj_succ(0,b0,b2)." in facts
    assert "gap(0,b0,b2,s2)." in facts
    assert "size_sum3(s2,s2,s2,s6)." in facts
    joined = "\n".join(facts)
    assert "block_succ(" not in joined
    assert "empty_block(" not in joined
    assert "adjacent(" not in joined
    # Neighbor gaps involving empty id b1 must be absent
    assert not any(f.startswith("gap(0,b0,b1,") for f in facts)
    assert not any(f.startswith("gap(0,b1,b2,") for f in facts)
