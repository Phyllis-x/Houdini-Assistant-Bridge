"""Main-thread dispatcher.

HOM is not thread-safe; every callable that touches ``hou`` must run on
Houdini's main thread. The dispatcher hides the difference between an
interactive Houdini session (where ``hdefereval`` is available) and a
headless / CLI-driven invocation (where direct execution is fine).
"""

from __future__ import annotations

import io
import logging
import sys
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Callable, Dict, Optional, Tuple

LOGGER = logging.getLogger("houdini_bridge.dispatcher")

try:  # pragma: no cover - Houdini runtime only
    import hdefereval  # type: ignore
except Exception:  # pragma: no cover
    hdefereval = None  # type: ignore[assignment]


class MainThreadDispatcher:
    """Runs callables on Houdini's main thread and surfaces results to workers."""

    def __init__(self, *, allow_direct_when_no_ui: bool = True) -> None:
        self._allow_direct = allow_direct_when_no_ui
        self._lock = threading.Lock()

    def run(self, func: Callable[[], Any]) -> Any:
        """Synchronously run *func* on the main thread and return its result."""

        if hdefereval is None:
            if not self._allow_direct:
                raise RuntimeError("hdefereval unavailable; refusing direct execution")
            return func()

        return hdefereval.executeInMainThreadWithResult(func)

    def run_capturing(self, func: Callable[[], Any]) -> Tuple[Any, str, str]:
        """Run *func* on the main thread and capture stdout/stderr."""

        out = io.StringIO()
        err = io.StringIO()

        def _wrapped() -> Any:
            with redirect_stdout(out), redirect_stderr(err):
                return func()

        result = self.run(_wrapped)
        return result, out.getvalue(), err.getvalue()


def execute_script(script: str, dispatcher: MainThreadDispatcher) -> Dict[str, Any]:
    """Compile and exec *script* on the main thread.

    The script runs in a fresh module-level namespace seeded with ``hou_bridge``
    pointing at :mod:`houdini_bridge.libraries`. Stdout/stderr are captured.
    """

    compiled = compile(script, "<houdini_bridge.exec>", "exec")
    namespace = _build_exec_namespace()

    def _runner() -> Any:
        exec(compiled, namespace)  # noqa: S102 — agent-controlled, gated upstream
        return namespace.get("__result__")

    try:
        result, stdout, stderr = dispatcher.run_capturing(_runner)
        return {
            "success": True,
            "output": stdout,
            "stderr": stderr,
            "result": result,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — we serialise the trace
        return {
            "success": False,
            "output": "",
            "stderr": "",
            "result": None,
            "error": _format_exception(exc),
        }


def execute_call(
    library: str,
    function: str,
    kwargs: Optional[Dict[str, Any]],
    dispatcher: MainThreadDispatcher,
    *,
    allow_destructive: bool = False,
) -> Dict[str, Any]:
    """Look up ``library.function`` and invoke it on the main thread."""

    from . import undo
    from .registry import get_registry

    registry = get_registry()
    spec = registry.get(library, function)

    if spec.danger == "destructive" and not allow_destructive:
        return {
            "success": False,
            "result": None,
            "error": (
                f"refusing destructive call {library}.{function} without "
                "allow_destructive=true"
            ),
        }

    callable_ = spec.callable
    if callable_ is None:
        return {
            "success": False,
            "result": None,
            "error": f"function {library}.{function} has no callable bound",
        }

    payload = dict(kwargs or {})

    def _runner() -> Any:
        if spec.danger in ("write", "destructive"):
            with undo.group(f"houdini_bridge:{library}.{function}"):
                return callable_(**payload)
        return callable_(**payload)

    try:
        result = dispatcher.run(_runner)
        return {"success": True, "result": result, "error": None}
    except TypeError as exc:
        return {
            "success": False,
            "result": None,
            "error": f"argument mismatch in {library}.{function}: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "result": None,
            "error": _format_exception(exc),
        }


def _build_exec_namespace() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {"__name__": "houdini_bridge.exec"}
    try:  # pragma: no cover - inside Houdini
        import hou  # type: ignore

        namespace["hou"] = hou
    except Exception:
        pass
    try:
        from . import libraries as hou_bridge  # type: ignore

        namespace["hou_bridge"] = hou_bridge
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("hou_bridge namespace unavailable: %s", exc)
    return namespace


def _format_exception(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()


_LAST_TRACEBACK_PEEK = sys.exc_info  # keep linter happy
