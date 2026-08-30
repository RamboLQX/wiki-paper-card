# Link Plan Schema

`wiki-linker` writes one `link-plan.json` after every paper card and digest in the batch has passed its audits. The `wiki-gap-mining` miner writes mining-mode plans (`purpose: "mining"`) when a write-back is confirmed.

## Top-Level Fields

```json
{
  "schema_version": "2.0",
  "purpose": "ingest",
  "batch": {
    "label": "optional run label (used by mining plans)",
    "source_pages": [
      {
        "source_ref": "wiki/sources/path/to/paper.md",
        "work_dir": "work/paper-name",
        "title": "Paper title",
        "short": "Short name"
      }
    ]
  },
  "topic_actions": []
}
```

`purpose` is optional and defaults to `ingest`. The two modes:

- `ingest` (paper-processing batches): `source_pages` contains the current
  batch (at least one), and topic actions may only reference batch pages.
- `mining` (gap-mining runs, written by the `wiki-gap-mining` miner):
  `source_pages` is empty, `batch.label` names the run, and topic actions
  reference *existing* wiki source pages. `create_topic` requires at least
  two referenced source pages (they must already exist in the wiki). The
  publisher appends the topic backlinks to those existing source pages.

`source_pages` contains the current batch only; in mining mode it is empty.

There are no hub actions: the linker writes topic actions only.

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
  "category": "评估框架",
  "remove_open_questions": ["Question fragment to remove"],
  "remove_research_gaps": ["Gap fragment to remove"],
  "annotate_research_gaps": [
    {"match": "Existing gap text fragment", "note": "同类空白见 [[Other Topic]] 的…"}
  ],
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
  "open_questions": [
    "A plain open question.",
    {
      "question": "An open question answered by this batch.",
      "status": "answered",
      "answered_by": ["wiki/sources/paper-c.md"],
      "answered_pointer": "[Paper: PDF p. 4]"
    }
  ],
  "research_gaps": [
    {
      "gap": "The gap and its origin.",
      "source_refs": ["wiki/sources/paper-a.md"],
      "direction": "What observation would move it forward.",
      "continuity": "A future paper may answer it.",
      "significance": "Why it matters: what judgment it would change.",
      "evidence_boundary": "Where existing methods stop.",
      "experiment": "The guess and how to test it (data/benchmark/metric/control).",
      "success_criterion": "What result counts as filling the gap.",
      "risk": "Where it may fail, per existing papers.",
      "priority": "高",
      "status": "open"
    },
    {
      "gap": "A gap this batch fills.",
      "source_refs": ["wiki/sources/paper-a.md"],
      "direction": "What observation would test the gap.",
      "continuity": "The answering paper closes this recorded direction.",
      "status": "answered",
      "answered_by": ["wiki/sources/paper-c.md"],
      "answered_pointer": "[Paper: PDF p. 5]"
    }
  ],
  "existing_page": null
}
```

Rules:

- `create_topic` requires at least two distinct batch source pages.
- `update_topic` requires a non-empty `existing_page`; it may include one new paper that answers or challenges an existing open question. When a paper answers an existing open question or fills an existing research gap, the linker marks that entry `status: "answered"` with non-empty `answered_by` (the answering paper's source refs) and `answered_pointer` (the evidence). The publisher then moves the entry from the open `## 开放问题` / `## 研究空白与候选方向` sections into the archive sections `## 已解决的问题` / `## 已解决的研究空白` on the topic page; the research dashboard and knowledge tree stop listing it.
- Comparison rows use canonical keys `paper`, `source_ref` (optional, for a wikilink), `method`, `intervention_granularity`, `main_result`, `boundary`, `pointer`. The legacy key `granularity` is still rendered but deprecated.
- Contradiction items use `position_a` / `position_b` with `position_a_source_ref` / `position_a_pointer` and `position_b_source_ref` / `position_b_pointer`, plus `resolving_evidence` naming the discriminating experiment that would settle the conflict. The legacy keys `source_ref_a` / `pointer_a` / `resolve` are still rendered but deprecated.
- `key_findings` kinds: `consensus` (multiple independent sources), `single` (one source), `conflict` (disputed). Each finding carries `claim`, optional `source_refs`, and optional `pointer`. The list may be empty when no finding meets the value threshold.
- `open_questions` entries are strings or objects with `question` and optional `status` (`open` default / `answered`). A string is shorthand for an open question. Answered objects require non-empty `answered_by` source refs and a non-empty `answered_pointer`. The list may be empty.
- `research_gaps` entries in a new plan must be objects with non-empty `gap`, `source_refs` (a non-empty list of the papers it traces to), `direction`, `continuity`, and optional `status` (`open` default / `answered`). Open gaps additionally require a non-empty `significance`; answered gaps additionally require non-empty `answered_by` and `answered_pointer`. The publisher retains legacy string rendering for historical compatibility, but `audit_link_plan.py` rejects strings in every newly submitted plan.
- Every open `research_gaps` entry must carry a non-empty `significance` that names the judgment or choice it would change; the audit rejects an open gap without it (see the shared [writing guide](../../wiki-shared/references/writing-guide.md)). Answered gaps are exempt. The other five v2 detail fields `evidence_boundary`, `experiment`, `success_criterion`, `risk`, and `priority` remain optional. `priority` uses the labels 高/中/低 (audit rejects other values). An entry carrying any v2 field but lacking both `evidence_boundary` and `experiment` renders with a `[待验证]` tag (a tentative direction); entries without any v2 field render exactly as before. Empty optional fields should be omitted rather than set to `""` (audit warns).
- Topic actions may carry an optional single-value `category` (for example `"评估框架"`): the publisher writes it into the topic frontmatter on create and on update (only when given), and the knowledge tree renders a category-first topic view from it. Omit it to leave a topic uncategorized. The category set is small and user-owned; proposing a new category requires user confirmation.
- Semantic dedup fields (used by mining write-back, available to the linker as well): `remove_open_questions` and `remove_research_gaps` are lists of non-empty strings; the publisher drops existing bullets whose text contains the fragment (whitespace-normalized substring match). `annotate_research_gaps` is a list of `{match, note}` objects; the publisher appends `note` to the matching open gap's 承接 ending, or as a `- 相关空白：…` sub-bullet when there is no such ending. Fragments matching nothing are no-ops; audit rejects malformed shapes, and unknown fields on a topic action are ignored by the publisher, so name these exactly.
- Classification between `key_findings` and `research_gaps` follows the two-question decision in `linker-brief.md`: findings change what a reader believes about the field's current state; gaps name something missing plus a direction and a way to check it. A statement satisfying both is recorded fully under `key_findings` and referenced by the gap. When a later paper answers an open item, record the answer's substance as a `key_findings` entry and mark the old item answered instead of silently dropping it.

## Publisher Boundary

`publish_wiki.py` applies only the actions in this plan. It does not invent topic promotions, duplicate aliases, or rewrite unrelated prose. Before any write, the publisher verifies that every page named by topic-action `papers`, by research-gap `source_refs`, or by answered evidence (`answered_by`) is either part of the current batch or an existing page under `wiki/sources/`, and that every batch source page has a finalized `paper-card.md`; any missing or invalid reference blocks the whole publish.
