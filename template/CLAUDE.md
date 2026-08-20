# CLAUDE.md

## Vault 约定

当前目录是 `wiki-paper-card` 的 Obsidian wiki 根目录。

- `raw/` 只读，禁止修改或重写用户资料。
- 生成的来源页、概念页、实体页和 topic 页只写入 `wiki/`。
- 批次中间产物写入 `work/`，不得混入 `wiki/`。
- 论文全文不得进入主会话。

## 处理入口

用户给出明确输入路径后，使用 `wiki-paper-card` skill 执行单篇或批量流程。子代理可用时使用 `wiki-processor` 和 `wiki-linker`；所有 wiki 写入最终由确定性 `publish_wiki.py` 执行。

如果 skill 或脚本不在 vault 中，优先使用 `WIKI_PAPER_CARD_ROOT` 指向 `wiki-paper-card` 仓库根目录。

## 知识边界

- 单篇论文内部候选保持在 Paper Card 中。
- 只有达到跨论文证据门槛的 L2 候选才能创建薄枢纽页。
- 不因词频创建页面，不静默覆盖矛盾，不自动删除已有页面。
