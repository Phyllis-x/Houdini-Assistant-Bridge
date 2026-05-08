"""End-to-end smoke test that runs without Houdini.

Spins up a fake bridge server (using the real ``HoudiniBridgeServer`` with a
no-op dispatcher), writes a discovery descriptor, then invokes the agent CLI
across ``list-sessions``, ``ping``, ``call``, and ``exec`` to verify the wire
protocol, the discovery file, and the CLI preflight stay in lockstep.

Run::

    python tools/smoketest.py

Exit code 0 on success, non-zero on failure.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "plugin" / "python"
CLI = REPO_ROOT / "agent" / "skills" / "houdini-bridge" / "scripts" / "houdini_bridge.py"


def _import_package_modules():
    sys.path.insert(0, str(PACKAGE_ROOT))
    from houdini_bridge import bootstrap, server  # noqa: WPS433 — intentional late import

    return bootstrap, server


def _write_temp_manifest(tmp_root: Path) -> Path:
    manifest_dir = tmp_root / "manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = REPO_ROOT / "agent" / "skills" / "houdini-bridge" / "manifest" / "houdini_bridge_manifest.json"
    if not manifest_path.exists():
        subprocess.check_call([sys.executable, str(REPO_ROOT / "tools" / "gen_manifest.py")])
    return manifest_path


def _run_cli(argv: list[str], env: dict) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(CLI), *argv]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)


def main() -> int:
    import json

    tmp_root = Path(tempfile.mkdtemp(prefix="houdini_bridge_smoke_"))
    discovery_dir = tmp_root / "sessions"
    discovery_dir.mkdir()

    env = os.environ.copy()
    env["HOUDINI_BRIDGE_DISCOVERY_DIR"] = str(discovery_dir)
    env["HOUDINI_BRIDGE_ALLOW_EXEC"] = "1"
    env["PYTHONPATH"] = str(PACKAGE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    bootstrap, server_module = _import_package_modules()

    # Register a fake "scene" call so we can exercise the structured RPC path.
    from houdini_bridge.libraries import scene as scene_lib  # noqa: WPS433
    from houdini_bridge.registry import bridge_function, get_registry, reset_registry

    @bridge_function(danger="read", summary="smoketest only — return a constant payload")
    def smoketest_echo(message: str = "hello") -> dict:
        return {"echo": message}

    scene_lib.smoketest_echo = smoketest_echo  # type: ignore[attr-defined]
    reset_registry()
    registry = get_registry()  # rebuild with our injected function

    # Re-write the manifest so the CLI preflight can see the injected function.
    manifest_path = REPO_ROOT / "agent" / "skills" / "houdini-bridge" / "manifest" / "houdini_bridge_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_backup = None
    if manifest_path.exists():
        manifest_backup = manifest_path.with_suffix(".json.smokebak")
        shutil.copy2(manifest_path, manifest_backup)
    manifest_path.write_text(
        json.dumps(registry.to_manifest(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Force the server to use the temporary discovery directory.
    os.environ["HOUDINI_BRIDGE_DISCOVERY_DIR"] = str(discovery_dir)

    server = server_module.HoudiniBridgeServer(host="127.0.0.1", port=0)
    server.start()
    failures: list[str] = []

    try:
        time.sleep(0.1)

        # 1) list-sessions should see the descriptor we just wrote.
        r1 = _run_cli(["list-sessions", "--json"], env)
        if r1.returncode != 0 or "session_id" not in r1.stdout:
            failures.append(f"list-sessions failed: rc={r1.returncode} out={r1.stdout!r} err={r1.stderr!r}")

        # 2) ping should round-trip.
        r2 = _run_cli(["ping", "--json"], env)
        if r2.returncode != 0 or '"pong": true' not in r2.stdout:
            failures.append(f"ping failed: rc={r2.returncode} out={r2.stdout!r} err={r2.stderr!r}")

        # 3) structured call to our injected function.
        r3 = _run_cli(
            ["call", "scene", "smoketest_echo", "--kwargs", '{"message": "world"}', "--json"],
            env,
        )
        if r3.returncode != 0 or '"echo": "world"' not in r3.stdout:
            failures.append(f"call failed: rc={r3.returncode} out={r3.stdout!r} err={r3.stderr!r}")

        # 4) preflight should reject an unknown library locally.
        r4 = _run_cli(["call", "scenex", "smoketest_echo", "--kwargs", "{}"], env)
        if r4.returncode == 0 or "preflight" not in r4.stderr:
            failures.append(f"preflight should have rejected scenex: rc={r4.returncode} err={r4.stderr!r}")

        # 5) preflight should reject unknown kwargs.
        r5 = _run_cli(
            ["call", "scene", "smoketest_echo", "--kwargs", '{"message_typo": "x"}'],
            env,
        )
        if r5.returncode == 0 or "unknown kwargs" not in r5.stderr:
            failures.append(f"preflight should have caught unknown kwargs: rc={r5.returncode} err={r5.stderr!r}")

        # 6) exec round-trip.
        r6 = _run_cli(
            ["--no-preflight", "exec", "print('exec-ok')", "--json"],
            env,
        )
        if r6.returncode != 0 or "exec-ok" not in r6.stdout:
            failures.append(f"exec failed: rc={r6.returncode} out={r6.stdout!r} err={r6.stderr!r}")
    finally:
        server.stop()
        shutil.rmtree(tmp_root, ignore_errors=True)
        if manifest_backup is not None and manifest_backup.exists():
            shutil.move(str(manifest_backup), str(manifest_path))

    if failures:
        sys.stderr.write("SMOKETEST FAILED\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        return 1

    print("smoketest ok: list-sessions, ping, call, exec, preflight (unknown lib + unknown kwargs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
