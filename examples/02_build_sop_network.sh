#!/usr/bin/env sh
# Build a basic SOP chain: geo / grid / mountain / null(OUT).
set -eu

CLI="python agent/skills/houdini-bridge/scripts/houdini_bridge.py"

$CLI call node create_node --kwargs '{"parent_path":"/obj","type_name":"geo","name":"geo_demo"}'

$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"grid","name":"grid1"}'

$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"mountain","name":"mountain1"}'

$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/mountain1","source_path":"/obj/geo_demo/grid1"}'

$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"normal","name":"normal1"}'

$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/normal1","source_path":"/obj/geo_demo/mountain1"}'

$CLI call node create_node --kwargs '{"parent_path":"/obj/geo_demo","type_name":"null","name":"OUT","set_display_flag":true,"set_render_flag":true}'

$CLI call node connect_inputs --kwargs '{"target_path":"/obj/geo_demo/OUT","source_path":"/obj/geo_demo/normal1"}'

$CLI call node layout_children --kwargs '{"parent_path":"/obj/geo_demo"}'

echo "== resulting network =="
$CLI call scene walk_network --kwargs '{"parent_path":"/obj/geo_demo","max_depth":1}'
