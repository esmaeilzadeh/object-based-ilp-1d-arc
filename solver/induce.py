"""Popper induction wrapper."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


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


def induce(
    exs_path: PathLike,
    bk_path: PathLike,
    bias_path: PathLike,
    timeout_s: int,
    work_dir: Optional[PathLike] = None,
) -> Optional[str]:
    """Run Popper; return program source or None."""
    Settings, learn_solution = _import_popper()

    cleanup = False
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="popper_"))
        cleanup = True
    else:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

    try:
        settings = Settings(
            cmd_line=False,
            quiet=True,
            solver="rc2",
            ex_file=str(exs_path),
            bk_file=str(bk_path),
            bias_file=str(bias_path),
            timeout=int(timeout_s),
        )
        prog, _terminated = learn_solution(settings)
        if not prog:
            return None
        out = work_dir / "program.pl"
        out.write_text(prog if prog.endswith("\n") else prog + "\n")
        return prog
    except Exception as e:
        print(f"[induce] failed: {e}")
        return None
    finally:
        if cleanup:
            shutil.rmtree(work_dir, ignore_errors=True)
