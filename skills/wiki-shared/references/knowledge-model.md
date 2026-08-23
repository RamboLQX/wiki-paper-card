# Knowledge Crystallization Model

## Goal

The source Paper Card is the detailed record. Topic pages carry comparison, synthesis, conflicts, and open questions. Entity pages are thin deterministic stubs that aggregate which papers use a public artifact.

Do not create a page just because a term can be extracted from one paper. Create a topic page when doing so makes later papers easier to connect and compare.

## Local Records

Terms, methods, mechanisms, frameworks, and model components stay local to the Paper Card:

- Valuable only inside the current paper: keep in Section 14 or a local table.
- Reusable but not yet cross-paper verified: keep the definition, evidence, and proposed relations in Sections 14-15 of the source Paper Card.

There are no standalone concept pages and no promotion ladder. Cross-paper synthesis happens on topic pages; the Paper Card keeps the paper-local record.

## Entity Stubs

Entity pages record public reusable artifacts — datasets, benchmarks, model families, and metrics — whose identity is guaranteed by their publisher. The deterministic `publish_wiki.py` generates and updates them from the batch digests' `analysis.datasets`, `analysis.models`, and `analysis.metrics` lists:

- The publisher normalizes names, merges name variants into one page (the shorter raw name becomes the page title, other spellings become aliases), and appends the current source pages to the `## 引用来源` list.
- An entity stub carries only: frontmatter, the page title, aliases, and source links. Definitions, evidence, and evaluations live in the source Paper Cards.
- Models mentioned only inside one paper's evaluation table without a public identity (for example a one-off checkpoint) stay local and must not be listed under `analysis.models`.

No LLM decides entity pages; the publisher is the only writer. Paper-private methods and components are not entities.

## Topic Pages

Topic pages are the primary synthesis surface for:

- comparing methods, evidence, models, datasets, and results across papers;
- recording contradictions and unresolved conflicts;
- listing open questions and research gaps;
- proposing discriminating experiments.

Create or update a topic page when at least two papers share the same problem, mechanism, or evidence space, or when a single paper directly answers an existing open question.

Research gaps and open questions are snapshots of the current corpus. Record a gap only when it carries a source anchor (which paper's limitation or uncovered setting) and a direction a future paper could advance; if a batch yields no genuine gap, leave the section empty rather than padding it.

## Cross-Page Connectivity

Connectivity between sources, topics, and entities is expressed as wikilinks inside prose and tables, which Obsidian's backlinks and graph already surface. Contradictions between papers are recorded explicitly in the `## 争议与不确定` section of a topic page.

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
- Legacy `wiki/concepts/` pages are no longer written or updated by the publisher; mark them `archived` or leave them as read-only references.
- Weak or abandoned nodes become `status: stub` or `archived`.
- Index and log record the state change.
