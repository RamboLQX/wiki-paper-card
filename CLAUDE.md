# CLAUDE.md

## 项目定位

`wiki-paper-card` 是面向 Obsidian LLM Wiki 的论文分析与知识结晶项目。当前唯一的运行宿主是 Claude Code，推荐通过 Obsidian 的 Claudian 插件使用。

## 安装与适配入口

当用户要求配置、安装、初始化或适配 `wiki-paper-card` 时，先读取并遵循 `docs/agent-quick-setup.md`。安装流程不得改写 `raw/`、删除已有知识页面或覆盖 Vault 级 `CLAUDE.md`。

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
