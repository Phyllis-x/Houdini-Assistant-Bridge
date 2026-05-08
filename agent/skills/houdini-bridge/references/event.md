# `event` — Reactive event subscriptions

## Functions

| Function              | Danger      | Description                                  |
| --------------------- | ----------- | -------------------------------------------- |
| `subscribe_node_event`| write       | Subscribe to a node lifecycle event.         |
| `unsubscribe`         | destructive | Cancel a previously created subscription.    |
| `list_subscriptions`  | read        | Show all active subscriptions.               |
| `drain_events`        | read        | Pop events from the buffer (FIFO).           |

## Supported `event_type` values

`removed`, `deleted`, `name_changed`, `input_rewired`, `parm_tuple_changed`,
`child_created`, `child_deleted`, `child_switched`.

## Idioms

### Watch a node for parm changes

```bash
$CLI call event subscribe_node_event --kwargs '{"node_path":"/obj/geo_demo/grid1","event_type":"parm_tuple_changed"}'
# (later) drain the buffer:
$CLI call event drain_events --kwargs '{"limit":100}'
```

## Notes

- The current implementation buffers events in-process and exposes them
  through `drain_events`. A streaming push channel will be added once the
  protocol layer supports long-poll or WebSocket transports.
