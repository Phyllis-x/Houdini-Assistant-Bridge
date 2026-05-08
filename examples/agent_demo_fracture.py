"""Agent demo — Voronoi-fractured cube with RBD bullet simulation.

Run this against a live Houdini 20.5+ session via::

    py agent/skills/houdini-bridge/scripts/houdini_bridge.py exec-file examples/agent_demo_fracture.py

The script:

1. Wipes any prior ``/obj/cube_fracture`` so it is safe to re-run.
2. Builds the SOP chain ``box -> scatter -> voronoifracture -> assemble ->
   rbdbulletsolver -> OUT(null)`` using the typed ``hou_bridge.*`` functions
   from the bridge libraries.
3. Lays out the network and prints a summary of the static fracture (piece
   count, bounds) so the agent can confirm it built correctly.

Scrub the timeline (1 -> 240) inside Houdini to watch the cube fall, hit the
ground plane, and break apart.
"""

from __future__ import annotations

import hou
import hou_bridge

ROOT = "/obj/cube_fracture"


def _set_first_existing_parm(node_path: str, candidates):
    """Set the first parameter from *candidates* that exists. Returns the name."""
    node = hou.node(node_path)
    if node is None:
        return None
    for name, value in candidates:
        parm = node.parm(name)
        if parm is not None:
            parm.set(value)
            return name
    return None


def main() -> None:
    print("== building cube fracture demo ==")

    existing = hou.node(ROOT)
    if existing is not None:
        print(f"removing prior {ROOT}")
        existing.destroy()

    with hou.undos.group("agent: cube fracture demo"):
        print("step 1/8: geo container")
        hou_bridge.node.create_node(parent_path="/obj", type_name="geo", name="cube_fracture")

        print("step 2/8: box (size 2, ty=5)")
        hou_bridge.node.create_node(parent_path=ROOT, type_name="box", name="box")
        hou_bridge.parameter.set_parms(
            node_path=f"{ROOT}/box",
            values={"sizex": 2, "sizey": 2, "sizez": 2, "ty": 5},
        )

        print("step 3/8: scatter 30 fracture seeds")
        hou_bridge.node.create_node(parent_path=ROOT, type_name="scatter", name="scatter")
        hou_bridge.node.connect_inputs(
            target_path=f"{ROOT}/scatter", source_path=f"{ROOT}/box"
        )
        _set_first_existing_parm(
            f"{ROOT}/scatter",
            [("npts", 30), ("force_total_count", 30), ("ptcount", 30)],
        )
        _set_first_existing_parm(f"{ROOT}/scatter", [("seed", 1)])
        _set_first_existing_parm(f"{ROOT}/scatter", [("relaxiterations", 0)])

        print("step 4/8: voronoifracture")
        hou_bridge.node.create_node(
            parent_path=ROOT, type_name="voronoifracture", name="voronoifracture"
        )
        hou_bridge.node.connect_inputs(
            target_path=f"{ROOT}/voronoifracture",
            source_path=f"{ROOT}/box",
            input_index=0,
        )
        hou_bridge.node.connect_inputs(
            target_path=f"{ROOT}/voronoifracture",
            source_path=f"{ROOT}/scatter",
            input_index=1,
        )

        print("step 5/8: assemble (create name attribute)")
        hou_bridge.node.create_node(parent_path=ROOT, type_name="assemble", name="assemble")
        hou_bridge.node.connect_inputs(
            target_path=f"{ROOT}/assemble", source_path=f"{ROOT}/voronoifracture"
        )
        _set_first_existing_parm(
            f"{ROOT}/assemble",
            [("createname", 1), ("doname", 1), ("name1", 1)],
        )

        last = "assemble"
        print("step 6/8: rbdbulletsolver (SOP-level RBD sim)")
        try:
            hou_bridge.node.create_node(
                parent_path=ROOT, type_name="rbdbulletsolver", name="solver"
            )
            hou_bridge.node.connect_inputs(
                target_path=f"{ROOT}/solver", source_path=f"{ROOT}/assemble"
            )
            _set_first_existing_parm(
                f"{ROOT}/solver",
                [("useground", 1), ("groundtype", 1), ("ground_plane", 1)],
            )
            last = "solver"
        except Exception as exc:
            print(f"  rbdbulletsolver unavailable ({exc}); leaving static fracture")

        print(f"step 7/8: OUT (null) wired from {last}")
        hou_bridge.node.create_node(
            parent_path=ROOT,
            type_name="null",
            name="OUT",
            set_display_flag=True,
            set_render_flag=True,
        )
        hou_bridge.node.connect_inputs(
            target_path=f"{ROOT}/OUT", source_path=f"{ROOT}/{last}"
        )

        print("step 8/8: layout")
        hou_bridge.node.layout_children(parent_path=ROOT)

    print("\n== static fracture summary ==")
    asm_summary = hou_bridge.geometry.get_geometry_summary(node_path=f"{ROOT}/assemble")
    print(f"point_count     = {asm_summary['point_count']}")
    print(f"primitive_count = {asm_summary['primitive_count']}")
    print(f"primitive_types = {asm_summary['primitive_types']}")
    bounds = asm_summary.get("bounds")
    if bounds:
        print(f"bounds.size     = {bounds['size']}")
        print(f"bounds.min      = {bounds['min']}")

    print("\nDONE — scrub the timeline in Houdini to watch the cube fall and shatter.")
    print(f"Network at {ROOT}; OUT is /obj/cube_fracture/OUT.")


main()
