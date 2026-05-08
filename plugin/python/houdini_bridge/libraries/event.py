"""Reactive event subscription scaffold.

The first version exposes a subscription registry that records callbacks
against Houdini event types. It is intentionally lightweight: handlers run
in-process and surface events through a polling endpoint plus a session log,
because a streaming push channel requires a different transport than the
current request/response framing.

Future versions can swap the polling buffer for a long-poll or WebSocket
bridge without changing the public function names.
"""

from __future__ import annotations

import collections
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional

from ..registry import bridge_function
from . import _common

LIBRARY = "event"

_LOCK = threading.Lock()
_BUFFER: Deque[Dict[str, Any]] = collections.deque(maxlen=1000)
_SUBSCRIPTIONS: Dict[str, Dict[str, Any]] = {}


@bridge_function(danger="write", summary="Subscribe to a node's events (added/removed/parm changed).")
def subscribe_node_event(node_path: str, event_type: str) -> Dict[str, Any]:
    hou = _common.require_hou()
    node = _common.resolve_node(node_path)
    enum = _resolve_node_event_enum(hou, event_type)
    sub_id = f"node:{node.path()}:{event_type}:{int(time.time() * 1000)}"

    def _callback(**event):
        _record_event(sub_id, "node", event_type, node.path(), event)

    node.addEventCallback((enum,), _callback)

    with _LOCK:
        _SUBSCRIPTIONS[sub_id] = {
            "kind": "node",
            "event_type": event_type,
            "node_path": node.path(),
            "node": node,
            "callback": _callback,
            "enum": enum,
        }
    return {"subscription_id": sub_id, "node": node.path(), "event_type": event_type}


@bridge_function(danger="destructive", summary="Cancel a previously created subscription.")
def unsubscribe(subscription_id: str) -> Dict[str, Any]:
    with _LOCK:
        sub = _SUBSCRIPTIONS.pop(subscription_id, None)
    if sub is None:
        raise LookupError(f"no subscription with id {subscription_id!r}")
    if sub["kind"] == "node":
        try:
            sub["node"].removeEventCallback((sub["enum"],), sub["callback"])
        except Exception:
            pass
    return {"subscription_id": subscription_id, "removed": True}


@bridge_function(danger="read", summary="List all active event subscriptions.")
def list_subscriptions() -> List[Dict[str, Any]]:
    with _LOCK:
        return [
            {
                "subscription_id": sub_id,
                "kind": sub["kind"],
                "event_type": sub.get("event_type"),
                "node_path": sub.get("node_path"),
            }
            for sub_id, sub in _SUBSCRIPTIONS.items()
        ]


@bridge_function(danger="read", summary="Drain buffered events (FIFO). Returns the popped events.")
def drain_events(limit: int = 100) -> Dict[str, Any]:
    capped = max(1, min(int(limit), _BUFFER.maxlen or 1000))
    out: List[Dict[str, Any]] = []
    with _LOCK:
        while _BUFFER and len(out) < capped:
            out.append(_BUFFER.popleft())
        remaining = len(_BUFFER)
    return {"events": out, "remaining": remaining}


def _record_event(subscription_id: str, kind: str, event_type: str, source: str, payload: Dict[str, Any]) -> None:
    with _LOCK:
        _BUFFER.append(
            {
                "ts": time.time(),
                "subscription_id": subscription_id,
                "kind": kind,
                "event_type": event_type,
                "source": source,
                "payload": _coerce_payload(payload),
            }
        )


def _coerce_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for key, value in payload.items():
        try:
            safe[key] = repr(value)
        except Exception:
            safe[key] = "<unrepr>"
    return safe


def _resolve_node_event_enum(hou: Any, event_type: str):
    name = event_type.strip().lower()
    mapping = {
        "removed": "BeingDeleted",
        "deleted": "BeingDeleted",
        "name_changed": "NameChanged",
        "input_rewired": "InputRewired",
        "parm_tuple_changed": "ParmTupleChanged",
        "child_created": "ChildCreated",
        "child_deleted": "ChildDeleted",
        "child_switched": "ChildSelectionChanged",
    }
    enum_name = mapping.get(name)
    if enum_name is None:
        raise ValueError(f"unsupported node event_type: {event_type!r}")
    enum = getattr(hou.nodeEventType, enum_name, None)
    if enum is None:
        raise ValueError(f"hou.nodeEventType.{enum_name} is unavailable in this Houdini build")
    return enum
