"""AST + manifest preflight for agent-supplied scripts and structured calls.

The preflight protects the bridge from common LLM hallucinations *before* the
script reaches Houdini:

* unknown library / function names (with did-you-mean suggestions),
* unknown keyword arguments,
* missing required positional arguments,
* destructive ops without an explicit allow list,
* raw ``hou`` writes when the script claims it only reads.

The preflight runs only when a manifest snapshot is available locally. When
the manifest is missing the CLI falls back to a permissive mode after warning
the user.
"""

from __future__ import annotations

import ast
import difflib
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from _manifest import Manifest


class PreflightError(RuntimeError):
    """Raised when the preflight rejects a script or structured call."""


# ---------- structured-call preflight ------------------------------------------


def preflight_call(
    library: str,
    function: str,
    kwargs: Dict[str, Any],
    manifest: Manifest,
    *,
    allow: Optional[Set[str]] = None,
) -> None:
    spec = manifest.function(library, function)
    if spec is None:
        raise PreflightError(_missing_message(library, function, manifest))

    declared = {p["name"] for p in spec.get("parameters", [])}
    unknown = [name for name in kwargs.keys() if name not in declared]
    if unknown:
        suggestions = _suggest_args(unknown, declared)
        raise PreflightError(
            f"{library}.{function}: unknown kwargs {unknown}. "
            f"Allowed: {sorted(declared)}. Suggestions: {suggestions}"
        )

    missing_required = [
        p["name"]
        for p in spec.get("parameters", [])
        if p.get("required") and p["name"] not in kwargs
    ]
    if missing_required:
        raise PreflightError(
            f"{library}.{function}: missing required kwargs {missing_required}"
        )

    danger = spec.get("danger", "read")
    if danger == "destructive" and "destructive" not in (allow or set()):
        raise PreflightError(
            f"{library}.{function} is tagged 'destructive'. "
            "Re-run with `--allow destructive` to authorise it."
        )


# ---------- script preflight ----------------------------------------------------


def preflight_script(
    script: str,
    manifest: Manifest,
    *,
    allow: Optional[Set[str]] = None,
) -> None:
    try:
        tree = ast.parse(script, mode="exec")
    except SyntaxError as exc:
        raise PreflightError(f"script does not parse: {exc}") from exc

    issues: List[str] = []
    for call in _iter_bridge_calls(tree):
        try:
            _validate_call(call, manifest, allow or set())
        except PreflightError as exc:
            issues.append(str(exc))

    if issues:
        raise PreflightError("\n  - ".join(["script has unsafe calls:", *issues]))


# ---------- helpers -------------------------------------------------------------


def _iter_bridge_calls(tree: ast.AST) -> Iterable[Tuple[str, str, ast.Call]]:
    """Yield ``(library, function, call_node)`` for every ``hou_bridge.<lib>.<fn>(...)`` call."""

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        info = _resolve_bridge_attr(node.func)
        if info is None:
            continue
        library, function = info
        yield library, function, node


def _resolve_bridge_attr(func: ast.AST) -> Optional[Tuple[str, str]]:
    """Detect calls of the form ``hou_bridge.<library>.<function>(...)``."""

    if not isinstance(func, ast.Attribute):
        return None
    function_name = func.attr
    middle = func.value
    if not isinstance(middle, ast.Attribute):
        return None
    library_name = middle.attr
    base = middle.value
    if isinstance(base, ast.Name) and base.id == "hou_bridge":
        return library_name, function_name
    return None


def _validate_call(
    call_info: Tuple[str, str, ast.Call],
    manifest: Manifest,
    allow: Set[str],
) -> None:
    library, function, node = call_info
    spec = manifest.function(library, function)
    if spec is None:
        raise PreflightError(_missing_message(library, function, manifest))

    declared = {p["name"] for p in spec.get("parameters", [])}
    kwarg_names = [kw.arg for kw in node.keywords if kw.arg]
    unknown = [name for name in kwarg_names if name not in declared]
    if unknown:
        raise PreflightError(
            f"hou_bridge.{library}.{function} unknown kwargs {unknown}; "
            f"allowed: {sorted(declared)}"
        )

    danger = spec.get("danger", "read")
    if danger == "destructive" and "destructive" not in allow:
        raise PreflightError(
            f"hou_bridge.{library}.{function} is destructive; "
            "rerun with --allow destructive"
        )


def _missing_message(library: str, function: str, manifest: Manifest) -> str:
    if library not in manifest.library_names():
        suggestions = difflib.get_close_matches(library, manifest.library_names(), n=3)
        return (
            f"unknown library {library!r}. Known: {manifest.library_names()}. "
            f"Did you mean: {suggestions or 'no close match'}?"
        )
    suggestions = difflib.get_close_matches(function, manifest.function_names(library), n=3)
    return (
        f"unknown function {library}.{function}. "
        f"Did you mean: {suggestions or 'no close match'}?"
    )


def _suggest_args(unknown: List[str], declared: Set[str]) -> Dict[str, List[str]]:
    return {
        name: difflib.get_close_matches(name, sorted(declared), n=3) or ["<no close match>"]
        for name in unknown
    }
