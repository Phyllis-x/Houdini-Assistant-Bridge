#!/usr/bin/env sh
# Inspect the geometry produced by the SOP chain in 02.
set -eu

CLI="python agent/skills/houdini-bridge/scripts/houdini_bridge.py"
NODE="/obj/geo_demo/OUT"

$CLI call node cook_node --kwargs "{\"path\":\"${NODE}\"}"

$CLI call geometry get_geometry_summary --kwargs "{\"node_path\":\"${NODE}\"}"

$CLI call geometry sample_points --kwargs "{\"node_path\":\"${NODE}\",\"count\":10,\"attribute\":\"P\"}"

$CLI call geometry list_attributes --kwargs "{\"node_path\":\"${NODE}\"}"
