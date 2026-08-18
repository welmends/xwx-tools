"""Running external processes."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence


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


def _merged_env(env: Mapping[str, str] | None) -> dict[str, str] | None:
    """Overlay ``env`` on top of the current environment."""
    if not env:
        return None
    return {**os.environ, **env}


def run(
    argv: Sequence[str],
    *,
    capture: bool = False,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Run ``argv``. With ``capture=True`` stderr is silenced and stdout returned.

    Never raises on a non-zero exit code — the caller decides what to do with
    ``returncode``. A ``timeout`` only applies to captured (non-interactive)
    runs; interactive ones must be allowed to wait on the user.
    """
    if capture:
        return subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            env=_merged_env(env),
            timeout=timeout,
        )
    return subprocess.run(list(argv), check=False, env=_merged_env(env))


def capture(
    argv: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> str | None:
    """Clean stdout of the command, or ``None`` if it failed or came back empty."""
    try:
        proc = run(argv, capture=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def capture_lines(
    argv: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> list[str] | None:
    """Non-empty stdout lines, or ``None`` when the command failed."""
    try:
        proc = run(argv, capture=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
