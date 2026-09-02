# Agent 快速安装适配说明

> 已安装的旧版 Vault 请使用 [Agent 升级与 Topic 迁移说明](agent-upgrade.md)。升级不等同于首次安装，运行入口更新和 Topic 内容迁移必须分开。

本文档供具备网络访问、终端执行和本地文件写入权限的 Agent 读取并执行。用户不需要手动复制安装命令，但必须提供或确认仓库安装目录、目标 Obsidian Vault 和运行宿主。

当前项目支持三个论文处理运行宿主：Claude Code（Obsidian 入口推荐 Claudian 插件）、DeepSeek Harness（DSH）与 Codex。DSH 和 Codex 从 Vault 根目录启动会话。其他 Agent 运行宿主暂不属于正式支持范围。

仓库尚未克隆时，推荐使用：

```text
请按照以下安装说明配置 wiki-paper-card：
安装说明：https://raw.githubusercontent.com/RamboLQX/wiki-paper-card/main/docs/agent-quick-setup.md
项目仓库：https://github.com/RamboLQX/wiki-paper-card.git
仓库安装目录：/absolute/path/to/wiki-paper-card
Obsidian Vault：/absolute/path/to/vault
运行宿主：claude / dsh / both / codex / all

请先检查路径和运行环境。如果仓库尚未存在，将仓库克隆到指定目录；
然后执行安装脚本、运行 smoke test，并分别报告已完成项目和仍需手动完成的步骤。
不要覆盖 Vault 中已有文件。
```

仓库已经克隆时，推荐使用：

```text
请阅读 /absolute/path/to/wiki-paper-card/docs/agent-quick-setup.md，并帮我配置 wiki-paper-card。
项目仓库：/absolute/path/to/wiki-paper-card
Obsidian Vault：/absolute/path/to/vault
运行宿主：claude / dsh / both / codex / all
```

## 执行目标

将 `wiki-paper-card` 接入现有或新建的 Obsidian Vault：

1. 确认 Python 与所选 Agent 运行环境。
2. 引导用户完成 Obsidian、Claudian（仅 Claude Code 宿主）等手动安装步骤。
3. 在 Vault 中补齐 Wiki 目录，但不覆盖已有文件。
4. 链接 skill 到宿主技能目录（Claude Code：`.claude/skills`；DSH：`.dsh/skills`；Codex：`.agents/skills`）。
5. 设置 `WIKI_PAPER_CARD_ROOT` 并运行现有 smoke test。
6. 返回安装报告和后续调用示例。

## 安全边界

- `raw/` 是用户资料目录，只读，禁止修改或重写。
- 不删除、不覆盖 Vault 中已有的知识页面、`index.md` 或 `log.md`。
- 不覆盖已有 `CLAUDE.md` 或 `AGENTS.md`，只能在用户确认后合并缺失的必要段落。
- 不读取或记录用户 API Key。
- Obsidian 和 Claudian 的图形界面安装步骤必须交还用户确认，不得宣称已经自动完成。
- 所有路径使用绝对路径，禁止根据文件名猜测 Vault 位置。

## 必要信息

执行前至少确认以下值：

