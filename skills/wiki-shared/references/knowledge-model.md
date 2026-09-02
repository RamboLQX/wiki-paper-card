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

Topics also serve as the shared tree's intermediate signpost nodes: the publisher nests each topic's assigned papers, currently open questions, and research gaps under the topic node in `knowledge-tree.md`. Readers can inspect the full hierarchy, while retrieval prunes by topic or paper leaf before opening only the selected pages.

Create or update a topic page when at least two papers share a defined problem
space or can support a coherent comparison question with a meaningful
comparison basis, or when a single paper directly answers, challenges, or
materially advances an existing open item. Sharing an umbrella field name,
mechanism family, or evidence modality is not sufficient when no cross-paper
judgment can be made.

A Topic is one stable comparison view, not a partition of a batch or a
container for an entire field. The same paper may belong to several Topics
when it supports independent judgments from different problem, method,
mechanism, measurement, evaluation, or evidence-setting views. These are
discovery prompts, not required categories. There is no target Topic count per
batch.

Prefer a new sibling Topic when adding papers would require broadening an
existing title or overview beyond a coherent comparison view, when the
research object or evidence setting changes the comparison question, or when
metrics and interventions cannot support the same judgment. Repeated caveats
that results are not directly comparable are a boundary warning. A
cross-setting Topic remains valid only when it asks an explicit comparative
question of its own rather than serving as an umbrella index.

Research gaps and open questions are snapshots of the current corpus. The
ingest linker may synthesize a gap only from four inputs: author-stated
limitations, Agent critical observations, unexplained results, and Topic seeds
that support cross-paper comparison. A single-paper proposal or open question
is not a complete gap. Record a gap only when it blocks a concrete judgment,
admits a discriminating study, names a meaningful failure or closure result,
and the current corpus has not already resolved it. If none passes, leave the
section empty.

When a later paper advances a research gap but leaves a decision-relevant boundary, the gap remains open and receives a stable-ID progress record containing the paper, method, result, evidence pointer, and remaining boundary. It stays in the open sections and aggregations with an 已有进展 marker. Only evidence that closes the original judgment boundary may mark it answered. The linker then preserves the gap ID, origin, and progress history and supplies the answering papers, evidence pointer, resolution method, result summary, and scope. The publisher moves the same ID to the detailed archive; the answer's substance also enters the structured finding ledger and complete reader-facing narrative.

## Content Placement Map

Each content type has exactly one home section. Writers (linker and miner) place
content by this table, which is the single source of truth for arrangement; do
not invent additional sections:

| 内容类型 | 落点 |
|---|---|
| 论文直接支持的发现 | link-plan `key_findings` 证据台账，并纳入 topic「综合认识」 |
| 论文承认的局限 | topic 对照表「边界」列 /「争议与不确定」 |
| 跨论文综合判断 | topic「综合认识」段落，引用 `key_findings` 台账 ID |
| 正式研究空白（边界与做法齐备） | topic「研究空白与候选方向」 |
| 待验证方向（缺边界或做法） | topic「研究空白与候选方向」，带 `[待验证]` 标签 |
| 研究设计备忘录（具体数据/识别策略/失败条件） | 只进 source 页 Section 16 或 `work/` 报告，不进 topic 页、不进 research.md |

Maturity of a gap is its field completeness, not a separate status: an entry
carrying structured detail but lacking both `evidence_boundary` and
`experiment` is a tentative direction; entries with both are formal research
gaps. These fields remain machine state. New gaps render their one- or
two-paragraph `reader_narrative`; older entries without it keep the legacy
labelled rendering.

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
5. Ingest rewrites the complete publisher-owned narrative sections from all
   current evidence; mining never writes narrative or comparison content.
6. Both producers address shared open items by stable ID. Text fragments are
   legacy compatibility only.
7. Every schema 3.0 update binds to `base_topic_sha256`; a stale plan is
   rejected and regenerated from the latest page.

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
