"""HDA / asset introspection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "asset"


@bridge_function(danger="read", summary="List installed HDA libraries (.hda / .otl).")
def list_installed_libraries() -> List[str]:
    hou = _common.require_hou()
    return list(hou.hda.loadedFiles())


@bridge_function(danger="write", summary="Install (load) an HDA library file.")
def install_library(path: str, *, force_reload: bool = False) -> Dict[str, Any]:
    hou = _common.require_hou()
    hou.hda.installFile(path, force_use_assets=force_reload)
    return {"installed": path, "force_reload": bool(force_reload)}


@bridge_function(danger="destructive", summary="Uninstall an HDA library file.")
def uninstall_library(path: str) -> Dict[str, Any]:
    hou = _common.require_hou()
    hou.hda.uninstallFile(path)
    return {"uninstalled": path}


@bridge_function(danger="read", summary="Inspect a node type definition (HDA).")
def get_definition_info(category: str, type_name: str) -> Dict[str, Any]:
    hou = _common.require_hou()
    cat_map = {
        "Sop": hou.sopNodeTypeCategory(),
        "Object": hou.objNodeTypeCategory(),
        "Vop": hou.vopNodeTypeCategory(),
        "Driver": hou.ropNodeTypeCategory(),
        "Dop": hou.dopNodeTypeCategory(),
        "Lop": hou.lopNodeTypeCategory(),
        "Top": hou.topNodeTypeCategory(),
    }
    if category not in cat_map:
        raise ValueError(f"unknown category: {category}")
    node_type = cat_map[category].nodeType(type_name)
    if node_type is None:
        raise LookupError(f"no node type {category}/{type_name}")
    definition = node_type.definition()
    info: Dict[str, Any] = {
        "category": category,
        "type": type_name,
        "description": node_type.description(),
        "is_hda": definition is not None,
    }
    if definition is not None:
        info.update(
            {
                "library_path": definition.libraryFilePath(),
                "icon": definition.icon(),
                "options": {
                    "is_locked": definition.isLocked() if hasattr(definition, "isLocked") else None,
                    "is_current": definition.isCurrent() if hasattr(definition, "isCurrent") else None,
                },
            }
        )
    return info


@bridge_function(danger="read", summary="List instances of a node type currently in the scene.")
def find_instances(category: str, type_name: str, limit: int = 100) -> Dict[str, Any]:
    hou = _common.require_hou()
    matches: List[Dict[str, Any]] = []
    for node in hou.node("/").allSubChildren(recurse_in_locked_nodes=False):
        try:
            if node.type().category().name() == category and node.type().name() == type_name:
                matches.append(_common.serialize_node(node))
                if len(matches) >= limit:
                    break
        except Exception:
            continue
    return {"category": category, "type": type_name, "instances": matches}
