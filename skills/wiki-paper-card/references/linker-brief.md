# Linker Brief

This brief defines the batch-level `wiki-linker` subagent contract.

## Required Reads

Before linking, read completely:

1. [The link plan schema](link-plan-schema.md).
2. [The local knowledge model](../../wiki-shared/references/knowledge-model.md).
3. [The wiki integration contract](wiki-integration.md).
4. [The shared wiki schema](../../wiki-shared/references/wiki-schema.md).

## Role

After every paper card and digest in the current batch passes its audits, read all digests once and produce:

```text
link-plan.json
```

The linker does not read `raw/`, does not write `wiki/`, and does not return paper text or full Paper Cards to the parent agent.

Entity pages are not the linker's job: the deterministic publisher generates and updates them from the digests' `analysis.datasets`, `analysis.models`, and `analysis.metrics` lists. The linker must not emit hub actions.

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
- Emit `key_findings` for a topic action only when a finding is genuine, marked `consensus` / `single` / `conflict` with a source pointer (see the value discipline below).
- Give every contradiction with two positions a `resolving_evidence` naming the evidence or benchmark that would settle it.
- Never use mention frequency as a promotion signal.
- Preserve contradictions instead of merging them away.
- Do not invent topics, aliases, or relations absent from the digests and existing pages.

## Value And Snapshot Discipline

- **Empty is a valid result**: every `key_findings`, `open_question`, or `research_gap` must change what a reader does next. A restatement of an abstract, or anything no future work can pick up, must not be written. If a batch yields no genuine gap, leave the section empty.
- **Snapshot semantics**: `consensus` = supported by two or more independent papers with no current counter-evidence; `single` = one paper; `conflict` = a recorded contradiction. Do not call a term "consensus" just because several papers mention it, and do not manufacture a conflict to fill space.
- **Research gap shape**: emit `research_gaps` only as objects with non-empty `gap` (the gap and its origin), `source_refs` (the papers it traces to), `direction` (what observation would move it forward), and `continuity` (a future paper may answer it; this batch need not). New plans must not use legacy string gaps. Record only the 2-3 gaps that most affect decisions.
- **Answers close items, they do not delete them**: when a batch paper answers an existing open question or fills an existing research gap on a topic page you update, emit that entry with `status: "answered"`, `answered_by` (the answering paper's source refs), and `answered_pointer` (the evidence). The publisher moves it to the topic page's archive section and the dashboards stop listing it. Record the substance of the answer as a `key_findings` entry so the field-state snapshot keeps it; do not silently drop the old item.

### Classification Decision: key_findings vs research_gaps

For every candidate statement, apply two questions in order:

1. **Does it change what a reader believes about the field's current state?**
   (For example: "all three methods omit significance tests", "method A and B
   agree on the failure mode", "results on the non-conflict subset disagree".)
   If yes, write it as a `key_findings` entry with its kind
   (`consensus` / `single` / `conflict`) and source pointers.
2. **Does it name something missing plus a direction a future paper can take
   and a way to check it?** If yes, write it as a `research_gaps` object with
   `gap`, `source_refs`, `direction`, and `continuity`.

A statement may satisfy both questions: record the full statement under
`key_findings`, and make the gap reference the finding instead of restating
it. A statement satisfying only one question is written only once. A
statement satisfying neither is not written at all.

The `## 关键发现` section of a topic page is the field-state snapshot; the
`## 研究空白与候选方向` section is the actionable map. Keep consensus
signals in the former even when they also motivate a gap in the latter.

## Link Plan Output

Follow [link-plan-schema.md](link-plan-schema.md).

- Include every finalized current batch source page, each with a short display name (`short`) used for wikilinks.
- Keep evidence, definitions, and topic summaries compact.
- Use source pointers exactly as they appear in the digests or existing pages.

## Return Protocol

Return only:

```text
status
output path
number of source pages
number of create_topic / update_topic actions
```
