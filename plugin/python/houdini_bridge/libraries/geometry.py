"""SOP geometry inspection — summaries, bounds, attributes, lightweight samples."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "geometry"


@bridge_function(danger="read", summary="High-level summary of a SOP node's cooked geometry.")
def get_geometry_summary(node_path: str) -> Dict[str, Any]:
    geo = _resolve_geometry(node_path)
    bounds = geo.boundingBox() if hasattr(geo, "boundingBox") else None
    summary: Dict[str, Any] = {
        "node": node_path,
        "point_count": len(geo.points()) if hasattr(geo, "points") else 0,
        "primitive_count": len(geo.prims()) if hasattr(geo, "prims") else 0,
        "vertex_count": geo.intrinsicValue("vertexcount") if hasattr(geo, "intrinsicValue") else None,
        "primitive_types": _primitive_type_histogram(geo),
        "attributes": _attribute_summary(geo),
        "groups": _group_summary(geo),
    }
    if bounds is not None:
        summary["bounds"] = {
            "min": [bounds.minvec().x(), bounds.minvec().y(), bounds.minvec().z()],
            "max": [bounds.maxvec().x(), bounds.maxvec().y(), bounds.maxvec().z()],
            "center": [bounds.center().x(), bounds.center().y(), bounds.center().z()],
            "size": [bounds.sizevec().x(), bounds.sizevec().y(), bounds.sizevec().z()],
        }
    return summary


@bridge_function(danger="read", summary="Sample N points from the geometry as raw JSON.")
def sample_points(
    node_path: str,
    count: int = 10,
    *,
    attribute: str = "P",
    offset: int = 0,
) -> Dict[str, Any]:
    geo = _resolve_geometry(node_path)
    points = list(geo.points())
    capped = min(int(count), _common.MAX_POINTS_INLINE)
    sliced = points[offset : offset + capped]

    samples = []
    for point in sliced:
        try:
            value = point.attribValue(attribute)
        except Exception as exc:  # noqa: BLE001
            value = {"__error__": str(exc)}
        samples.append({"number": point.number(), "value": _to_jsonable(value)})

    return {
        "node": node_path,
        "attribute": attribute,
        "samples": samples,
        "total_points": len(points),
        "offset": offset,
        "limit": capped,
        "truncated": len(points) > offset + capped,
    }


@bridge_function(danger="read", summary="Sample N primitives' centroids and groups.")
def sample_primitives(node_path: str, count: int = 10, offset: int = 0) -> Dict[str, Any]:
    geo = _resolve_geometry(node_path)
    prims = list(geo.prims())
    capped = min(int(count), _common.MAX_PRIMS_INLINE)
    sliced = prims[offset : offset + capped]

    samples = []
    for prim in sliced:
        try:
            centroid = prim.positionAtInterior(0.5, 0.5)
            centroid_value = [centroid.x(), centroid.y(), centroid.z()]
        except Exception:
            centroid_value = None
        samples.append(
            {
                "number": prim.number(),
                "type": prim.type().name() if hasattr(prim, "type") else "unknown",
                "vertex_count": prim.numVertices() if hasattr(prim, "numVertices") else 0,
                "centroid": centroid_value,
            }
        )

    return {
        "node": node_path,
        "samples": samples,
        "total_primitives": len(prims),
        "offset": offset,
        "limit": capped,
        "truncated": len(prims) > offset + capped,
    }


@bridge_function(danger="read", summary="List point/primitive/vertex/detail attributes.")
def list_attributes(node_path: str) -> Dict[str, List[Dict[str, Any]]]:
    geo = _resolve_geometry(node_path)
    return _attribute_summary(geo)


@bridge_function(danger="read", summary="Read a detail attribute value.")
def get_detail_attribute(node_path: str, attribute: str) -> Any:
    geo = _resolve_geometry(node_path)
    try:
        return _to_jsonable(geo.attribValue(attribute))
    except Exception as exc:  # noqa: BLE001
        raise LookupError(f"detail attribute {attribute!r} unavailable: {exc}") from exc


def _resolve_geometry(node_path: str):
    node = _common.resolve_node(node_path)
    if not hasattr(node, "geometry"):
        raise ValueError(f"node {node_path} does not produce geometry")
    geo = node.geometry()
    if geo is None:
        raise ValueError(f"node {node_path} has no cooked geometry; cook it first")
    return geo


def _primitive_type_histogram(geo: Any) -> Dict[str, int]:
    histogram: Dict[str, int] = {}
    for prim in geo.prims():
        try:
            type_name = prim.type().name()
        except Exception:
            type_name = "unknown"
        histogram[type_name] = histogram.get(type_name, 0) + 1
    return histogram


def _attribute_summary(geo: Any) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "point": [_attrib_dict(a) for a in geo.pointAttribs()],
        "primitive": [_attrib_dict(a) for a in geo.primAttribs()],
        "vertex": [_attrib_dict(a) for a in geo.vertexAttribs()],
        "detail": [_attrib_dict(a) for a in geo.globalAttribs()],
    }


def _group_summary(geo: Any) -> Dict[str, List[str]]:
    return {
        "point": [g.name() for g in geo.pointGroups()],
        "primitive": [g.name() for g in geo.primGroups()],
        "edge": [g.name() for g in geo.edgeGroups()],
    }


def _attrib_dict(attrib: Any) -> Dict[str, Any]:
    return {
        "name": attrib.name(),
        "type": attrib.dataType().name() if hasattr(attrib.dataType(), "name") else str(attrib.dataType()),
        "size": attrib.size() if hasattr(attrib, "size") else None,
    }


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    if isinstance(value, (tuple, list)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        out = [float(value.x()), float(value.y())]
        if hasattr(value, "z"):
            out.append(float(value.z()))
        if hasattr(value, "w"):
            out.append(float(value.w()))
        return out
    return repr(value)
