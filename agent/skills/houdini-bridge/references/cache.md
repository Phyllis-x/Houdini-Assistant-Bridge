# `cache` — File caches and ROPs

## Functions

| Function           | Danger      | Description                                 |
| ------------------ | ----------- | ------------------------------------------- |
| `inspect_cache_node` | read      | Cache node + on-disk frame coverage.        |
| `render_rop`       | write       | Render a ROP synchronously.                 |
| `clear_cache`      | destructive | Delete the on-disk frames for a cache node. |

## Idioms

### Did the cache finish?

```bash
$CLI call cache inspect_cache_node --kwargs '{"node_path":"/obj/geo_cache/filecache1"}'
```

The result includes `disk_state.missing` (sample of the first 50 missing
frames) and `disk_state.missing_count`.

### Trigger a cache (use sparingly)

```bash
$CLI call cache render_rop --kwargs '{"node_path":"/obj/geo_cache/filecache1","frame_range":[1,48]}'
```

### Wipe the cache before re-rendering

```bash
$CLI --allow destructive call cache clear_cache --kwargs '{"node_path":"/obj/geo_cache/filecache1","dry_run":false}'
```

`dry_run` defaults to `true` so the first call only enumerates candidate
files. Always inspect the candidate list before opting in to deletion.
