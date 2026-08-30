# Knowledge Crystallization Model

## Goal

The source Paper Card is the detailed record. Topic pages carry comparison, synthesis, conflicts, and open questions.

Do not create a page just because a term can be extracted from one paper. Create a topic page when doing so makes later papers easier to connect and compare.

## Local Records

Terms, methods, mechanisms, frameworks, and model components stay local to the Paper Card:

- Valuable only inside the current paper: keep in Section 14 or a local table.
- Reusable but not yet cross-paper verified: keep the definition, evidence, and proposed relations in Sections 14-15 of the source Paper Card.

There are no standalone concept pages, no entity pages, and no promotion ladder. Cross-paper synthesis happens on topic pages; the Paper Card keeps the paper-local record.

## Topic Pages

Topic pages are the primary synthesis surface for:

- comparing methods, evidence, models, datasets, and results across papers;
- recording contradictions and unresolved conflicts;
- listing open questions and research gaps;
- proposing discriminating experiments.

Topics also serve as the tree's intermediate signpost nodes: the publisher nests each topic's assigned papers, currently open questions, and research gaps under the topic node in `knowledge-tree.md` (human navigation), and lists the same topics with their one-line index descriptions in `agent-tree.md` (agent retrieval first hop), which is how retrieval prunes by topic before opening pages.

Create or update a topic page when at least two papers share the same problem, mechanism, or evidence space, or when a single paper directly answers an existing open question.

Research gaps and open questions are snapshots of the current corpus. Record a gap only when it carries a source anchor (which paper's limitation or uncovered setting) and a direction a future paper could advance; if a batch yields no genuine gap, leave the section empty rather than padding it.

When a later paper answers an open question or fills a research gap, the linker marks the item answered (`status: "answered"` with `answered_by` and `answered_pointer`); the publisher moves it to the topic page's archive sections `## 已解决的问题` / `## 已解决的研究空白`, so the open sections and the dashboards always reflect only the currently open items. The answer's substance is recorded as a `key_findings` entry, preserving the field-state history.

## Content Placement Map

Each content type has exactly one home section. Writers (linker and miner) place
content by this table, which is the single source of truth for arrangement; do
not invent additional sections:

| 内容类型 | 落点 |
|---|---|
| 论文直接支持的发现 | topic「关键发现」（共识/单篇） |
| 论文承认的局限 | topic 对照表「边界」列 /「争议与不确定」 |
| 跨论文综合判断 | topic「关键发现」（共识） |
| 正式研究空白（边界与做法齐备） | topic「研究空白与候选方向」 |
| 待验证方向（缺边界或做法） | topic「研究空白与候选方向」，带 `[待验证]` 标签 |
| 研究设计备忘录（具体数据/识别策略/失败条件） | 只进 source 页 Section 16 或 `work/` 报告，不进 topic 页、不进 research.md |

Maturity of a gap is its field completeness, not a separate status: an entry
carrying v2 detail fields but lacking both `evidence_boundary` and `experiment`
is a tentative direction; entries with both are formal research gaps. Entries
without any v2 field keep the legacy rendering.

A `category` frontmatter value classifies a topic by research question type
(for example 模型优化 vs 评估框架). It is a single value, optional, orthogonal
to the source-paper domain axis; the category set is small and user-owned.
Newly created topics default to `status: stub`, which means a candidate topic:
only pages supported by later ingest batches are promoted to `draft` /
`evergreen`.

## Edit-Merge Discipline

Topic pages are long-lived; literature keeps arriving. Every topic update is
an edit, not an append:

1. Read the target page's relevant sections before writing.
2. Merge near-duplicates instead of appending: a candidate whose meaning is
   already present is rewritten into the existing entry or dropped as
   "no new content".
3. Add only content that changes what a researcher can do next; a sentence
   that carries no information does not belong in any section.
4. Never double-write one candidate into both `open_questions` and
   `research_gaps`: entries with `source_refs` + `direction` go to
   `research_gaps`; plain reader-facing questions without a direction go to
   `open_questions`.

## Cross-Page Connectivity

Connectivity between sources and topics is expressed as wikilinks inside prose and tables, which Obsidian's backlinks and graph already surface. Contradictions between papers are recorded explicitly in the `## 争议与不确定` section of a topic page.

## Existing Page Updates

Before writing:

1. Read the target page.
2. Verify name disambiguation.
3. Add only facts, sources, and relations that are absent.
4. Do not restate existing content in different words.
5. Add the current source report link once.
6. Preserve existing contradictions; add a new entry instead of overwriting.

## Contradictions

When a new source conflicts with existing knowledge:

1. Keep both positions.
2. Add or update a `## 争议与不确定` section on the topic page.
3. Record the source pointer for each position.
4. State what evidence would resolve the conflict.

## Retirement

- Do not automatically delete pages.
- Legacy `wiki/concepts/` and `wiki/entities/` pages are no longer written or updated by the publisher; mark them `archived` or leave them as read-only references.
- Weak or abandoned nodes become `status: stub` or `archived`.
- Index and log record the state change.
