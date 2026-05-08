"""Agent demo - impact-triggered rock fracture with VDB dust.

Builds two cooperating networks via the bridge:

* ``/obj/rock_fracture``: an intact rock falls first. At ``IMPACT_FRAME`` the
  display switches to pre-fractured packed RBD pieces whose solver starts at
  the ground-contact frame.
* ``/obj/dust_smoke``: object_merge the live RBD pieces -> impact dust points
  -> rasterized density / velocity source -> Pyro Solver -> visualized volume -> OUT.

The fracture cooks instantly; the dust is a real Pyro solve driven by the
impact frame, so it advects, rolls, dissipates, and settles instead of staying
as a static density blob.

Run::

    py agent/skills/houdini-bridge/scripts/houdini_bridge.py exec-file examples/agent_demo_rock_destruction.py
"""

from __future__ import annotations

import hou
import hou_bridge

ROCK = "/obj/rock_fracture"
DUST = "/obj/dust_smoke"
IMPACT_FRAME = 38
FPS = 24.0
ROCK_SIZE = 3.0
START_HEIGHT = 10.0
GROUND_Y = 0.0
IMPACT_CENTER_Y = GROUND_Y + ROCK_SIZE * 0.5


def _set_parm(node_path: str, candidates):
    """Set the first parameter from *candidates* that exists on the node.

    Each candidate is a ``(parm_name, value)`` tuple. Returns the name that
    was set or ``None`` when nothing matched.
    """
    node = hou.node(node_path)
    if node is None:
        return None
    for name, value in candidates:
        parm = node.parm(name)
        if parm is None:
            continue
        try:
            parm.set(value)
            return name
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: failed to set {node_path}/{name}={value!r}: {exc}")
            continue
    return None


def _wipe(path: str) -> None:
    node = hou.node(path)
    if node is not None:
        print(f"removing prior {path}")
        node.destroy()


