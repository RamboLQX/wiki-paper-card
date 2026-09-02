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

In ingest mode, after every paper card and digest in the current batch passes
its audits, read all digests once and produce:

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

For a `purpose: "refresh"` run, the parent instead supplies all affected Topic
paths from the mining publish report, their matching sidecars, and the source
pages listed in those Topics. Read only those materials; never read `raw/` or
rerun a processor. All affected Topics belong in one plan.

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

### Ingest Topic Decision Order

For `purpose: "ingest"`, separate candidate discovery from existing-page
matching. Do not let the first broad existing Topic name become the default
destination for the batch.

1. Read all current digests and form candidate Topics from their specific
   contributions without using existing Topic names as cluster labels. Seed
   names do not need to match literally: merge or separate them according to
   the cross-paper judgment they can support.
2. Build candidate comparison views across the batch. Check for views centered
   on a shared problem or outcome, method or intervention, mechanism,
   measurement or evaluation, and evidence setting. These are discovery
   prompts, not required categories. Candidates may overlap in paper
   membership.
3. For each candidate, identify the research object, the comparison question,
   the evidence boundary, the included papers, and the basis on which those
   papers can actually be compared. Retain a candidate only when at least two
   papers can support a cross-paper judgment and a meaningful comparison
   dimension; shared vocabulary alone is insufficient.
4. Only then compare the candidate with existing Topics. Use `update_topic`
   when the candidate preserves the existing page's coherent comparison view,
   or when a new paper directly answers, challenges, or materially advances an
   existing open item. A shared umbrella term is not enough.
5. Use `create_topic` when at least two papers support a distinct comparison
   view and placing them in an existing page would make its comparison question
   or synthesis incoherent. Different research objects, non-exchangeable
   metrics, or incompatible intervention interfaces are split signals when
   they prevent a meaningful comparison.

A batch may emit several Topic actions, and one paper may belong to several
Topics when it supports several independent comparisons. Topic membership is
not a partition. Conversely, Topic count is not tied to batch count, and two
similar phrases do not justify two pages without distinct comparison views.

Before finalizing, inspect the paper-to-action membership map. If multiple
Topic actions form a disjoint partition of the batch, check whether a valuable
cross-cutting comparison view was missed. Do not manufacture overlap when no
such comparison exists, and do not create a whole-batch Topic unless it can
support a coherent cross-paper judgment and comparison dimension.

Repeated reliance on statements such as "the tasks or metrics are not directly
comparable" is a signal to reconsider the boundary. A cross-setting Topic is
valid only when it has an explicit comparison question and a coherent basis
for comparing evidence across those settings. Do not create a catch-all page
that merely collects every paper under a field name, and do not reduce the
number of actions to save narrative-writing work.

## Value And Placement Discipline

### Research-Gap Synthesis Order

Research gaps are synthesized at batch level, never copied from a single-paper
proposal. Use only these four inputs: author-stated `limitations`, Agent
`critical_observations`, `unexplained_results`, and Topic seeds that support a
cross-paper comparison. Do not use `analysis.open_questions`, Section 16 ideas,
or generic future-work text as gap evidence.

First cluster compatible signals across the batch without writing gap prose.
Then retain a cluster only when all four checks pass:

1. It names concrete missing knowledge rather than a broad underexplored area.
2. The missing knowledge blocks a research judgment, interpretation, or method
   choice that matters to a researcher.
3. A minimal study can distinguish the main competing explanations or
   possibilities.
4. The result that would weaken, falsify, or close the candidate can be named,
   and the current batch does not already provide it.

There is no target gap count. Zero valid gaps is an acceptable result.

