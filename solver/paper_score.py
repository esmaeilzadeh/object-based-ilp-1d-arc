"""Paper-comparable soft predictive accuracy (tp+tn)/total via do_test_ex."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

PathLike = Union[str, Path]

_DO_TEST = Path(__file__).resolve().parent / "lp" / "do_test.pl"


def soft_accuracy(matrix: Sequence[int]) -> float:
    tp, fn, tn, fp = (int(x) for x in matrix)
    total = tp + fn + tn + fp
    if total == 0:
        return 0.0
    return (tp + tn) / total


def failure_matrix(test_path: PathLike) -> List[int]:
    """Same fallback as 1d-arc/test.py when no usable program: [0, num_pos, num_neg, 0]."""
    from janus_swi import consult, query_once

    consult(str(_DO_TEST))
    consult(str(test_path))
    try:
        num_pos = int(query_once("num_pos(P)")["P"])
        num_neg = int(query_once("num_neg(N)")["N"])
    except Exception:
        return [0, 1, 0, 0]
    return [0, num_pos, num_neg, 0]


def score_program_soft(
    program: str,
    test_path: PathLike,
    *,
    work_dir: Optional[PathLike] = None,
) -> Tuple[List[int], float]:
    """Consult test.pl + program in a fresh Prolog state; return (matrix, soft_acc).

    Runs in a subprocess so prior janus consults (train ``bk.pl``, apply, …)
    cannot leak into the paper soft score.
    """
    import json
    import subprocess
    import sys

    work = Path(work_dir or Path(test_path).parent)
    work.mkdir(parents=True, exist_ok=True)
    prog_file = work / "_score_prog.pl"
    lines = []
    for line in program.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        lines.append(line)
    prog_file.write_text("\n".join(lines) + ("\n" if lines else ""))

    runner = work / "_score_runner.py"
    runner.write_text(
        "\n".join(
            [
                "import json, sys",
                "from janus_swi import consult, query_once",
                f"do_test = {str(_DO_TEST)!r}",
                f"test_path = {str(Path(test_path))!r}",
                f"prog_file = {str(prog_file)!r}",
                "try:",
                "    consult(do_test)",
                "    consult(test_path)",
                "    consult(prog_file)",
                "    res = query_once('do_test_ex(TP,FN,TN,FP)')",
                "    matrix = [int(res['TP']), int(res['FN']), int(res['TN']), int(res['FP'])]",
                "except Exception:",
                "    try:",
                "        consult(do_test)",
                "        consult(test_path)",
                "        num_pos = int(query_once('num_pos(P)')['P'])",
                "        num_neg = int(query_once('num_neg(N)')['N'])",
                "        matrix = [0, num_pos, num_neg, 0]",
                "    except Exception:",
                "        matrix = [0, 1, 0, 0]",
                "tp, fn, tn, fp = matrix",
                "total = tp + fn + tn + fp",
                "acc = (tp + tn) / total if total else 0.0",
                "print(json.dumps({'matrix': matrix, 'acc': acc}))",
            ]
        )
        + "\n"
    )
    try:
        out = subprocess.check_output(
            [sys.executable, str(runner)],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=120,
        )
        data = json.loads(out.strip().splitlines()[-1])
        matrix = [int(x) for x in data["matrix"]]
        return matrix, float(data["acc"])
    except Exception:
        try:
            matrix = failure_matrix(test_path)
        except Exception:
            matrix = [0, 1, 0, 0]
        return matrix, soft_accuracy(matrix)


def grid_to_out_program(ex_id: int, row: Sequence[int]) -> str:
    """Materialize closed-world nonzero ``out/3`` facts from a predicted grid."""
    facts = []
    for i, c in enumerate(row):
        c = int(c)
        if c != 0:
            facts.append(f"out({ex_id},{i},{c}).")
    return "\n".join(facts) + ("\n" if facts else "")