def _build_rock_fracture() -> str:
    """Build the multi-level rock fracture network. Returns the OUT path."""

    print("== /obj/rock_fracture ==")

    hou_bridge.node.create_node(parent_path="/obj", type_name="geo", name="rock_fracture")
    container = hou.node(ROCK)
    container.parm("ty").set(0)

    print("  falling_rock: intact 3m cube, free-fall until impact")
    hou_bridge.node.create_node(parent_path=ROCK, type_name="box", name="falling_rock")
    hou_bridge.parameter.set_parms(
        node_path=f"{ROCK}/falling_rock",
        values={"sizex": ROCK_SIZE, "sizey": ROCK_SIZE, "sizez": ROCK_SIZE},
    )
    fall = hou.node(f"{ROCK}/falling_rock")
    fall.parm("ty").setExpression(
        f"max({IMPACT_CENTER_Y}, {START_HEIGHT} - 0.5 * 9.8 * (max($F - 1, 0) / {FPS})^2)",
        hou.exprLanguage.Hscript,
    )

    print("  impact_rock: hidden source already placed on the ground")
    hou_bridge.node.create_node(parent_path=ROCK, type_name="box", name="impact_rock")
    hou_bridge.parameter.set_parms(
        node_path=f"{ROCK}/impact_rock",
        values={
            "sizex": ROCK_SIZE,
            "sizey": ROCK_SIZE,
            "sizez": ROCK_SIZE,
            "ty": IMPACT_CENTER_Y,
        },
    )

    print("  add normals (some downstream SOPs need them)")
    hou_bridge.node.create_node(parent_path=ROCK, type_name="normal", name="normals")
    hou_bridge.node.connect_inputs(target_path=f"{ROCK}/normals", source_path=f"{ROCK}/impact_rock")

    print("  rbdmaterialfracture::2.0 — concrete preset, fine detail")
    hou_bridge.node.create_node(
        parent_path=ROCK, type_name="rbdmaterialfracture::2.0", name="fracture"
    )
    hou_bridge.node.connect_inputs(target_path=f"{ROCK}/fracture", source_path=f"{ROCK}/normals")
    # Material type: try string then integer (concrete is index 0 in 20.5)
    if _set_parm(f"{ROCK}/fracture", [("materialtype", "concrete")]) is None:
        _set_parm(f"{ROCK}/fracture", [("materialtype", 0)])
    _set_parm(f"{ROCK}/fracture", [("fractureperpiece", 1)])
    # Detail size = piece size; smaller => more / finer pieces.
    _set_parm(f"{ROCK}/fracture", [("concrete_detailsize", 0.28)])
    _set_parm(f"{ROCK}/fracture", [("concrete_scatterpts1", 7)])
    _set_parm(f"{ROCK}/fracture", [("concrete_scatterpts2", 9)])
    _set_parm(f"{ROCK}/fracture", [("concrete_fractureseed1", 3)])
    _set_parm(f"{ROCK}/fracture", [("concrete_fractureseed2", 11)])
    _set_parm(f"{ROCK}/fracture", [("concrete_edgedetail", 1)])
    _set_parm(f"{ROCK}/fracture", [("concrete_interiordetail", 1)])
    _set_parm(f"{ROCK}/fracture", [("concrete_interiornoiseamp", 0.06)])
    _set_parm(f"{ROCK}/fracture", [("concrete_interiornoisefreq", 2.5)])

    print("  impact_constraints: glue constraints, weaker near the ground contact")
    hou_bridge.node.create_node(
        parent_path=ROCK, type_name="attribwrangle", name="impact_constraints"
    )
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/impact_constraints",
        source_path=f"{ROCK}/fracture",
        output_index=1,
    )
    constraints = hou.node(f"{ROCK}/impact_constraints")
    constraints.parm("class").set(1)  # Primitives
    constraints.parm("snippet").set(
        """// A falling block should fail from the contact face upward.
// Bottom constraints are weak and propagate damage quickly; upper constraints
// remain stronger so the top mass lags behind instead of exploding uniformly.
float y = 0.0;
foreach (int pt; primpoints(0, @primnum)) {
    vector pos = point(0, "P", pt);
    y += pos.y;
}
y /= max(1, len(primpoints(0, @primnum)));

float bottom = 1.0 - smooth(0.25, 2.55, y);
float mid = smooth(0.6, 1.7, y) * (1.0 - smooth(1.7, 3.05, y));

s@constraint_name = "Glue";
f@strength = fit(bottom, 0.0, 1.0, 7.5, 0.18);
f@strength *= fit01(rand(@primnum * 9.17), 0.65, 1.35);
f@propagate_rate = fit(bottom + mid * 0.4, 0.0, 1.0, 0.25, 2.8);
f@impulse_halflife = fit(bottom, 0.0, 1.0, 1.2, 0.18);
"""
    )

    print("  assemble: per-piece name attribute")
    hou_bridge.node.create_node(parent_path=ROCK, type_name="assemble", name="assemble")
    hou_bridge.node.connect_inputs(target_path=f"{ROCK}/assemble", source_path=f"{ROCK}/fracture")
    _set_parm(f"{ROCK}/assemble", [("createname", 1), ("doname", 1)])
    _set_parm(f"{ROCK}/assemble", [("pack_geo", 1)])

    print("  initial_motion: per-piece outward impulse + random angular velocity")
    hou_bridge.node.create_node(
        parent_path=ROCK, type_name="attribwrangle", name="initial_motion"
    )
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/initial_motion", source_path=f"{ROCK}/assemble"
    )
    wrangle = hou.node(f"{ROCK}/initial_motion")
    wrangle.parm("class").set(2)  # 2 = Points. Packed RBD pieces read point v/w.
    wrangle.parm("snippet").set(
        """// Bottom-driven impact motion. The RBD solver starts only at IMPACT_FRAME.
// Pieces near the ground contact receive the first impulse; higher pieces
// are mostly pulled apart by constraints and collisions.
vector impact = chv("impact_point");
vector radial = normalize(set(@P.x - impact.x, 0, @P.z - impact.z) + set(0.001, 0, 0.001));

float bottom = 1.0 - smooth(0.25, 2.35, @P.y);
float middle = smooth(0.55, 1.75, @P.y) * (1.0 - smooth(1.75, 3.1, @P.y));
float height_transfer = max(bottom, middle * 0.35);

// The contact face kicks sideways and slightly upward, while upper mass lags.
float impulse = chf("impact_strength") * height_transfer;
v@v = radial * impulse + set(0, fit(bottom, 0.0, 1.0, -0.35, 1.75), 0);

// A small downward velocity on top pieces keeps the block feeling heavy.
v@v += set(0, -0.55 * (1.0 - bottom), 0);

// Bottom pieces tumble first; upper pieces rotate after damage propagates.
int seed = random_shash(s@name);
vector wpiece = set(rand(seed * 3 + 0), rand(seed * 3 + 1), rand(seed * 3 + 2));
wpiece = wpiece - 0.5;
v@w = wpiece * chf("spin_strength") * fit(height_transfer, 0.0, 1.0, 0.15, 1.0);
"""
    )
    # Spare parms so values are visible in the UI and tweakable.
    template_group = wrangle.parmTemplateGroup()
    if wrangle.parm("impact_pointx") is None:
        template_group.append(
            hou.FloatParmTemplate(
                "impact_point",
                "Impact Point",
                3,
                default_value=(0.0, GROUND_Y, 0.0),
            )
        )
    if wrangle.parm("impact_strength") is None:
        template_group.append(
            hou.FloatParmTemplate("impact_strength", "Impact Strength", 1, default_value=(3.6,))
        )
    if wrangle.parm("spin_strength") is None:
        template_group.append(
            hou.FloatParmTemplate("spin_strength", "Spin Strength", 1, default_value=(12.0,))
        )
    wrangle.setParmTemplateGroup(template_group)

    print("  rbdbulletsolver: ground plane + 20 substeps + tuned friction/restitution")
    hou_bridge.node.create_node(
        parent_path=ROCK, type_name="rbdbulletsolver", name="solver"
    )
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/solver", source_path=f"{ROCK}/initial_motion"
    )
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/solver",
        source_path=f"{ROCK}/impact_constraints",
        input_index=1,
    )
    _set_parm(f"{ROCK}/solver", [("useground", 1)])
    _set_parm(f"{ROCK}/solver", [("startframe", IMPACT_FRAME)])
    _set_parm(f"{ROCK}/solver", [("substeps", 20)])
    _set_parm(f"{ROCK}/solver", [("ground_friction", 0.6)])
    _set_parm(f"{ROCK}/solver", [("ground_dynamicfriction", 0.4)])
    _set_parm(f"{ROCK}/solver", [("ground_bounce", 0.15)])
    _set_parm(f"{ROCK}/solver", [("enable_constraintbreaks", 1)])
    _set_parm(f"{ROCK}/solver", [("constraint_useimpact1", 1)])
    _set_parm(f"{ROCK}/solver", [("constraint_impactthreshold1", 1.4)])
    _set_parm(f"{ROCK}/solver", [("constraint_useforce1", 1)])
    _set_parm(f"{ROCK}/solver", [("constraint_forcethreshold1", 2.2)])

    print("  switch_on_impact: intact rock before impact, RBD pieces after impact")
    hou_bridge.node.create_node(parent_path=ROCK, type_name="switch", name="switch_on_impact")
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/switch_on_impact",
        source_path=f"{ROCK}/falling_rock",
        input_index=0,
    )
    hou_bridge.node.connect_inputs(
        target_path=f"{ROCK}/switch_on_impact",
        source_path=f"{ROCK}/solver",
        input_index=1,
    )
    switch = hou.node(f"{ROCK}/switch_on_impact")
    switch.parm("input").setExpression(f"if($F < {IMPACT_FRAME}, 0, 1)", hou.exprLanguage.Hscript)

    print("  OUT (null, display+render)")
    hou_bridge.node.create_node(
        parent_path=ROCK,
        type_name="null",
        name="OUT",
        set_display_flag=True,
        set_render_flag=True,
    )
    hou_bridge.node.connect_inputs(target_path=f"{ROCK}/OUT", source_path=f"{ROCK}/switch_on_impact")
    out = hou.node(f"{ROCK}/OUT")
    out.setDisplayFlag(True)
    out.setRenderFlag(True)

    hou_bridge.node.layout_children(parent_path=ROCK)
    return f"{ROCK}/OUT"


