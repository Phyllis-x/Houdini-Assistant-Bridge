# `parameter` — read / write parms, expressions, keyframes

## Functions

| Function                    | Danger      | Description                                   |
| --------------------------- | ----------- | --------------------------------------------- |
| `get_parm`                  | read        | Inspect a parm with optional keyframe info.   |
| `list_parms`                | read        | Paginated parm list.                          |
| `set_parm`                  | write       | Write a single value.                         |
| `set_parms`                 | write       | Write a batch (`{name: value, ...}`).         |
| `set_expression`            | write       | Set an HScript / Python expression.           |
| `revert_to_default`         | write       | Drop expressions / keyframes.                 |
| `add_keyframe`              | write       | Append a constant keyframe.                   |
| `clear_keyframes`           | destructive | Delete every keyframe on the parm.            |
| `append_multiparm_instance` | write       | Add a row to a multiparm.                     |
| `remove_multiparm_instance` | destructive | Remove a multiparm row by index.              |
| `add_spare_parameter`       | write       | Add a spare parm with type / range.           |

## Idioms

### Read before write

```bash
$CLI call parameter get_parm --kwargs '{"node_path":"/obj/geo_demo/grid1","parm_name":"sizex"}'
```

### Batch write

```bash
$CLI call parameter set_parms --kwargs '{"node_path":"/obj/geo_demo/grid1","values":{"sizex":10,"sizey":10,"rows":50,"cols":50}}'
```

### Animate over a frame range

```bash
$CLI call parameter add_keyframe --kwargs '{"node_path":"/obj/geo_demo/mountain1","parm_name":"height","frame":1,"value":0}'
$CLI call parameter add_keyframe --kwargs '{"node_path":"/obj/geo_demo/mountain1","parm_name":"height","frame":48,"value":2}'
```

### Driven by an expression

```bash
$CLI call parameter set_expression --kwargs '{"node_path":"/obj/geo_demo/grid1","parm_name":"sizex","expression":"sin($F * 0.1) * 5 + 10","language":"hscript"}'
```

## Notes

- `value` accepts arrays for tuple parms, e.g. `[1, 2, 3]` for a `vec3`.
- `clear_keyframes` and `remove_multiparm_instance` are `destructive`.
- The preflight catches typos in `parm_name` only at runtime; the manifest
  cannot validate parameter names because they vary per node type. Always
  read the parm first if you are unsure of the spelling.
