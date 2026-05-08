"""File cache / ROP inspection and controlled cooks."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "cache"

_FILECACHE_TYPES = {"filecache", "filecache::2.0", "rop_geometry", "rop_alembic"}


@bridge_function(danger="read", summary="Inspect a filecache / ROP node and its on-disk state.")
def inspect_cache_node(node_path: str) -> Dict[str, Any]:
    node = _common.resolve_node(node_path)
    type_name = node.type().name()
    info: Dict[str, Any] = {
        "node": node_path,
        "type": type_name,
        "frame_range": _read_parm(node, ("f1", "f2", "f3"), default=(None, None, None)),
        "file_path": _safe_eval_parm(node, "file") or _safe_eval_parm(node, "sopoutput") or _safe_eval_parm(node, "copoutput"),
    }
    pattern = info.get("file_path")
    if pattern:
        info["disk_state"] = _scan_pattern(pattern, *info["frame_range"][:2])
    return info


@bridge_function(danger="write", summary="Render the given ROP node (use sparingly — runs synchronously).")
def render_rop(node_path: str, *, frame_range: Optional[List[float]] = None) -> Dict[str, Any]:
    node = _common.resolve_node(node_path)
    if hasattr(node, "render"):
        if frame_range and len(frame_range) >= 2:
            node.render(frame_range=tuple(float(v) for v in frame_range[:2]))
        else:
            node.render()
        return {"rendered": node_path, "frame_range": frame_range}
    raise ValueError(f"node {node_path} is not a renderable ROP")


@bridge_function(danger="destructive", summary="Delete the on-disk files matching a cache pattern.")
def clear_cache(node_path: str, *, dry_run: bool = True) -> Dict[str, Any]:
    node = _common.resolve_node(node_path)
    pattern = _safe_eval_parm(node, "file") or _safe_eval_parm(node, "sopoutput")
    if not pattern:
        raise ValueError(f"node {node_path} does not expose a 'file' or 'sopoutput' parameter")
    f1, f2, _ = _read_parm(node, ("f1", "f2", "f3"), default=(None, None, None))
    candidates = _expand_pattern_paths(pattern, f1, f2)
    deleted = []
    if not dry_run:
        for p in candidates:
            try:
                os.remove(p)
                deleted.append(p)
            except OSError:
                continue
    return {
        "node": node_path,
        "pattern": pattern,
        "candidates": candidates,
        "deleted": deleted,
        "dry_run": dry_run,
    }


def _safe_eval_parm(node: Any, parm_name: str) -> Optional[str]:
    parm = node.parm(parm_name)
    if parm is None:
        return None
    try:
        return str(parm.eval())
    except Exception:
        return None


def _read_parm(node: Any, names: tuple, default) -> tuple:
    out = []
    for idx, name in enumerate(names):
        parm = node.parm(name)
        if parm is None:
            out.append(default[idx])
            continue
        try:
            out.append(parm.eval())
        except Exception:
            out.append(default[idx])
    return tuple(out)


def _scan_pattern(pattern: str, f1, f2) -> Dict[str, Any]:
    if f1 is None or f2 is None:
        return {"checked": False, "reason": "frame range unavailable"}
    try:
        f1i, f2i = int(f1), int(f2)
    except Exception:
        return {"checked": False, "reason": "non-integer frame range"}

    present = []
    missing = []
    for frame in range(f1i, f2i + 1):
        path = _format_pattern(pattern, frame)
        if os.path.exists(path):
            present.append(frame)
        else:
            missing.append(frame)
    return {
        "checked": True,
        "expected_frames": f2i - f1i + 1,
        "present": len(present),
        "missing": missing[:50],
        "missing_count": len(missing),
    }


def _format_pattern(pattern: str, frame: int) -> str:
    if "$F" in pattern:
        for token, width in (("$F4", 4), ("$F3", 3), ("$F2", 2), ("$F", 0)):
            if token in pattern:
                return pattern.replace(token, str(frame).zfill(width) if width else str(frame))
    return pattern


def _expand_pattern_paths(pattern: str, f1, f2) -> List[str]:
    if f1 is None or f2 is None:
        return [pattern]
    try:
        f1i, f2i = int(f1), int(f2)
    except Exception:
        return [pattern]
    return [_format_pattern(pattern, frame) for frame in range(f1i, f2i + 1)]
