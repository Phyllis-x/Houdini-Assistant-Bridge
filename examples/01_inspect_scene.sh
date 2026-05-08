#!/usr/bin/env sh
# Discover sessions, ping the live one, and print a scene summary.
set -eu

CLI="python agent/skills/houdini-bridge/scripts/houdini_bridge.py"

echo "== sessions =="
$CLI list-sessions

echo "== ping =="
$CLI ping

echo "== scene summary =="
$CLI call scene get_scene_summary

echo "== /obj children =="
$CLI call scene list_children --kwargs '{"parent_path":"/obj","limit":20}'
