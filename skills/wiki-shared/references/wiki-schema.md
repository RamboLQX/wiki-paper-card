# LLM Wiki Schema

## Directory Contract

```text
raw/            # User-owned source material, read only
wiki/
  entities/     # Long-lived organizations, products, methods, resources
  concepts/     # Transferable theories, frameworks, mechanisms, terms
  topics/       # Cross-paper synthesis, comparisons, open questions
  sources/      # Source reports, mirroring raw/ subdirectories
  meta/         # Indexes, logs, dashboards, conventions
  index.md
  log.md
```

The agent never modifies `raw/`.

`wiki/meta/research.md` is the machine-maintained research dashboard. The publisher renders it deterministically after each publish: open questions and research gaps aggregated from topic pages, plus the pending L1 candidate ledger, all grouped by domain (first directory under `wiki/sources/papers/`). A legacy `wiki/meta/candidates.md` (stem-based L1 ledger) is migrated into `research.md` on the first publish with the current publisher and is no longer written afterwards; `build_kb_context.py` reads `research.md` first and falls back to the legacy file.

`wiki/meta/knowledge-tree.md` is the machine-maintained navigation tree for LLM retrieval. The publisher rebuilds it deterministically after each publish, grouped by domain (first directory under `wiki/sources/papers/`), with per-node summaries, hub aliases, and per-domain open questions and research gaps aggregated from topic pages. Retrieval follows the two-mode protocol in `retrieval-protocol.md` (lookup pruning / survey expansion).

## Frontmatter

Every wiki page contains:

```yaml
---
tags: [entity]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
aliases: []
status: stub
---
```

Valid page tags:

```text
entity
concept
topic
source
meta
```

Paper source pages use:

```yaml
---
tags: [source, paper]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_sha256: ""
arxiv: ""
authors: ""
published: ""
venue: ""
status: stub
---
```

Status values:

```text
stub
draft
evergreen
archived
```

## Source Page

The source page is the primary paper entry and contains all Sections 01-16 in order.

Formulas are written outside Markdown tables. Use `$$...$$` for a displayed formula and `$...$` only for a short inline reference outside a table. Escape a literal pipe inside table math as `\|`.

Sections 14-16 keep local and reusable candidates. They use wiki-links to cross-paper hubs when a hub page exists:

```markdown
## 14. 学到的知识

- [[某概念|某概念]] — 本文提供的一个增量证据
- L1 候选：另一个可复用但尚未被第二篇论文印证的术语

## 15. 与已有知识连接

| 类型 | 对象 | 证据 | 结论 |
|---|---|---|---|
| supports | [[某概念]] | [Paper: Figure 3] | 本文结果与已有结论一致 |
| proposed | 候选对象 | [Paper: PDF p. 5] | 尚未建立跨论文页面，暂留本地 |

## 16. 研究想法

- 候选假设：...
- 与论文差异：...
- 验证方式：...
- 可能失败：...
```

The deterministic publisher appends a trailing `## 关联页面` section to each
source page, listing basename wikilinks to every hub and topic that cites the
page. This keeps the graph bidirectional after batch linking.

## Entity Page

Entity and concept pages are thin cross-paper hubs. Do not copy a Paper Card into them.

```markdown
# 页面名

一句话定义。

## 别名

## 证据

| 来源 | 断言 | 证据 | confidence |
|---|---|---|---|

## 关系

| 类型 | 对象 | 证据 | 说明 |
|---|---|---|---|

## 争议与矛盾

## 开放问题

## 引用来源
```

## Concept Page

```markdown
# 页面名

一句话定义。

## 别名

## 证据

| 来源 | 断言 | 证据 | confidence |
|---|---|---|---|

## 关系

| 类型 | 对象 | 证据 | 说明 |
|---|---|---|---|

## 争议与矛盾

## 开放问题

## 引用来源
```

## Topic Page

Topic pages are the primary synthesis surface. They compare sources and record open questions.

```markdown
# 页面名

## 概述

## 论文与方法对照

| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 |
|---|---|---|---|---|

## 关键发现

## 争议与不确定

## 相关实体与概念

## 开放问题

## 研究空白与候选方向
```

The `## 关键发现` section is rendered from the plan's `key_findings`, each marked 共识 / 单篇主张 / 分歧 with source pointers.

## Index And Log

`wiki/index.md` identifies entries by page identity. The deterministic publisher adds a page only when it is absent.

`wiki/log.md` is append-only and records:

```markdown
## [YYYY-MM-DD] ingest | 论文标题
- 新建：...
- 更新：...
- 摘要：...
```

The deterministic publisher does not rewrite historical log entries.

## Naming And Aliases

- Use the source's most common canonical name.
- Put variants in `aliases`, not separate pages.
- Do not create a page for every named model, dataset, metric, or module.
- A paper-specific internal name remains local unless it becomes an L2 cross-paper hub.
