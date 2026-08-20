# Knowledge Crystallization Model

## Goal

The source Paper Card is the detailed record. Wiki concept and entity pages are thin cross-paper hubs. Topic pages carry comparison, synthesis, conflicts, and open questions.

Do not create a page just because a term can be extracted from one paper. Create a page when doing so makes later papers easier to connect and compare.

## Tiers

### L0 Local Candidate

- Valuable only inside the current paper.
- Paper-specific component, label, or intermediate concept.
- Not independently reusable.

Action: keep in Section 14 or a local table. Do not create a wiki page.

### L1 Reusable Candidate

- Has a stable identity and evidence.
- Can be defined without the current paper's narrative.
- Not yet supported by a second independent source.

Action: keep the definition, evidence, and proposed relations in the source Paper Card. Do not create a standalone concept or entity page yet.

### L2 Cross-Paper Hub

- Supported by at least two independent source pages, or directly required to connect existing wiki pages or an existing open question.
- Definition is stable enough for cross-paper retrieval.
- Expected to accumulate relations or contradictions.

Action: create or update a thin concept or entity page with `status: stub`.

A hub page becomes `evergreen` only after:

- multiple independent sources support it;
- aliases and identity are stable;
- relations are disambiguated;
- no unresolved conflict blocks its use as a common reference.

## Hub Promotion Gates

Create or update a concept or entity page only when all of the following are true:

1. Identity is stable, not a one-off local name.
2. The candidate can be defined without the current paper's narrative.
3. At least one `[Paper]` or `[External]` source supports it.
4. At least two independent source pages support it, or the page is required to connect existing pages or an existing open question.
5. It is likely to interact with future sources.

Mention count is not a gate. An L1 candidate remains local until gate 4 is met.

## Hub Page Content

A concept or entity page must stay a navigation and comparison hub, not a second Paper Card:

```text
frontmatter
one-sentence definition
aliases
source evidence table
explicit relations
contradictions
open questions
```

Keep implementation details, ablations, and long result tables in the source Paper Card and link to it.

## Topic Pages

Topic pages are the primary synthesis surface for:

- comparing methods, evidence, models, datasets, and results across papers;
- recording contradictions and unresolved conflicts;
- listing open questions and research gaps;
- proposing discriminating experiments.

Create or update a topic page when at least two papers share the same problem, mechanism, or evidence space, or when a single paper directly answers an existing open question.

Research gaps and open questions are snapshots of the current corpus. Record a gap only when it carries a source anchor (which paper's limitation or uncovered setting) and a direction a future paper could advance; if a batch yields no genuine gap, leave the section empty rather than padding it.

## Relationship Types

```text
defines
uses
extends
implements
derived_from
supports
contradicts
same_as
is_instance_of
applied_to
```

Every relationship carries:

```text
type
target page
source pointer
provenance
confidence
```

Do not add a generic related-to edge.

## Existing Page Updates

Before writing:

1. Read the target page.
2. Verify name disambiguation.
3. Add only facts, sources, and relations that are absent.
4. Do not restate existing content in different words.
5. Add the current source report link once.
6. Preserve existing contradictions; add a new entry instead of overwriting.

## Aliases And Merges

- Use the shared terminology ledger for canonical names.
- Add synonyms to `aliases`.
- When two existing pages describe the same object, propose a merge; do not silently delete either page.

## Contradictions

When a new source conflicts with existing knowledge:

1. Keep both positions.
2. Add or update a `## 争议与矛盾` section.
3. Record the source pointer for each position.
4. State what evidence would resolve the conflict.

## Retirement

- Do not automatically delete pages.
- Weak or abandoned nodes become `status: stub` or `archived`.
- Index and log record the state change.
