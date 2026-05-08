# Visual Validation

Use visual validation after non-trivial Houdini scene changes. The goal is to
confirm the final viewport result matches the user's requirement before the
agent reports completion.

## When to run

Run this after:

- Building procedural scenes, props, materials, cameras, or lighting.
- Creating effects such as RBD fracture, pyro smoke/fire, particles, fluids, or
  vellum.
- Modifying an existing visible scene.
- Producing anything the user will judge by appearance.

Skip only for read-only diagnostics, tiny parameter edits, or headless Houdini
sessions where no Scene Viewer exists. If skipped, explain why.

## Required sequence

1. Set the representative frame.
2. Ensure the target output node has correct display/render flags.
3. Frame the target or scene in the viewport.
4. Capture a screenshot with `viewport.screenshot`.
5. Read the screenshot image and compare it to the requirement brief.
6. Query node errors and relevant geometry summaries.
7. Fix visible issues before final response.

## CLI template

```bash
CLI=python agent/skills/houdini-bridge/scripts/houdini_bridge.py

$CLI call scene set_current_frame --kwargs '{"frame":48}'
$CLI call viewport frame_node --kwargs '{"node_path":"/obj/final_OUT"}'
$CLI call viewport screenshot --kwargs '{"output_path":"outputs/viewport_checks/final.png","width":1280,"height":720,"frame":48}'
$CLI call node get_node_errors --kwargs '{"path":"/obj/final_OUT"}'
$CLI call geometry get_geometry_summary --kwargs '{"node_path":"/obj/final_OUT"}'
```

Then read `outputs/viewport_checks/final.png` as an image and inspect it.

## Visual checklist

- The requested object/effect is visible and not clipped out of frame.
- The frame matches the requested timing or the most representative moment.
- Main shapes, hierarchy, scale, and composition match the brief.
- Materials/colors/readability match the requested style.
- Effects behave plausibly: fracture origin, smoke source, particle direction,
  fluid surface, cloth drape, etc.
- No obvious missing display flag, empty geometry, giant bounding box, black
  screen, error node, or uncooked sim placeholder.
- If the user requested realism, look for physically plausible cause/effect
  rather than just visual presence.

## Response shape

```text
视觉验证：
截图：outputs/viewport_checks/final.png
结论：通过 / 需要修正 / 无法截图
检查点：<1-3 条最重要观察>
修正：<如果发现问题，说明已修正什么或还剩什么>
```

## Failure handling

- If `viewport.screenshot` says `no Scene Viewer pane available`, report that
  visual validation requires interactive Houdini and fall back to node/geometry
  checks.
- If the screenshot is empty or black, verify display flags, current frame,
  camera/view framing, and whether the target node cooked successfully.
- If image inspection contradicts geometry summaries, trust the screenshot for
  user-facing appearance and use summaries to diagnose the cause.
