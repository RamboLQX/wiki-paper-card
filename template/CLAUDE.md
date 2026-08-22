# CLAUDE.md

## Vault 约定

当前目录是 `wiki-paper-card` 的 Obsidian wiki 根目录。

- `raw/` 只读，禁止修改或重写用户资料。
- 生成的来源页、概念页、实体页和 topic 页只写入 `wiki/`。
- 批次中间产物写入 `work/`，不得混入 `wiki/`。
- 论文全文不得进入主会话。

## Skill 路由（先判断场景，再调用）

按场景选择入口，不按关键词猜测：

1. 处理论文（单篇或批量、PDF 或 source map）→ 调用 `wiki-paper-card` skill。
2. 在知识库上提问、检索、查证或写综述 → 不调用 `wiki-paper-card`，直接遵循
   `wiki-shared` 的 `references/retrieval-protocol.md`：先读
   `wiki/meta/knowledge-tree.md`（定向问答同时读 `wiki/meta/research.md`），
   再按 lookup 或 survey 模式下降检索；结论必须带页面与证据指针。
3. 修改 wiki 结构（建页、合并、别名、矛盾记录）→ 先读 `wiki-shared` 的
   `references/knowledge-model.md` 与 `references/wiki-schema.md`，且所有
   wiki 写入最终由确定性 `publish_wiki.py` 执行。
4. 与论文处理或知识库检索无关的请求 → 不调用本框架任何 skill。
5. `wiki-shared` 是只读参考包，不作为独立流程调用。

## 处理入口

用户给出明确输入路径后，使用 `wiki-paper-card` skill 执行单篇或批量流程。子代理可用时使用 `wiki-processor` 和 `wiki-linker`；所有 wiki 写入最终由确定性 `publish_wiki.py` 执行。

如果 skill 或脚本不在 vault 中，优先使用 `WIKI_PAPER_CARD_ROOT` 指向 `wiki-paper-card` 仓库根目录。

## 知识边界

- 单篇论文内部候选保持在 Paper Card 中。
- 只有达到跨论文证据门槛的 L2 候选才能创建薄枢纽页。
- 不因词频创建页面，不静默覆盖矛盾，不自动删除已有页面。
