"""Unit tests for lean typed-role object encoding (left-margin out_block/5)."""

from pathlib import Path

from solver.bias_gen import render_object_bias, render_object_bias_from_bk
from solver.encoder import _block_and_derived, encode_instance
from solver.grid import colored_blocks_with_left_margin
from solver.predicates import PREDICATES


def _facts(row):
    return set(
        _block_and_derived(
            0,
            row,
            typed_roles=True,
            include_cell_bridges=False,
            include_pixel_anchors=False,
        )
    )


def test_lean_block_atoms_typed():
    facts = _facts([2, 2, 2, 0, 5, 5])
    assert "block(0,b0,s0,s3,v2)." in facts
    assert "block(0,b1,s1,s2,v5)." in facts
    assert "obj_succ(0,b0,b1)." in facts
    assert not any(f.startswith("empty_block(") for f in facts)
    assert not any(f.startswith("gap(") for f in facts)
    assert not any(f.startswith("block_succ(") for f in facts)
    assert not any(f.startswith("pixel_block(") for f in facts)
    assert not any(f.startswith("in(") for f in facts)


def test_lean_size_lt_over_observed():
    """size_lt on lean path; sparse size_add includes margin +1."""
    facts = _facts([2, 2, 2, 0, 5, 5])  # lengths 3,2; left margins 0,1
    assert "size_lt(s2,s3)." in facts
    assert any(f.startswith("size_lt(") for f in facts)
    assert "size_add(s1,s0,s1)." in facts or "size_add(s0,s1,s1)." in facts
    assert "size_add(s1,s2,s3)." in facts or "size_add(s1,s1,s2)." in facts


def test_lean_cardinal_ordinal_bridge():
    """S1'b: size constant ↔ position index where values coincide."""
    facts = _facts([1, 1, 1, 0])  # width 4, block length 3, left 0
    assert "cardinal_ordinal(s3,p3)." in facts


def test_object_bias_includes_cardinal_ordinal():
    lean = "block(0,b0,s0,s3,v2).\ncardinal_ordinal(s3,p3).\n"
    text = render_object_bias_from_bk(lean, exs_text="pos(out_block(0,b0,s0,s3,v2)).")
    assert "body_pred(cardinal_ordinal,2)." in text
    assert "type(cardinal_ordinal,('size', 'position'))." in text


def test_object_bias_includes_size_lt():
    lean = "block(0,b0,s0,s3,v2).\nsize_lt(s2,s3).\n"
    text = render_object_bias_from_bk(lean, exs_text="pos(out_block(0,b0,s0,s3,v2)).")
    assert "body_pred(size_lt,2)." in text
    assert "type(size_lt,('size', 'size'))." in text


def test_object_bias_head_only():
    text = render_object_bias()
    assert "head_pred(out_block,5)." in text
    assert "head_pred(out,3)." not in text
    assert "max_vars(10)." in text
    assert "max_body(6)." in text
    assert "body_pred(size_lt,2)." in text
    assert "body_pred(cardinal_ordinal,2)." in text
    assert "body_pred(block,5)." in text
    assert "body_pred(empty_block,3)." not in text
    assert "body_pred(gap,4)." not in text


def test_encode_instance_object_only(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]},
            {"input": [[3, 3, 0, 4]], "output": [[3, 3, 0, 4]]},
        ],
        "test": [{"input": [[5, 0, 6]], "output": [[5, 0, 6]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    assert "pixel_block(" not in bk
    assert "block(" in bk
    assert "empty_block(" not in bk
    assert "gap(" not in bk
    assert enc.bias_object_path is not None
    assert enc.bias_object_path.exists()
    exs = enc.exs_object_path.read_text()
    assert "pos(out_block(0,b0,s0,s2,v1))." in exs
    assert "pos(out_block(0,b1,s1,s1,v2))." in exs
    assert "pos(out_block(0,b1,s1,v0))." not in exs
    assert not (tmp_path / "enc" / "exs.pl").exists()
    assert enc.typed_roles is True
    bias = enc.bias_object_path.read_text()
    assert "head_pred(out_block,5)." in bias
    assert "head_pred(out,3)." not in bias
    assert "not body_literal(C, block, 5, (0,1,_,_,_))" not in bias
    assert "not body_literal(C, block, 5, (0,_,_,_,_))." in bias


def test_object_bias_size_add_on_left_or_len():
    """Left is head var 2, Len is var 3; size_add must touch one of them."""
    text = render_object_bias()
    assert "bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), " in text
    assert "A != 2, B != 2, R != 2, A != 3, B != 3, R != 3." in text


def test_mechanical_bias_from_bk_no_category():
    lean = "block(0,b0,s0,s2,v1).\nobj_succ(0,b0,b1).\n"
    text = render_object_bias_from_bk(lean, exs_text="pos(out_block(0,b0,s0,s2,v1)).")
    assert "body_pred(block,5)." in text
    assert "head_pred(out_block,5)." in text


def test_lean_omits_extrema_and_named_macros():
    """Closed theory: no largest/parity/pairing/component facts."""
    facts = _facts([2, 2, 2, 0, 5, 5, 0, 7])
    banned = (
        "largest(",
        "non_largest(",
        "smallest(",
        "size_even(",
        "size_odd(",
        "obj_pair(",
        "component_start(",
        "component_len(",
        "empty_block(",
        "gap(",
    )
    for prefix in banned:
        assert not any(f.startswith(prefix) for f in facts), prefix
    text = render_object_bias()
    for name in (
        "largest",
        "non_largest",
        "size_even",
        "size_odd",
        "obj_pair",
        "component_start",
        "component_len",
        "empty_block",
        "gap",
    ):
        assert f"body_pred({name}," not in text


def test_predicates_inventory_has_no_size_parity():
    """size_even / size_odd must not exist even as unused inventory."""
    names = {p.name for p in PREDICATES}
    assert "size_even" not in names
    assert "size_odd" not in names


def test_exs_out_blocks_are_colored_with_left_margin(tmp_path: Path):
    inst = {
        "train": [{"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 4]]}],
        "test": [{"input": [[4, 8, 8, 8]], "output": [[8, 8, 8, 4]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    exs = enc.exs_object_path.read_text()
    out_blocks = colored_blocks_with_left_margin([8, 8, 8, 4])
    assert len(out_blocks) == 2
    assert out_blocks[0][0] == 0 and out_blocks[1][0] == 0
    assert "pos(out_block(0,b0,s0,s3,v8))." in exs
    assert "pos(out_block(0,b1,s0,s1,v4))." in exs


def test_move_shaped_left_margin_plus_one(tmp_path: Path):
    inst = {
        "train": [{"input": [[0, 1, 1, 0, 0]], "output": [[0, 0, 1, 1, 0]]}],
        "test": [{"input": [[0, 1, 1, 0, 0]], "output": [[0, 0, 1, 1, 0]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    exs = enc.exs_object_path.read_text()
    assert "block(0,b0,s1,s2,v1)." in bk
    assert "size_add(s1,s1,s2)." in bk
    assert "size_add(s1,s2,s3)." in bk  # +2 closure
    assert "size_add(s1,s3,s4)." in bk  # +3 closure
    assert "pos(out_block(0,b0,s2,s2,v1))." in exs
    assert "neg(out_block(0,b0,s3,s2,v1))." in exs  # full-width wrong Left
    assert "empty_block(" not in bk
