# CLAUDE.md

## 项目定位

`wiki-paper-card` 是面向 Obsidian LLM Wiki 的论文分析与知识结晶项目。运行宿主为 Claude Code（推荐通过 Obsidian 的 Claudian 插件使用）、DeepSeek Harness（DSH）与 Codex；DSH 和 Codex 从 Vault 根目录启动会话。

## 安装与适配入口

当用户要求配置、安装、初始化或适配 `wiki-paper-card` 时，先读取并遵循 `docs/agent-quick-setup.md`。安装流程不得改写 `raw/`、删除已有知识页面或覆盖 Vault 级 `CLAUDE.md` / `AGENTS.md`。

## 运行时 Skill 路由（在 Vault 中工作时）

Vault 运行时规范以内容一致的 `template/CLAUDE.md` 与 `template/AGENTS.md` 为准（`install.sh` 按宿主复制到 Vault 根目录；本仓库与 Vault 是不同位置）。核心路由规则：

1. 处理论文（单篇或批量、PDF 或 source map）→ 调用 `wiki-paper-card` skill。
2. 在知识库上提问、检索、查证或写综述 → 不调用 `wiki-paper-card`，遵循 `skills/wiki-shared/references/retrieval-protocol.md`：先读 `wiki/meta/agent-tree.md`（不存在时读 `wiki/meta/knowledge-tree.md`；选题类查询同时读 `wiki/meta/research.md`），按 lookup 或 survey 模式检索，结论必须带页面与证据指针。检索与综述只读，不回写 wiki。
3. 跨组或全库挖掘研究空白与候选方向 → 调用 `wiki-gap-mining` skill：先读后挖掘，报告经用户确认后才生成 link-plan 并走 `publish_wiki.py` 写回。
4. 修改 wiki 结构（建页、合并、别名、矛盾记录）→ 先读 knowledge-model 与 wiki-schema，所有 wiki 写入最终由确定性 `publish_wiki.py` 执行。
5. 与论文处理、知识库检索或空白挖掘无关的请求 → 不调用本框架任何 skill。

## 工作边界

- 不把用户论文 PDF 或私人 wiki 内容提交到本仓库。
- 运行时不修改用户 `raw/` 下的资料。
- 知识页面只做新增、更新和显式合并，不自动删除。
- 论文全文不能进入主会话；处理器只读取确定性 prepare 阶段生成的 bundle。
- `vendor/` 是固定的上游快照，修改前必须记录原因并更新 `UPSTREAM.md`。
- 新增流程必须先在 `skills/wiki-paper-card/references/workflow-contract.md` 或 `wiki-integration.md` 中定义验收条件。
- 知识节点准入规则统一放在 `skills/wiki-shared/references/knowledge-model.md`。

## 常用验证

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/smoke_test.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s vendor/nature-paper-card/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s vendor/nature-shared/tests -v
```
