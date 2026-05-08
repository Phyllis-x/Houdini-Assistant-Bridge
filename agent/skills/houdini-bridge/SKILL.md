---
name: houdini-bridge
description: Control a running SideFX Houdini session — introspect scenes, build SOP/LOP networks, edit parameters, read geometry summaries, and react to events. Use this skill whenever the user asks anything about the current Houdini scene, asks you to build or modify nodes/parameters/HDA assets, asks to run cooks or caches, or talks about a `.hip` file.
triggers:
  - "in Houdini"
  - "this hip"
  - "current scene"
  - "create a SOP"
  - "create a LOP"
  - "set parm"
  - "geometry summary"
  - "filecache"
  - "rop"
  - "hda"
allowed-tools: bash, read, write
---

# Houdini Bridge — Operating Manual

You can control a live Houdini session through the CLI at
`agent/skills/houdini-bridge/scripts/houdini_bridge.py`. The CLI talks to a
Python service running inside Houdini over loopback TCP. **Always prefer
`call <library> <function>` over `exec` when a typed library function exists.**

## Quick reference

```bash
# 0. Discover sessions (one-time, after Houdini launches)
python agent/skills/houdini-bridge/scripts/houdini_bridge.py list-sessions

# 1. Sanity check
python agent/skills/houdini-bridge/scripts/houdini_bridge.py ping

# 2. Look up the manifest before authoring any new call
python agent/skills/houdini-bridge/scripts/houdini_bridge.py libraries

# 3. Structured RPC into a typed function (preferred path)
python agent/skills/houdini-bridge/scripts/houdini_bridge.py call scene get_scene_summary

# 4. Inline Python escape hatch (use sparingly)
python agent/skills/houdini-bridge/scripts/houdini_bridge.py exec \
  "import hou_bridge; print(hou_bridge.scene.get_scene_summary())"
```

## Requirement intake gate

Before changing a Houdini scene for any non-trivial creative or technical
request, run a short requirement-intake step. This is mandatory for requests
such as building effects, changing simulations, creating assets, authoring
materials, caching, lighting, layout, or modifying an existing network.

1. **Extract the user's intent.** Restate what the user is asking for in clear
   production language, including the target result, scene object, timing,
   physical behavior, visual style, constraints, and expected deliverable.
2. **Complete missing detail conservatively.** Turn vague phrases into a
   concrete requirement draft, but mark assumptions explicitly. Do not treat
   assumptions as approved facts.
3. **Ask 3-5 preparation questions before work starts.** The questions should
   remove ambiguity that would change the node network, simulation setup, cache
   cost, or visual outcome. Prefer multiple-choice questions when it helps the
   user answer quickly.
4. **Wait for the user's answers before mutating the scene.** Read-only
   inspection is allowed if it helps ask better questions. Do not create,
   delete, rewire, cache, or cook heavy simulations until the intake is
   answered, unless the user explicitly says to proceed with defaults.
5. **After the answers, produce a compact final requirement brief and execution
   plan.** Then continue with the normal bridge workflow.

Use this response shape:

```text
需求描述草案：
<完整、细致地描述目标效果/资产/操作，列出关键假设。>

开始前需要确认：
1. <问题 1>
2. <问题 2>
3. <问题 3>
4. <可选问题 4>
5. <可选问题 5>
```

Good preparation questions usually cover:

- Target scene/object/network: which node, selection, or hip context should be
  modified?
- Visual reference: realism level, style, materials, lighting, camera, or
  reference clip/image.
- Physical behavior: forces, timing, scale, collision, constraints, smoke/fire,
  fluid, cloth, or destruction details.
- Performance budget: preview vs final quality, voxel size, particle count,
  frame range, cache/render expectations.
- Deliverable: viewport-only setup, reusable HDA, saved hip, cached sim, flipbook,
  or rendered frames.

## Mandatory rules

1. **Always run `libraries` first** in a new conversation to refresh the
   in-context manifest snapshot. Do not invent function names.
