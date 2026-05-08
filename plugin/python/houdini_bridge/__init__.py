"""Houdini Bridge — typed control surface for SideFX Houdini.

The package is importable both from inside Houdini (where ``hou`` exists) and
from a vanilla Python interpreter (where ``hou`` does not). Modules that need
``hou`` import it lazily.
"""

from __future__ import annotations

from .version import __version__
from .registry import Registry, get_registry

__all__ = [
    "__version__",
    "Registry",
    "get_registry",
    "start",
    "stop",
    "is_running",
]


def start(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    log_level: str = "INFO",
):
    """Start the in-process bridge server.

    Safe to call multiple times: subsequent calls are no-ops while a server is
    already running. Returns the live ``HoudiniBridgeServer`` instance.
    """

    from .bootstrap import start as _start

    return _start(host=host, port=port, log_level=log_level)


def stop() -> None:
    """Stop the running bridge server, if any."""

    from .bootstrap import stop as _stop

    _stop()


def is_running() -> bool:
    """Return ``True`` while a bridge server is active."""

    from .bootstrap import is_running as _running

    return _running()
