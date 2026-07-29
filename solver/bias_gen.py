"""Generate Popper bias files from the predicate inventory."""

from __future__ import annotations

from pathlib import Path
from typing import FrozenSet, Optional, Sequence

from solver.predicates import (
    OBJECT_BODY_ALLOWLIST,
    OBJECT_DENOISE_ALLOWLIST,
    OBJECT_FILL_ALLOWLIST,
    OBJECT_RECOLOR_ALLOWLIST,
    Predicate,
    body_preds_for_level,
    head_pred,
    head_pred_object,
)

_BIAS_DIR = Path(__file__).resolve().parent / "bias"


def _types_block(preds: Sequence[Predicate]) -> str:
    return "\n".join(f"type({p.name},{p.types})." for p in preds)


def _bad_body_for_ex_preds(preds: Sequence[Predicate]) -> str:
    lines = []
    for p in preds:
        if not p.types or p.types[0] != "ex":
            continue
        n = p.arity
        if n < 2 or n > 6:
            continue
        slots = ",".join(["_"] * (n - 1))
        lines.append(
            f"bad_body({p.name}, Vars):- vars(_, Vars), Vars = (V0,{slots}), V0 != 0."
        )
    return "\n".join(lines)


def _constants_for_level(level: int) -> list[str]:
    """Typed constants. Block/object bias omit most position/size constants.

    Object bias (level 4) omits value/position constants — colors bind from
    ``block/4``. Expose ``s1`` only so ILP can write a dedicated length-1 clause.

    Type names are single-quoted so they match ``Predicate.types`` atoms emitted
    by ``_types_block`` (Clingo strings). Unquoted atoms would type-mismatch
    against quoted head types and silently ban constant body literals.
    """
    lines = []
    if level != 4:
        for i in range(10):
            lines.append(f"constant(v{i}, 'value').")
    if level >= 3 and level != 4:
        for i in range(10):
            lines.append(f"constant(c{i}, 'position').")
        for i in range(10):
            lines.append(f"constant(s{i}, 'size').")
        for i in range(1, 10):
            lines.append(f"constant(r{i}, 'rank').")
    if level == 4:
        # Length-1 constant only; colors/sizes bind from block/size_sum3 facts.
        lines.append("constant(s1, 'size').")
    if level != 4:
        lines.append("constant(left, 'edge').")
        lines.append("constant(right, 'edge').")
    return lines


def _render(
    head: Predicate,
    bodies: Sequence[Predicate],
    *,
    max_vars: int,
    max_body: int,
    level: int,
    non_datalog: bool = True,
    include_constants: bool = True,
) -> str:
    all_typed = (head,) + tuple(bodies)
    parts = [
        f"max_vars({max_vars}).",
        f"max_body({max_body}).",
    ]
    # Object-head: keep datalog (head vars must appear in body). non_datalog
    # enabled unsafe Len-unbound clauses like out_block(_,Len,_,_):-block(_,_,Len,_).
    if non_datalog:
        parts.append("non_datalog.")
    parts.extend(
        [
            "",
            f"head_pred({head.name},{head.arity}).",
        ]
    )
    for p in bodies:
        parts.append(f"body_pred({p.name},{p.arity}).")
    if include_constants:
        parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    if include_constants:
        parts.extend(_constants_for_level(level))
        parts.append("")
    parts.append(_types_block(all_typed))
    if include_constants:
        parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(_bad_body_for_ex_preds(bodies))
    parts.append("")
    return "\n".join(parts) + "\n"


def render_bias(level: int, *, max_vars: int, max_body: int) -> str:
    return _render(
        head_pred(),
        body_preds_for_level(level),
        max_vars=max_vars,
        max_body=max_body,
        level=level,
    )


def _object_bias_from_allow(
    allow: FrozenSet[str],
    *,
    max_vars: int,
    max_body: int,
) -> str:
    """Shared object-head bias shape: datalog, single clause, no constants."""
    bodies = tuple(p for p in body_preds_for_level(4) if p.name in allow)
    text = _render(
        head_pred_object(),
        bodies,
        max_vars=max_vars,
        max_body=max_body,
        level=4,
        non_datalog=False,
        include_constants=False,
    )
    extra = (
        "max_clauses(1).\n"
        ":- not body_var(_,1).\n"
        ":- not body_var(_,2).\n"
    )
    lines = text.splitlines(keepends=True)
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.startswith("max_body("):
            out.append(extra)
            inserted = True
    return "".join(out)


