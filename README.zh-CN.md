# 米家控制 Skill

简体中文 | [English](README.md)

面向 Agent 的小米米家智能家居控制方案，底层通过安全的本地 CLI runtime 执行。

这个仓库包含两个相互独立的部分：

- `skills/controlling-mijia-smart-home`：通过 `npx skills add` 安装给 Agent 使用的 Skill。
- `mijiactl`：提供 `mijiactl` 命令的 Python 包。

这个拆分是刻意设计的：Skill 负责告诉 Agent 什么时候、按什么规则行动；`mijiactl` 负责本地执行、策略检查和稳定 JSON 输出。

## 快速开始

安装 Agent Skill：

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

从 GitHub Releases 安装最新 `mijiactl.exe`，然后初始化：

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression; mijiactl setup; mijiactl login; mijiactl config init
```

`mijiactl login` 会在终端显示二维码。请使用米家 App 扫码。授权文件保存到 `~/.config/mijiactl/auth.json`；命令输出不会打印 token 值。

检查当前安装的 runtime 版本：

```powershell
mijiactl version
```

上面的命令就是全局安装。它显式指定支持全局安装的目标：

`Claude Code`、`OpenClaw`、`Cline`、`Codex`、`Cursor`、`GitHub Copilot`、`Kiro CLI`、`Lingma`、`OpenCode`、`Qwen Code`、`Trae CN` 和 `Windsurf`。

PromptScript 不在默认目标列表里，因为当前 `skills` CLI 会返回 `PromptScript does not support global skill installation`。

## 使用案例

列出设备，给 Agent 或脚本消费：

```powershell
mijiactl devices --json
```

设备、家庭和场景列表默认缓存 3 天。如果改名、新增、删除设备或调整房间后需要重新发现，可以强制刷新：

```powershell
mijiactl devices --refresh --json
```

查看型号能力后打开灯：

```powershell
mijiactl info --model wlg.light.wy0a05 --json
mijiactl set --did <did> --prop switch-status --value true
```

读取某个属性的当前值：

```powershell
mijiactl get --did <did> --prop switch-status
```

启动洗衣机这类 MIoT action。注意这不是 `set on=true`：

```powershell
mijiactl info --model <washer_model> --json
mijiactl action --did <did> --action start-wash --confirm start-wash
```

执行带输入参数的 MIoT action，例如让小爱音箱朗读文本：

```powershell
mijiactl info --model xiaomi.wifispeaker.lx06 --json
mijiactl action --did <did> --action play-text --arg "我是 codex"
```

列出并执行场景。场景执行默认需要确认：

```powershell
mijiactl homes --json
mijiactl scene list --home-id <home_id>
mijiactl scene run --id <scene_id> --home-id <home_id> --confirm scene:<scene_id>
```

## 当前能力

- 二维码登录和脱敏授权检查。
- 家庭、房间、场景和设备列表。
- MIoT 能力查询、缓存和 JSON fallback。
- 属性读取和设置。
- 通过 `run_action` 执行 MIoT action，包括用可重复的 `--arg` 按顺序传入 MIoT action 参数。
- 场景列表和带确认的场景执行。
- 用户安全策略：禁用设备、禁用动作、需要确认的操作。

## 常用命令

```powershell
mijiactl version
mijiactl doctor
mijiactl setup
mijiactl login
mijiactl config init
mijiactl devices --json
mijiactl devices --refresh --json
mijiactl homes --json
mijiactl homes --refresh --json
mijiactl info --model <model> --json
mijiactl get --did <did> --prop <name>
mijiactl set --did <did> --prop <name> --value <value>
mijiactl action --did <did> --action <name>
mijiactl action --did <did> --action <name> --arg <value>
mijiactl scene list --home-id <home_id>
mijiactl scene list --home-id <home_id> --refresh
```

带输入参数的 action 需要按 `mijiactl info --model <model> --json` 里 `in` 列表的顺序逐个传 `--arg`。参数值使用和 `set --value` 相同的解析逻辑，`true`、`false`、整数和小数会在调用 MIoT 前自动转换。

`devices`、`homes` 和 `scene list` 会返回很小的 `data.cache` 对象，包含 `hit`、`created_at` 和 `expires_at`。普通控制命令内部也会使用未过期的设备快照，所以 Agent 不需要每次操作前都重新发现设备。

## 更新

更新 Agent Skill：重新执行同一个 `skills add` 命令即可。

```powershell
npx skills add stg609/mijia-control-skill --skill controlling-mijia-smart-home -g --agent claude-code openclaw cline codex cursor github-copilot kiro-cli lingma opencode qwen-code trae-cn windsurf -y
```

更新 `mijiactl` runtime 到最新 GitHub Release：

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 | Invoke-Expression
mijiactl version
```

