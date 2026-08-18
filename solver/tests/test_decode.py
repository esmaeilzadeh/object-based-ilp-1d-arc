"""Tests for out_block → pixel decoder."""

from pathlib import Path

import pytest

from solver.decode import apply_object_program
from solver.encoder import encode_instance


def test_object_decoder_paints_blocks(tmp_path: Path):
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]},
        ],
        "test": [{"input": [[2, 2, 0, 9]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    prog = "out_block(0,b0,s0,s2,v2).\nout_block(0,b1,s0,s1,v9).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert preds[0] == [2, 2, 0, 9]


def test_object_decoder_typed_roles(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[7, 0, 7]], "output": [[7, 7, 7]]}],
            "test": [{"input": [[7, 0, 7]]}],
        },
        tmp_path / "enc",
    )
    assert enc.typed_roles
    prog = "out_block(0,b0,s0,s3,v7).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert preds[0] == [7, 7, 7]


def test_object_decoder_rejects_overlap(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[1, 1, 0, 2]], "output": [[1, 1, 0, 2]]}],
            "test": [{"input": [[1, 1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    prog = "out_block(0,b0,s0,s3,v1).\nout_block(0,b0,s1,s2,v2).\n"
    with pytest.raises(ValueError):
        apply_object_program(
            prog,
            enc.bk_path,
            enc.train,
            typed_roles=True,
            block_geometry=enc.block_geometry,
        )


def test_train_then_test_apply_uses_fresh_engine(tmp_path: Path):
    """Consulting train bk then test_bk in one janus engine can SIGSEGV.

    Public apply_object_program must isolate each consult in a subprocess.
    """
    enc = encode_instance(
        {
            "train": [{"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]}],
            "test": [{"input": [[9, 0, 2, 2]], "output": [[9, 0, 2, 2]]}],
        },
        tmp_path / "enc",
    )
    train_prog = "out_block(0,b0,s0,s2,v2).\nout_block(0,b1,s0,s1,v9).\n"
    test_prog = "out_block(1,b0,s0,s1,v9).\nout_block(1,b1,s0,s2,v2).\n"
    train_preds = apply_object_program(
        train_prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    test_preds = apply_object_program(
        test_prog,
        enc.test_bk_path,
        enc.test,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert train_preds[0] == [2, 2, 0, 9]
    assert test_preds[1] == [9, 0, 2, 2]


def test_object_decoder_uses_body_inbid(tmp_path: Path):
    """Paint origin is the block/4 InBid the clause proves, not OutBid."""
    enc = encode_instance(
        {
            "train": [{"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]}],
            "test": [{"input": [[2, 2, 0, 9]]}],
        },
        tmp_path / "enc",
    )
    # OutBid b0, Off=0, copy the 9 from input b2 → paint at start(b2)=3.
    prog = "out_block(A,b0,s0,s1,v9) :- block(A,b2,s1,v9).\n"
    preds = apply_object_program(
        prog,
        enc.bk_path,
        enc.train,
        typed_roles=True,
        block_geometry=enc.block_geometry,
    )
    assert preds[0] == [0, 0, 0, 9]
