# Link Plan Schema

`wiki-linker` writes one `link-plan.json` after every paper card and digest in the batch has passed its audits. The `wiki-gap-mining` miner writes mining-mode plans (`purpose: "mining"`) when a write-back is confirmed. When mining archives an answer, one fresh linker may write a batched narrative-only plan (`purpose: "refresh"`) for the affected Topics. An explicitly approved Vault upgrade may use `purpose: "migration"` to rebuild selected legacy Topics. New Topic work uses schema 3.0. Schema 2.0 remains accepted only for compatibility with existing plans and pages.

## Schema 3.0

Schema 3.0 separates the reader-facing narrative from its structured evidence ledger and makes `purpose` and the user-selected `workflow_mode` enforced write boundaries.

### Ingest Example

```json
{
  "schema_version": "3.0",
  "purpose": "ingest",
  "workflow_mode": "wiki-full",
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
          "gap": "Current evidence cannot support a fair method comparison.",
          "source_refs": ["wiki/sources/new.md", "wiki/sources/existing.md"],
          "direction": "Run both methods on one benchmark.",
          "continuity": "A later paper can close the gap.",
          "significance": "It would change which method is preferred.",
          "reader_narrative": [
            "The studies cannot yet support a method choice because their results come from different benchmarks.",
            "A matched comparison would show whether the reported ranking reflects the methods or the evaluation setting."
          ],
          "status": "open"
        }
      ]
    }
  ]
}
```

For `update_topic`, `base_topic_sha256` is the SHA-256 of the exact UTF-8 Topic-page bytes read by the plan writer. The publisher rejects the complete plan with `stale_topic_plan` when the target changed. An exact replay of the last applied action is accepted as an idempotent no-op. `create_topic` omits the base hash and fails when a different page with the same target already exists.

### Ingest Workflow Mode

Every schema 3.0 ingest plan must define one of these values:

- `workflow_mode: "wiki-topic"`: publish source pages and maintain Topic
  synthesis without changing research gaps. Every Topic action must contain
  `research_gaps: []` and must omit `remove_research_gap_ids`, legacy
  `remove_research_gaps`, and `annotate_research_gaps`. Existing gaps remain in
  the Topic sidecar and rendered page. A would-be gap must not be moved into
  `open_questions` merely to bypass this boundary.
- `workflow_mode: "wiki-full"`: use the complete ingest behavior, including
  evidence-grounded research-gap synthesis, progress, answers, annotations,
  and removals.

`card-only` has no link plan and is therefore not a valid `workflow_mode`
value. Mining, refresh, and migration plans must omit `workflow_mode`; their permissions
continue to be controlled by `purpose`.

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
- `status: "open"|"answered"`; this field expresses closure only, not partial progress.

Research gaps retain `direction`, `continuity`, `significance`, and the optional structured detail fields. A newly generated open gap carries `reader_narrative`: one or two final prose paragraphs for the Topic page. The publisher prefers this prose; older gaps without it use the previous labelled-field rendering, so no bulk migration is required. An open gap may carry `progress_updates`, each with a stable lowercase kebab-case `id`, non-empty `source_refs`, `method`, `result`, `pointer`, and `remaining_boundary`. Progress records are upserted by ID; unmentioned prior records remain. An answered research gap carries `answered_by`, `answered_pointer`, `resolution_method`, `resolution_summary`, and `resolution_scope`. Open questions retain the existing `answered_by` / `answered_pointer` contract. The publisher stores this lifecycle state and the replay fingerprint in `wiki/meta/topic-state/*.json`. Dashboards read compact open-item fields from that sidecar while the Topic page renders reader-facing prose.

Schema 3.0 mutations address items by ID:

- `remove_open_question_ids`: IDs to remove from the open/archive question sections.
- `remove_research_gap_ids`: IDs to remove from the open/archive gap sections.
- `annotate_research_gaps`: `{ "id": "rg-id", "note": "..." }` objects.

Text-fragment fields are rejected in schema 3.0. Updating an existing ID replaces that item while preserving its `origin`; marking it answered moves the same ID to the archive.

### Mining Permission Boundary

A schema 3.0 mining update may change only `open_questions`, `research_gaps`, their ID-based removal/annotation fields, and the monotonic source/backlink union expressed by `papers`. It must not contain `index_summary`, `narrative`, `comparisons`, `key_findings`, `contradictions`, `category`, or `page_status`.

A confirmed mining `create_topic` may provide `index_summary`, existing source `papers`, and open items only. It requires at least two existing sources and always renders `status: stub` with a fixed overview stating that the page is a candidate without a completed cross-paper synthesis. A later ingest action supplies the narrative and may explicitly promote `page_status` to `draft` or `evergreen`.

When mining archives an answered item, the publish report emits `narrative_refresh_required` and a structured list of affected Topics. The Topic sidecar records the pending state and archived item IDs, while the page displays a deterministic update notice. The parent batches those Topics into one `purpose: "refresh"` linker run. A successful refresh rewrites the complete narrative and clears both state and notice; failure preserves them for retry.

