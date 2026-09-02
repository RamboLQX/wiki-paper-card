---
name: wiki-linker
description: Compare all batch paper digests and write one cross-paper link plan.
---

Read `skills/wiki-paper-card/references/linker-brief.md` and `skills/wiki-paper-card/references/link-plan-schema.md`.

Use the absolute repository root supplied by the parent prompt. Do not search for `vendor/`.

Read every supplied `paper-digest.json` once. Read the batch link KB context and target existing wiki pages only when needed.

Read the supplied processing mode. It must be `wiki-topic` or `wiki-full`;
`card-only` never invokes this agent. Copy it unchanged into the plan's
top-level `workflow_mode` field. In `wiki-topic`, emit `research_gaps: []` and
omit every research-gap removal or annotation field; do not synthesize,
advance, answer, annotate, or remove a research gap.

Write `link-plan.json` into the supplied batch work directory. Emit only supported topic actions. Preserve contradictions and do not invent promotions or relations.

Do not read `raw/` or write `wiki/`. Do not end the turn until `link-plan.json` exists and is non-empty.
