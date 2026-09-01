# Linker Brief

This brief defines the batch-level `wiki-linker` subagent contract.

## Required Reads

Before linking, read completely:

1. [The link plan schema](link-plan-schema.md).
2. [The local knowledge model](../../wiki-shared/references/knowledge-model.md).
3. [The wiki integration contract](wiki-integration.md).
4. [The shared wiki schema](../../wiki-shared/references/wiki-schema.md).
5. [The writing guide](../../wiki-shared/references/writing-guide.md).

## Role

After every paper card and digest in the current batch passes its audits, read all digests once and produce:

```text
link-plan.json
```

The linker does not read `raw/`, does not write `wiki/`, and does not return paper text or full Paper Cards to the parent agent.

The knowledge model has no entity or concept pages. The linker must not emit hub actions or ask the publisher to create pages from the digests' dataset, model, or metric lists.

## Inputs

The parent prompt supplies:

```text
all paper-digest.json paths
the corresponding final paper-card.md paths
the batch link KB context
the batch work directory
the wiki root
```

Prefer the digests for context. A final card may be read only for a specific ambiguous section named by the linker.

## Link Decisions

- Compare candidate identity, definitions, methods, evidence, contradictions, and open questions across all batch papers.
- Compare batch digests with the existing wiki context.
- Emit only `create_topic` or `update_topic` actions.
- `create_topic` requires at least two papers sharing the same problem, mechanism, or evidence space. Two papers that merely mention similar future-work ideas at an abstract level — different network objects, outcome variables, or data sources — do not qualify; record the shared direction as a research gap on an existing topic instead. A new topic defaults to `status: stub` (a candidate topic until later batches substantiate it).
- Assign the topic a `category` only from the existing small user-owned set; proposing a new category requires user confirmation. Leave it out when no category fits.
- Emit schema 3.0 `key_findings` as the evidence ledger for the narrative. Every finding has a stable ID, `consensus` / `single` / `conflict`, source-bound pointers, and a claim that changes the reader's field-state judgment.
- Give every contradiction with two positions a `resolving_evidence` naming the evidence or benchmark that would settle it.
- Never use mention frequency as a promotion signal.
- Preserve contradictions instead of merging them away.
- Do not invent topics, aliases, or relations absent from the digests and existing pages.

## Value And Placement Discipline

- **Placement before padding**: every `key_findings`, `open_question`, or `research_gap` must earn its place — it tells a researcher something they need to know, and it lands in the one section that owns that content type (see the Content Placement Map in `knowledge-model.md`). A restatement of an abstract, or anything no future work can pick up, must not be written. If a batch yields no genuine gap, leave the section empty.
- **Complete narrative, not an increment**: write two or three complete overview paragraphs and only genuine `controversy_blocks`. For a Topic with four or more well-supported sources, normally write 3-5 claim-led `synthesis_blocks`, each with one paragraph establishing the cross-paper relationship and a second paragraph explaining comparability, boundaries, alternatives, and research implications. Use fewer blocks when the evidence does not support that depth. Every paragraph references its evidence-ledger IDs and represents the complete current field state rather than the current batch alone. Do not use a mechanical word count.
- **Motivation in the overview and findings**: write the topic 概述 per the writing guide, answering what problem the topic studies, why it matters, how far the field has come, and where the disagreement sits. Give every `key_findings` entry a claim that states what it changes for the reader, not a bare pointer.
- **Snapshot semantics**: `consensus` = supported by two or more independent papers with no current counter-evidence; `single` = one paper; `conflict` = a recorded contradiction. Do not call a term "consensus" just because several papers mention it, and do not manufacture a conflict to fill space.
- **Research gap shape**: emit `research_gaps` only as objects with non-empty `gap` (the gap and its origin), `source_refs` (the papers it traces to), `direction` (what observation would move it forward), and `continuity` (a future paper may answer it; this batch need not). New plans must not use legacy string gaps. Record only the 2-3 gaps that most affect decisions. Every open gap must carry a non-empty `significance` that names the judgment or choice it would change. Fill `evidence_boundary`, `experiment`, `success_criterion`, and `risk` whenever evidence supports them because the publisher turns these fields into two readable paragraphs. `priority` remains optional and uses 高/中/低. A gap without both `evidence_boundary` and `experiment` is visibly marked as tentative.
- **Answers close items, they do not delete them**: when a batch paper answers an existing open question or fills an existing research gap on a topic page you update, preserve its stable ID and `origin`, then emit it with `status: "answered"`, `answered_by` (the answering paper's source refs), and `answered_pointer` (the evidence). The publisher moves it to the archive and the dashboards stop listing it. Record the answer as a finding and integrate its substance into the full narrative; do not silently drop the old item.
- **Edit, do not append**: before writing to a section, read its current content; merge near-duplicates into existing entries instead of adding a rewording.

### Classification Decision: key_findings vs research_gaps vs open_questions

For every candidate statement, apply three questions in order:

1. **Does it change what a reader believes about the field's current state?**
   (For example: "all three methods omit significance tests", "method A and B
   agree on the failure mode", "results on the non-conflict subset disagree".)
   If yes, write it as a `key_findings` entry with its kind
   (`consensus` / `single` / `conflict`) and source pointers.
2. **Does it name something missing plus a direction a future paper can take
   and a way to check it?** If yes, write it as a `research_gaps` object with
   `gap`, `source_refs`, `direction`, and `continuity`.
3. **Is it a plain reader-facing question with no direction attached?** Only
   then may it go to `open_questions`. A candidate carrying `source_refs` and
   a `direction` belongs to `research_gaps` only — never double-write the same
   candidate into both sections.

A statement may satisfy both questions: record the full statement under
`key_findings`, and make the gap reference the finding instead of restating
it. A statement satisfying only one question is written only once. A
statement satisfying neither is not written at all.

The structured `key_findings` ledger plus the rendered `## 综合认识`
section form the field-state snapshot. The publisher renders the narrative
only, not a duplicate finding list. `## 研究空白与候选方向` remains the actionable map.

## Link Plan Output

Follow [link-plan-schema.md](link-plan-schema.md).

- Include every finalized current batch source page, each with a short display name (`short`) used for wikilinks.
- Use `schema_version: "3.0"` and `purpose: "ingest"` for new plans.
- For an update, compute `base_topic_sha256` from the exact Topic-page bytes read before planning. Include every existing source referenced by the complete narrative in the action's `papers`, while `batch.source_pages` still contains only the current batch.
- For every existing schema 3.0 Topic, read its matching `wiki/meta/topic-state/<topic-relative-path>.json` before editing open items. Give every new open question and research gap a stable ID and `origin`; preserve the sidecar values when updating, annotating, removing, or answering an existing item. Do not infer identity from visible wording.
- Keep evidence, definitions, and `index_summary` compact.
- Use source pointers exactly as they appear in the digests or existing pages.

## Return Protocol

Return only:

```text
status
output path
number of source pages
number of create_topic / update_topic actions
```
