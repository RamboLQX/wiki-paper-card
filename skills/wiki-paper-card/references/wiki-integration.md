# Wiki Integration Contract

## Target Mapping

| Artifact | Destination |
|---|---|
| Full Sections 01-16 | `wiki/sources/<raw-relative-path>.md` |
| Entity stub (deterministic) | `wiki/entities/<canonical-name>.md` |
| Cross-paper synthesis | `wiki/topics/<topic-name>.md` |

Entity stubs are not link-plan actions: `publish_wiki.py` generates them from the batch digests' `analysis.datasets`, `analysis.models`, and `analysis.metrics` lists. The linker never writes hub actions.

## Plan Boundary

The deterministic publisher reads `link-plan.json` and applies only actions already recorded there.

- `create_topic` / `update_topic`: create or update a cross-paper synthesis page.

Do not invent additional promotions, duplicate aliases, or change unrelated prose.

## Source Page Write

1. Read the source page records from `link-plan.json`.
2. Create missing source directories.
3. Preserve `created` on updates and set `updated` to today.
4. Write `source_sha256` for PDF inputs.
5. Copy all 16 numbered sections in order from the finalized Paper Card.
6. Do not include internal protocol markers, formula reports, evidence coverage lists, or audit artifacts.
7. Keep formulas in the finalized format.

## Entity Stub Write

Entity stubs are generated only by the deterministic publisher:

1. Collect every name from the batch digests' `analysis.datasets`, `analysis.models`, and `analysis.metrics` lists.
2. Normalize each name; merge variants under one page: the shorter raw name becomes the page title, other spellings become aliases. A name resembling an existing page's name or alias appends to that page instead of creating a variant.
3. A new page contains only: frontmatter (`tags: [entity]`, `status: stub`, `sources`, `aliases`), the page title, a fixed note that the page is machine-generated, an `## 别名` section, and an `## 引用来源` section listing the source Paper Cards.
4. An existing page only gains missing aliases and missing source links; its other content is preserved.
5. Re-running the same batch is idempotent: unchanged pages are not rewritten.

Definitions, evidence, and evaluations live in the source Paper Cards; entity stubs do not carry them.

## Existing Entity Page Rules

1. Read the target page before editing.
2. Compare aliases and canonical names.
3. Add only missing aliases and source links.
4. Add the current source report link once.
5. Do not replace or restate existing content.

## Topic Page Write

Create or update a topic page when:

- at least two source pages share the same problem, mechanism, or evidence space;
- the batch plan marks the topic for synthesis;
- an existing topic page contains an open question that a new paper answers or challenges.

Include:

```markdown
## 论文与方法对照

## 关键发现

## 争议与不确定

## 开放问题

## 研究空白与候选方向
```

Do not create a topic page merely because a paper discusses a subject.

The publisher renders grouped or flat comparison records, key findings (共识/单篇主张/分歧), contradictions, open questions, and research gaps from the audited action. On update, new comparison rows are merged into the existing comparison table instead of appending a sub-table.

## Index And Log

`wiki/index.md`:

- add missing page identity only;
- use a one-sentence description for each entry.

`wiki/log.md`:

- append one operation entry for source and entity writes;
- append one batch synthesis entry after topic pages are published;
- do not change earlier entries.

## Idempotency

- Same PDF SHA-256 and unchanged target: no writes.
- Changed PDF: update report while preserving `created`.
- Legacy report without SHA-256: treat as changed and add the fingerprint.
- Re-running the same link plan and cards must not rewrite unchanged pages, entity stubs, index entries, or log entries.