如果你是开发模式源码安装，用：

```powershell
uv tool upgrade mijiactl
```

授权和策略文件保存在 `~/.config/mijiactl`，更新不会删除这些文件。

## 卸载和清理

如果只想删除 `mijiactl.exe`，但保留登录、策略和缓存，方便以后重新安装，使用 runtime 专用卸载脚本：

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/uninstall-mijiactl.ps1 | Invoke-Expression
```

如果要同时移除 Agent Skill 和 runtime，使用仓库级卸载脚本。它会先尝试 `npx skills remove`，再尝试 `npx skills uninstall`；如果当前 `skills` CLI 不支持自动卸载，会提示手动清理 Skill 目录：

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/uninstall.ps1 | Invoke-Expression
```

如果要彻底清理本机所有本项目数据，包括 `auth.json`、策略配置、能力缓存、设备/家庭/场景快照：

```powershell
& ([ScriptBlock]::Create((Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/uninstall.ps1))) -PurgeData
```

手动清理路径：

- runtime 可执行文件：`~/.mijiactl/bin/mijiactl.exe`
- runtime 安装目录：`~/.mijiactl`
- 授权、策略、能力缓存和快照：`~/.config/mijiactl`
- Agent Skill：如果 `skills` CLI 不能自动删除，请从各 Agent 的 skills 目录中删除 `controlling-mijia-smart-home`。

只有在你确定这台电脑以后不再使用当前米家授权时，才使用 `-PurgeData`。使用后如果重新安装，需要再次运行 `mijiactl login` 并扫码授权。

如果你已经有本地 checkout，对应命令是：

```powershell
.\scripts\uninstall-mijiactl.ps1
.\uninstall.ps1
.\uninstall.ps1 -PurgeData
```

所有命令都返回：

```json
{"ok": true, "error": null, "data": {}}
```

或：

```json
{"ok": false, "error": {"code": "ERROR_CODE", "message": "...", "data": {}}, "data": null}
```

## 安全策略

初始化策略：

```powershell
mijiactl config init
```

编辑：

```text
~/.config/mijiactl/config.json
```

策略字段：

- `disabled_devices`：永远不允许控制的设备。
- `disabled_actions`：永远不允许执行的动作或属性变更。
- `confirm_required`：执行前必须得到明确确认的设备或动作。

默认高风险类别包括门锁、摄像头、门铃、场景执行、家电启动、扫地机启动和插座通电。

## 一条命令安装

如果你接受远程 PowerShell 脚本，可以使用 bootstrap 脚本同时安装 Skill 和最新 Release 里的 `mijiactl.exe`。不习惯 `irm | iex` 的用户建议先打开脚本内容检查：

```powershell
Invoke-RestMethod https://raw.githubusercontent.com/stg609/mijia-control-skill/master/install.ps1 | Invoke-Expression
```

从本地 checkout 运行时，可以加 `-Login`：

```powershell
.\install.ps1 -Login
```

从 bootstrap 脚本安装时，可以用 `-Agents` 覆盖默认全局安装目标列表。只有开发源码安装时才需要 `-UseSourceRuntime`。