- **Placement before padding**: every `key_findings`, `open_question`, or `research_gap` must earn its place — it tells a researcher something they need to know, and it lands in the one section that owns that content type (see the Content Placement Map in `knowledge-model.md`). A restatement of an abstract, or anything no future work can pick up, must not be written. If a batch yields no genuine gap, leave the section empty.
- **Complete narrative, not an increment**: write two or three complete overview paragraphs and only genuine `controversy_blocks`. For a Topic with four or more well-supported sources, normally write 3-5 claim-led `synthesis_blocks`, each with one paragraph establishing the cross-paper relationship and a second paragraph explaining comparability, boundaries, alternatives, and research implications. Use fewer blocks when the evidence does not support that depth. Every paragraph references its evidence-ledger IDs and represents the complete current field state rather than the current batch alone. Do not use a mechanical word count.
- **Motivation in the overview and findings**: write the topic 概述 per the writing guide, answering what problem the topic studies, why it matters, how far the field has come, and where the disagreement sits. Give every `key_findings` entry a claim that states what it changes for the reader, not a bare pointer.
- **Snapshot semantics**: `consensus` = supported by two or more independent papers with no current counter-evidence; `single` = one paper; `conflict` = a recorded contradiction. Do not call a term "consensus" just because several papers mention it, and do not manufacture a conflict to fill space.
- **Research gap shape**: emit `research_gaps` only as objects with non-empty `gap`, `source_refs` (the papers it traces to), `direction` (what observation would move it forward), and `continuity` (a future paper may answer it; this batch need not). Treat `gap` as the reader-facing heading, not as a compressed study design. Give it an explicit research object as the grammatical subject and state one blocked judgment; do not begin a new Chinese heading with 缺少, 需要, 尚缺, or 亟需. Do not enumerate manipulated variables, controls, metrics, budgets, or implementation steps in the heading. Move those details into `reader_narrative`. New plans must not use legacy string gaps. Every open gap carries a non-empty `significance` naming the judgment or choice it would change and a `reader_narrative` of one or two final prose paragraphs. The prose should connect the evidence tension, blocked judgment, discriminating test, expected contribution, and meaningful failure without exposing field labels. Prefer one principal claim per sentence and split dense enumerations into separate sentences. Keep `evidence_boundary`, `experiment`, `success_criterion`, and `risk` as structured support when evidence allows. In ingest mode omit `priority`: the linker has no user-resource context for ranking. A gap without both `evidence_boundary` and `experiment` is visibly marked as tentative.
- **Partial progress stays open**: when a new paper advances a research gap but leaves a boundary that could still change the original judgment, keep `status: "open"` and add a stable-ID `progress_updates` record with `source_refs`, `method`, `result`, `pointer`, and `remaining_boundary`. Never mark a gap answered merely because a related paper exists.
- **Answers close items, they do not delete them**: mark a research gap answered only when the new evidence directly covers the recorded gap, performs the proposed or an equivalent test, and leaves no remaining boundary material to the original judgment. Preserve its stable ID, `origin`, and progress history; emit `status: "answered"`, `answered_by`, `answered_pointer`, `resolution_method`, `resolution_summary`, and `resolution_scope`. The publisher moves it to a detailed archive record and the dashboards stop listing it. Record the answer as a finding and integrate its substance into the full narrative; do not silently drop the old item. Open questions retain their existing answered fields.
- **Edit, do not append**: before writing to a section, read its current content; merge near-duplicates into existing entries instead of adding a rewording.

### Classification Decision: key_findings vs research_gaps vs open_questions

For every candidate statement, apply these decisions in order:

1. **Does it change what a reader believes about the field's current state?**
   (For example: "all three methods omit significance tests", "method A and B
   agree on the failure mode", "results on the non-conflict subset disagree".)
   If yes, write it as a `key_findings` entry with its kind
   (`consensus` / `single` / `conflict`) and source pointers.
2. **Does it come from one of the four eligible signals and pass all four
   research-gap checks above?** Only then write it as a `research_gaps` object
   with `gap`, `source_refs`, `direction`, `continuity`, and
   `reader_narrative`.
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

### Refresh Mode

When the parent requests the post-mining narrative refresh:

- use `schema_version: "3.0"`, `purpose: "refresh"`, an empty
  `batch.source_pages`, and a descriptive `batch.label`;
- emit exactly one `update_topic` action per reported Topic and no actions for
  any other Topic;
- compute `base_topic_sha256` from the exact post-mining page bytes;
- include the Topic's complete existing source membership in `papers`;
- rebuild `index_summary`, `narrative`, `key_findings`, `contradictions`, and
  `comparisons` from the current Topic, its archive, sidecar, and source pages;
- omit `open_questions`, `research_gaps`, all open-item mutation fields,
  `category`, and `page_status`; refresh cannot change them;
- integrate the newly resolved evidence into the field-state prose so the old
  gap is no longer described as unresolved.

The deterministic publisher accepts refresh only while the Topic sidecar says
that a refresh is pending. One exact replay is a no-op. A stale target or any
audit failure leaves the pending state and visible notice in place.

## Return Protocol

Return only:

```text
status
output path
number of source pages
number of create_topic / update_topic actions
```
