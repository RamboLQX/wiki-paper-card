# Wiki Integration Contract

## Target Mapping

| Artifact | Destination |
|---|---|
| Full Sections 01-16 | `wiki/sources/<raw-relative-path>.md` |
| Cross-paper synthesis | `wiki/topics/<topic-name>.md` |

There are no entity pages: public datasets, benchmarks, model families, and metrics stay in the Paper Card's Sections 14-16 as plain text. The linker never writes hub actions.

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

## Topic Page Write

Create or update a topic page when:

- at least two source pages share the same problem, mechanism, or evidence space;
- the batch plan marks the topic for synthesis;
- an existing topic page contains an open question that a new paper answers or challenges.

Include:

```markdown
## 概述

## 综合认识

## 争议与不确定

## 论文与方法对照

## 开放问题

## 研究空白与候选方向
```

Do not create a topic page merely because a paper discusses a subject.

For schema 3.0, the linker writes complete reader-facing prose in `narrative` and keeps `key_findings` / `contradictions` as the evidence ledger. Fixed second-level headings define publisher-owned narrative sections. The publisher derives standard Markdown evidence footnotes and does not render a duplicate finding list. Grouped or flat comparison records remain deterministic tables. On update, new flat comparison rows are merged into the existing comparison table instead of appending a sub-table.

The ingest linker is the sole producer for 概述, 综合认识, 争议与不确定, and 论文与方法对照. Mining plans may update only stable-ID open items and their monotonic source/backlink union. The schema 3.0 audit rejects a mining plan that carries narrative, comparison, finding, contradiction, category, or status fields.

### Resolved Items

Schema 3.0 `open_questions` and `research_gaps` entries carry stable `id`, immutable `origin`, and `status` (`open` default / `answered`). When an action marks an existing ID answered (`answered_by` + `answered_pointer`), the publisher moves that same ID from the open section into the corresponding archive section. IDs, origins, annotations, and the replay fingerprint live in `wiki/meta/topic-state/*.json`, not in the Topic Markdown. Archive sections are rendered only when they have content and are not aggregated into `wiki/meta/research.md` or `wiki/meta/knowledge-tree.md`.

Every schema 3.0 update carries `base_topic_sha256`. All target hashes and source references are checked before any write. A stale target blocks the complete plan. A legacy schema 3.0 Topic with complete managed comments migrates to clean Markdown and a sidecar on its next valid update. A Topic with neither complete legacy comments nor sidecar state rejects the update with `narrative_migration_required`.

## Index And Log

`wiki/index.md`:

- add missing page identity only;
- use a one-sentence description for each entry.

`wiki/log.md`:

- append one operation entry for source writes;
- append one batch synthesis entry after topic pages are published;
- do not change earlier entries.

## Idempotency

- Same PDF SHA-256 and unchanged target: no writes.
- Changed PDF: update report while preserving `created`.
- Legacy report without SHA-256: treat as changed and add the fingerprint.
- Re-running the same link plan and cards must not rewrite unchanged pages, index entries, or log entries.
