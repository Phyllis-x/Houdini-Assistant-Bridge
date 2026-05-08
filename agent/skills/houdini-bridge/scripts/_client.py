"""Minimal TCP client matching the Houdini-side framing.

4-byte big-endian length prefix + UTF-8 JSON body, in both directions.
"""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict, Optional, Tuple

LENGTH_HEADER = struct.Struct(">I")
MAX_FRAME_BYTES = 64 * 1024 * 1024


class BridgeError(RuntimeError):
    """Any failure on the agent side: discovery, framing, transport, or RPC."""


class BridgeClient:
    """Single-shot TCP client. Each ``send`` opens a fresh connection."""

    def __init__(
        self,
        endpoint: Tuple[str, int],
        *,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.endpoint = endpoint
        self.token = token
        self.timeout = timeout

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.token and "token" not in payload:
            payload = {**payload, "token": self.token}

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > MAX_FRAME_BYTES:
            raise BridgeError(f"request frame too large: {len(body)} bytes")

        host, port = self.endpoint
        try:
            with socket.create_connection((host, int(port)), timeout=self.timeout) as sock:
                sock.sendall(LENGTH_HEADER.pack(len(body)) + body)
                return _read_frame(sock)
        except (OSError, socket.timeout) as exc:
            raise BridgeError(f"connect/send to {host}:{port} failed: {exc}") from exc


def _read_frame(sock: socket.socket) -> Dict[str, Any]:
    header = _recv_exact(sock, LENGTH_HEADER.size)
    (length,) = LENGTH_HEADER.unpack(header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise BridgeError(f"invalid response length: {length}")
    body = _recv_exact(sock, length)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BridgeError(f"malformed response frame: {exc}") from exc


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise BridgeError("connection closed mid-frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
