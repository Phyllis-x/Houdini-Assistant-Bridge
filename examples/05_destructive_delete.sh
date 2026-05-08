#!/usr/bin/env sh
# Demonstrate that destructive ops require explicit allow.
set -eu

CLI="python agent/skills/houdini-bridge/scripts/houdini_bridge.py"

echo "== should fail (no --allow destructive) =="
if $CLI call node delete_node --kwargs '{"path":"/obj/geo_demo"}'; then
  echo "ERROR: delete should have been rejected by preflight" >&2
  exit 1
else
  echo "preflight rejected the call as expected"
fi

echo "== with explicit allow =="
$CLI --allow destructive call node delete_node --kwargs '{"path":"/obj/geo_demo"}'

echo "== confirm /obj/geo_demo no longer exists =="
$CLI call scene walk_network --kwargs '{"parent_path":"/obj","max_depth":1}'