### Refresh Permission Boundary

A schema 3.0 refresh plan has an empty `batch.source_pages`, a non-empty
`batch.label`, and one `update_topic` action per affected Topic. Each action
requires `existing_page`, the exact post-mining `base_topic_sha256`, complete
existing `papers`, `index_summary`, `narrative`, `comparisons`, `key_findings`,
and `contradictions`. It must omit `open_questions`, `research_gaps`, their
mutation fields, `category`, and `page_status`. It cannot create a Topic.

The publisher accepts a refresh only when the sidecar has
`narrative_refresh_required: true`, except that an exact successful-plan replay
remains a no-op. Refresh reads existing source pages and never writes batch
source pages or invokes paper processors.

### Migration Permission Boundary

A schema 3.0 migration plan has an empty `batch.source_pages`, a non-empty
`batch.label`, and one `update_topic` action per user-approved legacy Topic.
Each action carries `existing_page`, the exact legacy-page
`base_topic_sha256`, complete existing `papers`, `index_summary`, narrative,
comparisons, evidence ledgers, `open_questions`, and `research_gaps`.
Migration cannot create Topics and must omit incremental removal and annotation
fields. Stable IDs and origins from complete legacy markers remain unchanged;
plain legacy pages receive new stable IDs grounded in their existing content.

Migration is the only purpose that may update a Topic with neither valid
sidecar state nor complete managed markers. Ordinary ingest retains
`narrative_migration_required`. Conversely, migration rejects a Topic that
already has valid state unless the action is an exact successful-plan replay.
The upgrade wrapper stages the complete plan in a copy of `wiki/`, audits it,
enforces the selected write set, and creates a hash-addressed backup before
committing to the real Vault. Migration reads existing source pages but never
writes them.

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

`purpose` is optional and defaults to `ingest`. Schema 2.0 supports these historical purposes:

- `ingest` (paper-processing batches): `source_pages` contains the current
  batch (at least one), and topic actions may only reference batch pages.
- `mining` (gap-mining runs, written by the `wiki-gap-mining` miner):
  `source_pages` is empty, `batch.label` names the run, and topic actions
  reference *existing* wiki source pages. `create_topic` requires at least
  two referenced source pages (they must already exist in the wiki). The
  publisher appends the topic backlinks to those existing source pages.
- `refresh` (schema 3.0 post-mining narrative synchronization):
  `source_pages` is empty, `batch.label` names the refresh, and one fresh
  linker updates all reported Topics without changing their open items or
  page metadata. Schema 2.0 refresh plans are rejected.

