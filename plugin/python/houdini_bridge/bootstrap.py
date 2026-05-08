"""Bootstrap helpers that wire the server into Houdini at startup."""

from __future__ import annotations

import atexit
import logging
import os
from typing import Optional

from .dispatcher import MainThreadDispatcher
from .server import HoudiniBridgeServer

LOGGER = logging.getLogger("houdini_bridge.bootstrap")

_SERVER: Optional[HoudiniBridgeServer] = None


def start(
    host: Optional[str] = None,
    port: Optional[int] = None,
    *,
    log_level: str = "INFO",
) -> HoudiniBridgeServer:
    """Idempotent server start. Returns the live server instance."""

    global _SERVER

    if _SERVER is not None:
        return _SERVER

    _configure_logging(log_level)
    _register_hou_bridge_alias()

    final_host = host or os.environ.get("HOUDINI_BRIDGE_HOST", "127.0.0.1")
    final_port = (
        port
        if port is not None
        else int(os.environ.get("HOUDINI_BRIDGE_PORT", "0") or 0)
    )

    server = HoudiniBridgeServer(
        host=final_host,
        port=final_port,
        dispatcher=MainThreadDispatcher(),
    )
    server.start()

    _SERVER = server
    atexit.register(_safe_stop)
    _try_register_houdini_exit_hook()
    return server


def stop() -> None:
    """Stop the running server, if any."""

    global _SERVER
    if _SERVER is None:
        return
    _SERVER.stop()
    _SERVER = None


def is_running() -> bool:
    return _SERVER is not None


def get_server() -> Optional[HoudiniBridgeServer]:
    return _SERVER


def _configure_logging(level: str) -> None:
    root = logging.getLogger("houdini_bridge")
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s %(message)s"))
    root.addHandler(handler)
    try:
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
    except Exception:
        root.setLevel(logging.INFO)


def _safe_stop() -> None:
    try:
        stop()
    except Exception:  # pragma: no cover
        pass


def _try_register_houdini_exit_hook() -> None:
    """Register a Houdini-side exit callback when ``hou`` is importable."""

    try:  # pragma: no cover - Houdini only
        import hou  # type: ignore
    except Exception:
        return

    try:
        hou.session.houdini_bridge_stop = stop  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        LOGGER.debug("could not register hou.session hook: %s", exc)


def _register_hou_bridge_alias() -> None:
    """Make ``import hou_bridge`` resolve to ``houdini_bridge.libraries``.

    The exec dispatcher pre-binds ``hou_bridge`` as a name in the script
    namespace, but agent-authored scripts naturally write ``import hou_bridge``
    at the top. Register the package in :data:`sys.modules` so that import
    succeeds without any extra ceremony.
    """

    import sys

    try:
        from . import libraries as _libs

        sys.modules.setdefault("hou_bridge", _libs)
    except Exception as exc:  # pragma: no cover
        LOGGER.debug("could not register hou_bridge alias: %s", exc)
