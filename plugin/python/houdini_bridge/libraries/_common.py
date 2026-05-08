"""Shared helpers for typed bridge libraries.

The helpers here:

* lazily import ``hou`` and surface a clear error when called outside Houdini,
* normalise common return shapes (node, parameter, geometry summary),
* enforce conservative size caps so JSON responses stay small.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

MAX_POINTS_INLINE = 1000
MAX_PRIMS_INLINE = 1000
MAX_NODES_INLINE = 500
MAX_PARMS_INLINE = 200


class HouUnavailableError(RuntimeError):
    """Raised when a library function is called outside Houdini."""


def require_hou():
    """Return the live ``hou`` module or raise :class:`HouUnavailableError`."""

    try:
        import hou  # type: ignore

        return hou
    except Exception as exc:  # pragma: no cover
        raise HouUnavailableError("hou is unavailable; this function must run inside Houdini") from exc


def resolve_node(path: str):
    """Return ``hou.Node`` for *path*, raising ``LookupError`` if missing."""

    hou = require_hou()
    node = hou.node(path)
    if node is None:
        raise LookupError(f"no node at path {path!r}")
    return node


def serialize_node(node: Any, *, depth: int = 0) -> Dict[str, Any]:
    """Compact JSON-friendly summary of a single ``hou.Node``."""

    info: Dict[str, Any] = {
        "path": node.path(),
        "name": node.name(),
        "type": node.type().name(),
        "category": node.type().category().name(),
        "is_locked": node.isHardLocked() if hasattr(node, "isHardLocked") else False,
        "display_flag": _safe_bool(getattr(node, "isDisplayFlagSet", None)),
        "render_flag": _safe_bool(getattr(node, "isRenderFlagSet", None)),
        "bypass_flag": _safe_bool(getattr(node, "isBypassed", None)),
        "selected": _safe_bool(getattr(node, "isSelected", None)),
        "color": _color_tuple(node),
        "position": _position_tuple(node),
    }

    if hasattr(node, "children"):
        info["child_count"] = len(node.children())

    if depth > 0 and hasattr(node, "children"):
        info["children"] = [serialize_node(child, depth=depth - 1) for child in node.children()]

    return info


def serialize_parm(parm: Any, *, include_keyframes: bool = False) -> Dict[str, Any]:
    """JSON-friendly summary of a single ``hou.Parm``."""

    template = parm.parmTemplate() if hasattr(parm, "parmTemplate") else None

    info: Dict[str, Any] = {
        "name": parm.name(),
        "label": template.label() if template else parm.name(),
        "type": template.dataType().name() if template else "Unknown",
        "raw_value": parm.rawValue() if hasattr(parm, "rawValue") else None,
        "eval_value": _safe_eval(parm),
        "is_keyframed": _safe_bool(getattr(parm, "keyframes", None), call=lambda f: bool(f())),
        "is_locked": _safe_bool(getattr(parm, "isLocked", None)),
        "is_disabled": _safe_bool(getattr(parm, "isDisabled", None)),
        "is_at_default": _safe_bool(getattr(parm, "isAtDefault", None)),
    }

    if include_keyframes and hasattr(parm, "keyframes"):
        try:
            info["keyframes"] = [
                {
                    "frame": kf.frame(),
                    "value": kf.value(),
                    "expression": kf.expression() if hasattr(kf, "expression") else None,
                }
                for kf in parm.keyframes()
            ]
        except Exception as exc:  # noqa: BLE001
            info["keyframes_error"] = str(exc)

    return info


def page(items: Iterable[Any], *, limit: int, offset: int = 0) -> Dict[str, Any]:
    """Apply offset/limit to *items* and return a paginated envelope."""

    materialised = list(items)
    total = len(materialised)
    sliced = materialised[offset : offset + limit]
    return {
        "items": sliced,
        "total": total,
        "offset": offset,
        "limit": limit,
        "truncated": total > offset + limit,
    }


def _safe_bool(method: Any, *, call=lambda fn: bool(fn())) -> Optional[bool]:
    if method is None:
        return None
    try:
        return call(method)
    except Exception:
        return None


def _safe_eval(parm: Any) -> Any:
    try:
        return parm.eval()
    except Exception as exc:  # noqa: BLE001
        return {"__error__": str(exc)}


def _color_tuple(node: Any) -> Optional[List[float]]:
    try:
        color = node.color()
        return [float(color.rgb()[0]), float(color.rgb()[1]), float(color.rgb()[2])]
    except Exception:
        return None


def _position_tuple(node: Any) -> Optional[List[float]]:
    try:
        pos = node.position()
        return [float(pos.x()), float(pos.y())]
    except Exception:
        return None