```text
REPO_URL=https://github.com/RamboLQX/wiki-paper-card.git  # 仅仓库尚未克隆时需要
REPO_ROOT=/absolute/path/to/wiki-paper-card
VAULT_ROOT=/absolute/path/to/vault
HOST=claude|dsh|both|codex|all
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

- `claude`、`both` 或 `all`：检查 `command -v claude`；缺失时引导用户按官方说明安装 Claude Code。Obsidian 缺失时引导用户从 <https://obsidian.md/download> 下载并打开目标 Vault；Claudian 缺失时引导用户在 Obsidian 的 Community plugins 中安装并启用。
- `dsh`、`both` 或 `all`：确认用户的 DeepSeek Harness 环境可用（能启动会话并执行命令）。DSH 不需要在 Vault 内安装插件。
- `codex` 或 `all`：确认 Codex 桌面应用、CLI 或 IDE 扩展可用，并能从 Vault 根目录启动项目任务。不要为本框架修改用户的 `.codex/config.toml`。

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

- 只创建缺失目录与缺失文件；已有 `wiki/`、`CLAUDE.md`、`AGENTS.md`、知识页面一律保留。
- skill 使用符号链接；链接已存在且指向不同位置时报冲突并退出码 1，不会自动替换。
- Claude Code 宿主：链接 skill 到 `$VAULT_ROOT/.claude/skills/`，复制 agent 到 `$VAULT_ROOT/.claude/agents/`（同名不同内容报冲突）。
- DSH 宿主：链接 skill 到 `$VAULT_ROOT/.dsh/skills/`。DSH 自动发现该目录与 Vault 根目录的 `CLAUDE.md`/`AGENTS.md`。
- Codex 宿主：链接 skill 到 `$VAULT_ROOT/.agents/skills/`，安装 Vault 根 `AGENTS.md`，不创建 `.codex/agents` 或改写 Codex 全局配置。
- 资源目录链接：`adapters/`、`vendor/`、`scripts/` 软链到宿主层的 `../../` 位置（Claude Code：`$VAULT_ROOT/.claude/`；DSH：`$VAULT_ROOT/.dsh/`；Codex：`$VAULT_ROOT/.agents/`），保证 Skill 内 `../../` 引用在安装后可解析；安装结束按宿主自检 adapter 与共享资源，断链以退出码 1 报错。
- 仓库根指针：向每个所选宿主目录写入 `WIKI_PAPER_CARD_ROOT`（内容为 `$REPO_ROOT` 绝对路径）。Agent 会话在未设置同名环境变量时只读当前宿主指针；自检同时校验指针指向的 `vendor/nature-paper-card/SKILL.md` 可读。
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
- Codex：链接 `$REPO_ROOT/skills/{wiki-paper-card,wiki-shared,wiki-gap-mining}` 到 `$VAULT_ROOT/.agents/skills/`，并链接 `adapters`、`vendor`、`scripts` 到 `$VAULT_ROOT/.agents/`。
- 向所选宿主目录写入仓库根指针（内容为 `$REPO_ROOT` 绝对路径）：
  `printf '%s\n' "$REPO_ROOT" > "$VAULT_ROOT/.dsh/WIKI_PAPER_CARD_ROOT"`；
  `printf '%s\n' "$REPO_ROOT" > "$VAULT_ROOT/.claude/WIKI_PAPER_CARD_ROOT"`；
  `printf '%s\n' "$REPO_ROOT" > "$VAULT_ROOT/.agents/WIKI_PAPER_CARD_ROOT"`。
- 模板文件按缺失补齐：

```text
$REPO_ROOT/template/wiki/index.md
$REPO_ROOT/template/wiki/log.md
$REPO_ROOT/template/wiki/meta/paper-processing-conventions.md
$REPO_ROOT/template/CLAUDE.md  # Claude Code / DSH
$REPO_ROOT/template/AGENTS.md  # Codex
```

## 第五步：检查 Vault 级入口文件

- Claude Code/DSH 使用 `CLAUDE.md`，Codex 使用 `AGENTS.md`；`all` 同时安装两者。
- 如果目标文件已经存在且内容不同，不覆盖；报告需要人工合并的必要段落：

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

未设置环境变量时，Agent 会话只回退读取当前宿主目录下的指针文件：
`$VAULT_ROOT/.claude/WIKI_PAPER_CARD_ROOT`、`$VAULT_ROOT/.dsh/WIKI_PAPER_CARD_ROOT` 或 `$VAULT_ROOT/.agents/WIKI_PAPER_CARD_ROOT`。因此环境变量可以省略；设置了更稳妥。

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
test -f "$VAULT_ROOT/CLAUDE.md"                       # HOST 含 claude/dsh 时
test -f "$VAULT_ROOT/AGENTS.md"                       # HOST 含 codex 时
test -L "$VAULT_ROOT/.claude/skills/wiki-paper-card"   # HOST 含 claude 时
test -L "$VAULT_ROOT/.dsh/skills/wiki-paper-card"      # HOST 含 dsh 时
test -L "$VAULT_ROOT/.agents/skills/wiki-paper-card"   # HOST 含 codex 时
test -L "$VAULT_ROOT/.claude/adapters"                 # HOST 含 claude 时
test -L "$VAULT_ROOT/.dsh/adapters"                    # HOST 含 dsh 时
test -L "$VAULT_ROOT/.agents/adapters"                 # HOST 含 codex 时
test -r "$VAULT_ROOT/.dsh/adapters/dsh/dsh-mode.md"    # HOST 含 dsh 时
test -r "$VAULT_ROOT/.agents/adapters/codex/codex-mode.md" # HOST 含 codex 时
test -r "$VAULT_ROOT/.claude/WIKI_PAPER_CARD_ROOT"     # HOST 含 claude 时
test -r "$VAULT_ROOT/.dsh/WIKI_PAPER_CARD_ROOT"        # HOST 含 dsh 时
test -r "$VAULT_ROOT/.agents/WIKI_PAPER_CARD_ROOT"     # HOST 含 codex 时
```

DSH 需要新开会话确认 Skill 目录；Codex 需要从 Vault 根目录新开任务确认 `.agents/skills/` 发现与 `AGENTS.md` 路由。把这些宿主侧验收写入"仍需用户手动完成的步骤"。

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
Use wiki-paper-card in wiki-full mode to process raw/papers/example.pdf.
```

## 设计与来源

- Wiki 分层、Agent 持续维护、`index.md` 和 `log.md` 等设计参考 Karpathy 的 [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 思路。
- 论文分析内核和共享规则来自 `nature-skills`，固定版本与同步策略见 `UPSTREAM.md`。
- DSH 适配层见 `adapters/dsh/`，编排映射见 `adapters/dsh/dsh-mode.md`。
- Codex 适配层见 `adapters/codex/`，编排映射见 `adapters/codex/codex-mode.md`。
