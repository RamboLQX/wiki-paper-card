# Agent 快速安装适配说明

本文档供具备网络访问、终端执行和本地文件写入权限的 Agent 读取并执行。用户不需要手动复制安装命令，但必须提供或确认仓库安装目录、目标 Obsidian Vault 和运行宿主。

当前项目支持两个论文处理运行宿主：Claude Code（Obsidian 入口推荐 Claudian 插件）与 DeepSeek Harness（DSH，在 Vault 目录中启动会话）。用户自己的 Agent 工具负责引导或执行安装适配，其他 Agent 运行宿主的论文处理流程暂不属于正式支持范围。

仓库尚未克隆时，推荐使用：

```text
请按照以下安装说明配置 wiki-paper-card：
安装说明：https://raw.githubusercontent.com/RamboLQX/wiki-paper-card/main/docs/agent-quick-setup.md
项目仓库：https://github.com/RamboLQX/wiki-paper-card.git
仓库安装目录：/absolute/path/to/wiki-paper-card
Obsidian Vault：/absolute/path/to/vault
运行宿主：claude / dsh / both

请先检查路径和运行环境。如果仓库尚未存在，将仓库克隆到指定目录；
然后执行安装脚本、运行 smoke test，并分别报告已完成项目和仍需手动完成的步骤。
不要覆盖 Vault 中已有文件。
```

仓库已经克隆时，推荐使用：

```text
请阅读 /absolute/path/to/wiki-paper-card/docs/agent-quick-setup.md，并帮我配置 wiki-paper-card。
项目仓库：/absolute/path/to/wiki-paper-card
Obsidian Vault：/absolute/path/to/vault
运行宿主：claude / dsh / both
```

## 执行目标

将 `wiki-paper-card` 接入现有或新建的 Obsidian Vault：

1. 确认 Python 与所选 Agent 运行环境。
2. 引导用户完成 Obsidian、Claudian（仅 Claude Code 宿主）等手动安装步骤。
3. 在 Vault 中补齐 Wiki 目录，但不覆盖已有文件。
4. 链接 skill 到宿主技能目录（Claude Code：`.claude/skills`；DSH：`.dsh/skills`）。
5. 设置 `WIKI_PAPER_CARD_ROOT` 并运行现有 smoke test。
6. 返回安装报告和后续调用示例。

## 安全边界

- `raw/` 是用户资料目录，只读，禁止修改或重写。
- 不删除、不覆盖 Vault 中已有的知识页面、`index.md` 或 `log.md`。
- 不覆盖已有 `CLAUDE.md`，只能合并缺失的必要段落。
- 不读取或记录用户 API Key。
- Obsidian 和 Claudian 的图形界面安装步骤必须交还用户确认，不得宣称已经自动完成。
- 所有路径使用绝对路径，禁止根据文件名猜测 Vault 位置。

## 必要信息

执行前至少确认以下值：

```text
REPO_URL=https://github.com/RamboLQX/wiki-paper-card.git  # 仅仓库尚未克隆时需要
REPO_ROOT=/absolute/path/to/wiki-paper-card
VAULT_ROOT=/absolute/path/to/vault
HOST=claude|dsh|both
```

如果用户没有提供 `REPO_ROOT`、`VAULT_ROOT` 或 `HOST`，必须先询问。不能使用当前目录或主目录作为默认安装位置，也不能根据目录名称猜测 Vault。目标 Vault 根目录尚不存在时，创建前必须获得用户确认。

## 第一步：检查运行环境

Agent 应检查可用的命令：

```bash
command -v python3
python3 --version
python3 -m pip show pymupdf
```

- Python 3 缺失时，引导用户使用当前系统的官方安装方式。
- 处理 PDF 时，可以执行：

```bash
python3 -m pip install pymupdf
```

按 `HOST` 检查宿主环境：

- `claude` 或 `both`：检查 `command -v claude`；缺失时引导用户按官方说明安装 Claude Code。Obsidian 缺失时引导用户从 <https://obsidian.md/download> 下载并打开目标 Vault；Claudian 缺失时引导用户在 Obsidian 的 Community plugins 中安装并启用。
- `dsh` 或 `both`：确认用户的 DeepSeek Harness 环境可用（能启动会话并执行命令）。DSH 不需要在 Vault 内安装插件，会话在 Vault 目录中启动即可。

Agent 无法完成 GUI 操作时，应把这些项目列入待用户操作清单，而不是标记为已完成。

## 第二步：定位项目仓库

如果 `REPO_ROOT` 已存在，使用该路径。

如果用户提供仓库 URL 和已确认的安装目录，执行：

```bash
git clone "$REPO_URL" "$REPO_ROOT"
```

不要自动选择用户主目录下的未指定路径。

## 第三步：执行安装脚本（推荐）

仓库自带幂等安装脚本，同时处理目录补齐、模板复制与宿主 skill 链接：

```bash
"$REPO_ROOT/scripts/install.sh" --repo-root "$REPO_ROOT" --host "$HOST" "$VAULT_ROOT"
```

脚本行为与安全保证：

