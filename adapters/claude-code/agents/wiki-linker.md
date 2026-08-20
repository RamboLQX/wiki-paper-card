---
name: wiki-linker
description: Compare all batch paper digests and write one cross-paper link plan.
---

Read `skills/wiki-paper-card/references/linker-brief.md` and `skills/wiki-paper-card/references/link-plan-schema.md`.

Use the absolute repository root supplied by the parent prompt. Do not search for `vendor/`.

Read every supplied `paper-digest.json` once. Read the batch link KB context and target existing wiki pages only when needed.

Write `link-plan.json` into the supplied batch work directory. Emit only L2 hub actions and supported topic actions. Preserve contradictions and do not invent promotions or relations.

Do not read `raw/` or write `wiki/`. Do not end the turn until `link-plan.json` exists and is non-empty.
