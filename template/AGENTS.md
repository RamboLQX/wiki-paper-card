# wiki-paper-card Vault 规则

## Vault 约定

当前目录是 `wiki-paper-card` 的 Obsidian wiki 根目录。

- `raw/` 只读，禁止修改或重写用户资料。
- 生成的来源页和 topic 页只写入 `wiki/`。
- 批次中间产物写入 `work/`，不得混入 `wiki/`。
- 论文全文不得进入主会话。

## Skill 路由（先判断场景，再调用）

按场景选择入口，不按关键词猜测：

1. 处理论文（单篇或批量、PDF 或 source map）→ 调用 `wiki-paper-card` skill。
2. 升级已安装的 wiki-paper-card 或迁移旧 Topic → 调用 `wiki-paper-card`
   skill 的 `references/upgrade-contract.md`；先只读检查，将运行入口升级与
   Topic 内容迁移分开。用户确认范围前不改写 `wiki/`，不隐式执行全库迁移。
3. 在知识库上提问、检索、查证或写综述 → 不调用 `wiki-paper-card`，直接遵循
   `wiki-shared` 的 `references/retrieval-protocol.md`：先读
   `wiki/meta/knowledge-tree.md`（具体论文未命中时回退 `wiki/index.md` 与
   `wiki/sources/`；选题类查询同时读 `wiki/meta/research.md`），
   再按 lookup 或 survey 模式下降检索；结论必须带页面与证据指针。检索与
   综述只读，不回写 wiki。
4. 跨组或全库挖掘研究空白与候选方向（在指定的若干组或整个知识库内深挖开放
   问题、研究空白，并综合已解决问题）→ 调用 `wiki-gap-mining` skill：先读后
   挖掘，报告经用户确认后才生成 link-plan 并走 `publish_wiki.py` 写回。
5. 修改 wiki 结构（建页、合并、别名、矛盾记录）→ 先读 `wiki-shared` 的
   `references/knowledge-model.md` 与 `references/wiki-schema.md`，且所有
   wiki 写入最终由确定性 `publish_wiki.py` 执行。
6. 与论文处理、知识库检索或空白挖掘无关的请求 → 不调用本框架任何 skill。
7. `wiki-shared` 是只读参考包，不作为独立流程调用。

## 处理入口

用户给出论文后，先按 `wiki-paper-card` skill 固定一次处理范围：仅 Paper Card（`card-only`）、Paper Card + Topic 且不维护研究空白（`wiki-topic`），或完整 Wiki（`wiki-full`）。用户已经明确范围时直接执行；只说“处理/分析论文”而未说明范围时询问一次，不逐篇询问。子 Agent 可用时，每篇论文使用一个独立 processor；只有两个 Wiki 模式才为全批次使用一个 linker，并由确定性 `publish_wiki.py` 执行所有 wiki 写入。`card-only` 在 `work/` 中完成且不得写入 `wiki/`。具体宿主映射见安装后的 `adapters/` 目录。

如果 skill 或脚本不在 vault 中，使用 `WIKI_PAPER_CARD_ROOT` 指向 `wiki-paper-card` 仓库根目录。未设置环境变量时，只读取当前宿主目录下的指针文件 `WIKI_PAPER_CARD_ROOT`（Claude Code：`.claude/`；DSH：`.dsh/`；Codex：`.agents/`，由 `install.sh` 写入）。解析后先验证 `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md` 可读；失败即停止并向用户报告，不读取其他宿主指针，不猜测路径。

## 知识边界

- 论文私有术语、组件与一次性命名保持在 Paper Card 中，不建独立概念页，也不建实体页。
- 不因词频创建页面，不静默覆盖矛盾，不自动删除已有页面。
