# Agent 快速安装适配说明

本文档供用户自己的 Agent 读取并执行。用户不需要手动复制这些命令，只需要提供项目仓库和目标 Obsidian Vault 的位置。

当前项目的论文处理运行宿主是 Claude Code 和 Obsidian Claudian。用户自己的 Agent 工具负责引导或执行安装适配，其他 Agent 运行宿主的论文处理流程暂不属于正式支持范围。

推荐触发语句：

```text
请阅读 <REPO_ROOT>/docs/agent-quick-setup.md，并帮我配置 wiki-paper-card。
项目仓库：/path/to/wiki-paper-card
Obsidian Vault：/path/to/vault
```

如果仓库尚未克隆，可以用仓库 URL 代替本地路径。

## 执行目标

将 `wiki-paper-card` 接入现有或新建的 Obsidian Vault：

1. 确认 Python 和 Agent 运行环境。
2. 引导用户完成 Obsidian、Claudian 和 Claude Code 等手动安装步骤。
3. 在 Vault 中补齐 Wiki 目录，但不覆盖已有文件。
4. 链接 skill，复制 Claude Code agent，合并 Vault 级 `CLAUDE.md`。
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

执行前至少确认以下两个值：

```text
REPO_ROOT=/path/to/wiki-paper-card
VAULT_ROOT=/path/to/vault
```

如果用户没有提供，必须先询问，不能使用当前目录或主目录作为默认 Vault。

## 第一步：检查运行环境

Agent 应检查可用的命令：

```bash
command -v python3
command -v claude
python3 --version
python3 -m pip show pymupdf
```

- Python 3 缺失时，引导用户使用当前系统的官方安装方式。
- 处理 PDF 时，可以执行：

```bash
python3 -m pip install pymupdf
```

- Claude Code 缺失时，引导用户按照官方安装说明配置。
- Obsidian 缺失时，引导用户从 <https://obsidian.md/download> 下载并打开目标 Vault。
- Claudian 缺失时，引导用户在 Obsidian 的 Community plugins 中安装并启用。

Agent 无法完成 GUI 操作时，应把这些项目列入待用户操作清单，而不是标记为已完成。

## 第二步：定位项目仓库

如果 `REPO_ROOT` 已存在，使用该路径。

如果用户只提供仓库 URL，使用用户同意的目录执行：

```bash
git clone <repository-url> "$REPO_ROOT"
```

不要自动选择用户主目录下的未指定路径。

## 第三步：补齐 Vault 目录

只创建缺失目录，不修改已有内容：

```bash
mkdir -p "$VAULT_ROOT/raw/papers"
mkdir -p "$VAULT_ROOT/wiki/sources"
mkdir -p "$VAULT_ROOT/wiki/concepts"
mkdir -p "$VAULT_ROOT/wiki/entities"
mkdir -p "$VAULT_ROOT/wiki/topics"
mkdir -p "$VAULT_ROOT/work"
mkdir -p "$VAULT_ROOT/.claude/skills"
mkdir -p "$VAULT_ROOT/.claude/agents"
```

使用项目模板补齐 Wiki 文件时，只添加目标 Vault 中不存在的文件。执行前检查每个目标文件，已有文件必须保留原内容：

```text
$REPO_ROOT/template/wiki/index.md
$REPO_ROOT/template/wiki/log.md
$REPO_ROOT/template/wiki/meta/paper-processing-conventions.md
```

如果当前运行环境没有可用的 no-clobber 复制命令，逐个检查目标是否存在，再复制缺失文件。

## 第四步：链接 skill 与复制 agent

优先使用符号链接：

```bash
ln -s "$REPO_ROOT/skills/wiki-paper-card" "$VAULT_ROOT/.claude/skills/wiki-paper-card"
ln -s "$REPO_ROOT/skills/wiki-shared" "$VAULT_ROOT/.claude/skills/wiki-shared"
```

如果目标链接已经存在，先确认它指向同一仓库。指向不同位置时不要自动替换，应报告并询问用户。

复制 Claude Code agent：

```bash
cp "$REPO_ROOT"/adapters/claude-code/agents/*.md "$VAULT_ROOT/.claude/agents/"
```

同名文件已存在时不要静默覆盖，应比较并报告差异。

## 第五步：合并 Vault 级 CLAUDE.md

- 如果 `$VAULT_ROOT/CLAUDE.md` 不存在，复制 `$REPO_ROOT/template/CLAUDE.md`。
- 如果已经存在，只合并模板中缺失的必要段落：

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

持久化方式由用户使用的 Agent 工具决定，通常可以设置在其环境变量或 Claudian 配置中。Agent 应说明当前会话已经生效，并告知用户如何持久化。

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
test -d "$VAULT_ROOT/wiki/concepts"
test -d "$VAULT_ROOT/wiki/entities"
test -d "$VAULT_ROOT/wiki/topics"
test -d "$VAULT_ROOT/.claude/skills"
test -d "$VAULT_ROOT/.claude/agents"
test -f "$VAULT_ROOT/CLAUDE.md"
```

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
