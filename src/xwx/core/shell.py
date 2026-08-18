"""Execucao de processos externos."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence


class CommandNotFound(RuntimeError):
    """O binario nao esta no PATH."""


def which(binary: str) -> str | None:
    return shutil.which(binary)


def require(binary: str, hint: str = "") -> str:
    path = which(binary)
    if path is None:
        message = f"'{binary}' nao encontrado no PATH."
        if hint:
            message = f"{message} {hint}"
        raise CommandNotFound(message)
    return path


def run(argv: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    """Roda ``argv``. Com ``capture=True`` silencia stderr e devolve stdout.

    Nunca levanta em codigo de saida != 0 — quem chama decide o que fazer com
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
    """stdout limpo do comando, ou ``None`` se falhar/vier vazio."""
    proc = run(argv, capture=True)
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None
