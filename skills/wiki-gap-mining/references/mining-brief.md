# Mining Brief

This brief defines the gap-mining agent (miner) contract for
`wiki-gap-mining`.

## Required Reads

Before mining, read completely:

1. [The retrieval protocol](../../wiki-shared/references/retrieval-protocol.md).
2. [The wiki schema](../../wiki-shared/references/wiki-schema.md).
3. [The local knowledge model](../../wiki-shared/references/knowledge-model.md).
4. [The link plan schema](../../wiki-paper-card/references/link-plan-schema.md)
   and [the wiki integration contract](../../wiki-paper-card/references/wiki-integration.md).

## Inputs

The parent prompt supplies:

```text
scope: domain names or "all"
wiki root
work directory (for notes, report, and link plan)
```

The miner reads only existing wiki pages, the two meta indexes, and
targeted source-page sections. It never reads `raw/` or full paper text,
never writes `wiki/`, and never returns paper text to the parent agent.

## Read Plan

Follow the survey discipline of the retrieval protocol:

1. Read `wiki/meta/agent-tree.md` (fallback: `wiki/meta/knowledge-tree.md`)
   and `wiki/meta/research.md` to get the currently open questions and gaps
   in scope.
2. Enumerate the scoped topic pages: topics whose `sources` frontmatter
   intersects the selected domains (cross-domain topics included when any
   source is inside).
3. Read each scoped topic page completely, including the archive sections
   `## 已解决的问题` and `## 已解决的研究空白`.
4. Drill into a source-page section only to verify an evidence pointer you
   will reuse.
5. Keep intermediate notes in `work/gap-mining-notes.md`.

## Mining Discipline

The value discipline from the linker brief applies with a wider lens:

- **Placement before padding.** Every candidate must earn its place: it
  tells a researcher something they need to know and lands in the one
  section that owns that content type (see the Content Placement Map in
  `knowledge-model.md`). Report "no genuine new gap" instead of padding.
- **Every candidate gap carries**: `gap` (the gap and its origin),
  `source_refs` (the existing papers it traces to), `direction` (what
  observation would move it forward), a suggested landing page (an
  existing topic, or a new cross-group topic), and the v2 detail fields —
  `significance`, `evidence_boundary`, `experiment`, `success_criterion`,
  `risk`, and `priority` (高/中/低) — filled from evidence already in the
  wiki. A candidate missing both `evidence_boundary` and `experiment` is a
  tentative direction and is reported as such.
- **Three patterns to look for**, in order of value:
  1. cross-group common gaps: the same missing setting or benchmark shows
     up across several domains;
  2. cross-group coverage holes: a limitation recorded in one domain is not
     addressed or even mentioned by the methods of another domain that
     could address it;
  3. continuity: resolving a gap in one group exposes a new gap (the
     archive sections are the input here).
- **Merge similar candidates instead of multiplying them.** Candidates that
  converge on the same missing setting become one entry with multiple
  `source_refs`, never one entry per group.
- **Record only the 2-3 candidates that most affect decisions.** More may
  be recorded only when the user asks for an exhaustive list.
- **Grade every candidate** into one of: (a) 已有 topic 的补充空白, (b)
  待验证方向 (tentative, stays tagged), (c) 候选新 topic, (d) 仅保留在报告.
  Formal topic creation is the exception, not the default: a candidate may
  become a new topic only with explicit user confirmation, and such a page
  stays `status: stub` (candidate topic) until later ingest batches
  substantiate it. Never rely on two papers merely mentioning similar
  future ideas.
- **One candidate, one home section.** A candidate with `source_refs` and a
  `direction` goes to `research_gaps`; a plain reader-facing question
  without a direction goes to `open_questions`. Never double-write.
- Do not invent findings, pages, or pointers. Every claim traces to pages
  and evidence pointers already in the wiki.

## Resolved-Item Synthesis

The archive sections are first-class mining input, not dead storage:

1. Collect all `## 已解决的问题` and `## 已解决的研究空白` entries in scope.
2. In the report, summarize the resolved trail per scope: which gaps were
   filled, by which papers, and which new questions the resolutions exposed.
3. When the mining finds that a gap recorded in one group was actually
   resolved by another group, mark that relationship in the report and, if
   the user confirms write-back, emit the entry as
   `status: "answered"` with `answered_by` naming the resolving papers.
