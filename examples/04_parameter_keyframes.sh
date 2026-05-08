#!/usr/bin/env sh
# Edit parms and add keyframes. Every change is undoable with Ctrl+Z.
set -eu

CLI="python agent/skills/houdini-bridge/scripts/houdini_bridge.py"

$CLI call parameter set_parms --kwargs '{
  "node_path": "/obj/geo_demo/grid1",
  "values": {"sizex": 12, "sizey": 12, "rows": 80, "cols": 80}
}'

$CLI call parameter set_parm --kwargs '{
  "node_path": "/obj/geo_demo/mountain1",
  "parm_name": "elementsize",
  "value": 1.5
}'

$CLI call parameter add_keyframe --kwargs '{
  "node_path": "/obj/geo_demo/mountain1",
  "parm_name": "height",
  "frame": 1,
  "value": 0.0
}'

$CLI call parameter add_keyframe --kwargs '{
  "node_path": "/obj/geo_demo/mountain1",
  "parm_name": "height",
  "frame": 48,
  "value": 2.5
}'

echo "== final parm state =="
$CLI call parameter get_parm --kwargs '{
  "node_path": "/obj/geo_demo/mountain1",
  "parm_name": "height",
  "include_keyframes": true
}'
