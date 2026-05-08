"""Wire protocol: 4-byte big-endian length prefix + UTF-8 JSON body.

Used by both the Houdini-side server and the agent-side CLI client.
"""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict

LENGTH_HEADER = struct.Struct(">I")
MAX_FRAME_BYTES = 64 * 1024 * 1024


class ProtocolError(RuntimeError):
    """Raised when framing is malformed or oversized."""


def encode_frame(payload: Dict[str, Any]) -> bytes:
    """Serialize *payload* to a length-prefixed UTF-8 JSON frame."""

    body = json.dumps(payload, ensure_ascii=False, default=_default).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise ProtocolError(f"frame too large: {len(body)} bytes")
    return LENGTH_HEADER.pack(len(body)) + body


def decode_frame(body: bytes) -> Dict[str, Any]:
    """Parse a UTF-8 JSON frame body into a dict."""

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"malformed frame: {exc}") from exc


def read_frame(sock: socket.socket) -> Dict[str, Any]:
    """Read exactly one framed message from *sock* and return the decoded dict."""

    header = _recv_exact(sock, LENGTH_HEADER.size)
    (length,) = LENGTH_HEADER.unpack(header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ProtocolError(f"invalid frame length: {length}")
    body = _recv_exact(sock, length)
    return decode_frame(body)


def write_frame(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Send *payload* as a single framed message on *sock*."""

    sock.sendall(encode_frame(payload))


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ProtocolError("connection closed mid-frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _default(value: Any) -> Any:
    """JSON fallback for Houdini types we cannot serialize directly."""

    repr_value = repr(value)
    return {"__repr__": repr_value, "__type__": type(value).__name__}
