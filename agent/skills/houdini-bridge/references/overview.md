# Reference Overview

Each per-library reference describes:

- **Purpose** — when to reach for the library.
- **Functions** — the exhaustive function list with danger tag, argument
  shape, and a short JSON example call.
- **Idioms** — combinations the agent should reach for first.

The reference files are derived from the same manifest the CLI preflight
uses, so if the source library adds or renames a function, regenerate the
manifest first (`python tools/gen_manifest.py`) and update the relevant
reference file.

| Reference                              | Library    |
| -------------------------------------- | ---------- |
| [scene.md](scene.md)                   | `scene`    |
| [node.md](node.md)                     | `node`     |
| [parameter.md](parameter.md)           | `parameter`|
| [geometry.md](geometry.md)             | `geometry` |
| [asset.md](asset.md)                   | `asset`    |
| [cache.md](cache.md)                   | `cache`    |
| [viewport.md](viewport.md)             | `viewport` |
| [event.md](event.md)                   | `event`    |
| [requirement-intake.md](requirement-intake.md) | Pre-work requirement clarification |
