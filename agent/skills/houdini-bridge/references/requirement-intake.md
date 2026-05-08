# Requirement Intake

Use this workflow before starting non-trivial Houdini work. The goal is to turn
a short user request into a clear production brief, then ask a small number of
high-value questions before touching the scene.

## When to use

Use requirement intake for:

- Creating or changing effects: RBD, pyro, fluid, vellum, particles, crowds.
- Building or modifying SOP/LOP/material/camera/light networks.
- Editing an existing `.hip` scene where the target node or desired outcome is
  ambiguous.
- Running expensive cooks, caches, flipbooks, or renders.
- Turning a creative description into concrete Houdini nodes.

Skip the intake only for simple read-only requests, direct diagnostics, or tiny
explicit edits where the user already supplied all relevant details.

## Output shape

```text
需求描述草案：
<把用户意图补充为完整、细致、可执行的需求描述。说明目标对象、视觉效果、
物理行为、时间范围、质量要求、输出物，以及当前假设。>

开始前需要确认：
1. <会影响实现方式的问题>
2. <会影响视觉/物理结果的问题>
3. <会影响性能/缓存/输出的问题>
4. <可选问题>
5. <可选问题>
```

Ask 3-5 questions. Keep them specific. Avoid asking questions whose answers do
not change the implementation.

## Question checklist

- **Scene target**: Which node, object, selection, or network should be changed?
- **Scale and timing**: Unit scale, frame range, impact frame, speed, duration.
- **Physical driver**: Gravity, collision object, force direction, constraints,
  fracture origin, emission source, wind, turbulence.
- **Look development**: material, color, density, realism level, reference style,
  camera/viewing angle.
- **Quality budget**: viewport preview vs final sim, voxel size, particle count,
  substeps, cache/render expectations.
- **Deliverable**: only build nodes, save hip, create reusable HDA, cache sim,
  produce flipbook, or render frames.

## Example

User: "做一个方块落地破碎带烟雾。"

```text
需求描述草案：
我会创建一个完整方块从高处自由落体，在接触地面后由底部冲击触发破碎。
破碎应从接触面向上传播，碎块有大/中/小层次，并由碎块速度驱动 Pyro
石粉尘。默认做视口可播放预览，先不写磁盘缓存。

开始前需要确认：
1. 方块尺寸和下落高度按默认 3m / 10m 可以吗？
2. 破碎风格更偏混凝土、石头、玻璃，还是低多边形演示？
3. 烟尘要轻薄石粉、浓厚爆尘，还是介于两者之间？
4. 需要实时预览优先，还是可以接受较慢但更真实的 Pyro？
5. 结果只需要当前 Houdini 场景，还是要保存 hip/cache/flipbook？
```
