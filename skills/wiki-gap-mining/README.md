# wiki-gap-mining

**状态：Beta**

`wiki-gap-mining` 基于已经积累的研究 Wiki，梳理尚未解决的问题、证据不足之处和候选研究方向。

[返回项目 README](../../README.md)

## 适合处理的任务

- 挖掘指定研究主题中的开放问题和研究空白。
- 比较多个主题之间仍未解决的问题。
- 分析整个知识库中的候选研究方向。
- 检查已有问题是否被后续论文回答。

## 可以直接这样说

```text
使用 wiki-gap-mining 挖掘 <主题名称> 中的研究空白与候选方向。

使用 wiki-gap-mining 比较 <主题一> 和 <主题二> 中仍未解决的问题。

使用 wiki-gap-mining 挖掘整个研究 Wiki 中的研究空白与候选方向。
```

## 主要产物

- `work/gap-mining-notes.md`：挖掘 Agent 的工作笔记，用于整理线索。这是中间产物，你不需要读。
- `work/gap-mining-report.md`：面向你的研究空白报告，带来源依据、可检验方向和建议落点。报告末尾的「待确认清单」需要你逐项确认。
- 你确认后，结果才通过确定性发布流程写回 Topic 页的「开放问题」和「研究空白与候选方向」区块，并同步研究仪表盘。

只读报告不确认，知识库不会有任何变化。所有产物的完整解释见[工作产物与工作流说明](../../docs/artifacts.md)。

## 处理原则

- 只分析已经进入 Wiki 的内容，不负责处理新论文。
- 第一阶段只读，不直接修改 `wiki/`。
- 候选研究空白需要现有 Paper Card 或 Topic 提供来源依据。
- 用户逐项确认后，确定性发布流程才会更新 Topic。
- 没有可靠的新空白也是有效结果，不会为了数量补充低质量条目。

完整执行规则见 [`SKILL.md`](SKILL.md) 和[挖掘说明](references/mining-brief.md)。

普通提问、查证和综述检索使用 [`wiki-shared` 的共享检索协议](../wiki-shared/references/retrieval-protocol.md)，不触发本 Skill。
