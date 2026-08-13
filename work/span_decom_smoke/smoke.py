"""Throwaway smoke: Decom-analogue span encoding (no Bid/Rank).

Both input and output use (Start, Len, Color) on the shared pixel ruler:
  block(E, Start, Len, Color)
  out_block(E, Start, Len, Color)

Does not modify solver/. Isolated under work/span_decom_smoke/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from solver.grid import flatten, segment_all_runs, segment_blocks
from solver.induce import induce

DATASET = ROOT / "raw_data/onedarcraw/dataset"
OUT_ROOT = Path(__file__).resolve().parent / "runs"

# Easy (co-located or uniform shift) vs correspondence-critical.
TASKS = [
    ("1d_fill", 0),
    ("1d_move_1p", 0),
    ("1d_recolor_cmp", 0),
    ("1d_denoising_1c", 0),
    ("1d_flip", 0),
    ("1d_mirror", 0),
    ("1d_hollow", 0),
]


def _p(i: int) -> str:
    return f"p{i}"


def _s(i: int) -> str:
    return f"s{i}"


def _v(i: int) -> str:
    return f"v{i}"


def _bk_for_row(ex: int, row: Sequence[int]) -> Tuple[List[str], Set[int], int]:
    """Lean object BK keyed by start column (shared ruler)."""
    facts: List[str] = []
    runs = segment_all_runs(row)
    w = len(row)
    colored = [(s, e, c) for s, e, c in runs if c != 0]
    observed: Set[int] = {0, 1}
    lengths: List[int] = []

    for s, e, c in colored:
        L = e - s + 1
        lengths.append(L)
        observed.add(L)
        facts.append(f"block({ex},{_p(s)},{_s(L)},{_v(c)}).")

    for (s1, e1, _c1), (s2, e2, _c2) in zip(colored, colored[1:]):
        L1 = e1 - s1 + 1
        L2 = e2 - s2 + 1
        g = s2 - e1 - 1
        observed.add(g)
        facts.append(f"obj_succ({ex},{_p(s1)},{_p(s2)}).")
        facts.append(f"gap({ex},{_p(s1)},{_p(s2)},{_s(g)}).")
        total = L1 + g + L2
        if total <= w:
            facts.append(f"size_sum3({_s(L1)},{_s(g)},{_s(L2)},{_s(total)}).")
            observed.add(total)
        for x, y in ((L1, g), (1, g), (g, L2)):
            sm = x + y
            if 0 <= sm <= w:
                facts.append(f"size_add({_s(x)},{_s(y)},{_s(sm)}).")
                observed.add(sm)

    for i in range(0, len(colored) - 1, 2):
        s1 = colored[i][0]
        s2 = colored[i + 1][0]
        facts.append(f"obj_pair({ex},{_p(s1)},{_p(s2)}).")

    if colored:
        max_L = max(e - s + 1 for s, e, _c in colored)
        for s, e, _c in colored:
            L = e - s + 1
            if L == max_L:
                facts.append(f"largest({ex},{_p(s)}).")
            else:
                facts.append(f"non_largest({ex},{_p(s)}).")

    for L in list(observed):
        if L >= 2 and L <= w:
            facts.append(f"size_add({_s(1)},{_s(L - 1)},{_s(L)}).")
            observed.add(L - 1)

    sizes = sorted(x for x in observed if x >= 0)
    for a in sizes:
        for b in sizes:
            if a < b:
                facts.append(f"size_lt({_s(a)},{_s(b)}).")

    # Shared-ruler arithmetic (Decom-style translation of Start).
    offs = sorted({1, 2, 3} | {x for x in observed if 1 <= x <= w})
    for i in range(w):
        for k in offs:
            j = i + k
            if j <= w:
                facts.append(f"offset_pos({_p(i)},{_s(k)},{_p(j)}).")
            j = i - k
            if j >= 0:
                facts.append(f"offset_pos({_p(i)},{_s(k)},{_p(j)}).")
        if i < w:
            facts.append(f"cardinal_ordinal({_s(i)},{_p(i)}).")

    for sz in sizes:
        facts.append(f"size_even({_s(sz)})." if sz % 2 == 0 else f"size_odd({_s(sz)}).")

    return facts, observed, w


def _exs_for_train(train: List[Tuple[int, List[int], List[int]]]) -> List[str]:
    pos: List[str] = []
    neg: List[str] = []
    for ex, inp, out in train:
        w = len(out)
        in_spans = [(s, e - s + 1, c) for s, e, c in segment_blocks(inp)]
        true: Set[Tuple[int, int, int]] = set()
        colors: Set[int] = set()
        observed = {0, 1}
        for s, e, c in segment_blocks(inp):
            observed.add(e - s + 1)
        for s, e, c in segment_blocks(out):
            L = e - s + 1
            true.add((s, L, c))
            colors.add(c)
            observed.add(L)
            observed.add(s)
            pos.append(f"pos(out_block({ex},{_p(s)},{_s(L)},{_v(c)})).")
        if not true:
            continue
        len_cands = sorted(set(observed) | set(range(1, min(w, 12) + 1)))
        start_cands = sorted(set(range(0, w)) | {s for s, _L, _c in in_spans})
        for s, L, c in true:
            for v in range(1, 10):
                if v != c:
                    neg.append(f"neg(out_block({ex},{_p(s)},{_s(L)},{_v(v)})).")
            for L2 in len_cands:
                if L2 < 1 or L2 == L:
                    continue
                if (s, L2, c) in true:
                    continue
                neg.append(f"neg(out_block({ex},{_p(s)},{_s(L2)},{_v(c)})).")
            for s2 in start_cands:
                if s2 == s or not (0 <= s2 < w):
                    continue
                if (s2, L, c) in true:
                    continue
                neg.append(f"neg(out_block({ex},{_p(s2)},{_s(L)},{_v(c)})).")
        # Identity/prefix killers at each input span start.
        for s, Lin, c in in_spans:
            for L0 in range(1, Lin + 1):
                if (s, L0, c) not in true:
                    neg.append(f"neg(out_block({ex},{_p(s)},{_s(L0)},{_v(c)})).")
    seen: Set[str] = set()
    out_lines: List[str] = []
    for line in pos + neg:
        if line in seen:
            continue
        seen.add(line)
        out_lines.append(line)
    return out_lines


def _bias(bk_text: str, exs_text: str) -> str:
    sizes = sorted({int(m) for m in __import__("re").findall(r"\bs(\d+)\b", bk_text + exs_text)})
    values = sorted({int(m) for m in __import__("re").findall(r"\bv(\d+)\b", bk_text + exs_text)})
    sizes = sorted(set(sizes) | {0, 1})
    preds = [
        ("block", 4, "('ex','position','size','value')"),
        ("obj_succ", 3, "('ex','position','position')"),
        ("obj_pair", 3, "('ex','position','position')"),
        ("gap", 4, "('ex','position','position','size')"),
        ("largest", 2, "('ex','position')"),
        ("non_largest", 2, "('ex','position')"),
        ("size_add", 3, "('size','size','size')"),
        ("size_sum3", 4, "('size','size','size','size')"),
        ("size_lt", 2, "('size','size')"),
        ("offset_pos", 3, "('position','size','position')"),
        ("cardinal_ordinal", 2, "('size','position')"),
        ("size_even", 1, "('size',)"),
        ("size_odd", 1, "('size',)"),
    ]
    present = {n for n, _a, _t in preds if f"{n}(" in bk_text}
    parts = [
        "max_vars(10).",
        "max_body(6).",
        "max_clauses(3).",
        "enable_multi_clause.",
        ":- not body_var(_,1).",
        ":- not body_var(_,2).",
        ":- not body_var(_,3).",
        "",
        "head_pred(out_block,4).",
    ]
    for n, a, _t in preds:
        if n in present:
            parts.append(f"body_pred({n},{a}).")
    parts.append("body_pred(C,1):- constant(C,_).")
    parts.append("")
    for i in sizes:
        parts.append(f"constant(s{i}, 'size').")
    for i in values:
        parts.append(f"constant(v{i}, 'value').")
    parts.append("")
    parts.append("type(out_block,('ex','position','size','value')).")
    for n, _a, t in preds:
        if n in present:
            parts.append(f"type({n},{t}).")
    parts.append("type(C,(T,)):- constant(C,T).")
    parts.append("")
    # Require some input block in the clause; do NOT pin head Start (that kills shifts).
    parts.append(":- clause(C), not body_literal(C, block, 4, (0,_,_,_)).")
    if "offset_pos" in present:
        parts.append(
            "bad_body(offset_pos, Vars):- vars(_, Vars), Vars = (A,_,R), "
            "A != 1, R != 1."
        )
    if "size_add" in present:
        parts.append(
            "bad_body(size_add, Vars):- vars(_, Vars), Vars = (A,B,R), "
            "A != 2, B != 2, R != 2."
        )
    if "size_sum3" in present:
        parts.append(
            "bad_body(size_sum3, Vars):- vars(_, Vars), Vars = (A,B,C,R), "
            "A != 2, B != 2, C != 2, R != 2."
        )
    parts.append("")
    return "\n".join(parts) + "\n"


def encode_task(src: Path, out_dir: Path) -> Dict:
    obj = json.loads(src.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    train = []
    for i, pair in enumerate(obj["train"]):
        train.append((i, flatten(pair["input"]), flatten(pair["output"])))
    test_in = flatten(obj["test"][0]["input"])
    test_out = flatten(obj["test"][0]["output"])
    test_id = len(train)

    bk_lines: List[str] = []
    test_bk: List[str] = []
    max_w = max(len(r) for _i, r, o in train for r in (r, o))
    max_w = max(max_w, len(test_in), len(test_out))
    for ex, inp, _out in train:
        facts, _obs, _w = _bk_for_row(ex, inp)
        bk_lines.extend(facts)
    facts, _obs, _w = _bk_for_row(test_id, test_in)
    test_bk.extend(facts)

    for i in range(10):
        bk_lines.append(f"v{i}(v{i}).")
        test_bk.append(f"v{i}(v{i}).")
    for i in range(max_w + 1):
        bk_lines.append(f"s{i}(s{i}).")
        test_bk.append(f"s{i}(s{i}).")

    bk_lines = sorted(set(bk_lines))
    test_bk = sorted(set(test_bk))
    exs = _exs_for_train(train)
    (out_dir / "bk.pl").write_text("\n".join(bk_lines) + "\n")
    (out_dir / "test_bk.pl").write_text("\n".join(test_bk) + "\n")
    (out_dir / "exs.pl").write_text("\n".join(exs) + "\n")
    (out_dir / "bias.pl").write_text(_bias("\n".join(bk_lines), "\n".join(exs)))
    meta = {
        "train": [{"id": e, "input": inp, "output": out} for e, inp, out in train],
        "test": {"id": test_id, "input": test_in, "output": test_out},
    }
    (out_dir / "grids.json").write_text(json.dumps(meta))
    return meta


def _collect(ex_id: int, width: int) -> List[Tuple[int, int, int]]:
    from janus_swi import query_once

    blocks = []
    for s in range(0, width):
        for L in range(1, width - s + 1):
            for c in range(1, 10):
                atom = f"out_block({ex_id},{_p(s)},{_s(L)},{_v(c)})"
                try:
                    res = query_once(atom)
                except Exception:
                    continue
                if res.get("truth"):
                    blocks.append((s, L, c))
    return blocks


def paint(program: str, bk_path: Path, examples: List[Tuple[int, int]]) -> Dict[int, List[int]]:
    """examples: (ex_id, width)."""
    from janus_swi import consult, query_once

    tmp = bk_path.parent / "_apply.pl"
    tmp.write_text(":- dynamic out_block/4.\n" + program)
    consult(str(bk_path))
    consult(str(tmp))
    out: Dict[int, List[int]] = {}
    try:
        for ex_id, w in examples:
            row = [0] * w
            occupied: Dict[int, int] = {}
            for s, L, c in _collect(ex_id, w):
                if s < 0 or s + L > w:
                    raise ValueError(f"OOB {ex_id} {s}+{L}")
                for p in range(s, s + L):
                    if p in occupied and occupied[p] != c:
                        raise ValueError(f"overlap {ex_id}:{p}")
                    occupied[p] = c
                    row[p] = c
            out[ex_id] = row
        return out
    finally:
        try:
            query_once("retractall(out_block(_,_,_,_))")
        except Exception:
            pass


def run_one(cat: str, trial: int, timeout: int) -> Dict:
    src = DATASET / cat / f"{cat}_{trial}.json"
    work = OUT_ROOT / f"{cat}_{trial}"
    if work.exists():
        import shutil

        shutil.rmtree(work)
    meta = encode_task(src, work / "encode")
    ir = induce(
        work / "encode" / "exs.pl",
        work / "encode" / "bk.pl",
        work / "encode" / "bias.pl",
        timeout,
        work / "popper",
    )
    result = {
        "task": f"{cat}_{trial}",
        "status": ir.status,
        "elapsed_s": round(ir.elapsed_s, 2),
        "error": ir.error,
        "program": ir.program,
        "train_exact": False,
        "test_exact": False,
        "failure": None,
    }
    if not ir.program:
        result["failure"] = ir.status
        return result
    train_ex = [(t["id"], len(t["output"])) for t in meta["train"]]
    try:
        preds = paint(ir.program, work / "encode" / "bk.pl", train_ex)
    except Exception as e:
        result["failure"] = f"decode:{e}"
        return result
    for t in meta["train"]:
        if preds.get(t["id"]) != t["output"]:
            result["failure"] = "paint_verify_failed"
            (work / "program.pl").write_text(ir.program)
            return result
    result["train_exact"] = True
    tw = len(meta["test"]["output"])
    try:
        tpred = paint(
            ir.program,
            work / "encode" / "test_bk.pl",
            [(meta["test"]["id"], tw)],
        )[meta["test"]["id"]]
    except Exception as e:
        result["failure"] = f"test_decode:{e}"
        return result
    result["test_exact"] = tpred == meta["test"]["output"]
    if not result["test_exact"]:
        result["failure"] = "test_mismatch"
    (work / "program.pl").write_text(ir.program)
    return result


def main() -> None:
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    print(f"span-decom smoke timeout={timeout}s tasks={len(TASKS)}", flush=True)
    rows = []
    for cat, trial in TASKS:
        print(f"--- {cat}_{trial} ---", flush=True)
        r = run_one(cat, trial, timeout)
        rows.append(r)
        prog = (r.get("program") or "").replace("\n", " | ")[:200]
        print(
            f"  {r['status']:10} train={r['train_exact']} test={r['test_exact']} "
            f"{r['elapsed_s']}s fail={r['failure']}\n  {prog}",
            flush=True,
        )
    summary = {
        "timeout": timeout,
        "n": len(rows),
        "train_ok": sum(1 for r in rows if r["train_exact"]),
        "test_ok": sum(1 for r in rows if r["test_exact"]),
        "rows": [{k: v for k, v in r.items() if k != "program"} | {"program": r.get("program")} for r in rows],
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(
        f"\nDONE train_exact {summary['train_ok']}/{summary['n']} "
        f"test_exact {summary['test_ok']}/{summary['n']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
