# wiki-paper-card

**状态：Stable**

`wiki-paper-card` 将单篇论文或一个主题目录下的多篇论文整理为可核验、可连接的研究 Wiki。

[返回项目 README](../../README.md)

## 适合处理的任务

- 分析一篇 PDF 或 `nature-reader` source map。
- 批量处理一个研究主题目录。
- 重新生成已有 Paper Card。
- 在满足准入条件时创建或更新跨论文 Topic。

## 可以直接这样说

```text
使用 wiki-paper-card 处理 raw/papers/example.pdf。

使用 wiki-paper-card 批量处理 raw/papers/<主题名称>/ 下的全部论文。

使用 wiki-paper-card 重新处理 raw/papers/example.pdf。
```

## 主要产物

- `wiki/sources/papers/` 下的 Paper Card。
- `wiki/topics/` 下满足准入条件的 Topic。
- 更新后的 `wiki/index.md`、知识树和日志。
- `work/` 下的中间报告与审计结果。

## 处理原则

- Paper Card 保留研究问题、方法、实验、结论、局限和原文位置。
- 每篇论文先独立分析并完成检查，再建立跨论文关系。
- Topic 需要至少两篇论文共享同一问题、机制或证据空间。
- `raw/` 始终只读，最终知识页面只通过确定性发布流程写入。

完整执行规则见 [`SKILL.md`](SKILL.md) 和[工作流契约](references/workflow-contract.md)。

知识库问答、信息查证和综述检索使用 [`wiki-shared` 的共享检索协议](../wiki-shared/references/retrieval-protocol.md)。
