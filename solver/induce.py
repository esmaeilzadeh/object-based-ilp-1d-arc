"""Popper induction wrapper."""

from __future__ import annotations

import multiprocessing as mp
import re
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_MAX_BODY_RE = re.compile(r"max_body\((\d+)\)\.")
_MAX_CLAUSES_RE = re.compile(r"max_clauses\((\d+)\)\.")


@dataclass
class InduceResult:
    program: Optional[str]
    status: str  # ok | timeout | exhausted | error
    elapsed_s: float
    error: Optional[str] = None
    max_literals: int = 0


def _import_popper():
    """Prefer editable install (`pip install -e ./popper`); fall back to vendored path."""
    try:
        from popper.util import Settings
        from popper.loop import learn_solution
        return Settings, learn_solution
    except ImportError:
        from popper.popper.util import Settings
        from popper.popper.loop import learn_solution
        return Settings, learn_solution


def _literals_from_bias(bias_path: Path, *, override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    text = Path(bias_path).read_text()
    body_m = _MAX_BODY_RE.search(text)
    clauses_m = _MAX_CLAUSES_RE.search(text)
    max_body = int(body_m.group(1)) if body_m else 6
    max_clauses = int(clauses_m.group(1)) if clauses_m else 3
    return (1 + max_body) * max_clauses


def _worker(
    exs: str,
    bk: str,
    bias: str,
    timeout_s: int,
    max_literals: int,
    out_prog: str,
    q: mp.Queue,
) -> None:
    try:
        Settings, learn_solution = _import_popper()
        settings = Settings(
            cmd_line=False,
            quiet=True,
            solver="rc2",
            ex_file=exs,
            bk_file=bk,
            bias_file=bias,
            timeout=int(timeout_s),
            max_literals=int(max_literals),
            functional_test=True,
        )
        prog, _terminated = learn_solution(settings)
        if prog:
            Path(out_prog).write_text(prog if prog.endswith("\n") else prog + "\n")
            q.put(("ok", prog, None))
        else:
            q.put(("exhausted", None, None))
    except Exception as e:  # noqa: BLE001 — surface to parent
        q.put(("error", None, str(e)))


def induce(
    exs_path: PathLike,
    bk_path: PathLike,
    bias_path: PathLike,
    timeout_s: int,
    work_dir: Optional[PathLike] = None,
    *,
    max_literals: Optional[int] = None,
) -> InduceResult:
    """Run Popper in a child process; return program + status (honest timeout)."""
    cleanup = False
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="popper_"))
        cleanup = True
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    lit_cap = _literals_from_bias(Path(bias_path), override=max_literals)
    out_prog = work_dir / "program.pl"
    q: mp.Queue = mp.Queue()
    t0 = time.time()
    join_budget = max(int(timeout_s), 1)

    proc = mp.Process(
        target=_worker,
        args=(
            str(exs_path),
            str(bk_path),
            str(bias_path),
            join_budget,
            lit_cap,
            str(out_prog),
            q,
        ),
    )
    try:
        proc.start()
        proc.join(join_budget + 5)  # small grace over Popper's own timeout
        elapsed = time.time() - t0

        if proc.is_alive():
            proc.terminate()
            proc.join(10)
            if proc.is_alive():
                proc.kill()
                proc.join(5)
            leftover = out_prog.read_text() if out_prog.exists() else None
            return InduceResult(
                program=leftover or None,
                status="timeout",
                elapsed_s=elapsed,
                max_literals=lit_cap,
            )

        status, prog, err = "exhausted", None, None
        try:
            if not q.empty():
                status, prog, err = q.get_nowait()
        except Exception:
            pass

        if status == "error":
            print(f"[induce] failed: {err}")
            return InduceResult(
                program=None,
                status="error",
                elapsed_s=elapsed,
                error=err,
                max_literals=lit_cap,
            )
        if prog:
            return InduceResult(
                program=prog,
                status="ok",
                elapsed_s=elapsed,
                max_literals=lit_cap,
            )
        # Clean exit, empty program (or timed out inside Popper with no write)
        if elapsed >= join_budget * 0.95:
            return InduceResult(
                program=None,
                status="timeout",
                elapsed_s=elapsed,
                max_literals=lit_cap,
            )
        return InduceResult(
            program=None,
            status="exhausted",
            elapsed_s=elapsed,
            max_literals=lit_cap,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[induce] failed: {e}")
        return InduceResult(
            program=None,
            status="error",
            elapsed_s=time.time() - t0,
            error=str(e),
            max_literals=lit_cap,
        )
    finally:
        if cleanup:
            shutil.rmtree(work_dir, ignore_errors=True)
