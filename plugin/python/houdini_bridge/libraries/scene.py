"""Scene introspection: hip file, network roots, takes, frame range."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "scene"

_TOP_LEVEL_NETWORKS = ("/obj", "/out", "/shop", "/mat", "/ch", "/img", "/stage", "/tasks", "/vex")


@bridge_function(danger="read", summary="High-level summary of the current hip file.")
def get_scene_summary() -> Dict[str, Any]:
    hou = _common.require_hou()
    hip_path = hou.hipFile.path()
    networks = []
    for path in _TOP_LEVEL_NETWORKS:
        node = hou.node(path)
        if node is None:
            continue
        children = node.children()
        networks.append(
            {
                "path": path,
                "child_count": len(children),
                "children_preview": [child.name() for child in children[:10]],
            }
        )

    return {
        "hip": hip_path,
        "hip_name": hou.hipFile.basename(),
        "houdini_version": ".".join(str(v) for v in hou.applicationVersion()),
        "fps": hou.fps(),
        "frame_range": {
            "start": hou.playbar.frameRange()[0],
            "end": hou.playbar.frameRange()[1],
            "playback_start": hou.playbar.playbackRange()[0],
            "playback_end": hou.playbar.playbackRange()[1],
            "current_frame": hou.frame(),
        },
        "current_take": hou.takes.currentTake().name() if hou.takes.currentTake() else "Main",
        "networks": networks,
    }


@bridge_function(danger="read", summary="List immediate children of a network node.")
def list_children(parent_path: str = "/obj", limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    parent = _common.resolve_node(parent_path)
    children = parent.children()
    return _common.page(
        [_common.serialize_node(child) for child in children],
        limit=min(limit, _common.MAX_NODES_INLINE),
        offset=offset,
    )


@bridge_function(danger="read", summary="Recursive walk of a network with depth cap.")
def walk_network(parent_path: str = "/obj", max_depth: int = 1) -> Dict[str, Any]:
    parent = _common.resolve_node(parent_path)
    return _common.serialize_node(parent, depth=max(0, min(max_depth, 4)))


@bridge_function(danger="read", summary="Currently selected nodes across the editor.")
def get_selected_nodes() -> List[Dict[str, Any]]:
    hou = _common.require_hou()
    return [_common.serialize_node(node) for node in hou.selectedNodes()]


@bridge_function(danger="read", summary="List Houdini takes with their parents.")
def list_takes() -> List[Dict[str, Any]]:
    hou = _common.require_hou()
    return [
        {
            "name": take.name(),
            "parent": take.parent().name() if take.parent() else None,
            "is_current": take == hou.takes.currentTake(),
        }
        for take in hou.takes.takes()
    ]


@bridge_function(danger="read", summary="Read the current playbar frame.")
def get_current_frame() -> float:
    hou = _common.require_hou()
    return float(hou.frame())


@bridge_function(danger="write", summary="Set the playbar to a specific frame.")
def set_current_frame(frame: float) -> Dict[str, Any]:
    hou = _common.require_hou()
    hou.setFrame(float(frame))
    return {"frame": float(hou.frame())}


@bridge_function(danger="write", summary="Set the playbar frame range.")
def set_frame_range(start: float, end: float, playback_start: Optional[float] = None, playback_end: Optional[float] = None) -> Dict[str, Any]:
    hou = _common.require_hou()
    hou.playbar.setFrameRange(float(start), float(end))
    pb_start = float(playback_start) if playback_start is not None else float(start)
    pb_end = float(playback_end) if playback_end is not None else float(end)
    hou.playbar.setPlaybackRange(pb_start, pb_end)
    return {
        "frame_range": [float(start), float(end)],
        "playback_range": [pb_start, pb_end],
    }


@bridge_function(danger="write", summary="Save the current hip file to disk.")
def save_hip(path: Optional[str] = None) -> Dict[str, Any]:
    hou = _common.require_hou()
    if path:
        hou.hipFile.save(file_name=path)
    else:
        hou.hipFile.save()
    return {"hip": hou.hipFile.path()}
