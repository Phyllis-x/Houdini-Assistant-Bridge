# Houdini Assistant Bridge

> 中文版本见 [README.zh-CN.md](README.zh-CN.md)

A typed control surface for SideFX Houdini that lets local AI agents introspect
scenes, build node networks, edit parameters, inspect geometry, and react to
editor events — with undoable writes and local-only discovery.

The bridge runs a Python service **inside** the Houdini process, while an
agent-side CLI discovers running sessions over the loopback interface and sends
typed RPCs.

## Highlights

- **In-process Python service.** Runs inside Houdini, so every operation has
  full access to the `hou` HOM API and runs on Houdini's main thread through a
  dispatcher.
- **Typed library surface.** Eight `HoudiniBridge*Library` modules cover scene,
  node, parameter, geometry, asset, cache, viewport, and reactive events. Each
  function returns JSON-friendly data.
- **Local discovery.** Each Houdini session writes a small JSON descriptor to a
  per-user directory; the CLI lists, filters, and connects without any
  multicast configuration.
- **Length-prefixed JSON protocol.** 4-byte big-endian length + UTF-8 JSON
  payload, identical framing for both directions.
- **AST + manifest preflight.** The CLI parses agent-generated scripts before
  sending them, validates every `hou_bridge.<library>.<fn>` call against an
  auto-generated manifest, suggests corrections for typos, and rejects unknown
  kwargs locally.
- **Undoable writes.** Every write op is wrapped in `hou.undos.group(...)` —
  Ctrl+Z in Houdini reverts anything the bridge did.
- **Loopback only.** TCP server binds `127.0.0.1` exclusively; no remote access
  by default.

## Quick Start

### 1. Install the Houdini package

Copy or symlink [plugin/packages/houdini_bridge.json](plugin/packages/houdini_bridge.json)
into your Houdini packages folder, e.g.:

```text
%USERPROFILE%\Documents\houdini20.5\packages\houdini_bridge.json
```

Edit the `HOUDINI_BRIDGE_ROOT` entry inside the JSON so it points at the
absolute path of this repository's `plugin/` directory. Launch Houdini —
the bridge starts at `pythonrc` time and prints:

```json
{
  "HOUDINI_BRIDGE_ROOT": "/absolute/path/to/houdini-assistant-bridge/plugin"
}
```

```text
[houdini_bridge] listening on 127.0.0.1:<port>, session id=<uuid>
```

### 2. Run the CLI

```bash
python agent/skills/houdini-bridge/scripts/houdini_bridge.py ping
# -> pong (session=..., hip=...)

python agent/skills/houdini-bridge/scripts/houdini_bridge.py call \
    scene get_scene_summary
```

### 3. Use it from an Agent

Point Cursor / Claude Code / Codex at
[agent/skills/houdini-bridge/SKILL.md](agent/skills/houdini-bridge/SKILL.md).
The skill teaches the agent how to query the manifest and call the bridge
through `houdini_bridge.py`.

## Repository Layout

```text
houdini-assistant-bridge/
├── plugin/
│   ├── packages/houdini_bridge.json         # Houdini package descriptor
│   ├── scripts/                              # Houdini lifecycle hooks
│   │   ├── 123.py                            #   no-hip startup
│   │   └── 456.py                            #   hip-loaded startup
│   └── python/houdini_bridge/                # service + libraries
│       ├── server.py · dispatcher.py · discovery.py
│       ├── protocol.py · registry.py · undo.py
│       └── libraries/                        # typed API surface
├── agent/skills/houdini-bridge/
│   ├── SKILL.md
│   ├── scripts/houdini_bridge.py             # CLI
│   └── references/                           # per-library docs
├── tools/gen_manifest.py                     # manifest + wrapper generator
├── docs/                                     # architecture, protocol, safety
├── examples/                                 # ready-to-send agent scripts
└── README.md
```

## Requirements

- **Houdini 19.5 / 20.0 / 20.5 / 21.0** with Python 3.9+ (Houdini ships its own
  interpreter).
- **Python 3.9+** on PATH for the agent-side CLI (only the standard library is
  used).
- **Windows 10/11**, macOS, or Linux. Discovery directory paths are
  cross-platform.

## Safety

- Every write op runs inside `hou.undos.group(...)`.
- The TCP server binds `127.0.0.1` only.
- Agents must opt in to destructive ops with `--allow destructive`; without it,
  the preflight rejects calls flagged `destructive` in the manifest.

## Publishing Notes

This repository intentionally does not track local Houdini cache files, hip
autosaves, flipbooks, renders, logs, or editor settings. The checked-in package
descriptor is a template: replace `<ABSOLUTE_PATH_TO_REPO_PLUGIN>` with your own
absolute plugin path after cloning.

## License

MIT.
