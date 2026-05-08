"""Agent-side CLI for Houdini Assistant Bridge.

Single-file entry point. Stdlib-only so it runs from any Python 3.9+ on PATH
without an install step. Subcommands:

    list-sessions               # show every Houdini session that wrote a descriptor
    ping [--session ID]          # send a ping
    exec   <code>                # AST-preflight, then send an exec request
    exec-file <path>             # ditto, from a file
    call   <library> <function>  # structured RPC into a typed bridge function
    libraries                    # print the on-disk manifest
    refresh-manifest             # ask the live server for the manifest snapshot

Common flags:
    --session <id>          target a specific Houdini session
    --hip <substr>          filter by hip path substring
    --pid <int>             filter by process id
    --endpoint host:port    skip discovery and connect directly
    --token <secret>        forward the shared-secret token
    --timeout <seconds>     RPC deadline (default 30)
    --json                  emit the raw JSON envelope
    --allow destructive     opt in to destructive ops
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
MANIFEST_PATH = SKILL_ROOT / "manifest" / "houdini_bridge_manifest.json"

# Make the in-tree helpers importable as ``_preflight``, ``_discovery`` etc.
sys.path.insert(0, str(HERE))

from _client import BridgeClient, BridgeError  # noqa: E402
from _discovery import (  # noqa: E402
    SessionInfo,
    list_sessions,
    pick_session,
)
from _manifest import Manifest, load_manifest  # noqa: E402
from _preflight import PreflightError, preflight_call, preflight_script  # noqa: E402


# ---------- argument parsing ----------------------------------------------------


def _add_common_flags(parser: argparse.ArgumentParser, *, on_subparser: bool = False) -> None:
    """Common flags accepted both before and after the subcommand.

    On subparsers we default to ``argparse.SUPPRESS`` so that omitting a flag at
    the subparser level does *not* clobber the value the user supplied at the
    top level.
    """

    suppress = argparse.SUPPRESS if on_subparser else None

    parser.add_argument("--session", default=suppress, help="Filter by session id")
    parser.add_argument("--hip", default=suppress, help="Filter by hip path substring")
    parser.add_argument("--pid", type=int, default=suppress, help="Filter by Houdini process id")
    parser.add_argument(
        "--endpoint",
        default=suppress,
        help="host:port — skip discovery and connect directly (env HOUDINI_BRIDGE_ENDPOINT)",
    )
    parser.add_argument("--token", default=suppress, help="Shared-secret token (env HOUDINI_BRIDGE_TOKEN)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=(30.0 if not on_subparser else argparse.SUPPRESS),
        help="RPC timeout in seconds",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=(False if not on_subparser else argparse.SUPPRESS),
        help="Emit raw JSON envelope",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=(None if not on_subparser else argparse.SUPPRESS),
        help="Opt in to a danger level — pass --allow destructive to enable destructive ops",
    )
    parser.add_argument(
        "--no-preflight",
        action="store_true",
        default=(False if not on_subparser else argparse.SUPPRESS),
        help="Disable AST + manifest preflight (not recommended)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="houdini_bridge", description=__doc__)
    _add_common_flags(parser)

    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("list-sessions", "List all Houdini sessions discovered locally"),
        ("ping", "Ping the targeted session"),
        ("libraries", "Print the on-disk manifest"),
    ):
        sp = sub.add_parser(name, help=help_text)
        _add_common_flags(sp, on_subparser=True)

    refresh = sub.add_parser("refresh-manifest", help="Pull the manifest from a live session")
    _add_common_flags(refresh, on_subparser=True)
    refresh.add_argument("--out", default=str(MANIFEST_PATH), help="Where to write the manifest JSON")

    p_exec = sub.add_parser("exec", help="Run a Python snippet inside Houdini")
    _add_common_flags(p_exec, on_subparser=True)
    p_exec.add_argument("code", help="Python source to run")

    p_exec_file = sub.add_parser("exec-file", help="Run a Python file inside Houdini")
    _add_common_flags(p_exec_file, on_subparser=True)
    p_exec_file.add_argument("path", help="Path to a .py file to send")

    p_call = sub.add_parser("call", help="Invoke a typed bridge function")
    _add_common_flags(p_call, on_subparser=True)
    p_call.add_argument("library", help="Library short name, e.g. node")
    p_call.add_argument("function", help="Function name, e.g. create_node")
    p_call.add_argument(
        "--kwargs",
        help='JSON object of keyword arguments, e.g. \'{"path":"/obj"}\'',
        default="{}",
    )

    return parser


# ---------- main entry point ----------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "allow", None) is None:
        args.allow = []

    try:
        if args.command == "list-sessions":
            return _cmd_list_sessions(args)
        if args.command == "libraries":
            return _cmd_libraries(args)

        endpoint = _resolve_endpoint(args)
        token = args.token or os.environ.get("HOUDINI_BRIDGE_TOKEN")
        client = BridgeClient(endpoint=endpoint, token=token, timeout=args.timeout)

        if args.command == "ping":
            return _cmd_ping(args, client)
        if args.command == "refresh-manifest":
            return _cmd_refresh_manifest(args, client)
        if args.command == "exec":
            return _cmd_exec(args, client, args.code)
        if args.command == "exec-file":
            return _cmd_exec(args, client, Path(args.path).read_text(encoding="utf-8"))
        if args.command == "call":
            return _cmd_call(args, client)
    except BridgeError as exc:
        _emit_error(args, str(exc))
        return 2
    except PreflightError as exc:
        _emit_error(args, f"preflight: {exc}")
        return 3
    except FileNotFoundError as exc:
        _emit_error(args, str(exc))
        return 4
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        return 130

    parser.error(f"unknown command: {args.command!r}")
    return 1


# ---------- subcommand implementations ------------------------------------------


def _cmd_list_sessions(args: argparse.Namespace) -> int:
    sessions = list_sessions()
    if args.json_output:
        print(json.dumps([s.to_dict() for s in sessions], ensure_ascii=False, indent=2))
        return 0
    if not sessions:
        print("no Houdini bridge sessions discovered")
        return 0
    print(f"{'PID':>7}  {'PORT':>5}  {'VERSION':<10}  SESSION                           HIP")
    for sess in sessions:
        print(
            f"{sess.pid:>7}  {sess.port:>5}  {sess.houdini_version:<10}  "
            f"{sess.session_id:<32}  {sess.hip or '<unsaved>'}"
        )
    return 0


def _cmd_libraries(args: argparse.Namespace) -> int:
    manifest = load_manifest(MANIFEST_PATH)
    if args.json_output:
        print(json.dumps(manifest.raw, ensure_ascii=False, indent=2))
        return 0
    for lib_name in sorted(manifest.libraries):
        functions = manifest.libraries[lib_name]
        print(f"\n[{lib_name}]  ({len(functions)} functions)")
        for fn_name in sorted(functions):
            spec = functions[fn_name]
            tag = spec.get("danger", "read")
            summary = spec.get("summary", "")
            print(f"  - {fn_name:<32} {tag:<11} {summary}")
    return 0


def _cmd_refresh_manifest(args: argparse.Namespace, client: BridgeClient) -> int:
    response = client.send({"id": _new_id(), "command": "list-libraries"})
    _ensure_success(response)
    payload = response.get("result")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest written to {out_path}")
    return 0


def _cmd_ping(args: argparse.Namespace, client: BridgeClient) -> int:
    response = client.send({"id": _new_id(), "command": "ping"})
    if args.json_output:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if response.get("success") else 1
    if not response.get("success"):
        _emit_error(args, response.get("error") or "ping failed")
        return 1
    payload = response.get("result", {})
    print(
        "pong "
        f"session={payload.get('session_id', '?')[:8]} "
        f"version={payload.get('houdini_version', '?')} "
        f"hip={payload.get('hip') or '<unsaved>'}"
    )
    return 0


def _cmd_exec(args: argparse.Namespace, client: BridgeClient, code: str) -> int:
    if not args.no_preflight:
        manifest = load_manifest(MANIFEST_PATH, optional=True)
        if manifest is not None:
            preflight_script(code, manifest, allow=set(args.allow))
    response = client.send(
        {
            "id": _new_id(),
            "command": "exec",
            "script": code,
            "allow_destructive": "destructive" in args.allow,
        }
    )
    _ensure_success(response)
    if args.json_output:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    if response.get("output"):
        sys.stdout.write(response["output"])
        if not response["output"].endswith("\n"):
            sys.stdout.write("\n")
    if response.get("stderr"):
        sys.stderr.write(response["stderr"])
        if not response["stderr"].endswith("\n"):
            sys.stderr.write("\n")
    return 0


def _cmd_call(args: argparse.Namespace, client: BridgeClient) -> int:
    try:
        kwargs = json.loads(args.kwargs)
    except json.JSONDecodeError as exc:
        raise BridgeError(f"--kwargs is not valid JSON: {exc}") from exc
    if not isinstance(kwargs, dict):
        raise BridgeError("--kwargs must decode to a JSON object")

    if not args.no_preflight:
        manifest = load_manifest(MANIFEST_PATH, optional=True)
        if manifest is not None:
            preflight_call(args.library, args.function, kwargs, manifest, allow=set(args.allow))

    response = client.send(
        {
            "id": _new_id(),
            "command": "call",
            "library": args.library,
            "function": args.function,
            "kwargs": kwargs,
            "allow_destructive": "destructive" in args.allow,
        }
    )
    _ensure_success(response)
    if args.json_output:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(response.get("result"), ensure_ascii=False, indent=2))
    return 0


# ---------- helpers -------------------------------------------------------------


def _resolve_endpoint(args: argparse.Namespace) -> Tuple[str, int]:
    explicit = args.endpoint or os.environ.get("HOUDINI_BRIDGE_ENDPOINT")
    if explicit:
        host, _, port_str = explicit.rpartition(":")
        if not host:
            raise BridgeError(f"--endpoint must be host:port, got {explicit!r}")
        return host, int(port_str)

    sessions = list_sessions()
    sess = pick_session(
        sessions,
        session_id=args.session,
        hip_substring=args.hip,
        pid=args.pid,
    )
    if sess is None:
        if not sessions:
            raise BridgeError(
                "no Houdini sessions discovered — make sure a session is running and the "
                "package descriptor is installed"
            )
        raise BridgeError(
            f"no session matched filters (session={args.session}, hip={args.hip}, pid={args.pid}); "
            f"{len(sessions)} candidates available"
        )
    return sess.host, sess.port


def _ensure_success(response: Dict[str, Any]) -> None:
    if not response.get("success"):
        raise BridgeError(response.get("error") or "request failed")


def _emit_error(args: argparse.Namespace, message: str) -> None:
    if getattr(args, "json_output", False):
        sys.stderr.write(json.dumps({"success": False, "error": message}) + "\n")
    else:
        sys.stderr.write(f"error: {message}\n")


def _new_id() -> str:
    return uuid.uuid4().hex


if __name__ == "__main__":
    sys.exit(main())
