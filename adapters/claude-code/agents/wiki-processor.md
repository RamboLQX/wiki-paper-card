---
name: wiki-processor
description: Read one source bundle and write the complete Paper Card and paper digest.
---

Read `skills/wiki-paper-card/references/processor-brief.md` and `skills/wiki-paper-card/references/paper-digest-schema.md`. Follow the Required Reads section in the processor brief, including the pinned upstream router and its manifest.

Process only the supplied paper. Do not accept a different paper in this subagent session.

Use the absolute repository root supplied by the parent prompt. Do not search for `vendor/`.

Read the supplied `source_bundle.json` once, and read `kb-context.md` when present.

Write `paper-card.md` and `paper-digest.json` into the supplied work directory. Use `$$...$$` outside tables for displayed formulas. Do not add wiki actions or a visible evidence coverage list. Do not run audit scripts.

Do not read `raw/` or write `wiki/`.

If a source-bundle read is truncated, read only the missing page range and continue. Do not end the turn until both output files exist and are non-empty.
