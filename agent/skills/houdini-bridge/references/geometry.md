# `geometry` — SOP geometry summaries and lightweight samples

The geometry library is read-only. Its job is to surface enough information
about cooked SOP geometry to reason about it without dumping whole point
arrays back to the agent.

## Functions

| Function                | Danger | Description                                    |
| ----------------------- | ------ | ---------------------------------------------- |
| `get_geometry_summary`  | read   | Counts, bounds, attributes, groups.            |
| `sample_points`         | read   | N points + their value of one attribute.       |
| `sample_primitives`     | read   | N prims + centroid + vertex count.             |
| `list_attributes`       | read   | Point / primitive / vertex / detail attributes.|
| `get_detail_attribute`  | read   | Read a detail attribute value.                 |

## Idioms

### Always start with the summary

```bash
$CLI call geometry get_geometry_summary --kwargs '{"node_path":"/obj/geo_demo/OUT"}'
```

The response contains point count, primitive count, bounding box, attribute
list, and group list — usually all you need to plan the next step.

### Sample points / prims when you need real values

```bash
$CLI call geometry sample_points --kwargs '{"node_path":"/obj/geo_demo/OUT","count":20,"attribute":"P"}'
$CLI call geometry sample_primitives --kwargs '{"node_path":"/obj/geo_demo/OUT","count":10}'
```

The `count` is capped at 1000 to keep responses small. Use `offset` to page.

## Notes

- The node must have produced cooked geometry. If not, call
  `node.cook_node` first.
- `sample_points` returns one attribute at a time. Call it again per
  attribute or use `list_attributes` first to plan which to fetch.
