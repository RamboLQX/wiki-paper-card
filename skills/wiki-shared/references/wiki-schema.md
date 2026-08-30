# LLM Wiki Schema

## Directory Contract

```text
raw/            # User-owned source material, read only
wiki/
  topics/       # Cross-paper synthesis, comparisons, open questions
  sources/      # Source reports, mirroring raw/ subdirectories
  meta/         # Indexes, logs, dashboards, conventions
  index.md
  log.md
```

The agent never modifies `raw/`.

Legacy `wiki/entities/` and `wiki/concepts/` directories from older installs are ignored by the publisher: it never writes or lists their pages. They may be marked `archived` or kept as read-only references.

`wiki/meta/research.md` is the machine-maintained research dashboard. The publisher renders it deterministically after each publish: open questions and research gaps aggregated from topic pages, grouped by domain (first directory under `wiki/sources/papers/`). It is the question-type-first view of the same topic-page data that the knowledge tree shows domain-first, so the two documents intentionally share the same open-item bullets. It aggregates only *currently open* items; answered items live in the topic pages' archive sections. When no open item remains, the dashboard shows a placeholder instead of stale content.

`wiki/meta/knowledge-tree.md` is the machine-maintained navigation tree for LLM retrieval. The publisher rebuilds it deterministically after each publish, grouped by domain (first directory under `wiki/sources/papers/`), with per-node summaries and per-domain open questions and research gaps aggregated from topic pages (same open-item bullets as the dashboard, open-only). Retrieval follows the two-mode protocol in `retrieval-protocol.md` (lookup pruning / survey expansion).

## Frontmatter

Every wiki page contains:

```yaml
---
tags: [topic]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
aliases: []
status: stub
---
```

Valid page tags:

```text
topic
source
meta
```

Legacy `concept` and `entity` pages from older installs are no longer written or updated; the publisher leaves them untouched.

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

Sections 14-16 keep local and reusable candidates. They use wiki-links to topic pages when such a page exists; public datasets, benchmarks, model families, and metrics stay as plain text (there are no entity pages):

```markdown
## 14. 学到的知识

- LLaVA 1.5 — 本文提供的一个增量证据
- 本地候选：另一个可复用但尚未跨论文印证的术语

## 15. 与已有知识连接

| 类型 | 对象 | 证据 | 结论 |
|---|---|---|---|
| supports | [[某主题]] | [Paper: Figure 3] | 本文结果与已有结论一致 |
| proposed | 候选对象 | [Paper: PDF p. 5] | 暂留本地，不建独立页面 |

## 16. 研究想法

- 候选假设：...
- 与论文差异：...
- 验证方式：...
- 可能失败：...
```

The deterministic publisher appends a trailing `## 关联页面` section to each
source page, listing basename wikilinks to every topic that cites the
page. This keeps the graph bidirectional after batch linking.

## Topic Page

Topic pages are the primary synthesis surface. They compare sources and record open questions.

Topic frontmatter may carry an optional single-value `category` (for example
`"模型优化"` or `"评估框架"`), written by the publisher when a topic action
provides it. The category classifies the topic by research question type and
is orthogonal to the source-paper domain axis; the knowledge tree renders a
category-first topic view from it. Omit it for uncategorized topics.

```markdown
# 页面名

## 概述

## 论文与方法对照

| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |
|---|---|---|---|---|---|---|

## 关键发现

## 争议与不确定

## 开放问题

## 研究空白与候选方向

## 已解决的问题

## 已解决的研究空白
```

The `## 关键发现` section is rendered from the plan's `key_findings`, each marked 共识 / 单篇主张 / 分歧 with source pointers.

The open `## 开放问题` and `## 研究空白与候选方向` sections hold only items still open. When a later paper answers an open item, the publisher removes it from the open section and appends it to the archive sections `## 已解决的问题` / `## 已解决的研究空白` (rendered only when they have content, never aggregated into the dashboards).

### Research Gap Rendering

A gap renders as a main bullet plus optional indented detail sub-bullets; only
fields that were written appear:

```markdown
- <gap 描述>（来源：[[论文A]]；可检验方向：…；承接：…）
  - 为什么值得做：…
  - 现有方法卡在哪：…
  - 怎么检验：…
  - 做到什么算成：…
  - 可能行不通：…
  - 优先级：高/中/低 + 理由
```

An entry that carries v2 detail fields but lacks both `现有方法卡在哪` and
`怎么检验` is a tentative direction and its main line gains a `[待验证]` tag.
Entries without any detail field render as the legacy single line. The main
line stays the compact summary; the dashboards aggregate only main lines,
sorted by priority (高 < 中 < 低 < unmarked).

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
