"""Local session discovery.

Each Houdini session writes a JSON descriptor to
``~/.houdini_bridge/sessions/<pid>.json`` so the CLI can enumerate all live
sessions without any multicast configuration. Stale descriptors (PID no longer
running) are filtered by the CLI when it pings each endpoint.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

SCHEMA_VERSION = 1


def discovery_root() -> Path:
    """Return the per-user discovery directory, creating it on demand."""

    override = os.environ.get("HOUDINI_BRIDGE_DISCOVERY_DIR")
    base = Path(override) if override else Path.home() / ".houdini_bridge" / "sessions"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class SessionDescriptor:
    """The on-disk JSON shape for a discovered Houdini bridge session."""

    schema: int
    session_id: str
    pid: int
    host: str
    port: int
    hip: str
    hfs: str
    houdini_version: str
    hostname: str
    started_at: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, blob: str) -> "SessionDescriptor":
        data = json.loads(blob)
        return cls(
            schema=int(data.get("schema", SCHEMA_VERSION)),
            session_id=str(data["session_id"]),
            pid=int(data["pid"]),
            host=str(data.get("host", "127.0.0.1")),
            port=int(data["port"]),
            hip=str(data.get("hip", "")),
            hfs=str(data.get("hfs", "")),
            houdini_version=str(data.get("houdini_version", "")),
            hostname=str(data.get("hostname", "")),
            started_at=float(data.get("started_at", 0.0)),
        )


def write_descriptor(descriptor: SessionDescriptor) -> Path:
    """Persist *descriptor* under the discovery root and return its path."""

    target = discovery_root() / f"{descriptor.pid}.json"
    target.write_text(descriptor.to_json(), encoding="utf-8")
    return target


def remove_descriptor(pid: int) -> None:
    """Delete the descriptor for *pid* if it exists."""

    target = discovery_root() / f"{pid}.json"
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass


def iter_descriptors() -> Iterable[SessionDescriptor]:
    """Yield every readable descriptor under the discovery root."""

    for entry in sorted(discovery_root().glob("*.json")):
        try:
            yield SessionDescriptor.from_json(entry.read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            continue


def list_descriptors() -> List[SessionDescriptor]:
    """Return all readable descriptors as a list."""

    return list(iter_descriptors())


def find_descriptor(
    *,
    session_id: Optional[str] = None,
    hip_contains: Optional[str] = None,
    pid: Optional[int] = None,
) -> Optional[SessionDescriptor]:
    """Return the first descriptor matching all provided filters."""

    for desc in iter_descriptors():
        if session_id and desc.session_id != session_id:
            continue
        if pid and desc.pid != pid:
            continue
        if hip_contains and hip_contains.lower() not in desc.hip.lower():
            continue
        return desc
    return None


def collect_session_metadata(host: str, port: int, session_id: str) -> SessionDescriptor:
    """Build a :class:`SessionDescriptor` for the current Houdini process."""

    try:
        import hou  # type: ignore

        hip = hou.hipFile.path()  # type: ignore[union-attr]
        version = ".".join(str(v) for v in hou.applicationVersion())  # type: ignore[union-attr]
    except Exception:
        hip = ""
        version = ""

    hfs = os.environ.get("HFS", "")

    return SessionDescriptor(
        schema=SCHEMA_VERSION,
        session_id=session_id,
        pid=os.getpid(),
        host=host,
        port=port,
        hip=hip,
        hfs=hfs,
        houdini_version=version,
        hostname=socket.gethostname(),
        started_at=time.time(),
    )


def python_version_tag() -> str:
    """Return a short string useful for diagnostic logs."""

    return f"{sys.version_info.major}.{sys.version_info.minor}"
