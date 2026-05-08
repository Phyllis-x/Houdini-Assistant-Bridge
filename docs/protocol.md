# Protocol

The wire protocol uses a 4-byte big-endian unsigned length prefix followed by a
UTF-8 JSON body. The same framing is used in both directions on the same TCP
connection.

```text
[4-byte BE length][JSON body ...]
```

A connection is single-shot per request: client opens, sends one framed
request, reads one framed response, then closes. Reusing a connection is
allowed but not required and not assumed by the CLI.

## Requests

```jsonc
{
  "id":      "uuid-string",         // required, echoed back
  "command": "ping" | "exec" | "call" | "list-libraries" | "shutdown",
  "script":  "...python source...", // exec only
  "library": "scene",                // call only
  "function": "get_scene_summary",   // call only
  "kwargs":  { ... },                // call only, JSON-friendly map
  "args":    [ ... ],                // call only, optional positional
  "timeout": 30,                     // optional seconds, default 30
  "allow_destructive": false         // optional, defaults false
}
```

### Commands

| Command           | Behaviour                                                              |
| ----------------- | ---------------------------------------------------------------------- |
| `ping`            | Returns `pong` plus session metadata.                                  |
| `list-libraries`  | Returns the in-memory manifest snapshot for the running server.        |
| `exec`            | Runs `script` in a fresh module, captures stdout/stderr, returns both. |
| `call`            | Looks up `library.function` in the registry, invokes with `kwargs`.    |
| `shutdown`        | Stops the server cleanly; refused unless `HOUDINI_BRIDGE_ALLOW_SHUTDOWN=1`. |

## Responses

```jsonc
{
  "id":      "uuid-string",
  "success": true,
  "output":  "captured stdout",   // exec only
  "stderr":  "captured stderr",   // exec only
  "result":  <json value>,        // call only
  "error":   null                  // string when success=false
}
```

Errors carry an `error` string and `success: false`; for failures during
`call`, `error` is the formatted exception with its repr line and the
relevant Houdini node path when known.

## Examples

### Ping

```jsonc
// request
{"id": "1", "command": "ping"}

// response
{"id": "1", "success": true, "result": {
  "pong": true,
  "session_id": "...",
  "hip": "C:/work/test.hip",
  "houdini_version": "20.5.123"
}}
```

### Structured call

```jsonc
// request
{"id": "2", "command": "call",
 "library": "node", "function": "create_node",
 "kwargs": {"parent_path": "/obj", "type_name": "geo", "name": "geo_demo"},
 "allow_destructive": false}

// response
{"id": "2", "success": true,
 "result": {"path": "/obj/geo_demo", "type": "geo", "session_id": "..."}}
```

### Inline exec

```jsonc
// request
{"id": "3", "command": "exec",
 "script": "import hou_bridge\nprint(hou_bridge.scene.get_scene_summary())\n"}

// response
{"id": "3", "success": true,
 "output": "{...}", "stderr": ""}
```

## Discovery

Discovery is filesystem-based. Every Houdini session writes a JSON descriptor
to `~/.houdini_bridge/sessions/<pid>.json`. The CLI lists files, opens each
descriptor, and pings the corresponding endpoint to confirm liveness.

## Security

- The TCP listener binds `127.0.0.1` only.
- Optional shared-secret tokens can be enabled via `HOUDINI_BRIDGE_TOKEN`; when
  set, the client must include the same value in the `token` field of every
  request.
- `exec` is rate-limited and gated by `HOUDINI_BRIDGE_ALLOW_EXEC=1` if you
  want to fully disable arbitrary code while keeping `call` available.
