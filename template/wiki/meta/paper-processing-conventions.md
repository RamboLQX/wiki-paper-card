---
tags: [meta]
created: 2026-08-15
updated: 2026-08-15
status: evergreen
---

# 论文处理约定

## 核心要求

- 论文 PDF 放在 `raw/papers/`，只读。
- 来源报告写入 `wiki/sources/`，路径镜像 raw 相对路径。
- 全文只由每篇一个 processor 读取一次，主对话不载入论文正文、完整卡片或完整摘要。
- 所有 Paper Card 先独立完成，再统一比较批次摘要并生成 link-plan。
- 论文私有术语、组件与一次性命名保留在源页；公共数据集/基准/模型家族/指标写入 digest 的 datasets/models/metrics，实体 stub 由发布器确定性生成，不建概念页。
- topic 页面承担跨论文比较、矛盾、开放问题和研究空白；关键发现、研究空白、开放问题只写有真实价值的条目，没有就留空，不为填满而硬写。
- 公式本体放在 Markdown 表格外，使用 `$$...$$`。
- 索引和日志只增加真实变更。
