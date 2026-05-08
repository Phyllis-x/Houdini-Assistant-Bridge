# Safety

## Threat model

Houdini Assistant Bridge assumes a single-user developer workstation. The only
intended caller is a local AI agent running on the same machine. The threat
model focuses on:

1. Preventing remote code execution from off-host.
2. Bounding accidental destructive edits by the agent.
3. Surfacing every change to the human operator through Houdini's undo stack.

## Network

- The TCP server binds `127.0.0.1` and refuses to bind any other interface.
- Discovery writes session descriptors under the user's home directory only.
- An optional shared-secret token (`HOUDINI_BRIDGE_TOKEN`) gates every request
  when set; mismatched tokens fail closed before reaching the dispatcher.

## Process

- HOM access is funnelled through the dispatcher and runs on Houdini's main
  thread.
- The server does not import additional third-party packages at runtime — the
  bridge stays inside Houdini's existing Python environment.
- `shutdown` is refused unless `HOUDINI_BRIDGE_ALLOW_SHUTDOWN=1`.

## Edits

- Every write op runs inside `hou.undos.group(label)`. Ctrl+Z reverts.
- Library functions are tagged with one of three danger levels and the
  manifest carries the tag:

  | Tag           | Examples                                                    |
  | ------------- | ----------------------------------------------------------- |
  | `read`        | `scene.get_scene_summary`, `node.list_children`             |
  | `write`       | `node.set_parm`, `node.create_node`, `node.connect_inputs`  |
  | `destructive` | `node.delete_node`, `cache.clear_cache`, `asset.uninstall`  |

- The CLI preflight rejects any `destructive` call unless the user passes
  `--allow destructive` (or `allow_destructive=true` over the wire).

## Data limits

- Geometry summaries are paginated and capped at conservative defaults
  (`MAX_POINTS_INLINE = 1000`, `MAX_PRIMS_INLINE = 1000`). Callers ask for
  larger samples explicitly.
- Node tree dumps default to depth-1 with summary counts per child container;
  agents must request deeper traversal explicitly.

## Operator visibility

- Every successful write op is also logged to Houdini's status bar via
  `hou.ui.setStatusMessage` so the human operator sees what changed.
- The bridge writes a rolling JSON log at
  `~/.houdini_bridge/logs/<session_id>.log` (capped at 5 MB) listing
  `request_id`, `command`, `library.function`, latency, and result size.