4. The resolved trail itself stays in the report; it is not written back
   to wiki pages (the topic archive sections already hold the entries).

## Report Contract

`work/gap-mining-report.md`:

```markdown
# 研究空白挖掘报告

## 范围与日期

## Top 空白速览

1. <gap 一句话> — 为什么值钱：<significance 一句话> — 怎么做：<direction>

## 当前开放清单（来自 research.md，范围内）

## 候选研究空白

- 候选：<gap>
  - 来源：<wikilinks + evidence pointers>
  - 为什么值得做：<significance>
  - 现有方法卡在哪：<evidence_boundary>
  - 怎么检验：<experiment>
  - 做到什么算成：<success_criterion>
  - 可能行不通：<risk>
  - 优先级：<高/中/低 + 理由>
  - 可检验方向：<direction>
  - 建议落点：<existing topic page, or 新建 topic: name>

## 候选分级

- <candidate> — 分级：<补充空白 / 待验证方向 / 候选新 topic / 仅保留在报告>

## 跨组已解决关系

- <gap in domain A> — 已被 <paper> 解决（证据指针）；建议标记 answered 并归档

## 已解决轨迹

- <domain>: 哪些空白被填补、由谁、暴露的新问题

## 未发现新空白的部分

- <domain list, when applicable>

## 待确认清单

- 候选 A：采用？[是/否] 落点：[现有 topic X / 新建候选 topic / 仅留在报告]
  知识状态：[正式空白 / 待验证方向] 写入：[research_gaps]
```

The candidate fields keep the exact names of the link-plan `research_gaps`
fields so the Phase B translation is mechanical — the miner never rewrites
candidate text while producing the plan. The Top 速览 lists candidates in
priority order (高 < 中 < 低 < unmarked). Candidates marked 仅保留在报告
produce no page change.

## Link Plan Contract (Write-Back)

After the user confirms candidates via the 待确认清单, write one
`link-plan.json` that reflects exactly the confirmed choices:

- `schema_version: "2.0"`, `purpose: "mining"`.
- `batch.source_pages` is empty; `batch.label` names the run
  (for example `"gap mining 2026-08"`).
- **Mining write-back allows only three kinds of change**: adding
  `open_questions` / `research_gaps` entries to an existing topic; marking
  cross-group resolved items `status: "answered"` (the publisher archives
  them); and a `create_topic` for a candidate the user explicitly confirmed
  as a new candidate topic. The miner never emits `comparisons`,
  `key_findings`, or `contradictions` in a mining plan, and never touches
  概述 or 论文与方法对照 — those belong to the ingest linker only.
- One `update_topic` action per confirmed candidate on an existing topic:
  `papers` lists the existing supporting source pages; the candidate goes
  into `open_questions` or `research_gaps` (objects with
  `source_refs`/`direction`/`continuity`, `status: "open"`, plus the v2
  detail fields from the report, verbatim).
- Cross-group resolutions become `status: "answered"` entries with
  `answered_by` and `answered_pointer` (the publisher archives them).
- A `create_topic` requires at least two existing source pages that share
  the same problem, mechanism, or evidence space, and the user's explicit
  confirmation; `papers` lists those existing pages. Such pages stay
  `status: stub` (candidate topics). A `category` may be given only from
  the existing user-owned set; proposing a new category requires user
  confirmation.
- **Semantic dedup before writing**: read the target topic page's relevant
  sections; a candidate whose meaning is already present is rewritten into
  the existing entry or dropped as "no new content" instead of appended.
  Express these edits deterministically through `remove_open_questions` /
  `remove_research_gaps` (text fragments of the entries to drop) and
  `annotate_research_gaps` (`match` + `note`, for cross-referencing the
  same gap recorded on another topic).
- Before any write, the publisher verifies that every page listed in `papers`,
  in a gap's `source_refs`, or in `answered_by` exists under `wiki/sources/`; a
  missing or invalid page blocks the complete mining publish instead of
  silently skipping its backlink.
- The miner writes the plan file only; `audit_link_plan.py` and
  `publish_wiki.py` perform the writes.

## Return Protocol

Return only:

```text
status
report path
link-plan path (when write-back was confirmed)
number of update_topic / create_topic actions
```

A report without a confirmed write-back is a complete Phase A result.