def _build_dust_smoke(rock_pieces_path: str) -> str:
    """Build the velocity-driven Pyro dust network. Returns the OUT path."""

    print("\n== /obj/dust_smoke ==")
    hou_bridge.node.create_node(parent_path="/obj", type_name="geo", name="dust_smoke")

    print("  object_merge live RBD pieces")
    hou_bridge.node.create_node(parent_path=DUST, type_name="object_merge", name="get_rocks")
    _set_parm(
        f"{DUST}/get_rocks",
        [("objpath1", rock_pieces_path)],
    )
    _set_parm(f"{DUST}/get_rocks", [("xformtype", 1)])

    print("  velocity_dust: density = clamp(|v| * 0.6, 0, 4) so fast pieces emit more dust")
    hou_bridge.node.create_node(parent_path=DUST, type_name="attribwrangle", name="velocity_dust")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/velocity_dust", source_path=f"{DUST}/get_rocks"
    )
    vdust = hou.node(f"{DUST}/velocity_dust")
    vdust.parm("class").set(2)  # 2 = Points
    vdust.parm("snippet").set(
        """// Treat per-point velocity magnitude as dust intensity.
// Pieces moving fast (just after fracture / impact) emit more dust.
float speed = length(v@v);
f@density = clamp(speed * 0.6, 0.0, 4.0);
// Inflate emission slightly along velocity so dust trails the motion.
v@v = v@v;
"""
    )

    print("  pyrosource: scatter dust points over the fractured rock surface")
    hou_bridge.node.create_node(parent_path=DUST, type_name="pyrosource", name="dust_source")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/dust_source", source_path=f"{DUST}/velocity_dust"
    )
    _set_parm(f"{DUST}/dust_source", [("mode", 0)])  # Surface Scatter
    _set_parm(f"{DUST}/dust_source", [("particlesep", 0.08)])

    print("  impact_dust: short-lived velocity-driven dust source at ground contact")
    hou_bridge.node.create_node(parent_path=DUST, type_name="attribwrangle", name="impact_dust")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/impact_dust", source_path=f"{DUST}/dust_source"
    )
    impact_dust = hou.node(f"{DUST}/impact_dust")
    impact_dust.parm("class").set(2)  # Points
    impact_dust.parm("snippet").set(
        f"""int impact = {IMPACT_FRAME};
if (@Frame < impact) {{
    f@density = 0.0;
    f@pscale = 0.0;
    v@v = 0;
}} else {{
    vector center = set(0, {IMPACT_CENTER_Y}, 0);
    vector radial = normalize(set(@P.x - center.x, 0, @P.z - center.z) + set(0.001, 0, 0.001));
    float age = clamp((@Frame - impact) / 26.0, 0.0, 1.0);
    float near_ground = smooth(2.6, 0.1, @P.y);
    float burst = pow(1.0 - age, 2.2) * near_ground;

    // Low per-point density: many surface samples accumulate into soft stone dust.
    f@density = burst * fit01(rand(@ptnum * 17.23 + @Frame), 0.08, 0.22);
    f@pscale = fit01(burst, 0.08, 0.28);

    // Dust is pushed sideways by the impact, lifts slightly, then settles.
    float turbulent = fit01(rand(@ptnum * 41.7), -1.0, 1.0);
    vector sideways = radial * fit01(1.0 - age, 5.0, 0.8);
    vector lift = set(0, fit01(1.0 - age, 1.4, 0.15), 0);
    vector curlish = set(-radial.z, 0, radial.x) * turbulent * 1.2;
    v@v = (sideways + lift + curlish) * burst;
}}
"""
    )

    print("  rasterize_pyro_source: convert impact points into density and velocity VDBs")
    hou_bridge.node.create_node(parent_path=DUST, type_name="volumerasterizeattributes", name="rasterize_pyro_source")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/rasterize_pyro_source", source_path=f"{DUST}/impact_dust"
    )
    _set_parm(f"{DUST}/rasterize_pyro_source", [("attributes", "density v")])
    _set_parm(f"{DUST}/rasterize_pyro_source", [("voxelsize", 0.14)])
    _set_parm(f"{DUST}/rasterize_pyro_source", [("particlescale", 1.3)])
    _set_parm(f"{DUST}/rasterize_pyro_source", [("densityattrib", "density")])
    _set_parm(f"{DUST}/rasterize_pyro_source", [("densityscale", 1.0)])

    print("  pyro_dust_sim: physically advect, disturb, dissipate, and settle the dust")
    hou_bridge.node.create_node(parent_path=DUST, type_name="pyrosolver", name="pyro_dust_sim")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/pyro_dust_sim", source_path=f"{DUST}/rasterize_pyro_source"
    )
    _set_parm(f"{DUST}/pyro_dust_sim", [("startframe", IMPACT_FRAME)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("divsize", 0.16)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("substep", 1), ("substeps", 2)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("enable_buoyancy", 0)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("enable_density_gravity", 1)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("density_gravity_scale", 0.18)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("enable_dissipation", 1)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("dissipation", 0.075)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("enable_disturbance", 1)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("disturbance", 0.75)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("disturbance_blocksize", 0.35)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("enable_turbulence", 1)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("turbulence", 0.35)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("turbulence_swirlsize", 1.4)])
    _set_parm(f"{DUST}/pyro_dust_sim", [("resize_padding", 1.2)])

    print("  visualize_dust: viewport-friendly grey density")
    hou_bridge.node.create_node(parent_path=DUST, type_name="volumevisualization", name="visualize_dust")
    hou_bridge.node.connect_inputs(
        target_path=f"{DUST}/visualize_dust", source_path=f"{DUST}/pyro_dust_sim"
    )
    _set_parm(f"{DUST}/visualize_dust", [("densityfield", "density")])
    _set_parm(f"{DUST}/visualize_dust", [("densityscale", 1.6)])

    print("  OUT (null, display+render)")
    hou_bridge.node.create_node(
        parent_path=DUST,
        type_name="null",
        name="OUT",
        set_display_flag=True,
        set_render_flag=True,
    )
    hou_bridge.node.connect_inputs(target_path=f"{DUST}/OUT", source_path=f"{DUST}/visualize_dust")
    out = hou.node(f"{DUST}/OUT")
    out.setDisplayFlag(True)
    out.setRenderFlag(True)

    hou_bridge.node.layout_children(parent_path=DUST)
    return f"{DUST}/OUT"