如果当前 shell 没有 `irm` alias，请直接使用上面的完整 `Invoke-RestMethod` 写法。如果安全策略不允许管道执行脚本，可以先下载再运行：

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/stg609/mijia-control-skill/master/scripts/install-mijiactl.ps1 -OutFile install-mijiactl.ps1
.\install-mijiactl.ps1
```

也可以手动安装：从最新 GitHub Release 下载 `mijiactl-windows-x64.exe`，重命名为 `mijiactl.exe`，放到 `~/.mijiactl/bin`，并把该目录加入用户 `Path`。

## Runtime 分发

最终用户不需要把整个仓库复制到 skills 目录。预期分发方式是：

- Agent 指令：由 `npx skills add` 从 `skills/controlling-mijia-smart-home` 安装。
- Runtime：从 GitHub Releases 下载 `mijiactl-windows-x64.exe` 到 `~/.mijiactl/bin`。
- 开发备用路径：`uv tool install "mijiactl[mijia] @ git+https://github.com/stg609/mijia-control-skill.git"`。

## 实现原理

运行时设计、控制流程、安全策略、能力缓存和 release 打包方式见 [docs/architecture.md](docs/architecture.md)。

这个项目参考和使用了米家自动化社区的成果，感谢：

- [`Do1e/mijia-api`](https://github.com/Do1e/mijia-api)，即 PyPI 上的 `mijiaAPI`，提供底层 Python 米家 API。
- [`moneshvenkul/mijia-skills`](https://github.com/moneshvenkul/mijia-skills)，提供了较早的 Agent Skill 风格组织方式参考。
- [`ssttkkl/mijia-skill`](https://github.com/ssttkkl/mijia-skill) 以及相关 MIoT action 控制文章，说明了洗衣机等复杂设备为什么必须使用 MIoT action。

## License

本仓库使用 `GPL-3.0-or-later`。直接运行时依赖 `mijiaAPI==3.0.5` 在 PyPI 上标注为 `GPL-3.0-or-later`，因此当前项目不适合标为 MIT。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 仓库结构

```text
mijiactl/                                提供 mijiactl 命令的 Python 包
scripts/                                Release 安装和构建脚本
skills/controlling-mijia-smart-home/     通过 npx skills add 安装的 Agent Skill
evals/                    维护者用于回归检查的 Agent prompts
tests/                    单元测试和打包测试
```

## Skill 分发

canonical Skill 目录：

```text
skills/controlling-mijia-smart-home/
```

导出独立 Skill：

```powershell
mijiactl-export-skill --out dist/controlling-mijia-smart-home
```

发布前验证：

```powershell
uv run --no-project python -m unittest discover -s tests
uv run --no-project --with pyyaml python <path-to-quick_validate.py> skills/controlling-mijia-smart-home
```

## 发布检查清单

- 搜索 `serviceToken`、`ssecurity`、`passToken`、`userId`、`deviceId` 等关键词；只有文档说明和测试 fixture 应该命中。
- 确认安装命令里没有仓库 owner 占位符。
- 运行单元测试：`uv run --no-project python -m unittest discover -s tests`。
- 用目标 Agent 的 Skill validator 校验 Skill 目录。
- 构建 Python 包：`uv build`。
- 本地运行 `.\scripts\build-release.ps1` 构建 Windows 可执行文件，或推送 `v*` tag 让 GitHub Actions 发布 `mijiactl-windows-x64.exe`。
- 确认 wheel 包含 `mijiactl`、`skills/controlling-mijia-smart-home`、`README.md`、`README.zh-CN.md` 和 `install.ps1`。
- 在干净机器或临时用户配置下验证 README 的安装路径。

## 维护者 Eval

Agent 回归 prompt 放在 `evals/evals.json`，覆盖首次安装、列设备、安全开灯、高风险确认、洗衣机 action 行为，以及带参数的小爱音箱 TTS action。

## 维护说明

- 保持 `skills/controlling-mijia-smart-home/SKILL.md` 简洁，把安装和安全细节放到 `references/`。
- runtime 代码统一放在 `mijiactl` 下；`skills/controlling-mijia-smart-home` 只放 Agent Skill。
- 不要在测试、文档或命令输出里暴露授权 token。
- 每次调整策略或命令行为，都补对应测试。
- 优先保持稳定 JSON 输出，方便 Agent 基于 `ok` 和 `error.code` 分支。
