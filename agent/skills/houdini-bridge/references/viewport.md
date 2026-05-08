# `viewport` — Scene Viewer state and screenshots

## Functions

| Function       | Danger | Description                                       |
| -------------- | ------ | ------------------------------------------------- |
| `list_viewers` | read   | Enumerate Scene Viewer panes and viewports.       |
| `screenshot`   | write  | Capture a flipbook frame to disk.                 |
| `frame_node`   | write  | Frame the current viewport on a node.             |

## Idioms

### Validate visually after a build

```bash
$CLI call scene set_current_frame --kwargs '{"frame":48}'
$CLI call viewport frame_node --kwargs '{"node_path":"/obj/final_OUT"}'
$CLI call viewport screenshot --kwargs '{"output_path":"outputs/viewport_checks/final.png","width":1280,"height":720,"frame":48}'
```

After capture, read the returned image path and inspect it visually. The agent
must compare the screenshot against the requirement brief before saying the task
is complete. Pair the screenshot with `node.get_node_errors` and
`geometry.get_geometry_summary` when validating effects or procedural assets.

## Notes

- Viewport ops require an interactive Houdini session — they fail in
  headless `hython`.
- `frame_node` currently calls `frameAll()`; future versions will allow
  selecting just the requested node.
