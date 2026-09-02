---
name: wiki-processor
description: Read one source bundle and write the mode-required Paper Card outputs.
---

Read `skills/wiki-paper-card/references/processor-brief.md` and `skills/wiki-paper-card/references/paper-digest-schema.md`. Follow the Required Reads section in the processor brief, including the pinned upstream router and its manifest.

Process only the supplied paper. Do not accept a different paper in this subagent session.

Use the absolute repository root supplied by the parent prompt. Do not search for `vendor/`.

Read the supplied `source_bundle.json` once, and read `kb-context.md` when present.

Read the processing mode supplied by the parent. Always write `paper-card.md`
into the supplied work directory. Write `paper-digest.json` only in
`wiki-topic` or `wiki-full`; in `card-only`, do not generate it. Use `$$...$$`
outside tables for displayed formulas. Do not add wiki actions or a visible
evidence coverage list. Do not run audit scripts.

Do not read `raw/` or write `wiki/`.

If a source-bundle read is truncated, read only the missing page range and continue. Do not end the turn until every output required by the selected mode exists and is non-empty.
