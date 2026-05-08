"""Node CRUD: create / delete / move / connect / layout."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "node"


@bridge_function(danger="read", summary="Inspect a single node by absolute path.")
def get_node(path: str, *, include_parms: bool = False) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    info = _common.serialize_node(node, depth=0)

    info["inputs"] = [
        {"index": idx, "path": inp.path() if inp else None}
        for idx, inp in enumerate(node.inputs())
    ]
    info["outputs"] = [
        {"index": idx, "path": out.path()}
        for idx, conn in enumerate(node.outputConnections())
        for out in [conn.outputNode()]
    ]
    if include_parms:
        info["parms"] = [
            _common.serialize_parm(parm)
            for parm in node.parms()[: _common.MAX_PARMS_INLINE]
        ]
    return info


@bridge_function(danger="write", summary="Create a node by type underneath a parent.")
def create_node(
    parent_path: str,
    type_name: str,
    name: Optional[str] = None,
    *,
    position: Optional[List[float]] = None,
    set_display_flag: bool = False,
    set_render_flag: bool = False,
) -> Dict[str, Any]:
    hou = _common.require_hou()
    parent = _common.resolve_node(parent_path)
    new_node = parent.createNode(type_name, node_name=name)
    if position and len(position) >= 2:
        new_node.setPosition(hou.Vector2(float(position[0]), float(position[1])))
    if set_display_flag and hasattr(new_node, "setDisplayFlag"):
        new_node.setDisplayFlag(True)
    if set_render_flag and hasattr(new_node, "setRenderFlag"):
        new_node.setRenderFlag(True)
    return _common.serialize_node(new_node)


@bridge_function(danger="destructive", summary="Delete a node by absolute path.")
def delete_node(path: str) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    parent_path = node.parent().path() if node.parent() else None
    node.destroy()
    return {"deleted": path, "parent": parent_path}


@bridge_function(danger="write", summary="Rename a node.")
def rename_node(path: str, new_name: str) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    node.setName(new_name, unique_name=True)
    return _common.serialize_node(node)


@bridge_function(danger="write", summary="Move a node to a new (x, y) network coordinate.")
def move_node(path: str, x: float, y: float) -> Dict[str, Any]:
    hou = _common.require_hou()
    node = _common.resolve_node(path)
    node.setPosition(hou.Vector2(float(x), float(y)))
    return _common.serialize_node(node)


@bridge_function(danger="write", summary="Connect two nodes' input/output indices.")
def connect_inputs(
    target_path: str,
    source_path: str,
    *,
    input_index: int = 0,
    output_index: int = 0,
) -> Dict[str, Any]:
    target = _common.resolve_node(target_path)
    source = _common.resolve_node(source_path)
    target.setInput(int(input_index), source, int(output_index))
    return {
        "target": target_path,
        "source": source_path,
        "input_index": int(input_index),
        "output_index": int(output_index),
    }


@bridge_function(danger="write", summary="Disconnect a node's input.")
def disconnect_input(target_path: str, input_index: int = 0) -> Dict[str, Any]:
    target = _common.resolve_node(target_path)
    target.setInput(int(input_index), None)
    return {"target": target_path, "input_index": int(input_index)}


@bridge_function(danger="write", summary="Auto-layout a network's children.")
def layout_children(parent_path: str) -> Dict[str, Any]:
    parent = _common.resolve_node(parent_path)
    parent.layoutChildren()
    return {"laid_out": parent_path, "child_count": len(parent.children())}


@bridge_function(danger="write", summary="Set the display flag on a node.")
def set_display_flag(path: str, value: bool = True) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    if not hasattr(node, "setDisplayFlag"):
        raise ValueError(f"node {path} has no display flag")
    node.setDisplayFlag(bool(value))
    return _common.serialize_node(node)


@bridge_function(danger="write", summary="Set the render flag on a node.")
def set_render_flag(path: str, value: bool = True) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    if not hasattr(node, "setRenderFlag"):
        raise ValueError(f"node {path} has no render flag")
    node.setRenderFlag(bool(value))
    return _common.serialize_node(node)


@bridge_function(danger="write", summary="Bypass or unbypass a node.")
def set_bypass(path: str, value: bool = True) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    if not hasattr(node, "bypass"):
        raise ValueError(f"node {path} cannot be bypassed")
    node.bypass(bool(value))
    return _common.serialize_node(node)


@bridge_function(danger="write", summary="Cook a node and return its cook stats.")
def cook_node(path: str, *, force: bool = False) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    node.cook(force=bool(force))
    stats: Dict[str, Any] = {"path": path, "cooked": True}
    if hasattr(node, "cookCount"):
        stats["cook_count"] = node.cookCount()
    if hasattr(node, "errors"):
        stats["errors"] = list(node.errors())
    if hasattr(node, "warnings"):
        stats["warnings"] = list(node.warnings())
    return stats


@bridge_function(danger="read", summary="List all node types available in a category.")
def list_node_types(category: str = "Sop", limit: int = 200, offset: int = 0) -> Dict[str, Any]:
    hou = _common.require_hou()
    categories = {
        "Sop": hou.sopNodeTypeCategory(),
        "Object": hou.objNodeTypeCategory(),
        "Driver": hou.ropNodeTypeCategory(),
        "Vop": hou.vopNodeTypeCategory(),
        "Dop": hou.dopNodeTypeCategory(),
        "Chop": hou.chopNodeTypeCategory(),
        "Cop2": hou.cop2NodeTypeCategory(),
        "Lop": hou.lopNodeTypeCategory(),
        "Top": hou.topNodeTypeCategory(),
        "Shop": hou.shopNodeTypeCategory(),
    }
    if category not in categories:
        raise ValueError(f"unknown node category: {category}")
    types = sorted(categories[category].nodeTypes().keys())
    return _common.page(types, limit=limit, offset=offset)


@bridge_function(danger="read", summary="List a node's recorded errors and warnings.")
def get_node_errors(path: str) -> Dict[str, Any]:
    node = _common.resolve_node(path)
    return {
        "path": path,
        "errors": list(node.errors()) if hasattr(node, "errors") else [],
        "warnings": list(node.warnings()) if hasattr(node, "warnings") else [],
        "messages": list(node.messages()) if hasattr(node, "messages") else [],
    }
