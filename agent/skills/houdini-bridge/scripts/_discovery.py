"""Filesystem-based session discovery.

Mirrors the Houdini-side helper but reads-only. Lives next to the CLI so it
can ship as a single skill folder without depending on the Houdini package
being on ``sys.path``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


def discovery_root() -> Path:
    override = os.environ.get("HOUDINI_BRIDGE_DISCOVERY_DIR")
    if override:
        return Path(override)
    return Path.home() / ".houdini_bridge" / "sessions"


@dataclass
class SessionInfo:
    session_id: str
    pid: int
    host: str
    port: int
    hip: str
    hfs: str
    houdini_version: str
    hostname: str
    started_at: float

    def to_dict(self) -> dict:
        return self.__dict__


def list_sessions() -> List[SessionInfo]:
    root = discovery_root()
    if not root.exists():
        return []
    out: List[SessionInfo] = []
    for entry in sorted(root.glob("*.json")):
        try:
            blob = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        try:
            out.append(
                SessionInfo(
                    session_id=str(blob["session_id"]),
                    pid=int(blob.get("pid", 0)),
                    host=str(blob.get("host", "127.0.0.1")),
                    port=int(blob["port"]),
                    hip=str(blob.get("hip", "")),
                    hfs=str(blob.get("hfs", "")),
                    houdini_version=str(blob.get("houdini_version", "")),
                    hostname=str(blob.get("hostname", "")),
                    started_at=float(blob.get("started_at", 0.0)),
                )
            )
        except (KeyError, ValueError):
            continue
    return out


def pick_session(
    sessions: Iterable[SessionInfo],
    *,
    session_id: Optional[str] = None,
    hip_substring: Optional[str] = None,
    pid: Optional[int] = None,
) -> Optional[SessionInfo]:
    matches = []
    for sess in sessions:
        if session_id and not sess.session_id.startswith(session_id):
            continue
        if hip_substring and hip_substring.lower() not in sess.hip.lower():
            continue
        if pid is not None and sess.pid != pid:
            continue
        matches.append(sess)
    if not matches:
        return None
    matches.sort(key=lambda s: s.started_at, reverse=True)
    return matches[0]
