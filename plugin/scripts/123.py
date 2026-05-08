"""Houdini auto-start hook (no hip loaded).

Houdini executes ``$HOUDINI_PATH/scripts/123.py`` once when the editor starts
without a hip file. We use it to bring up the bridge server immediately so
the agent CLI can discover the session even before any scene is opened.

The matching ``456.py`` covers the "Houdini started with a hip" path.
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
    except Exception as exc:  # noqa: BLE001 — never break Houdini's startup
        LOGGER.warning("houdini_bridge failed to start: %s", exc)


_autostart()
