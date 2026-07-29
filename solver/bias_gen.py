"""Generate Popper bias files.

Object bias is a uniform mechanical transform of an instance's BK/exs:
body preds and constants are taken from facts that appear there — never from
category / task name.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import FrozenSet, Optional, Sequence, Set

from solver.predicates import (
    OBJECT_BODY_ALLOWLIST,
    Predicate,
    body_preds_for_level,
    head_pred,
    head_pred_object,
)

_BIAS_DIR = Path(__file__).resolve().parent / "bias"

_FACT_PRED_RE = re.compile(r"^([a-z][a-z0-9_]*)\(")
_SIZE_CONST_RE = re.compile(r"\bs(\d+)\b")
_VALUE_CONST_RE = re.compile(r"\bv(\d+)\b")


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
    """Typed constants for pixel/dual biases (not object)."""
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


def _preds_present_in_bk(bk_text: str, allow: FrozenSet[str]) -> Set[str]:
    present: Set[str] = set()
    for line in bk_text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        m = _FACT_PRED_RE.match(s)
        if m and m.group(1) in allow:
            present.add(m.group(1))
    return present


def _constants_present_in_texts(*texts: str) -> tuple[Set[int], Set[int]]:
    """Return (size_ids, value_ids) mentioned as sN / vN in BK or exs."""
    sizes: Set[int] = set()
    values: Set[int] = set()
    for text in texts:
        for m in _SIZE_CONST_RE.finditer(text):
            sizes.add(int(m.group(1)))
        for m in _VALUE_CONST_RE.finditer(text):
            values.add(int(m.group(1)))
    return sizes, values


def render_object_bias_from_bk(
    bk_text: str,
    *,
    exs_text: str = "",
    max_vars: int = 10,
    max_body: int = 6,
    max_clauses: int = 3,
) -> str:
    """Mechanical object bias from one instance's BK (+ optional exs).

    Same algorithm for every task: expose only body preds that appear as BK
    facts (within the lean object allowlist), and only size/value constants
    that appear in BK/exs. No category-name branching.
    """
    present = _preds_present_in_bk(bk_text, OBJECT_BODY_ALLOWLIST)
    # Always allow ``block`` if typed object BK is non-empty — head binds from it.
    if "block(" in bk_text or any(
        ln.strip().startswith("block(") for ln in bk_text.splitlines()
    ):
        present.add("block")
    bodies = tuple(
        p for p in body_preds_for_level(4) if p.name in present
    )
    # Prefer stable order by inventory order (already), fall back empty-safe.
    if not bodies:
        bodies = tuple(
            p for p in body_preds_for_level(4) if p.name == "block"
        )

    sizes, values = _constants_present_in_texts(bk_text, exs_text)
    # Off=0 / unit length are ubiquitous bindings; include if any size consts exist
    # or always include s0/s1 when typed sizes are used (mechanical defaults).
    sizes.add(0)
    sizes.add(1)

    hp = head_pred_object()
    all_typed = (hp,) + bodies
    parts = [
        f"max_vars({max_vars}).",
        f"max_body({max_body}).",
        f"max_clauses({max_clauses}).",
        "enable_multi_clause.",
        ":- not body_var(_,1).",
        ":- not body_var(_,2).",
        ":- not body_var(_,3).",
        "",
        f"head_pred({hp.name},{hp.arity}).",
    ]
    for p in bodies:
        parts.append(f"body_pred({p.name},{p.arity}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    for i in sorted(sizes):
        parts.append(f"constant(s{i}, 'size').")
    for i in sorted(values):
        parts.append(f"constant(v{i}, 'value').")
    parts.append("")
    parts.append(_types_block(all_typed))
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    parts.append(_bad_body_for_ex_preds(bodies))
    parts.append("")
    return "\n".join(parts) + "\n"


def render_object_bias(*, max_vars: int = 10, max_body: int = 6) -> str:
    """Static fallback: full lean allowlist (tests / non-instance paths only)."""
    bk_lines = [f"{name}(dummy)." for name in sorted(OBJECT_BODY_ALLOWLIST)]
    return render_object_bias_from_bk(
        "\n".join(bk_lines),
        exs_text="",
        max_vars=max_vars,
        max_body=max_body,
    )


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
    """Write static pixel/dual biases; object bias is instance-generated at encode."""
    out_dir = out_dir or _BIAS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "block.pl").write_text(render_bias(2, max_vars=8, max_body=12))
    (out_dir / "dual.pl").write_text(render_bias(3, max_vars=9, max_body=16))
    (out_dir / "object.pl").write_text(render_object_bias())
    (out_dir / "pixel.pl").write_text(_pixel_only_bias())


if __name__ == "__main__":
    write_bias_files()
    print(f"wrote {_BIAS_DIR}")
