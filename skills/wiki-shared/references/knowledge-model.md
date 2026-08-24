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

Create or update a topic page when at least two papers share the same problem, mechanism, or evidence space, or when a single paper directly answers an existing open question.

Research gaps and open questions are snapshots of the current corpus. Record a gap only when it carries a source anchor (which paper's limitation or uncovered setting) and a direction a future paper could advance; if a batch yields no genuine gap, leave the section empty rather than padding it.

When a later paper answers an open question or fills a research gap, the linker marks the item answered (`status: "answered"` with `answered_by` and `answered_pointer`); the publisher moves it to the topic page's archive sections `## 已解决的问题` / `## 已解决的研究空白`, so the open sections and the dashboards always reflect only the currently open items. The answer's substance is recorded as a `key_findings` entry, preserving the field-state history.

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
