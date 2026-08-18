"""Decode object-head programs (out_block) into pixel grids."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

from solver.encoder import (
    ExampleGrids,
    _bid,
    _col,
    _sz,
    _uid,
    block_geometry_for_row,
)
from solver.grid import segment_all_runs

PathLike = Union[str, Path]

# Consulted with the hypothesis so decode can read the body's InBid.
_ORIGIN_HELPERS = """
first_block((A,B), Ex, InBid) :-
    (first_block(A, Ex, InBid) -> true ; first_block(B, Ex, InBid)).
first_block(block(Ex, InBid, _, _), Ex, InBid) :- nonvar(InBid).
origin_inbid(Ex, OutBid, Off, Len, C, InBid) :-
    clause(out_block(Ex, OutBid, Off, Len, C), Body), Body \\== true,
    call(Body), first_block(Body, Ex, InBid).
"""


def _strip_program(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def _int_bid(val: object) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, int):
        return int(val)
    s = str(val)
    if s.startswith("b") and s[1:].isdigit():
        return int(s[1:])
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    return None


def _rank_origin_bids(row: Sequence[int]) -> Dict[int, int]:
    """OutBid rank → all-run input bid of the k-th colored run."""
    mapping: Dict[int, int] = {}
    k = 0
    for bid, (_s, _e, c) in enumerate(segment_all_runs(row)):
        if c == 0:
            continue
        mapping[k] = bid
        k += 1
    return mapping


def _origin_inbids(
    ex_id: int,
    out_bid: int,
    off: int,
    L: int,
    c: int,
    *,
    typed_roles: bool,
) -> List[int]:
    """Input bids bound by the first ``block/4`` in a successful clause proof."""
    from janus_swi import query_once

    t = typed_roles
    atom = (
        f"origin_inbid({ex_id},{_bid(out_bid, t)},"
        f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)}, InBid)"
    )
    try:
        res = query_once(atom)
    except Exception:
        return []
    if not res.get("truth"):
        return []
    bid = _int_bid(res.get("InBid"))
    return [bid] if bid is not None else []


def _collect_out_blocks(
    ex_id: int,
    width: int,
    geometry: Dict[int, Tuple[int, int]],
    inp: Sequence[int],
    *,
    typed_roles: bool = False,
    min_len: int = 1,
    extra_offs: Sequence[int] = (),
) -> List[Tuple[int, int, int]]:
    """Enumerate grounded ``out_block(Ex, OutBid, Off, Len, Color)``.

    Returns ``(paint_start, Len, Color)`` with
    ``paint_start = start(InBid)+Off`` for the InBid the clause proves.
    Body-less facts fall back to the same-rank colored input.
    """
    from janus_swi import query_once

    t = typed_roles
    offs = set(range(-width, width + 1))
    offs.update(int(x) for x in extra_offs)
    rank_origin = _rank_origin_bids(inp)
    max_out = min(width - 1, max(list(rank_origin.keys()) + list(geometry.keys()) + [4]))
    blocks: List[Tuple[int, int, int]] = []
    for out_bid in range(max_out + 1):
        for off in sorted(offs):
            for L in range(max(min_len, 1), width + 1):
                for c in range(1, 10):
                    atom = (
                        f"out_block({ex_id},{_bid(out_bid, t)},"
                        f"{_sz(off, t)},{_sz(L, t)},{_col(c, t)})"
                    )
                    try:
                        res = query_once(atom)
                    except Exception:
                        continue
                    if not res.get("truth"):
                        continue
                    inbids = _origin_inbids(
                        ex_id, out_bid, off, L, c, typed_roles=typed_roles
                    )
                    if not inbids:
                        fb = rank_origin.get(out_bid)
                        inbids = [fb] if fb is not None else []
                    for in_bid in inbids:
                        if in_bid not in geometry:
                            continue
                        start, _end = geometry[in_bid]
                        paint = start + off
                        if L < min_len or paint < 0 or paint + L > width:
                            continue
                        blocks.append((paint, L, c))
    return blocks


def apply_object_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = False,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
) -> Dict[int, List[int]]:
    """Paint pixels from ``out_block(Ex, OutBid, Off, Len, Color)``.

    Paint at ``start(InBid)+Off`` for the input block the clause binds.
    Overlap, OOB, or ambiguous color raises ValueError (verify treats as fail).

    Janus/SWI is process-global: consulting train ``bk.pl`` then ``test_bk.pl``
    in one interpreter can SIGSEGV in ``libswipl`` GC. Each apply runs in a
    fresh subprocess unless ``SOLVER_APPLY_INPROC=1``.
    """
    import os

    if os.environ.get("SOLVER_APPLY_INPROC") == "1":
        return _apply_object_program_inproc(
            program,
            bk_path,
            examples,
            typed_roles=typed_roles,
            block_geometry=block_geometry,
        )
    return _apply_object_program_isolated(
        program,
        bk_path,
        examples,
        typed_roles=typed_roles,
        block_geometry=block_geometry,
    )


def _apply_object_program_isolated(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = False,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
) -> Dict[int, List[int]]:
    import json
    import os
    import subprocess
    import sys
    import tempfile

    payload = {
        "program": program,
        "bk_path": str(bk_path),
        "examples": [
            {"ex_id": int(eg.ex_id), "inp": list(eg.inp), "out": None if eg.out is None else list(eg.out)}
            for eg in examples
        ],
        "typed_roles": bool(typed_roles),
        "block_geometry": {
            str(eid): {str(bid): [int(span[0]), int(span[1])] for bid, span in bids.items()}
            for eid, bids in (block_geometry or {}).items()
        },
    }
    root = Path(__file__).resolve().parents[1]
    tmp = Path(tempfile.mkdtemp(prefix="apply_obj_"))
    req = tmp / "req.json"
    req.write_text(json.dumps(payload))
    env = os.environ.copy()
    env["SOLVER_APPLY_INPROC"] = "1"
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "solver.decode", "--apply-object", str(req)],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("apply_object_program subprocess timed out") from e
    finally:
        try:
            req.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass
    if r.returncode < 0 or r.returncode == 139:
        raise RuntimeError(
            f"apply_object_program SWI/janus crashed (returncode={r.returncode})"
        )
    line = (r.stdout or "").strip().splitlines()
    if not line:
        err = (r.stderr or "").strip() or f"returncode={r.returncode}"
        raise RuntimeError(f"apply_object_program subprocess produced no JSON: {err}")
    data = json.loads(line[-1])
    if data.get("ok"):
        return {int(k): list(v) for k, v in data["preds"].items()}
    if data.get("error_type") == "ValueError":
        raise ValueError(data.get("error") or "apply_object_program failed")
    raise RuntimeError(data.get("error") or "apply_object_program failed")


def _apply_object_program_inproc(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = False,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
) -> Dict[int, List[int]]:
    """In-process janus consult. Caller must not mix train/test BK in one engine."""
    from janus_swi import consult, query_once

    prog = _strip_program(program)
    tmp = Path(bk_path).parent / "_apply_object_prog.pl"
    # Dynamic so later Popper tester retractall(out_block(...)) can clean up.
    tmp.write_text(":- dynamic out_block/5.\n" + _ORIGIN_HELPERS + prog)

    consult(str(bk_path))
    consult(str(tmp))

    geo = block_geometry
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            if eg.out is not None:
                w = len(eg.out)
            else:
                w = len(eg.inp)
            eg_geo = (
                geo[eg.ex_id]
                if geo is not None and eg.ex_id in geo
                else block_geometry_for_row(eg.inp)
            )
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect_out_blocks(
                eg.ex_id, w, eg_geo, eg.inp, typed_roles=typed_roles
            ):
                if L <= 0 or s < 0 or s + L > w:
                    raise ValueError(
                        f"out_block({eg.ex_id},paint→{s},{L},{c}) out of bounds width={w}"
                    )
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(
                            f"ambiguous/overlap at {eg.ex_id}:{p} "
                            f"{occupied[p]} vs {c}"
                        )
                    occupied[p] = c
                    row[p] = c
            out[eg.ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out_block(_,_,_,_,_))")
        except Exception:
            pass
        try:
            query_once("abolish(out_block/5)")
        except Exception:
            pass


def _collect_out_pixels(
    ex_id: int,
    width: int,
    pids: Sequence[int],
    unit_starts: Dict[int, int],
    *,
    typed_roles: bool = False,
    extra_offs: Sequence[int] = (),
) -> List[Tuple[int, int]]:
    """Returns ``(paint_pos, Color)`` for grounded ``out_pixel/4``."""
    from janus_swi import query_once

    t = typed_roles
    offs = set(range(-width, width + 1))
    offs.update(int(x) for x in extra_offs)
    paints: List[Tuple[int, int]] = []
    for pid in pids:
        if pid not in unit_starts:
            continue
        start = unit_starts[pid]
        for off in sorted(offs):
            paint = start + off
            if paint < 0 or paint >= width:
                continue
            for c in range(1, 10):
                atom = (
                    f"out_pixel({ex_id},{_uid(pid, t)},{_sz(off, t)},{_col(c, t)})"
                )
                try:
                    res = query_once(atom)
                except Exception:
                    continue
                if res.get("truth"):
                    paints.append((paint, c))
    return paints


def apply_hybrid_program(
    block_program: str,
    unit_program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
    *,
    typed_roles: bool = True,
    block_geometry: Optional[Dict[int, Dict[int, Tuple[int, int]]]] = None,
    unit_geometry: Optional[Dict[int, Dict[int, int]]] = None,
    extra_offs: Sequence[int] = (),
) -> Dict[int, List[int]]:
    """Paint bulky spans then units. Overlap raises ValueError."""
    from janus_swi import consult, query_once

    tmp = Path(bk_path).parent / "_apply_hybrid_prog.pl"
    tmp.write_text(
        ":- dynamic out_block/5.\n:- dynamic out_pixel/4.\n"
        + _ORIGIN_HELPERS
        + _strip_program(block_program)
        + "\n"
        + _strip_program(unit_program)
        + "\n"
    )
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            w = len(eg.out) if eg.out is not None else len(eg.inp)
            bgeo = (
                block_geometry[eg.ex_id]
                if block_geometry is not None and eg.ex_id in block_geometry
                else {}
            )
            ugeo = (
                unit_geometry[eg.ex_id]
                if unit_geometry is not None and eg.ex_id in unit_geometry
                else {}
            )
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect_out_blocks(
                eg.ex_id,
                w,
                bgeo,
                eg.inp,
                typed_roles=typed_roles,
                min_len=2,
                extra_offs=extra_offs,
            ):
                if L < 2 or s < 0 or s + L > w:
                    raise ValueError(
                        f"out_block({eg.ex_id},paint→{s},{L},{c}) invalid width={w}"
                    )
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(
                            f"ambiguous/overlap at {eg.ex_id}:{p} "
                            f"{occupied[p]} vs {c}"
                        )
                    occupied[p] = c
                    row[p] = c
            for p, c in _collect_out_pixels(
                eg.ex_id,
                w,
                list(ugeo.keys()),
                ugeo,
                typed_roles=typed_roles,
                extra_offs=extra_offs,
            ):
                if p in occupied:
                    raise ValueError(
                        f"unit/block overlap at {eg.ex_id}:{p} "
                        f"{occupied[p]} vs {c}"
                    )
                occupied[p] = c
                row[p] = c
            out[eg.ex_id] = row
        return out
    finally:
        for atom in (
            "retractall(out_block(_,_,_,_,_))",
            "retractall(out_pixel(_,_,_,_))",
            "abolish(out_block/5)",
            "abolish(out_pixel/4)",
        ):
            try:
                query_once(atom)
            except Exception:
                pass


def apply_pixel_program(
    program: str,
    bk_path: PathLike,
    examples: Sequence[ExampleGrids],
) -> Dict[int, List[int]]:
    """Paint ``out(Ex, Pos, Color)``; overlap / two colours raise."""
    from janus_swi import consult, query_once

    tmp = Path(bk_path).parent / "_apply_pixel_prog.pl"
    tmp.write_text(":- dynamic out/3.\n" + _strip_program(program))
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for eg in examples:
            w = len(eg.out) if eg.out is not None else len(eg.inp)
            row = [0] * w
            occupied: Dict[int, int] = {}
            for i in range(w):
                for c in range(1, 10):
                    atom = f"out({eg.ex_id},{i},{c})"
                    try:
                        res = query_once(atom)
                    except Exception:
                        continue
                    if res.get("truth"):
                        if i in occupied and occupied[i] != c:
                            raise ValueError(
                                f"ambiguous out/3 at {eg.ex_id}:{i}"
                            )
                        occupied[i] = c
                        row[i] = c
            out[eg.ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out(_,_,_))")
        except Exception:
            pass
        try:
            query_once("abolish(out/3)")
        except Exception:
            pass


def _cli(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Object-program paint (subprocess helper)")
    p.add_argument("--apply-object", type=Path, required=True)
    args = p.parse_args(argv)
    payload = json.loads(Path(args.apply_object).read_text())
    examples = [
        ExampleGrids(int(e["ex_id"]), list(e["inp"]), None if e.get("out") is None else list(e["out"]))
        for e in payload["examples"]
    ]
    geo = {
        int(eid): {int(bid): (int(span[0]), int(span[1])) for bid, span in bids.items()}
        for eid, bids in (payload.get("block_geometry") or {}).items()
    }
    try:
        preds = _apply_object_program_inproc(
            payload["program"],
            payload["bk_path"],
            examples,
            typed_roles=bool(payload.get("typed_roles")),
            block_geometry=geo or None,
        )
    except ValueError as e:
        print(json.dumps({"ok": False, "error_type": "ValueError", "error": str(e)}))
        return 0
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error_type": type(e).__name__, "error": str(e)}))
        return 1
    print(json.dumps({"ok": True, "preds": {str(k): v for k, v in preds.items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())

