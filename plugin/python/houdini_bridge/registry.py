"""Library + function registry.

Each ``houdini_bridge.libraries.<name>`` module declares a ``LIBRARY`` constant
(a string used by the agent) and exports public functions tagged with
``@bridge_function(danger=...)``. The registry collects them into a flat
table and produces the manifest snapshot consumed by the CLI preflight.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

DANGER_LEVELS = ("read", "write", "destructive")


@dataclass(frozen=True)
class FunctionSpec:
    """Manifest entry for a single library function."""

    library: str
    name: str
    danger: str
    summary: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    returns: Optional[str] = None
    callable: Optional[Callable[..., Any]] = field(default=None, repr=False)

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "library": self.library,
            "name": self.name,
            "danger": self.danger,
            "summary": self.summary,
            "parameters": self.parameters,
            "returns": self.returns,
        }


def bridge_function(*, danger: str = "read", summary: Optional[str] = None):
    """Decorator that tags a callable as part of the bridge surface."""

    if danger not in DANGER_LEVELS:
        raise ValueError(f"invalid danger level: {danger!r}")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func.__bridge_meta__ = {  # type: ignore[attr-defined]
            "danger": danger,
            "summary": summary or _first_doc_line(func),
        }
        return func

    return decorator


class Registry:
    """In-memory map of ``library_name -> function_name -> FunctionSpec``."""

    def __init__(self) -> None:
        self._libraries: Dict[str, Dict[str, FunctionSpec]] = {}

    def register_module(self, module: Any) -> None:
        library = getattr(module, "LIBRARY", None)
        if not library:
            return
        bucket = self._libraries.setdefault(library, {})
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            meta = getattr(obj, "__bridge_meta__", None)
            if meta is None:
                continue
            bucket[name] = _build_spec(library, name, obj, meta)

    def discover(self, package_name: str = "houdini_bridge.libraries") -> None:
        package = importlib.import_module(package_name)
        for info in pkgutil.iter_modules(package.__path__):
            if info.name.startswith("_"):
                continue
            module = importlib.import_module(f"{package_name}.{info.name}")
            self.register_module(module)

    def libraries(self) -> Dict[str, Dict[str, FunctionSpec]]:
        return dict(self._libraries)

    def get(self, library: str, function: str) -> FunctionSpec:
        try:
            return self._libraries[library][function]
        except KeyError as exc:
            raise LookupError(f"unknown bridge function: {library}.{function}") from exc

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "schema": 1,
            "libraries": {
                lib: {fn.name: fn.to_manifest() for fn in fns.values()}
                for lib, fns in sorted(self._libraries.items())
            },
        }


_REGISTRY: Optional[Registry] = None


def get_registry() -> Registry:
    """Return the lazy-initialized package registry."""

    global _REGISTRY
    if _REGISTRY is None:
        registry = Registry()
        registry.discover()
        _REGISTRY = registry
    return _REGISTRY


def reset_registry() -> None:
    """Drop the cached registry; useful in tests."""

    global _REGISTRY
    _REGISTRY = None


def _build_spec(
    library: str,
    name: str,
    func: Callable[..., Any],
    meta: Dict[str, Any],
) -> FunctionSpec:
    sig = inspect.signature(func)
    parameters: List[Dict[str, Any]] = []
    for param in sig.parameters.values():
        if param.name == "self":
            continue
        parameters.append(
            {
                "name": param.name,
                "kind": param.kind.name,
                "required": param.default is inspect.Parameter.empty,
                "default": _safe_default(param.default),
                "annotation": _annotation_str(param.annotation),
            }
        )
    return FunctionSpec(
        library=library,
        name=name,
        danger=meta.get("danger", "read"),
        summary=meta.get("summary") or "",
        parameters=parameters,
        returns=_annotation_str(sig.return_annotation),
        callable=func,
    )


def _annotation_str(annotation: Any) -> Optional[str]:
    if annotation is inspect.Parameter.empty or annotation is inspect.Signature.empty:
        return None
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__qualname__", None) or repr(annotation)


def _safe_default(default: Any) -> Any:
    if default is inspect.Parameter.empty:
        return None
    if isinstance(default, (str, int, float, bool, type(None))):
        return default
    if isinstance(default, (list, tuple)):
        return [_safe_default(v) for v in default]
    return repr(default)


def _first_doc_line(func: Callable[..., Any]) -> str:
    doc = inspect.getdoc(func) or ""
    return doc.split("\n", 1)[0].strip()
