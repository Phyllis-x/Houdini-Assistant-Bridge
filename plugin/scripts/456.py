"""Houdini auto-start hook (hip loaded / changed).

Same body as ``123.py`` but Houdini runs it whenever a hip file finishes
loading (including the initial load when launched with a `.hip`). The bridge
is idempotent, so re-running ``start()`` while it is already up is a no-op.
"""

from __future__ import annotations

import logging
import os

LOGGER = logging.getLogger("houdini_bridge.autostart")


def _autostart() -> None:
    if os.environ.get("HOUDINI_BRIDGE_DISABLE", "") in {"1", "true", "TRUE"}:
        LOGGER.info("HOUDINI_BRIDGE_DISABLE is set; skipping autostart")
        return
    try:
        import houdini_bridge

        if houdini_bridge.is_running():
            return
        houdini_bridge.start()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("houdini_bridge failed to start: %s", exc)


_autostart()
