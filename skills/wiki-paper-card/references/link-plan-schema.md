# Link Plan Schema

`wiki-linker` writes one `link-plan.json` after every paper card and digest in the batch has passed its audits. The `wiki-gap-mining` miner writes mining-mode plans (`purpose: "mining"`) when a write-back is confirmed. New Topic work uses schema 3.0. Schema 2.0 remains accepted only for compatibility with existing plans and pages.

## Schema 3.0

Schema 3.0 separates the reader-facing narrative from its structured evidence ledger and makes `purpose` an enforced write boundary.

### Ingest Example

```json
{
  "schema_version": "3.0",
  "purpose": "ingest",
  "batch": {"source_pages": []},
  "topic_actions": [
    {
      "action": "update_topic",
      "id": "topic-id",
      "name": "Topic name",
      "existing_page": "wiki/topics/Topic name.md",
      "base_topic_sha256": "64 lowercase hex characters",
      "papers": ["wiki/sources/new.md", "wiki/sources/existing.md"],
      "index_summary": "One sentence for the index and retrieval trees.",
      "page_status": "draft",
      "narrative": {
        "overview": {
          "paragraphs": [
            {
              "id": "overview-scope",
              "text": "A complete reader-facing paragraph.",
              "finding_refs": ["kf-shared-result"]
            }
          ]
        },
        "synthesis_blocks": [
          {
            "id": "synthesis-shared-result",
            "heading": "A claim-led heading",
            "paragraphs": [
              {
                "text": "A complete synthesis paragraph.",
                "finding_refs": ["kf-shared-result"]
              }
            ]
          }
        ],
        "controversy_blocks": []
      },
      "key_findings": [
        {
          "id": "kf-shared-result",
          "claim": "The structured field-state claim.",
          "kind": "consensus",
          "source_refs": ["wiki/sources/new.md", "wiki/sources/existing.md"],
          "pointers": [
            {"source_ref": "wiki/sources/new.md", "pointer": "[Paper: PDF p. 3]"},
            {"source_ref": "wiki/sources/existing.md", "pointer": "[Paper: PDF p. 4]"}
          ]
        }
      ],
      "contradictions": [],
      "comparisons": [],
      "open_questions": [
        {
          "id": "oq-transfer",
          "origin": "ingest",
          "question": "Does the result transfer?",
          "source_refs": ["wiki/sources/new.md"],
          "status": "open"
        }
      ],
      "research_gaps": [
        {
          "id": "rg-unified-benchmark",
          "origin": "ingest",
          "gap": "A unified benchmark is missing.",
          "source_refs": ["wiki/sources/new.md", "wiki/sources/existing.md"],
          "direction": "Run both methods on one benchmark.",
          "continuity": "A later paper can close the gap.",
          "significance": "It would change which method is preferred.",
          "status": "open"
        }
      ]
    }
  ]
}
```

For `update_topic`, `base_topic_sha256` is the SHA-256 of the exact UTF-8 Topic-page bytes read by the plan writer. The publisher rejects the complete plan with `stale_topic_plan` when the target changed. An exact replay of the last applied action is accepted as an idempotent no-op. `create_topic` omits the base hash and fails when a different page with the same target already exists.

### Narrative And Evidence Rules

- `index_summary` is the one-sentence index/tree signpost. It is not rendered as the visible overview.
- `key_findings[].id` and `contradictions[].id` are unique lowercase kebab-case IDs within the action.
- Every finding has `claim`, `kind`, non-empty `source_refs`, and source-bound `pointers[]`. A `consensus` finding needs at least two independent sources.
- Each narrative paragraph contains final prose plus non-empty `finding_refs`; `contradiction_refs` is optional. All references resolve inside the same action.
- The publisher replaces `overview`, `synthesis_blocks`, and `controversy_blocks` by fixed second-level heading boundaries and derives standard Markdown footnotes from the referenced ledger entries. It does not render `key_findings` again as bullets or expose publisher protocol in the Topic Markdown.
- Narrative text contains no Markdown bullets and no batch-history language such as 本批, 本次新增, or 追加证据.
- `papers` contains every source referenced by the action, including existing Wiki sources needed to rebuild the complete narrative. An ingest action must reference at least one current-batch source.

### Stable Open Items

In schema 3.0, every `open_questions` and `research_gaps` entry is an object with:

- a stable lowercase kebab-case `id`;
- immutable provenance `origin: "ingest"|"mining"`;
- non-empty `source_refs` contained in the action's `papers`;
- `status: "open"|"answered"`; answered entries also carry `answered_by` and `answered_pointer`.

Research gaps retain `direction`, `continuity`, `significance`, and the optional v2 detail fields. The publisher stores `id`, `origin`, annotations, and the replay fingerprint in `wiki/meta/topic-state/*.json`. Dashboards read compact open-item fields from that sidecar while the Topic page renders reader-facing prose.

Schema 3.0 mutations address items by ID:

- `remove_open_question_ids`: IDs to remove from the open/archive question sections.
- `remove_research_gap_ids`: IDs to remove from the open/archive gap sections.
- `annotate_research_gaps`: `{ "id": "rg-id", "note": "..." }` objects.

Text-fragment fields are rejected in schema 3.0. Updating an existing ID replaces that item while preserving its `origin`; marking it answered moves the same ID to the archive.

### Mining Permission Boundary

A schema 3.0 mining update may change only `open_questions`, `research_gaps`, their ID-based removal/annotation fields, and the monotonic source/backlink union expressed by `papers`. It must not contain `index_summary`, `narrative`, `comparisons`, `key_findings`, `contradictions`, `category`, or `page_status`.

A confirmed mining `create_topic` may provide `index_summary`, existing source `papers`, and open items only. It requires at least two existing sources and always renders `status: stub` with a fixed overview stating that the page is a candidate without a completed cross-paper synthesis. A later ingest action supplies the narrative and may explicitly promote `page_status` to `draft` or `evergreen`.

When mining archives an answered item, the publish report emits `narrative_refresh_recommended`; mining still does not rewrite the narrative.

## Schema 2.0 Compatibility

### Top-Level Fields

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
