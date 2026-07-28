"""Tests for out_block → pixel decoder."""

from pathlib import Path

from solver.decode import apply_object_program
from solver.encoder import encode_instance


def test_object_decoder_paints_blocks(tmp_path: Path):
    # Identity-like: output spans share starts with input blocks (bid anchors).
    inst = {
        "train": [
            {"input": [[2, 2, 0, 9]], "output": [[2, 2, 0, 9]]},
        ],
        "test": [{"input": [[2, 2, 0, 9]]}],
    }
    enc = encode_instance(inst, tmp_path / "enc")
    # bids: 0=[2,2], 1=empty, 2=[9]
    prog = "out_block(0,0,2,2).\nout_block(0,2,1,9).\n"
    preds = apply_object_program(
        prog, enc.bk_path, enc.train, block_geometry=enc.block_geometry
    )
    assert preds[0] == [2, 2, 0, 9]


def test_object_decoder_typed_roles(tmp_path: Path):
    enc = encode_instance(
        {
            "train": [{"input": [[7, 0, 7]], "output": [[7, 7, 7]]}],
            "test": [{"input": [[7, 0, 7]]}],
        },
        tmp_path / "enc",
        include_pixels=False,
    )
    assert enc.typed_roles
    # Anchor left colored block b1 (runs: empty b0, color b1, empty? wait [7,0,7]
    # b0=7@0, b1=0@1, b2=7@2 → out merge anchors b0, len 3
    prog = "out_block(0,b0,s3,v7).\n"
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
            "train": [{"input": [[1, 0, 2]], "output": [[1, 0, 2]]}],
            "test": [{"input": [[1, 0, 2]]}],
        },
        tmp_path / "enc",
    )
    # bid0 start0 len3 covers all; bid2 paints cell 2 with other color
    prog = "out_block(0,0,3,1).\nout_block(0,2,1,2).\n"
    try:
        apply_object_program(
            prog, enc.bk_path, enc.train, block_geometry=enc.block_geometry
        )
        assert False, "expected overlap error"
    except ValueError:
        pass
