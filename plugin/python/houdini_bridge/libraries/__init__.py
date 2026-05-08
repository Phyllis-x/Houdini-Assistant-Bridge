"""Typed library surface exposed to the Agent.

Each public submodule defines a ``LIBRARY`` constant (the short name used in
manifest / preflight / CLI ``call``) and exports functions decorated with
:func:`houdini_bridge.registry.bridge_function`. Importing the package as
``hou_bridge`` inside ``exec`` scripts is the recommended idiomatic surface.
"""

from __future__ import annotations

from . import asset, cache, event, geometry, node, parameter, scene, viewport

__all__ = [
    "asset",
    "cache",
    "event",
    "geometry",
    "node",
    "parameter",
    "scene",
    "viewport",
]