2. **Use `call`, not `exec`,** whenever the manifest has a function for the
   task. `exec` is the escape hatch for compositions the manifest does not
   cover yet.
3. **Pass `--allow destructive`** only when the user explicitly approves an
   irreversible op (delete node, clear cache, uninstall HDA, remove keyframes).
4. **Read before write.** Always summarise the relevant slice of the scene
   first (`scene.walk_network`, `node.get_node`, `parameter.list_parms`) and
   confirm the plan before mutating anything.
5. **One change at a time.** Prefer many small `call` requests over a single
   monolithic `exec` script — the agent should be able to abort cleanly.
6. **Trust the preflight.** If the CLI rejects a call locally, fix the call;
   do not pass `--no-preflight` unless the user asks for it explicitly.

## Library catalogue

| Library      | Use when…                                                                |
| ------------ | ------------------------------------------------------------------------ |
| `scene`      | Reading hip / network roots / takes / playbar; saving the file.          |
| `node`       | Creating, deleting, wiring, laying out, cooking nodes.                   |
| `parameter`  | Reading or writing parm values, expressions, keyframes, multiparms.      |
| `geometry`   | Inspecting cooked SOP geometry — bounds, attribs, samples.               |
| `asset`      | HDA library install / uninstall / introspection.                         |
| `cache`      | File cache + ROP inspection; gated cook + on-disk frame state.           |
| `viewport`   | Scene Viewer screenshots and basic state.                                |
| `event`      | Subscribe to node lifecycle / parm change events; drain the buffer.      |

Detailed per-library docs live in [references/](references/).

## Common tasks

### Create a SOP test network

```bash
CLI=python agent/skills/houdini-bridge/scripts/houdini_bridge.py

$CLI call node create_node --kwargs '{"parent_path":"/obj","type_name":"geo","name":"geo_demo"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"grid","name":"grid1"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"mountain","name":"mountain1"}'
$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/mountain1","source_path":"/obj/geo_demo/grid1"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"null","name":"OUT","set_display_flag":true,"set_render_flag":true}'
$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/OUT","source_path":"/obj/geo_demo/mountain1"}'
$CLI call node layout_children --kwargs '{"parent_path":"/obj/geo_demo"}'
```

### Inspect what you just made

```bash
$CLI call scene walk_network --kwargs '{"parent_path":"/obj/geo_demo","max_depth":1}'
$CLI call geometry get_geometry_summary --kwargs '{"node_path":"/obj/geo_demo/OUT"}'
```

### Edit parameters and add a keyframe

```bash
$CLI call parameter set_parm --kwargs '{"node_path":"/obj/geo_demo/grid1","parm_name":"sizex","value":12}'
$CLI call parameter add_keyframe --kwargs '{"node_path":"/obj/geo_demo/mountain1","parm_name":"height","frame":1,"value":0.0}'
$CLI call parameter add_keyframe --kwargs '{"node_path":"/obj/geo_demo/mountain1","parm_name":"height","frame":48,"value":2.0}'
```

### Destructive op (asks for confirmation)

```bash
# Will fail without --allow destructive
$CLI call node delete_node --kwargs '{"path":"/obj/geo_demo"}'
$CLI --allow destructive call node delete_node --kwargs '{"path":"/obj/geo_demo"}'
```

## Recovery patterns

- If you get `unknown function`, run `libraries` to refresh the manifest, then
  use the suggested name from the preflight error.
- If `ping` fails, re-run `list-sessions`. The descriptor may be stale because
  Houdini was closed unexpectedly.
- If the response says "no Scene Viewer pane available", remind the user that
  viewport ops require an interactive Houdini, not headless `hython`.

## Boundaries

- The bridge binds `127.0.0.1` only and never reaches off-host.
- All write ops are wrapped in `hou.undos.group(...)` — Ctrl+Z reverts.
- Geometry returns are size-capped (default 1000 points / primitives). Ask for
  paginated samples instead of dumping whole arrays.
