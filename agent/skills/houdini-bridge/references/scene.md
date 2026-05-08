# `scene` — hip file, networks, takes, playbar

Use the scene library to orient yourself: figure out the hip file, the
top-level networks, the current selection, the frame range, and the takes.

## Functions

| Function              | Danger | Description                              |
| --------------------- | ------ | ---------------------------------------- |
| `get_scene_summary`   | read   | One-shot summary of the hip file.        |
| `list_children`       | read   | Paginated children of any network.       |
| `walk_network`        | read   | Depth-bounded recursive node tree.       |
| `get_selected_nodes`  | read   | Current selection across all editors.    |
| `list_takes`          | read   | All takes plus the current one.          |
| `get_current_frame`   | read   | Current playbar frame.                   |
| `set_current_frame`   | write  | Move the playbar.                        |
| `set_frame_range`     | write  | Set frame and playback ranges.           |
| `save_hip`            | write  | Save the hip (optional alternative path).|

## Idioms

### Orient before doing anything else

```bash
houdini_bridge.py call scene get_scene_summary
```

The response tells you the hip path, the version, the active take, the frame
range, and the names of the top-level networks with child counts.

### Drill into a network

```bash
houdini_bridge.py call scene walk_network --kwargs '{"parent_path":"/obj","max_depth":2}'
```

Walk depth is capped at 4 to keep responses bounded.

### Confirm what the user has selected

```bash
houdini_bridge.py call scene get_selected_nodes
```
