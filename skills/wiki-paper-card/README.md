# wiki-paper-card

**状态：Stable**

`wiki-paper-card` 将单篇论文或一个主题目录下的多篇论文整理为可核验的 Paper Card，并按需连接到研究 Wiki。

[返回项目 README](../../README.md)

## 适合处理的任务

- 分析一篇 PDF 或 `nature-reader` source map。
- 批量处理一个研究主题目录。
- 重新生成已有 Paper Card。
- 在满足准入条件时创建或更新跨论文 Topic。
- 将 Paper Card 和 Topic 写成完整、易读的学术段落，以标准脚注保留证据，并将发布器状态移出可见 Markdown。
- 只读检查已安装 Vault，分开升级运行入口与显式迁移旧 Topic。

## 可以直接这样说

```text
使用 wiki-paper-card 以 card-only 模式处理 raw/papers/example.pdf，只需要 Paper Card。

使用 wiki-paper-card 以 wiki-topic 模式处理 raw/papers/<主题名称>/，维护 Topic 但不维护研究空白。

使用 wiki-paper-card 以 wiki-full 模式完整处理 raw/papers/<主题名称>/，包含研究空白维护。

请升级 wiki-paper-card；先只读检查，在我确认范围前不要改写 wiki/。
```

未说明范围时，Agent 会在开始前只询问一次；同一批论文不会逐篇询问。

## 主要产物

- `card-only` 在 `work/` 中交付经过审计的 Paper Card，不写 `wiki/`。
- 两个 Wiki 模式在 `wiki/sources/papers/` 下发布 Paper Card。
- `wiki/topics/` 下满足准入条件的 Topic。
- 更新后的 `wiki/index.md`、知识树和日志。
- `work/` 下的中间报告与审计结果。

所有产物的含义与完整工作流见[工作产物与工作流说明](../../docs/artifacts.md)。

## 处理原则

- Paper Card 用可连续阅读的段落解释研究问题、方法、实验、结论、局限和研究想法，同时保留原文位置与必要的比较表。
- 每篇论文先独立分析并完成检查，再建立跨论文关系。
- `wiki-topic` 保留已有研究空白但不新增、推进、回答、标注或删除它们；`wiki-full` 才执行完整空白维护。
- Topic 需要至少两篇论文共享同一问题、机制或证据空间。
- `raw/` 始终只读，最终知识页面只通过确定性发布流程写入。

完整执行规则见 [`SKILL.md`](SKILL.md)、[工作流契约](references/workflow-contract.md) 和[升级契约](references/upgrade-contract.md)。

知识库问答、信息查证和综述检索使用 [`wiki-shared` 的共享检索协议](../wiki-shared/references/retrieval-protocol.md)。
