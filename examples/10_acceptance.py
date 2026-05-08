"""MVP acceptance test driver.

Runs the canonical "build a SOP demo, inspect it, edit parms, undo / delete"
flow against a live Houdini session. Skips automatically when no session is
discovered — useful as a CI smoke test that turns into a real integration
test as soon as Houdini is available on the host.

Usage::

    python examples/10_acceptance.py

Exit code 0 on success, 2 when no Houdini session was discovered, 1 on any
failed assertion.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = [sys.executable, str(REPO / "agent" / "skills" / "houdini-bridge" / "scripts" / "houdini_bridge.py")]


def call(*args: str, allow_fail: bool = False) -> dict:
    cmd = [*CLI, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode and not allow_fail:
        sys.stderr.write(f"FAIL: {' '.join(args)}\n{result.stderr}\n")
        sys.exit(1)
    if not result.stdout.strip():
        return {"_returncode": result.returncode, "_stderr": result.stderr}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_raw": result.stdout, "_returncode": result.returncode}


def main() -> int:
    sessions_raw = subprocess.run([*CLI, "list-sessions", "--json"], capture_output=True, text=True)
    if sessions_raw.returncode != 0 or not sessions_raw.stdout.strip():
        print("no Houdini session discovered — acceptance skipped")
        return 2
    sessions = json.loads(sessions_raw.stdout)
    if not sessions:
        print("no Houdini session discovered — acceptance skipped")
        return 2

    print(f"running against session {sessions[0]['session_id'][:8]} ({sessions[0]['hip'] or '<unsaved>'})")

    print("step 1: ping")
    pong = call("--json", "ping")
    assert pong.get("success") and pong["result"]["pong"] is True, pong

    print("step 2: scene summary")
    summary = call("--json", "call", "scene", "get_scene_summary")
    assert summary["success"], summary
    assert "/obj" in [n["path"] for n in summary["result"]["networks"]]

    print("step 3: build SOP chain")
    call("call", "node", "create_node",
         "--kwargs", json.dumps({"parent_path": "/obj", "type_name": "geo", "name": "geo_acceptance"}))
    call("call", "node", "create_node",
         "--kwargs", json.dumps({"parent_path": "/obj/geo_acceptance", "type_name": "grid", "name": "grid1"}))
    call("call", "node", "create_node",
         "--kwargs", json.dumps({"parent_path": "/obj/geo_acceptance", "type_name": "mountain", "name": "mountain1"}))
    call("call", "node", "connect_inputs",
         "--kwargs", json.dumps({"target_path": "/obj/geo_acceptance/mountain1",
                                 "source_path": "/obj/geo_acceptance/grid1"}))
    call("call", "node", "create_node",
         "--kwargs", json.dumps({"parent_path": "/obj/geo_acceptance", "type_name": "null",
                                 "name": "OUT", "set_display_flag": True, "set_render_flag": True}))
    call("call", "node", "connect_inputs",
         "--kwargs", json.dumps({"target_path": "/obj/geo_acceptance/OUT",
                                 "source_path": "/obj/geo_acceptance/mountain1"}))
    call("call", "node", "layout_children",
         "--kwargs", json.dumps({"parent_path": "/obj/geo_acceptance"}))

    print("step 4: parm + keyframe writes")
    call("call", "parameter", "set_parms",
         "--kwargs", json.dumps({"node_path": "/obj/geo_acceptance/grid1",
                                 "values": {"sizex": 12, "sizey": 12, "rows": 80, "cols": 80}}))
    call("call", "parameter", "add_keyframe",
         "--kwargs", json.dumps({"node_path": "/obj/geo_acceptance/mountain1",
                                 "parm_name": "height", "frame": 1, "value": 0.0}))
    call("call", "parameter", "add_keyframe",
         "--kwargs", json.dumps({"node_path": "/obj/geo_acceptance/mountain1",
                                 "parm_name": "height", "frame": 48, "value": 2.5}))

    print("step 5: cook + geometry summary")
    call("call", "node", "cook_node", "--kwargs", json.dumps({"path": "/obj/geo_acceptance/OUT"}))
    summary = call("--json", "call", "geometry", "get_geometry_summary",
                   "--kwargs", json.dumps({"node_path": "/obj/geo_acceptance/OUT"}))
    assert summary["success"] and summary["result"]["point_count"] > 0, summary

    print("step 6: preflight rejects destructive without allow")
    rejected = call("call", "node", "delete_node",
                    "--kwargs", json.dumps({"path": "/obj/geo_acceptance"}),
                    allow_fail=True)
    assert rejected.get("_returncode") != 0, rejected

    print("step 7: explicit destructive cleanup")
    call("--allow", "destructive", "call", "node", "delete_node",
         "--kwargs", json.dumps({"path": "/obj/geo_acceptance"}))

    print("\nACCEPTANCE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
