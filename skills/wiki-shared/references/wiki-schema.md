# LLM Wiki Schema

## Directory Contract

```text
raw/            # User-owned source material, read only
wiki/
  entities/     # Deterministic stubs for public datasets, benchmarks, model families, metrics
  topics/       # Cross-paper synthesis, comparisons, open questions
  sources/      # Source reports, mirroring raw/ subdirectories
  meta/         # Indexes, logs, dashboards, conventions
  index.md
  log.md
```

The agent never modifies `raw/`.

`wiki/meta/research.md` is the machine-maintained research dashboard. The publisher renders it deterministically after each publish: open questions and research gaps aggregated from topic pages, grouped by domain (first directory under `wiki/sources/papers/`).

`wiki/meta/knowledge-tree.md` is the machine-maintained navigation tree for LLM retrieval. The publisher rebuilds it deterministically after each publish, grouped by domain (first directory under `wiki/sources/papers/`), with per-node summaries, entity aliases, and per-domain open questions and research gaps aggregated from topic pages. Retrieval follows the two-mode protocol in `retrieval-protocol.md` (lookup pruning / survey expansion).

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
topic
source
meta
```

Legacy `concept` pages from older installs are no longer written or updated; the publisher leaves them untouched.

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

Sections 14-16 keep local and reusable candidates. They use wiki-links to topic and entity pages when such a page exists:

```markdown
## 14. 学到的知识

- [[某实体|某实体]] — 本文提供的一个增量证据
- 本地候选：另一个可复用但尚未跨论文印证的术语

## 15. 与已有知识连接

| 类型 | 对象 | 证据 | 结论 |
|---|---|---|---|
| supports | [[某实体]] | [Paper: Figure 3] | 本文结果与已有结论一致 |
| proposed | 候选对象 | [Paper: PDF p. 5] | 暂留本地，不建独立页面 |

## 16. 研究想法

- 候选假设：...
- 与论文差异：...
- 验证方式：...
- 可能失败：...
```

The deterministic publisher appends a trailing `## 关联页面` section to each
source page, listing basename wikilinks to every topic and entity that cites the
page. This keeps the graph bidirectional after batch linking.

## Entity Page

Entity pages are thin deterministic stubs written only by `publish_wiki.py`. They aggregate which source pages use a public artifact. Do not copy a Paper Card into them, and do not create them by hand.

```markdown
# 页面名

> 本页由 publish_wiki.py 确定性生成，只聚合引用本实体的论文；定义与评价见各来源论文页。

## 别名

## 引用来源

- [[论文A|论文标题A]]
- [[论文B|论文标题B]]
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

## 相关实体

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
- A paper-specific internal name remains local in the Paper Card.
