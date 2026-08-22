# Link Plan Schema

`wiki-linker` writes one `link-plan.json` after every paper card and digest in the batch has passed its audits.

## Top-Level Fields

```json
{
  "schema_version": "1.0",
  "batch": {
    "source_pages": [
      {
        "source_ref": "wiki/sources/path/to/paper.md",
        "work_dir": "work/paper-name",
        "title": "Paper title",
        "short": "Short name"
      }
    ]
  },
  "hub_actions": [],
  "topic_actions": []
}
```

`source_pages` contains the current batch only.

## Hub Action

```json
{
  "action": "create_hub|update_hub",
  "id": "stable-id",
  "name": "Canonical name",
  "kind": "concept|entity",
  "tier": "L2",
  "aliases": [],
  "definition": "One or two sentences.",
  "source_refs": [
    "wiki/sources/paper-a.md",
    "wiki/sources/paper-b.md"
  ],
  "connect_existing": false,
  "existing_page": null,
  "evidence": [
    {
      "source_ref": "wiki/sources/paper-a.md",
      "pointer": "[Paper: PDF p. 3, Fig. 2]",
      "claim": "What the source reports."
    }
  ],
  "relations": [],
  "contradictions": [],
  "open_questions": []
}
```

Rules:

- Hub actions must use `L2`.
- `create_hub` requires at least two distinct batch `source_refs` or `connect_existing: true`.
- `update_hub` requires `connect_existing: true` or a non-empty `existing_page`.
- Every evidence row needs `source_ref`, `pointer`, and `claim`.
- Relation fields follow the knowledge model.
- `contradictions` must preserve both positions with their source pointers.

## Topic Action

```json
{
  "action": "create_topic|update_topic",
  "id": "topic-id",
  "name": "Topic name",
  "papers": [
    "wiki/sources/paper-a.md",
    "wiki/sources/paper-b.md"
  ],
  "summary": "Short synthesis.",
  "comparisons": [],
  "key_findings": [
    {
      "claim": "A conclusion shared across papers.",
      "kind": "consensus",
      "source_refs": ["wiki/sources/paper-a.md", "wiki/sources/paper-b.md"],
      "pointer": "[Paper: PDF p. 3, Fig. 1]"
    }
  ],
  "contradictions": [],
  "open_questions": [],
  "research_gaps": [
    {
      "gap": "The gap and its origin.",
      "source_refs": ["wiki/sources/paper-a.md"],
      "direction": "What observation would move it forward.",
      "continuity": "A future paper may answer it."
    }
  ],
  "existing_page": null
}
```

Rules:

- `create_topic` requires at least two distinct batch source pages.
- `update_topic` requires a non-empty `existing_page`; it may include one new paper that answers or challenges an existing open question.
- Comparison rows use canonical keys `paper`, `source_ref` (optional, for a wikilink), `method`, `intervention_granularity`, `main_result`, `boundary`, `pointer`. The legacy key `granularity` is still rendered but deprecated.
- Contradiction items use `position_a` / `position_b` with `position_a_source_ref` / `position_a_pointer` and `position_b_source_ref` / `position_b_pointer`, plus `resolving_evidence` naming the discriminating experiment that would settle the conflict. The legacy keys `source_ref_a` / `pointer_a` / `resolve` are still rendered but deprecated.
- `key_findings` kinds: `consensus` (multiple independent sources), `single` (one source), `conflict` (disputed). Each finding carries `claim`, optional `source_refs`, and optional `pointer`. The list may be empty when no finding meets the value threshold.
- `research_gaps` entries are objects with `gap`, `source_refs` (the papers it traces to), `direction`, and `continuity`. Legacy string entries are still rendered as a bullet list for backward compatibility.
- Classification between `key_findings` and `research_gaps` follows the two-question decision in `linker-brief.md`: findings change what a reader believes about the field's current state; gaps name something missing plus a direction and a way to check it. A statement satisfying both is recorded fully under `key_findings` and referenced by the gap.

## Publisher Boundary

`publish_wiki.py` applies only the actions in this plan. It does not invent promotions, duplicate aliases, or rewrite unrelated prose.
