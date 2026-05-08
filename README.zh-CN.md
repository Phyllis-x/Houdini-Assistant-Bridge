# Houdini Assistant Bridge

为 SideFX Houdini 提供一个类型化的控制面板，让本地 AI agent 可以审视场景、
搭建节点网络、编辑参数、读取几何摘要并订阅编辑器事件，所有写操作可被
Houdini 撤销，发现与连接全部走本机回环。

Houdini 进程内运行 Python 服务，Agent 侧 CLI 通过本机回环发现运行中的会话，
并发出类型化 RPC。

## 亮点

- **进程内 Python 服务。** 直接拿到 `hou` HOM API，所有操作通过 dispatcher
  调度回 Houdini 主线程。
- **类型化库表面。** 八个 `HoudiniBridge*Library`，覆盖 scene / node /
  parameter / geometry / asset / cache / viewport / reactive event，函数返回
  JSON-friendly 数据。
- **本地发现。** 每个 Houdini 会话在用户目录下写入小 JSON 描述符，CLI 列出、
  过滤并连接，无需任何多播配置。
- **长度前缀 JSON 协议。** 4 字节大端长度 + UTF-8 JSON，双向同款。
- **AST + manifest 预检。** CLI 在发送脚本前解析 Python AST，把
  `hou_bridge.<library>.<fn>` 调用对照自动生成的 manifest，提供拼写建议，本地
  拒绝未知 kwargs。
- **可撤销写入。** 所有写操作包在 `hou.undos.group(...)` 中，Houdini Ctrl+Z
  可回滚 bridge 的任意改动。
- **仅回环监听。** TCP 服务只绑 `127.0.0.1`，默认不可被网络访问。

## 快速开始

### 1. 安装 Houdini package

把 [plugin/packages/houdini_bridge.json](plugin/packages/houdini_bridge.json)
复制或链接到 Houdini packages 目录，例如：

```text
%USERPROFILE%\Documents\houdini20.5\packages\houdini_bridge.json
```

编辑 JSON 里的 `HOUDINI_BRIDGE_ROOT`，让它指向当前仓库的 `plugin/` 绝对路径。
启动 Houdini，桥接在 `pythonrc` 阶段启动并打印：

```json
{
  "HOUDINI_BRIDGE_ROOT": "/absolute/path/to/houdini-assistant-bridge/plugin"
}
```

```text
[houdini_bridge] listening on 127.0.0.1:<port>, session id=<uuid>
```

### 2. 运行 CLI

```bash
python agent/skills/houdini-bridge/scripts/houdini_bridge.py ping
python agent/skills/houdini-bridge/scripts/houdini_bridge.py call scene get_scene_summary
```

### 3. 在 Agent 里使用

把 [agent/skills/houdini-bridge/SKILL.md](agent/skills/houdini-bridge/SKILL.md)
喂给 Cursor / Claude Code / Codex，里面教 Agent 怎么查 manifest、怎么通过
`houdini_bridge.py` 调用桥接能力。

## 仓库结构

```text
houdini-assistant-bridge/
├── plugin/
│   ├── packages/houdini_bridge.json
│   ├── scripts/
│   │   ├── 123.py    # Houdini 启动钩子（无 hip）
│   │   └── 456.py    # Houdini 启动钩子（载入 hip）
│   └── python/houdini_bridge/
│       ├── server.py · dispatcher.py · discovery.py
│       ├── protocol.py · registry.py · undo.py
│       └── libraries/
├── agent/skills/houdini-bridge/
│   ├── SKILL.md
│   ├── scripts/houdini_bridge.py
│   └── references/
├── tools/gen_manifest.py
├── docs/
├── examples/
└── README.md
```

## 环境要求

- **Houdini 19.5 / 20.0 / 20.5 / 21.0**，自带 Python 3.9+。
- **Python 3.9+** 在 PATH 上，给 Agent CLI 使用，仅依赖标准库。
- **Windows 10/11、macOS 或 Linux** 均可，发现目录路径跨平台。

## 安全

- 所有写操作在 `hou.undos.group(...)` 中执行。
- TCP 服务只绑 `127.0.0.1`。
- Agent 调用 `destructive` 标记的函数必须显式 `--allow destructive`，否则
  preflight 直接拒绝。

## 发布说明

仓库不会跟踪本地 Houdini 缓存、hip autosave、flipbook、渲染输出、日志或编辑器
配置。提交的 package 描述符是模板，克隆后请把
`<ABSOLUTE_PATH_TO_REPO_PLUGIN>` 替换成你本机的 `plugin/` 绝对路径。

## License

MIT.