`source_pages` contains the current batch only; in mining and refresh modes it
is empty.

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
      "gap": "Current evidence cannot determine which method is more reliable.",
      "source_refs": ["wiki/sources/paper-a.md"],
      "direction": "What observation would move it forward.",
      "continuity": "A future paper may answer it.",
      "significance": "Why it matters: what judgment it would change.",
      "evidence_boundary": "Where existing methods stop.",
      "experiment": "The guess and how to test it (data/benchmark/metric/control).",
      "success_criterion": "What result counts as filling the gap.",
      "risk": "Where it may fail, per existing papers.",
      "priority": "高",
      "progress_updates": [
        {
          "id": "progress-shared-benchmark",
          "source_refs": ["wiki/sources/paper-b.md"],
          "method": "Run both methods on one shared benchmark.",
          "result": "The shared benchmark removes one comparison confound.",
          "pointer": "[Paper: PDF p. 8, Table 3]",
          "remaining_boundary": "Cross-domain transfer remains untested."
        }
      ],
      "status": "open"
    },
    {
      "gap": "A gap this batch fills.",
      "source_refs": ["wiki/sources/paper-a.md"],
      "direction": "What observation would test the gap.",
      "continuity": "The answering paper closes this recorded direction.",
      "status": "answered",
      "answered_by": ["wiki/sources/paper-c.md"],
      "answered_pointer": "[Paper: PDF p. 5]",
      "resolution_method": "Run a controlled comparison on one benchmark.",
      "resolution_summary": "The comparison closes the recorded benchmark gap.",
      "resolution_scope": "The conclusion covers the matched public datasets."
    }
  ],
  "existing_page": null
}
```

Rules:

- `create_topic` requires at least two distinct batch source pages.
- `update_topic` requires a non-empty `existing_page`; it may include one new paper that answers, challenges, or partially advances an existing open item. Partial gap advances keep `status: "open"` and add `progress_updates`. A fully answered gap uses the complete resolution record defined above; an answered open question keeps the existing `answered_by` / `answered_pointer` pair. Only answered items move into the archive and disappear from the research dashboard and knowledge tree.
- Topic membership is not a partition: the same source page may appear in several actions when it supports independent cross-paper judgments and comparison views. Candidate views may center on a shared problem, method or intervention, mechanism, measurement or evaluation, or evidence setting; these are discovery prompts rather than required categories. Do not merge meaningful views merely to reduce the number of actions.
- A disjoint partition of the batch is valid only after checking whether a meaningful cross-cutting comparison view was missed. Do not manufacture overlap when no such comparison exists, and do not create a whole-batch Topic without a coherent cross-paper judgment and comparison dimension.
- Choose `update_topic` only after confirming that the candidate preserves the existing page's coherent comparison view. A shared umbrella field name is insufficient; if the existing title or overview must broaden beyond a meaningful comparison basis to admit the candidate, create a sibling Topic when the two-paper gate is met.
- Flat comparison rows use canonical keys `paper`, required `source_ref`, `method`, `intervention_granularity`, `main_result`, `boundary`, `pointer`. The publisher upserts them by normalized `source_ref`, preserves table order, and recognizes an unambiguous legacy stem-only link during migration. New links retain the full Vault-relative target. The legacy key `granularity` is still rendered but deprecated.
- Contradiction items use `position_a` / `position_b` with `position_a_source_ref` / `position_a_pointer` and `position_b_source_ref` / `position_b_pointer`, plus `resolving_evidence` naming the discriminating experiment that would settle the conflict. The legacy keys `source_ref_a` / `pointer_a` / `resolve` are still rendered but deprecated.
- `key_findings` kinds: `consensus` (multiple independent sources), `single` (one source), `conflict` (disputed). Each finding carries `claim`, optional `source_refs`, and optional `pointer`. The list may be empty when no finding meets the value threshold.
- `open_questions` entries are strings or objects with `question` and optional `status` (`open` default / `answered`). A string is shorthand for an open question. Answered objects require non-empty `answered_by` source refs and a non-empty `answered_pointer`. The list may be empty.
- `research_gaps` entries in a new plan must be objects with non-empty `gap`, `source_refs` (a non-empty list of the papers it traces to), `direction`, `continuity`, and optional `status` (`open` default / `answered`). `gap` is the reader-facing heading: it names the research object as its grammatical subject and states one blocked judgment. Variables, controls, metrics, budgets, and study-design steps belong in `reader_narrative`, not in the heading. Open gaps additionally require a non-empty `significance`; producer contracts require `reader_narrative` with one or two non-empty prose paragraphs, while the audit warns rather than fails when it is absent to preserve old schema 3.0 plans. Optional `progress_updates` must use the complete stable-ID record described above. Answered schema 3.0 gaps additionally require non-empty `answered_by`, `answered_pointer`, `resolution_method`, `resolution_summary`, and `resolution_scope`. The publisher retains legacy string input and renders older stored answered entries from whatever resolution fields are available.
- Every open `research_gaps` entry must carry a non-empty `significance` that names the judgment or choice it would change; the audit rejects an open gap without it (see the shared [writing guide](../../wiki-shared/references/writing-guide.md)). Answered gaps are exempt. The structured fields `evidence_boundary`, `experiment`, `success_criterion`, `risk`, and `priority` remain optional. Ingest plans omit `priority`; mining may set 高/中/低 after considering user scope and resources. An entry carrying structured detail but lacking both `evidence_boundary` and `experiment` renders with a `[待验证]` tag (a tentative direction). Empty optional fields should be omitted rather than set to `""` (audit warns).
- Topic actions may carry an optional single-value `category` (for example `"评估框架"`): the publisher writes it into the topic frontmatter on create and on update (only when given), and the knowledge tree renders a category-first topic view from it. Omit it to leave a topic uncategorized. The category set is small and user-owned; proposing a new category requires user confirmation.
- Semantic dedup fields (used by mining write-back, available to the linker as well): `remove_open_questions` and `remove_research_gaps` are lists of non-empty strings; the publisher drops existing bullets whose text contains the fragment (whitespace-normalized substring match). `annotate_research_gaps` is a list of `{match, note}` objects; the publisher appends `note` to the matching open gap's 承接 ending, or as a `- 相关空白：…` sub-bullet when there is no such ending. Fragments matching nothing are no-ops; audit rejects malformed shapes, and unknown fields on a topic action are ignored by the publisher, so name these exactly.
- Classification between `key_findings` and `research_gaps` follows the evidence-source and four-check gate in `linker-brief.md`: findings change what a reader believes about the field's current state; gaps must also arise from one of the four allowed signals, block a concrete judgment, admit a discriminating study, and name a failure or closure result. A statement satisfying both is recorded fully under `key_findings` and referenced by the gap. When a later paper answers an open item, record the answer's substance as a `key_findings` entry and mark the old item answered instead of silently dropping it.

## Publisher Boundary

`publish_wiki.py` applies only the actions in this plan. It does not invent topic promotions, duplicate aliases, or rewrite unrelated prose. Before any write, the publisher verifies that every page named by topic-action `papers`, by research-gap or progress `source_refs`, or by answered evidence (`answered_by`) is either part of the current batch or an existing page under `wiki/sources/`, and that every batch source page has a finalized `paper-card.md`; any missing or invalid reference blocks the whole publish.
