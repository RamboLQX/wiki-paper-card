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

`wiki/meta/research.md` is the machine-maintained research dashboard. The publisher renders it deterministically after each publish: open questions and research gaps aggregated from topic pages, grouped by domain (first directory under `wiki/sources/papers/`). It is the question-type-first view of the same topic-page data that the knowledge tree shows topic-nested, so the two documents share the same open items. It aggregates only *currently open* items; answered items live in the topic pages' archive sections. When no open item remains, the dashboard shows a placeholder instead of stale content.

`wiki/meta/knowledge-tree.md` is the machine-maintained tree shared by readers and LLM retrieval. The publisher rebuilds it deterministically after each publish: topic-first — each domain groups its topics as signpost nodes (one-line index description), with the topic's assigned papers, currently open questions, and research gaps nested under each topic; papers assigned to no topic land in the per-domain unassigned group; a category-first topic view follows. It aggregates only *currently open* items; answered items live in the topic pages' archive sections. Retrieval remains progressive: match the hierarchy or a paper leaf first, then open only the selected branch and page per `retrieval-protocol.md`.

Legacy Vaults may still contain `wiki/meta/agent-tree.md`. Current publishers neither read nor update it; after upgrading, users may safely delete that obsolete generated file.

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
category-first topic view from it. Omit it for uncategorized topics. The
category set is small and user-owned: the publisher groups whatever values
exist in frontmatter and never proposes categories itself. A recommended
starting set (per-vault, not enforced): 评测基准与数据集 / 消解与干预方法 /
行为规律 / 机制解释 / 多模态冲突 / 跨域迁移与统一度量 / 综述与元评估 /
领域应用.

Schema 3.0 keeps publisher state outside the reader-facing page. Each Topic has
a JSON sidecar under `wiki/meta/topic-state/` that mirrors its relative path.
The sidecar stores the last action fingerprint, stable open-item IDs and
origins, and gap annotations. It is application state, not research content.

```markdown
# 页面名

## 概述

<2-3 complete reader-facing paragraphs with Markdown footnote references>

## 综合认识

### <claim-led heading>
<cross-paper relationship paragraph>

<comparability, boundary, alternative explanation, and implication paragraph>

## 争议与不确定

### <disputed question>
<positions, boundary, and discriminating evidence>

## 证据注释

[^topic-evidence-1]: [[source page]] [Paper: precise pointer].

## 论文与方法对照

| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |
|---|---|---|---|---|---|---|

## 开放问题

## 研究空白与候选方向

## 已解决的问题

## 已解决的研究空白
```

The `## 概述` opens the page with two or three complete paragraphs written per the
shared [writing guide](writing-guide.md). It defines the problem and value,
then states the current field position and its main boundary. `## 综合认识`
contains three to five claim-led subsections when a mature Topic has enough
evidence. Each subsection normally separates the cross-paper relationship from
comparability, limitations, alternative explanations, and research implications.

Schema 3.0 `key_findings` and `contradictions` remain in the link plan as the
evidence ledger. Narrative paragraphs reference their stable IDs, and the
publisher renders standard Markdown footnote references and definitions. It
never duplicates the ledger as a `## 关键发现` bullet list.

Fixed second-level headings define the publisher-owned sections. Ingest
replaces their bodies; mining is read-only for narrative and comparison
content. Empty controversy and evidence-note sections are omitted. Existing
schema 3.0 pages that still contain legacy managed comments migrate to clean
Markdown and a sidecar on their next valid update. A page with neither legacy
markers nor a valid sidecar fails with `narrative_migration_required`; no
implicit whole-vault migration exists.

The open `## 开放问题` and `## 研究空白与候选方向` sections hold only items still open. Schema 3.0 stores each item's stable ID and immutable origin in the Topic sidecar. Research-gap `status` expresses closure only: partial advances remain open and are stored as stable-ID `progress_updates` with their sources, method, result, pointer, and remaining boundary. Topic prose renders the full history; dashboard and tree aggregation keep the gap visible with an `[已有进展]` marker. When an item is answered, the publisher moves the same ID into the archive and excludes it from both aggregations.

When no independent open question remains, the publisher keeps the `## 开放问题` heading and renders a plain explanatory placeholder. The placeholder is not a list item, is never aggregated into the dashboard or knowledge tree, and is replaced automatically when a real open question is added. Questions with a concrete direction remain research gaps only; the placeholder does not relax that deduplication rule.

### Research Gap Rendering

A schema 3.0 gap renders as a heading plus reader-facing prose. Only supported
fields appear:

```markdown
### <gap 描述>

**为什么值得做。** ... **现有证据边界。** ... 这一判断来自 [[论文A]]。

**推进方向。** ... **验证方式。** ... **成功条件。** ...
**可能失败。** ... **后续承接。** ... **优先级。** 高/中/低。

**已有进展 1。** [[论文B]] 提供了新的推进证据。 **采用方法。** ...
**取得结果。** ... **证据位置。** [Paper: PDF p. X]

**仍未解决。** ...
```

Every open gap carries `significance`; the link-plan audit rejects an open gap
without it. An entry with detail fields but without both `evidence_boundary`
and `experiment` is a tentative direction and its heading gains `[待验证]`.
Dashboards use the sidecar's compact `gap` and `priority` fields rather than
parsing or duplicating the visible prose.

An answered schema 3.0 gap renders under `## 已解决的研究空白` with its
answering paper, `resolution_method`, `resolution_summary`, `resolution_scope`,
and `answered_pointer`. Older sidecar entries without these additive fields
remain readable using the fields already present; no bulk Vault migration is
performed.

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