- 只创建缺失目录与缺失文件；已有 `wiki/`、`CLAUDE.md`、知识页面一律保留。
- skill 使用符号链接；链接已存在且指向不同位置时报冲突并退出码 1，不会自动替换。
- Claude Code 宿主：链接 skill 到 `$VAULT_ROOT/.claude/skills/`，复制 agent 到 `$VAULT_ROOT/.claude/agents/`（同名不同内容报冲突）。
- DSH 宿主：链接 skill 到 `$VAULT_ROOT/.dsh/skills/`。DSH 自动发现该目录与 Vault 根目录的 `CLAUDE.md`/`AGENTS.md`。
- 资源目录链接：`adapters/`、`vendor/`、`scripts/` 软链到宿主层的 `../../` 位置（Claude Code：`$VAULT_ROOT/.claude/`；DSH：`$VAULT_ROOT/.dsh/`），保证技能内 `../../` 引用（如 `../../adapters/dsh/dsh-mode.md`）在安装后仍可解析；安装结束自检这些引用，断链以退出码 1 报错。
- 退出码非 0 时，把脚本输出的 CONFLICT/ERROR 行逐条报告给用户，不擅自处理。

## 第四步：手动安装（不使用脚本时的等价步骤）

仅当用户明确要求逐步手动安装时使用。

补齐目录：

```bash
mkdir -p "$VAULT_ROOT/raw/papers"
mkdir -p "$VAULT_ROOT/wiki/sources" "$VAULT_ROOT/wiki/topics" "$VAULT_ROOT/wiki/meta"
mkdir -p "$VAULT_ROOT/work"
```

链接 skill 并复制模板文件，规则与脚本一致（no-clobber、链接冲突报告不替换）：

- Claude Code：链接 `$REPO_ROOT/skills/{wiki-paper-card,wiki-shared,wiki-gap-mining}` 到 `$VAULT_ROOT/.claude/skills/`，复制 `$REPO_ROOT/adapters/claude-code/agents/*.md` 到 `$VAULT_ROOT/.claude/agents/`，并链接 `adapters`、`vendor`、`scripts` 到 `$VAULT_ROOT/.claude/`。
- DSH：链接 `$REPO_ROOT/skills/{wiki-paper-card,wiki-shared,wiki-gap-mining}` 到 `$VAULT_ROOT/.dsh/skills/`，并链接 `adapters`、`vendor`、`scripts` 到 `$VAULT_ROOT/.dsh/`。
- 模板文件按缺失补齐：

```text
$REPO_ROOT/template/wiki/index.md
$REPO_ROOT/template/wiki/log.md
$REPO_ROOT/template/wiki/meta/paper-processing-conventions.md
$REPO_ROOT/template/CLAUDE.md
```

## 第五步：合并 Vault 级 CLAUDE.md

- 如果 `$VAULT_ROOT/CLAUDE.md` 不存在，脚本已复制 `$REPO_ROOT/template/CLAUDE.md`。
- 如果已经存在且内容不同，只合并模板中缺失的必要段落：

```text
## Vault 约定
## 处理入口
## 知识边界
```

合并原则：

- 保留原文件全部内容。
- 不重复已有段落。
- 遇到与本项目规则冲突的表述时，报告冲突，不擅自改写用户规则。
- 不写入 API Key、论文路径或私人资料路径。

## 第六步：设置项目根目录

当前会话使用：

```bash
export WIKI_PAPER_CARD_ROOT="$REPO_ROOT"
```

持久化方式由用户使用的宿主决定（Claudian 配置或启动 shell 的环境变量）。Agent 应说明当前会话已经生效，并告知用户如何持久化。

## 第七步：验证

执行现有 smoke test，不新增独立预检脚本：

```bash
PYTHONDONTWRITEBYTECODE=1 \
WIKI_PAPER_CARD_ROOT="$REPO_ROOT" \
python3 "$REPO_ROOT/scripts/smoke_test.py"
```

检查关键路径：

```bash
test -d "$VAULT_ROOT/raw/papers"
test -d "$VAULT_ROOT/wiki/sources"
test -d "$VAULT_ROOT/wiki/topics"
test -f "$VAULT_ROOT/CLAUDE.md"
test -L "$VAULT_ROOT/.claude/skills/wiki-paper-card"   # HOST 含 claude 时
test -L "$VAULT_ROOT/.dsh/skills/wiki-paper-card"      # HOST 含 dsh 时
test -L "$VAULT_ROOT/.claude/adapters"                 # HOST 含 claude 时
test -L "$VAULT_ROOT/.dsh/adapters"                    # HOST 含 dsh 时
test -r "$VAULT_ROOT/.dsh/adapters/dsh/dsh-mode.md"    # HOST 含 dsh 时
```

DSH 宿主额外说明：skill 目录在会话启动时编入目录，需要新开一个 DSH 会话才能确认 `wiki-paper-card` 出现在会话技能列表里；把这一条写入"仍需用户手动完成的步骤"。

## 第八步：返回安装报告

最终输出至少包含：

```text
已完成的配置项
仍需用户手动完成的步骤
smoke test 结果
下一次论文处理调用示例
```

示例调用：

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

## 设计与来源

- Wiki 分层、Agent 持续维护、`index.md` 和 `log.md` 等设计参考 Karpathy 的 [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思路。
- 论文分析内核和共享规则来自 `nature-skills`，固定版本与同步策略见 `UPSTREAM.md`。
- DSH 适配层见 `adapters/dsh/`，编排映射见 `adapters/dsh/dsh-mode.md`。
