"""Viewport — screenshots, frame range flipbooks, basic state queries."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "viewport"


@bridge_function(danger="read", summary="List Scene Viewer viewports and their state.")
def list_viewers() -> Dict[str, Any]:
    hou = _common.require_hou()
    out = []
    for pane in hou.ui.paneTabs():
        if not isinstance(pane, hou.SceneViewer):
            continue
        viewport = pane.curViewport()
        out.append(
            {
                "name": pane.name(),
                "viewport": viewport.name() if viewport else None,
                "type": viewport.type().name() if viewport else None,
            }
        )
    return {"viewers": out}


@bridge_function(danger="write", summary="Capture a screenshot of the current Scene Viewer.")
def screenshot(
    output_path: str,
    *,
    width: int = 1280,
    height: int = 720,
    frame: Optional[float] = None,
) -> Dict[str, Any]:
    hou = _common.require_hou()
    pane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if pane is None:
        raise RuntimeError("no Scene Viewer pane available")

    if frame is not None:
        hou.setFrame(float(frame))

    settings = pane.flipbookSettings().stash()
    settings.frameRange((hou.frame(), hou.frame()))
    settings.outputToMPlay(False)
    settings.output(output_path)
    settings.useResolution(True)
    settings.resolution((int(width), int(height)))
    pane.flipbook(pane.curViewport(), settings)

    return {
        "path": output_path,
        "width": int(width),
        "height": int(height),
        "frame": float(hou.frame()),
        "exists": os.path.exists(output_path),
    }


@bridge_function(danger="write", summary="Frame the viewport on a specific node.")
def frame_node(node_path: str) -> Dict[str, Any]:
    hou = _common.require_hou()
    pane = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
    if pane is None:
        raise RuntimeError("no Scene Viewer pane available")
    node = _common.resolve_node(node_path)
    viewport = pane.curViewport()
    viewport.frameSelected() if False else viewport.frameAll()
    return {"framed": node.path()}
