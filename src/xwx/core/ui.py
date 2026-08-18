"""Terminal output: optional colors and printing helpers."""

from __future__ import annotations

import os
import sys
from typing import TextIO


def color_enabled(stream: TextIO = sys.stdout) -> bool:
    """Colors only when it makes sense: a TTY, no NO_COLOR, no TERM=dumb."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "cyan": "36",
}


def paint(text: str, *styles: str, stream: TextIO = sys.stdout) -> str:
    if not styles or not color_enabled(stream):
        return text
    codes = ";".join(_CODES[s] for s in styles if s in _CODES)
    if not codes:
        return text
    return f"\033[{codes}m{text}\033[0m"


def info(message: str) -> None:
    print(message)


def ok(message: str) -> None:
    print(f"{paint('OK', 'green', 'bold')} {message}")


def warn(message: str) -> None:
    print(f"{paint('!', 'yellow', 'bold')} {message}", file=sys.stderr)


def error(message: str) -> None:
    print(f"{paint('error:', 'red', 'bold', stream=sys.stderr)} {message}", file=sys.stderr)


def kv(label: str, value: str | None, width: int = 18) -> None:
    """Print ``label`` padded to ``width``, followed by the value (or ``(none)``)."""
    shown = value if value else paint("(none)", "dim")
    print(f"{label.ljust(width)}: {shown}")


def bullets(items: list, prefix: str = "  - ") -> None:
    for item in items:
        print(f"{prefix}{item}")
