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
$CLI call viewport screenshot --kwargs '{"output_path":"D:/tmp/check.png","width":1280,"height":720}'
```

## Notes

- Viewport ops require an interactive Houdini session — they fail in
  headless `hython`.
- `frame_node` currently calls `frameAll()`; future versions will allow
  selecting just the requested node.
