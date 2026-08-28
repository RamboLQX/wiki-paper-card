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

1. Read `wiki/meta/knowledge-tree.md` and `wiki/meta/research.md` to get
   the currently open questions and gaps in scope.
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

- **Empty is a valid result.** Every candidate must change what a reader
  does next. Report "no genuine new gap" instead of padding.
- **Every candidate gap carries**: `gap` (the gap and its origin),
  `source_refs` (the existing papers it traces to), `direction` (what
  observation would move it forward), and a suggested landing page (an
  existing topic, or a new cross-group topic).
- **Three patterns to look for**, in order of value:
  1. cross-group common gaps: the same missing setting or benchmark shows
     up across several domains;
  2. cross-group coverage holes: a limitation recorded in one domain is not
     addressed or even mentioned by the methods of another domain that
     could address it;
  3. continuity: resolving a gap in one group exposes a new gap (the
     archive sections are the input here).
- **Record only the 2-3 candidates that most affect decisions.** More may
  be recorded only when the user asks for an exhaustive list.
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

## 当前开放清单（来自 research.md，范围内）

## 候选研究空白

- 候选：<gap>
  - 来源：<wikilinks + evidence pointers>
  - 可检验方向：<direction>
  - 建议落点：<existing topic page, or 新建 topic: name>

## 跨组已解决关系

- <gap in domain A> — 已被 <paper> 解决（证据指针）；建议标记 answered 并归档

## 已解决轨迹

- <domain>: 哪些空白被填补、由谁、暴露的新问题

## 未发现新空白的部分

- <domain list, when applicable>
```

## Link Plan Contract (Write-Back)

After the user confirms which candidates to adopt, write one
`link-plan.json`:

- `schema_version: "2.0"`, `purpose: "mining"`.
- `batch.source_pages` is empty; `batch.label` names the run
  (for example `"gap mining 2026-08"`).
- One `update_topic` action per confirmed candidate on an existing topic:
  `papers` lists the existing supporting source pages; the candidate goes
  into `open_questions` or `research_gaps` (objects with
  `source_refs`/`direction`/`continuity`, `status: "open"`).
- Cross-group resolutions become `status: "answered"` entries with
  `answered_by` and `answered_pointer` (the publisher archives them).
- A candidate with no fitting topic may `create_topic` when at least two
  existing source pages support it; `papers` lists those existing pages.
- Before any write, the publisher verifies that every page listed in `papers`
  exists under `wiki/sources/`; a missing or invalid page blocks the complete
  mining publish instead of silently skipping its backlink.
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
