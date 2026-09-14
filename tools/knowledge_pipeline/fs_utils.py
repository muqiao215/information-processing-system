"""Shared filesystem helpers for the knowledge pipeline.

`atomic_write_text` is the single durable-write seam used by the acquisition
orchestrator, the knowledge pack builder, and phase-2 preprocessing. A process
killed mid-write leaves the previous target intact and at worst a `.tmp<pid>`
leftover in the same directory; the target file itself is never torn.
"""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, data: str, encoding: str = "utf-8") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}")
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return path
