"""Decom-faithful pixel-road encode (``out/3``). No task-name branches."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import List, Union

from solver.encoder import EncodeResult, ExampleGrids, _load_json
from solver.grid import flatten

PathLike = Union[str, Path]


def _decom():
    p = Path(__file__).resolve().parents[1] / "raw_data" / "onedarcraw" / "decompo_parser.py"
    spec = importlib.util.spec_from_file_location("decompo_parser", p)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ground_bk(instance_facts: str, template: str) -> str:
    import clingo

    solver = clingo.Control(["-Wnone"])
    solver.add("base", [], instance_facts + template)
    solver.ground([("base", [])])
    out = ""
    for x in solver.solve(yield_=True):
        out += "\n" + ".\n".join(str(x).split(" ")) + "\n"
    return out + ".\n"


def _example_facts(eg: ExampleGrids) -> List[str]:
    facts: List[str] = []
    max_i = 0
    for i, x in enumerate(eg.inp):
        x = int(x)
        if x == 0:
            facts.append(f"empty({eg.ex_id},{i}).")
        else:
            facts.append(f"in({eg.ex_id},{i},{x}).")
        max_i = i
    facts.append(f"max_position({max_i + 1}).")
    return facts


def _pixel_exs_neg_gen(examples: List[ExampleGrids], neg_gen: str) -> str:
    """Decom ``json2csv`` exs: nonzero gold ``pos``, clingo ``NEG_GEN`` negs.

    Gold zeros go into the closed-world generator only (so they are not
    learning positives and are not negatives). Positions are ``0..32``.
    """
    import clingo

    learning_pos: List[str] = []
    gen_exs: List[str] = []
    examples_id = set()
    for eg in examples:
        assert eg.out is not None
        examples_id.add(eg.ex_id)
        for i, x in enumerate(eg.out):
            x = int(x)
            line = f"pos(out({eg.ex_id},{i},{x}))."
            gen_exs.append(line)
            if x != 0:
                learning_pos.append(line)

    encoding = neg_gen
    for ex in examples_id:
        encoding += f"example({ex}).\n"
    encoding += "\n".join(gen_exs) + "\n"

    solver = clingo.Control(["-Wnone"])
    solver.add("base", [], encoding)
    solver.ground([("base", [])])
    negs: List[str] = []
    for atom in solver.symbolic_atoms.by_signature("neg", arity=1):
        xs = atom.symbol.arguments[0].arguments
        ex = xs[0].number
        idx = xs[1].number
        try:
            val = xs[2].number
        except Exception:
            val = xs[2].name
        negs.append(f"neg(out({ex},{idx},{val})).")
    return "\n".join(learning_pos + negs) + ("\n" if learning_pos or negs else "")


def encode_pixel_instance(src: Union[PathLike, dict], out_dir: PathLike) -> EncodeResult:
    """Write Decom-style ``bk.pl`` / ``exs.pl`` / ``bias.pl`` for ``out/3``."""
    decom = _decom()
    obj = _load_json(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train: List[ExampleGrids] = []
    for i, pair in enumerate(obj["train"]):
        train.append(ExampleGrids(i, flatten(pair["input"]), flatten(pair["output"])))
    # Decom json2csv enumerates each split from 0 (train and test files are separate).
    test: List[ExampleGrids] = []
    for j, pair in enumerate(obj["test"]):
        out = (
            flatten(pair["output"])
            if "output" in pair and pair["output"] is not None
            else None
        )
        test.append(ExampleGrids(j, flatten(pair["input"]), out))

    inst_train = "\n".join(f for eg in train for f in _example_facts(eg)) + "\n"
    inst_test = "\n".join(f for eg in test for f in _example_facts(eg)) + "\n"
    train_bk = _ground_bk(inst_train, decom.BK)
    test_bk = _ground_bk(inst_test, decom.BK)

    bk_path = out_dir / "bk.pl"
    test_bk_path = out_dir / "test_bk.pl"
    exs_pixel_path = out_dir / "exs.pl"
    bias_pixel_path = out_dir / "bias.pl"
    test_path = out_dir / "test.pl"
    bk_path.write_text(train_bk)
    test_bk_path.write_text(test_bk)
    exs_pixel_path.write_text(_pixel_exs_neg_gen(train, decom.NEG_GEN))
    bias_pixel_path.write_text(decom.BIAS)

    labeled = [eg for eg in test if eg.out is not None]
    test_exs = _pixel_exs_neg_gen(labeled, decom.NEG_GEN) if labeled else ""
    test_path.write_text(test_exs + ("\n" if test_exs else "") + test_bk)

    dummy_object = out_dir / "exs_object.pl"
    dummy_object.write_text("% pixel road: no out_block\n")

    return EncodeResult(
        train=train,
        test=test,
        out_dir=out_dir,
        bk_path=bk_path,
        test_bk_path=test_bk_path,
        test_path=test_path,
        exs_object_path=dummy_object,
        bias_object_path=None,
        typed_roles=False,
        road="pixel",
        exs_pixel_path=exs_pixel_path,
        bias_pixel_path=bias_pixel_path,
    )
