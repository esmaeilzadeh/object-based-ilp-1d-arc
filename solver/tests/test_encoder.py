"""Unit tests for lean typed-role object encoding."""

from pathlib import Path

from solver.bias_gen import render_object_bias, render_object_bias_from_bk
from solver.encoder import _block_and_derived, encode_instance


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
    assert "block(0,b0,s3,v2)." in facts
    assert "block(0,b2,s2,v5)." in facts
    assert "obj_succ(0,b0,b2)." in facts
    assert not any(f.startswith("pixel_block(") for f in facts)
    assert not any(f.startswith("empty_block(") for f in facts)
    assert not any(f.startswith("in(") for f in facts)


def test_lean_size_lt_over_observed():
    """S1a: size_lt on lean path; sparse size_add unchanged."""
    facts = _facts([2, 2, 2, 0, 5, 5])  # lengths 3,2; gap 1
    assert "size_lt(s2,s3)." in facts
    assert any(f.startswith("size_lt(") for f in facts)
    # Sparse size_add still present (not dense width²).
    assert "size_add(s1,s2,s3)." in facts or "size_add(s1,s1,s2)." in facts


def test_lean_cardinal_ordinal_bridge():
    """S1'b: size constant ↔ position index where values coincide."""
    facts = _facts([1, 1, 1, 0])  # width 4, block length 3
    assert "cardinal_ordinal(s3,p3)." in facts


def test_object_bias_includes_cardinal_ordinal():
    lean = "block(0,b0,s3,v2).\ncardinal_ordinal(s3,p3).\n"
    text = render_object_bias_from_bk(lean, exs_text="pos(out_block(0,b0,s0,s3,v2)).")
    assert "body_pred(cardinal_ordinal,2)." in text
    assert "type(cardinal_ordinal,('size', 'position'))." in text


def test_object_bias_includes_size_lt():
    lean = "block(0,b0,s3,v2).\nsize_lt(s2,s3).\n"
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
    assert enc.bias_object_path is not None
    assert enc.bias_object_path.exists()
    assert "out_block(" in enc.exs_object_path.read_text()
    assert not (tmp_path / "enc" / "exs.pl").exists()
    assert enc.typed_roles is True
    bias = enc.bias_object_path.read_text()
    assert "head_pred(out_block,5)." in bias
    assert "head_pred(out,3)." not in bias


def test_object_bias_size_add_bidirectional():
    """S6: size_add legal if any arg is head Off/Len (compute or check)."""
    text = render_object_bias()
    assert "bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), " in text
    assert "A != 2, A != 3, B != 2, B != 3, R != 2, R != 3." in text
    # Old result-only guard must be gone.
    assert "Vars = (_,_,R), R != 2, R != 3." not in text
    assert "Vars = (_,_,_,R), R != 2, R != 3." not in text
    assert "bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), " in text


def test_mechanical_bias_from_bk_no_category():
    lean = "block(0,b0,s2,v1).\nobj_succ(0,b0,b2).\n"
    text = render_object_bias_from_bk(lean, exs_text="pos(out_block(0,b0,s0,s2,v1)).")
    assert "body_pred(block,4)." in text
    assert "head_pred(out_block,5)." in text


def test_sz_negative_is_smk():
    from solver.encoder import _sz

    assert _sz(-1, True) == "sm1"
    assert _sz(-2, True) == "sm2"
    assert _sz(0, True) == "s0"
    assert _sz(-1, False) == "-1"


def test_anchor_flip_same_color_grow_left():
    from solver.encoder import anchor_input_block_offset

    inp = [0] * 13 + [4] + [8] * 7 + [0] * 4
    bid, off = anchor_input_block_offset(inp, 13, 19, 8)
    assert off == -1
    runs = [(i, s) for i, (s, _e, c) in enumerate(
        __import__("solver.grid", fromlist=["segment_all_runs"]).segment_all_runs(inp)
    ) if c == 8]
    assert bid == runs[0][0]
    bid_u, off_u = anchor_input_block_offset(inp, 20, 20, 4)
    assert bid_u != bid
    assert off_u == 7


def test_anchor_pcopy_1c_unique_template():
    import json
    from pathlib import Path

    from solver.encoder import anchor_input_block_offset
    from solver.grid import flatten, segment_blocks

    obj = json.loads(
        Path("raw_data/onedarcraw/dataset/1d_pcopy_1c/1d_pcopy_1c_0.json").read_text()
    )
    inp = flatten(obj["train"][1]["input"])
    out = flatten(obj["train"][1]["output"])
    # Later L=3 copy should parent to the unique L=3 template, not an L=1 seed.
    spans = list(segment_blocks(out))
    s, e, c = spans[-1]
    bid, off = anchor_input_block_offset(inp, s, e, c)
    from solver.grid import segment_all_runs

    tmpl = max(
        [(i, st, en, col) for i, (st, en, col) in enumerate(segment_all_runs(inp)) if col],
        key=lambda r: r[2] - r[1],
    )
    assert bid == tmpl[0]
    assert off == s - tmpl[1]
    assert off > 0


def test_anchor_pcopy_mc_seed_not_template():
    from solver.encoder import anchor_input_block_offset

    inp = [0, 0, 1, 1, 1, 0, 0, 4, 0]
    bid, off = anchor_input_block_offset(inp, 6, 8, 4)
    assert off == -1
    from solver.grid import segment_all_runs

    seed = [i for i, (s, e, c) in enumerate(segment_all_runs(inp)) if c == 4][0]
    assert bid == seed


def test_encode_flip_emits_sm1(tmp_path: Path):
    inst = {
        "train": [
            {
                "input": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0]],
                "output": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 8, 8, 8, 8, 8, 8, 4, 0, 0, 0, 0]],
            }
        ],
        "test": [
            {
                "input": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0]],
                "output": [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 8, 8, 8, 8, 8, 8, 8, 4, 0, 0, 0, 0]],
            }
        ],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    bk = enc.bk_path.read_text()
    test_bk = enc.test_bk_path.read_text()
    bias = enc.bias_object_path.read_text()
    exs = enc.exs_object_path.read_text()
    assert "sm1(sm1)." in bk
    assert "sm1(sm1)." in test_bk
    assert "constant(sm1, 'size')." in bias
    assert "sm1" in exs
    assert "s-1" not in exs


def test_encode_identity_no_smk(tmp_path: Path):
    inst = {
        "train": [{"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]}],
        "test": [{"input": [[3, 0, 4]], "output": [[3, 0, 4]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    assert "sm1(sm1)." not in enc.bk_path.read_text()
    assert "constant(sm1, 'size')." not in enc.bias_object_path.read_text()
