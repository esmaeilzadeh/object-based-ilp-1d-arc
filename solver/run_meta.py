"""Collect and attach provenance metadata for eval / solver runs."""

from __future__ import annotations

import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _git(cmd: list[str], *, cwd: Optional[Path] = None) -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["git", *cmd],
            cwd=str(cwd) if cwd else None,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def collect_run_meta(
    *,
    mode: Optional[str] = None,
    timeout: Optional[int] = None,
    jobs: Optional[int] = None,
    trials: Optional[str] = None,
    dataset: Optional[str] = None,
    out: Optional[str] = None,
    repo_root: Optional[Path] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Best-effort run provenance. Missing git fields are null, not invented."""
    root = repo_root or Path.cwd()
    sha = _git(["rev-parse", "HEAD"], cwd=root)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    dirty_out = _git(["status", "--porcelain"], cwd=root)
    describe = _git(["describe", "--always", "--dirty", "--tags"], cwd=root)
    meta: Dict[str, Any] = {
        "schema": "eval-run-meta/v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "git_sha": sha,
        "git_branch": branch,
        "git_dirty": bool(dirty_out) if dirty_out is not None else None,
        "git_describe": describe,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "mode": mode,
        "timeout": timeout,
        "jobs": jobs,
        "trials": trials,
        "dataset": str(dataset) if dataset is not None else None,
        "out": str(out) if out is not None else None,
        "pid": os.getpid(),
    }
    if extra:
        meta.update(extra)
    return meta


def mark_finished(meta: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(meta)
    out["finished_at"] = datetime.now(timezone.utc).isoformat()
    return out


def slim_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Compact stamp for per-task JSON rows."""
    keys = (
        "schema",
        "git_sha",
        "git_branch",
        "git_dirty",
        "mode",
        "timeout",
        "jobs",
        "started_at",
    )
    return {k: meta.get(k) for k in keys}
