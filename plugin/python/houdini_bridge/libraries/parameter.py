"""Parameter access: get / set / expression / keyframes / multiparm."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "parameter"


@bridge_function(danger="read", summary="Inspect a single parameter on a node.")
def get_parm(node_path: str, parm_name: str, *, include_keyframes: bool = False) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    return _common.serialize_parm(parm, include_keyframes=include_keyframes)


@bridge_function(danger="read", summary="List all parameters on a node.")
def list_parms(node_path: str, limit: int = 100, offset: int = 0, include_invisible: bool = False) -> Dict[str, Any]:
    node = _common.resolve_node(node_path)
    parms = list(node.parms())
    if not include_invisible:
        parms = [p for p in parms if not (hasattr(p, "isHidden") and p.isHidden())]
    return _common.page(
        [_common.serialize_parm(parm) for parm in parms],
        limit=min(limit, _common.MAX_PARMS_INLINE),
        offset=offset,
    )


@bridge_function(danger="write", summary="Write a single value to a parameter.")
def set_parm(node_path: str, parm_name: str, value: Any) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    parm.set(_coerce_value(parm, value))
    return _common.serialize_parm(parm)


@bridge_function(danger="write", summary="Write multiple parameters at once.")
def set_parms(node_path: str, values: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(values, dict):
        raise ValueError("values must be a JSON object of parm_name -> value")
    node = _common.resolve_node(node_path)
    coerced = {name: _coerce_value(node.parm(name), value) for name, value in values.items() if node.parm(name) is not None}
    node.setParms(coerced)
    return {
        "node": node_path,
        "updated": list(coerced.keys()),
        "skipped": [name for name in values.keys() if name not in coerced],
    }


@bridge_function(danger="write", summary="Set an expression on a parameter.")
def set_expression(
    node_path: str,
    parm_name: str,
    expression: str,
    *,
    language: str = "hscript",
) -> Dict[str, Any]:
    hou = _common.require_hou()
    parm = _resolve_parm(node_path, parm_name)
    lang_enum = {
        "hscript": hou.exprLanguage.Hscript,
        "python": hou.exprLanguage.Python,
    }.get(language.lower())
    if lang_enum is None:
        raise ValueError(f"unknown expression language: {language!r}")
    parm.setExpression(expression, language=lang_enum)
    return _common.serialize_parm(parm)


@bridge_function(danger="write", summary="Remove any expression / keyframes from a parameter.")
def revert_to_default(node_path: str, parm_name: str) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    parm.revertToDefaults()
    return _common.serialize_parm(parm)


@bridge_function(danger="write", summary="Add a constant keyframe at a frame.")
def add_keyframe(node_path: str, parm_name: str, frame: float, value: float) -> Dict[str, Any]:
    hou = _common.require_hou()
    parm = _resolve_parm(node_path, parm_name)
    keyframe = hou.Keyframe()
    keyframe.setFrame(float(frame))
    keyframe.setValue(float(value))
    parm.setKeyframe(keyframe)
    return _common.serialize_parm(parm, include_keyframes=True)


@bridge_function(danger="destructive", summary="Delete every keyframe on a parameter.")
def clear_keyframes(node_path: str, parm_name: str) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    parm.deleteAllKeyframes()
    return _common.serialize_parm(parm)


@bridge_function(danger="write", summary="Append an instance to a multiparm.")
def append_multiparm_instance(node_path: str, parm_name: str) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    if not hasattr(parm, "insertMultiParmInstance"):
        raise ValueError(f"parameter {parm_name!r} on {node_path} is not a multiparm")
    count = parm.eval()
    try:
        count_int = int(count)
    except Exception:
        count_int = 0
    parm.insertMultiParmInstance(count_int)
    return _common.serialize_parm(parm)


@bridge_function(danger="destructive", summary="Remove a multiparm instance by index.")
def remove_multiparm_instance(node_path: str, parm_name: str, index: int) -> Dict[str, Any]:
    parm = _resolve_parm(node_path, parm_name)
    if not hasattr(parm, "removeMultiParmInstance"):
        raise ValueError(f"parameter {parm_name!r} on {node_path} is not a multiparm")
    parm.removeMultiParmInstance(int(index))
    return _common.serialize_parm(parm)


@bridge_function(danger="write", summary="Add a spare parameter using a parm template.")
def add_spare_parameter(
    node_path: str,
    parm_name: str,
    label: str,
    *,
    parm_type: str = "float",
    default: Optional[float] = 0.0,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Dict[str, Any]:
    hou = _common.require_hou()
    node = _common.resolve_node(node_path)
    template_group = node.parmTemplateGroup()
    parm_type_lower = parm_type.lower()
    if parm_type_lower == "float":
        template = hou.FloatParmTemplate(parm_name, label, 1, default_value=(default or 0.0,))
    elif parm_type_lower == "int":
        template = hou.IntParmTemplate(parm_name, label, 1, default_value=(int(default or 0),))
    elif parm_type_lower == "string":
        template = hou.StringParmTemplate(parm_name, label, 1)
    elif parm_type_lower == "toggle":
        template = hou.ToggleParmTemplate(parm_name, label, default_value=bool(default))
    else:
        raise ValueError(f"unknown parm_type: {parm_type!r}")

    if hasattr(template, "setMinValue") and min_value is not None:
        template.setMinValue(float(min_value))
    if hasattr(template, "setMaxValue") and max_value is not None:
        template.setMaxValue(float(max_value))

    template_group.addParmTemplate(template)
    node.setParmTemplateGroup(template_group)
    return _common.serialize_parm(node.parm(parm_name))


def _resolve_parm(node_path: str, parm_name: str):
    node = _common.resolve_node(node_path)
    parm = node.parm(parm_name) or node.parmTuple(parm_name)
    if parm is None:
        raise LookupError(f"parameter {parm_name!r} not found on {node_path}")
    return parm


def _coerce_value(parm: Any, value: Any) -> Any:
    if parm is None:
        return value
    if isinstance(value, list):
        return tuple(value)
    return value
