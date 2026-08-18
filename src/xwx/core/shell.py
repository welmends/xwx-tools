"""Running external processes."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence


class CommandNotFound(RuntimeError):
    """The binary is not on PATH."""


def which(binary: str) -> str | None:
    return shutil.which(binary)


def require(binary: str, hint: str = "") -> str:
    path = which(binary)
    if path is None:
        message = f"'{binary}' was not found on PATH."
        if hint:
            message = f"{message} {hint}"
        raise CommandNotFound(message)
    return path


def run(argv: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    """Run ``argv``. With ``capture=True`` stderr is silenced and stdout returned.

    Never raises on a non-zero exit code — the caller decides what to do with
    ``returncode``.
    """
    if capture:
        return subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    return subprocess.run(list(argv), check=False)


def capture(argv: Sequence[str]) -> str | None:
    """Clean stdout of the command, or ``None`` if it failed or came back empty."""
    proc = run(argv, capture=True)
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None
