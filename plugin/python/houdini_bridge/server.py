"""TCP JSON server.

Runs in a dedicated worker thread inside Houdini. Each accepted connection
reads exactly one framed request, dispatches it to the main thread via
:class:`MainThreadDispatcher`, and writes a single framed response.
"""

from __future__ import annotations

import logging
import os
import socket
import socketserver
import threading
import time
from typing import Any, Callable, Dict, Optional

from . import discovery, protocol
from .dispatcher import MainThreadDispatcher, execute_call, execute_script
from .registry import get_registry

LOGGER = logging.getLogger("houdini_bridge.server")

SUPPORTED_COMMANDS = {"ping", "exec", "call", "list-libraries", "shutdown"}


class _RequestHandler(socketserver.BaseRequestHandler):
    server: "HoudiniBridgeServer"  # type: ignore[assignment]

    def handle(self) -> None:  # noqa: D401 — socketserver hook
        sock: socket.socket = self.request
        sock.settimeout(self.server.read_timeout_seconds)
        try:
            request = protocol.read_frame(sock)
        except protocol.ProtocolError as exc:
            LOGGER.warning("malformed request: %s", exc)
            return

        response = self.server.handle_request_payload(request)

        try:
            protocol.write_frame(sock, response)
        except OSError as exc:
            LOGGER.warning("failed to write response: %s", exc)


class _ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class HoudiniBridgeServer:
    """Loopback TCP server bridging an Agent CLI to Houdini's main thread."""

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        token: Optional[str] = None,
        read_timeout_seconds: float = 60.0,
        dispatcher: Optional[MainThreadDispatcher] = None,
        on_session_metadata: Optional[Callable[[discovery.SessionDescriptor], None]] = None,
    ) -> None:
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(f"refusing non-loopback bind: {host!r}")

        self._host = host
        self._requested_port = port
        self._token = token or os.environ.get("HOUDINI_BRIDGE_TOKEN") or None
        self.read_timeout_seconds = read_timeout_seconds
        self._dispatcher = dispatcher or MainThreadDispatcher()
        self._on_session_metadata = on_session_metadata

        self._tcp: Optional[_ThreadedTCPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._descriptor: Optional[discovery.SessionDescriptor] = None

        self._session_id = _new_session_id()

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def address(self) -> tuple:
        if self._tcp is None:
            return (self._host, self._requested_port)
        return self._tcp.server_address

    @property
    def port(self) -> int:
        return int(self.address[1])

    def start(self) -> None:
        if self._tcp is not None:
            return

        self._tcp = _ThreadedTCPServer((self._host, self._requested_port), _RequestHandler)
        self._tcp.handle_request_payload = self.handle_request_payload  # type: ignore[attr-defined]
        self._tcp.read_timeout_seconds = self.read_timeout_seconds  # type: ignore[attr-defined]

        self._thread = threading.Thread(
            target=self._tcp.serve_forever,
            name="houdini-bridge-server",
            daemon=True,
        )
        self._thread.start()

        self._descriptor = discovery.collect_session_metadata(
            host=self._host, port=self.port, session_id=self._session_id
        )
        discovery.write_descriptor(self._descriptor)
        if self._on_session_metadata is not None:
            try:
                self._on_session_metadata(self._descriptor)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("session metadata hook failed: %s", exc)

        LOGGER.info(
            "[houdini_bridge] listening on %s:%d, session=%s",
            self._host,
            self.port,
            self._session_id,
        )

    def stop(self) -> None:
        if self._tcp is None:
            return
        try:
            self._tcp.shutdown()
            self._tcp.server_close()
        finally:
            self._tcp = None
            self._thread = None
            if self._descriptor is not None:
                discovery.remove_descriptor(self._descriptor.pid)
                self._descriptor = None
            LOGGER.info("[houdini_bridge] stopped")

    def handle_request_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a single decoded request and return a response payload."""

        request_id = payload.get("id", "")
        command = payload.get("command")
        if command not in SUPPORTED_COMMANDS:
            return _error(request_id, f"unsupported command: {command!r}")

        if self._token is not None and payload.get("token") != self._token:
            return _error(request_id, "invalid or missing token")

        started = time.perf_counter()

        if command == "ping":
            response = self._handle_ping(request_id)
        elif command == "list-libraries":
            response = self._handle_list_libraries(request_id)
        elif command == "exec":
            response = self._handle_exec(request_id, payload)
        elif command == "call":
            response = self._handle_call(request_id, payload)
        elif command == "shutdown":
            response = self._handle_shutdown(request_id)
        else:  # pragma: no cover — covered by SUPPORTED_COMMANDS guard
            response = _error(request_id, f"unhandled command: {command!r}")

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.setdefault("metrics", {})["elapsed_ms"] = round(elapsed_ms, 3)
        return response

    def _handle_ping(self, request_id: str) -> Dict[str, Any]:
        descriptor = self._descriptor
        return _ok(
            request_id,
            {
                "pong": True,
                "session_id": self._session_id,
                "hip": descriptor.hip if descriptor else "",
                "houdini_version": descriptor.houdini_version if descriptor else "",
                "hostname": descriptor.hostname if descriptor else "",
                "pid": os.getpid(),
            },
        )

    def _handle_list_libraries(self, request_id: str) -> Dict[str, Any]:
        return _ok(request_id, get_registry().to_manifest())

    def _handle_exec(self, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if os.environ.get("HOUDINI_BRIDGE_ALLOW_EXEC", "1") not in {"1", "true", "TRUE"}:
            return _error(request_id, "exec is disabled by HOUDINI_BRIDGE_ALLOW_EXEC")
        script = payload.get("script", "")
        if not isinstance(script, str) or not script.strip():
            return _error(request_id, "exec requires non-empty 'script' field")
        result = execute_script(script, self._dispatcher)
        return {"id": request_id, **result}

    def _handle_call(self, request_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        library = payload.get("library")
        function = payload.get("function")
        if not library or not function:
            return _error(request_id, "call requires 'library' and 'function' fields")
        kwargs = payload.get("kwargs") or {}
        if not isinstance(kwargs, dict):
            return _error(request_id, "kwargs must be a JSON object")
        try:
            result = execute_call(
                library=library,
                function=function,
                kwargs=kwargs,
                dispatcher=self._dispatcher,
                allow_destructive=bool(payload.get("allow_destructive")),
            )
        except LookupError as exc:
            return _error(request_id, str(exc))
        return {"id": request_id, **result}

    def _handle_shutdown(self, request_id: str) -> Dict[str, Any]:
        if os.environ.get("HOUDINI_BRIDGE_ALLOW_SHUTDOWN", "0") not in {"1", "true", "TRUE"}:
            return _error(request_id, "shutdown disabled (set HOUDINI_BRIDGE_ALLOW_SHUTDOWN=1)")
        threading.Thread(target=self.stop, name="houdini-bridge-shutdown", daemon=True).start()
        return _ok(request_id, {"shutting_down": True})


def _ok(request_id: str, result: Any) -> Dict[str, Any]:
    return {"id": request_id, "success": True, "result": result, "error": None}


def _error(request_id: str, message: str) -> Dict[str, Any]:
    return {"id": request_id, "success": False, "result": None, "error": message}


def _new_session_id() -> str:
    import uuid

    return uuid.uuid4().hex