def main() -> None:
    print("== rock destruction + dust demo ==")

    _wipe(ROCK)
    _wipe(DUST)
    _wipe("/obj/cube_fracture")

    with hou.undos.group("agent: rock destruction demo"):
        rock_out = _build_rock_fracture()
        _build_dust_smoke(f"{ROCK}/solver")

    hou.setFrame(1)

    print("\n== fracture summary (frame 1) ==")
    asm_summary = hou_bridge.geometry.get_geometry_summary(node_path=f"{ROCK}/assemble")
    print(f"piece polys (primitive_count) = {asm_summary['primitive_count']}")
    print(f"piece points (point_count)   = {asm_summary['point_count']}")
    if asm_summary.get("bounds"):
        print(f"bounds.size                  = {asm_summary['bounds']['size']}")

    print("\nDONE")
    print("- /obj/rock_fracture/OUT  : RBD pieces (cooks instantly per frame)")
    print("- /obj/dust_smoke/OUT     : Pyro-simulated impact dust density")
    print("\nIn Houdini:")
    print("  1. Open Network View, drill into /obj/rock_fracture and /obj/dust_smoke.")
    print("  2. In viewport, frame the rock pieces (Space+H, then G to focus selection).")
    print("  3. Press Spacebar to play. The cube stays intact until frame 38, then fractures.")
    print("  4. Tweak: /obj/rock_fracture/initial_motion -> Impact Strength / Spin Strength")
    print("           /obj/rock_fracture/fracture → Concrete Detail Size (smaller = finer)")
    print("           /obj/dust_smoke/pyro_dust_sim -> Voxel Size / Turbulence / Dissipation")


main()
