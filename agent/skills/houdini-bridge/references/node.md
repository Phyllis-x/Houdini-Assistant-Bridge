# `node` — create / delete / wire / lay out / cook

Use the node library for any structural changes to a network.

## Functions

| Function              | Danger      | Description                                   |
| --------------------- | ----------- | --------------------------------------------- |
| `get_node`            | read        | Inspect one node, optionally with parms.      |
| `create_node`         | write       | Create a typed node under a parent.           |
| `delete_node`         | destructive | Delete a node by absolute path.               |
| `rename_node`         | write       | Rename keeping uniqueness.                    |
| `move_node`           | write       | Set network coordinates.                      |
| `connect_inputs`      | write       | Wire `source -> target` at given indices.     |
| `disconnect_input`    | write       | Clear an input wire.                          |
| `layout_children`     | write       | Auto-layout a network's children.             |
| `set_display_flag`    | write       | Toggle display flag.                          |
| `set_render_flag`     | write       | Toggle render flag.                           |
| `set_bypass`          | write       | Bypass / unbypass.                            |
| `cook_node`           | write       | Cook a node and return its stats.             |
| `list_node_types`     | read        | Available node types in a category.           |
| `get_node_errors`     | read        | Errors / warnings / messages for a node.      |

## Idioms

### Build a small SOP chain

```bash
$CLI call node create_node --kwargs '{"parent_path":"/obj","type_name":"geo","name":"geo_demo"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"grid"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"mountain"}'
$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/mountain1","source_path":"/obj/geo_demo/grid1"}'
$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"null","name":"OUT","set_display_flag":true,"set_render_flag":true}'
$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/OUT","source_path":"/obj/geo_demo/mountain1"}'
$CLI call node layout_children --kwargs '{"parent_path":"/obj/geo_demo"}'
```

### Inspect a single node before editing

```bash
$CLI call node get_node --kwargs '{"path":"/obj/geo_demo/grid1","include_parms":true}'
```

### Discover what types are available

```bash
$CLI call node list_node_types --kwargs '{"category":"Sop","limit":50}'
```

## Notes

- `delete_node` is `destructive`; the preflight requires `--allow destructive`.
- Always call `layout_children` after creating multiple nodes so the
  network is readable in the network view.
- `cook_node` runs synchronously on the main thread; avoid using it for
  long-running cooks.
