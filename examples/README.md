# Examples

These scripts are the canonical "happy path" the agent should follow during
development. They double as MVP acceptance tests: when each one completes
without errors against a freshly launched Houdini, the bridge is healthy.

| File                                                | What it shows                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------- |
| [01_inspect_scene.sh](01_inspect_scene.sh)         | Discover sessions, ping, summarise the hip file.                    |
| [02_build_sop_network.sh](02_build_sop_network.sh) | Build a `geo / grid / mountain / null` SOP chain with auto-layout.  |
| [03_geometry_summary.sh](03_geometry_summary.sh)   | Read the geometry summary and sample a few points.                  |
| [04_parameter_keyframes.sh](04_parameter_keyframes.sh) | Set parm values and add keyframes — Ctrl+Z reverts.            |
| [05_destructive_delete.sh](05_destructive_delete.sh) | Demonstrates the destructive-allow gate.                          |
| [10_acceptance.py](10_acceptance.py)               | Python script that runs all of the above as MVP acceptance.         |

## Prerequisites

1. The Houdini package is installed (see top-level [README](../README.md)).
2. Houdini is launched and the bridge log line "listening on 127.0.0.1:..."
   has appeared.
3. The agent CLI is on PATH or invoked from the repo root via
   `python agent/skills/houdini-bridge/scripts/houdini_bridge.py`.

The shell snippets are written in POSIX sh; on Windows PowerShell, replace
`\` line continuations with backticks or paste them as a single line.