def render_object_bias(*, max_vars: int = 10, max_body: int = 5) -> str:
    """Fill-oriented object bias (no ``largest`` — that clutters merge search)."""
    return _object_bias_from_allow(
        OBJECT_FILL_ALLOWLIST, max_vars=max_vars, max_body=max_body
    )


def render_object_denoise_bias(*, max_vars: int = 8, max_body: int = 3) -> str:
    """Denoise-oriented object bias: ``block`` + ``largest`` only."""
    return _object_bias_from_allow(
        OBJECT_DENOISE_ALLOWLIST, max_vars=max_vars, max_body=max_body
    )


def render_object_recolor_bias(
    *,
    max_vars: int = 6,
    max_body: int = 3,
    max_clauses: int = 2,
    include_size_constants: bool = False,
    lean_block_only: bool = False,
) -> str:
    """Recolor-oriented object bias: multi-clause + color constants.

    ``lean_block_only`` drops largest/parity preds (for count→color with
    size constants and ``max_clauses`` ≥ 3).
    """
    allow = frozenset({"block"}) if lean_block_only else OBJECT_RECOLOR_ALLOWLIST
    bodies = tuple(p for p in body_preds_for_level(4) if p.name in allow)
    hp = head_pred_object()
    all_typed = (hp,) + bodies
    parts = [
        f"max_vars({max_vars}).",
        f"max_body({max_body}).",
        f"max_clauses({max_clauses}).",
        "enable_multi_clause.",
        "",
        f"head_pred({hp.name},{hp.arity}).",
    ]
    for p in bodies:
        parts.append(f"body_pred({p.name},{p.arity}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    # Quote type names to match Predicate.types / _types_block (Clingo strings).
    for i in range(10):
        parts.append(f"constant(v{i}, 'value').")
    if include_size_constants:
        for i in range(1, 10):
            parts.append(f"constant(s{i}, 'size').")
    parts.append("")
    type_lines = "\n".join(f"type({p.name},{p.types})." for p in all_typed)
    parts.append(type_lines)
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(_bad_body_for_ex_preds(bodies))
    parts.append("")
    return "\n".join(parts) + "\n"


def _pixel_only_bias() -> str:
    """Paper-parity pixel bias (Decom relational decomposition)."""
    return """max_vars(7).
max_body(20).
non_datalog.

:- not body_var(_,1).
:- not body_var(_,2).

head_pred(out,3).
body_pred(in,3).
body_pred(empty,2).
body_pred(width,2).
body_pred(my_succ,2).
body_pred(lt,2).
body_pred(add,3).
body_pred(C,1):- constant(C,_).

constant(v0, value).
constant(v1, value).
constant(v2, value).
constant(v3, value).
constant(v4, value).
constant(v5, value).
constant(v6, value).
constant(v7, value).
constant(v8, value).
constant(v9, value).
constant(c0, position).
constant(c1, position).
constant(c2, position).
constant(c3, position).
constant(c4, position).
constant(c5, position).
constant(c6, position).
constant(c7, position).
constant(c8, position).
constant(c9, position).

type(out,(ex,position,value)).
type(in,(ex,position,value)).
type(empty,(ex,position)).
type(width,(ex,position)).
type(my_succ,(position,position)).
type(lt,(position,position)).
type(add,(position,position,position)).
type(C,(T,)):- constant(C,T).

bad_body(in, Vars):- vars(_, Vars), Vars = (V0,_,_), V0 != 0.
bad_body(empty, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
bad_body(width, Vars):- vars(_, Vars), Vars = (V0,_), V0 != 0.
"""


def write_bias_files(out_dir: Optional[Path] = None) -> None:
    out_dir = out_dir or _BIAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "block.pl").write_text(render_bias(2, max_vars=8, max_body=12))
    (out_dir / "dual.pl").write_text(render_bias(3, max_vars=9, max_body=16))
    (out_dir / "object.pl").write_text(render_object_bias())
    (out_dir / "object_denoise.pl").write_text(render_object_denoise_bias())
    (out_dir / "object_recolor.pl").write_text(render_object_recolor_bias())
    (out_dir / "object_recolor_sz.pl").write_text(
        render_object_recolor_bias(include_size_constants=True, max_vars=6, max_body=5)
    )
    # Count→color: three size→color clauses; lean vocab keeps search tiny.
    (out_dir / "object_recolor_cnt.pl").write_text(
        render_object_recolor_bias(
            include_size_constants=True,
            lean_block_only=True,
            max_vars=5,
            max_body=3,
            max_clauses=3,
        )
    )
    (out_dir / "pixel.pl").write_text(_pixel_only_bias())


if __name__ == "__main__":
    write_bias_files()
    print("wrote", _BIAS_DIR)
