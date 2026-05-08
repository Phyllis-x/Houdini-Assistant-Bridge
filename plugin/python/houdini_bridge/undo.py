"""Undo group helpers.

Always wrap write ops via ``with houdini_bridge.undo.group("label"):`` so the
operator can revert anything the agent did with a single Ctrl+Z. The helper
degrades to a no-op when ``hou`` is unavailable (e.g. during manifest
generation outside Houdini).
"""

from __future__ import annotations

import contextlib
from typing import Iterator

try:  # pragma: no cover - exercised inside Houdini only
    import hou  # type: ignore
except Exception:  # pragma: no cover - hou not present
    hou = None  # type: ignore[assignment]


@contextlib.contextmanager
def group(label: str) -> Iterator[None]:
    """Open an undo group named *label* for the duration of the block."""

    if hou is None:
        yield
        return

    with hou.undos.group(label):  # type: ignore[union-attr]
        yield


def is_available() -> bool:
    """Return ``True`` when ``hou`` is importable."""

    return hou is not None
