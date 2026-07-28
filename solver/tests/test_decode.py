"""Tests for out_block → pixel decoder."""

from pathlib import Path

from solver.decode import apply_object_program
from solver.encoder import encode_instance


def test_object_decoder_paints_blocks(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[0, 0, 9, 2]]},
        ],
        "test": [{"input": [[2, 2, 0, 9]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    prog = "out_block(0,2,1,9).\nout_block(0,3,1,2).\n"
    preds = apply_object_program(prog, enc.bk_path, enc.train)
    assert preds[0] == [0, 0, 9, 2]


def test_object_decoder_typed_roles(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[2, 2, 0, 9]], "output": [[0, 0, 9, 2]]}],
            "test": [{"input": [[2, 2, 0, 9]]}],
        },
        tmp_path / "enc",
        include_pixels=False,
    )
    assert enc.typed_roles
    prog = "out_block(0,p2,s1,v9).\nout_block(0,p3,s1,v2).\n"
    preds = apply_object_program(
        prog, enc.bk_path, enc.train, typed_roles=True
    )
    assert preds[0] == [0, 0, 9, 2]


def test_object_decoder_rejects_overlap(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[1, 0, 2]], "output": [[1, 0, 2]]}],
            "test": [{"input": [[1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    prog = "out_block(0,0,2,1).\nout_block(0,1,2,2).\n"
    try:
        apply_object_program(prog, enc.bk_path, enc.train)
        assert False, "expected overlap error"
    except ValueError:
        pass
