# Paper Digest Schema

`wiki-processor` writes one `paper-digest.json` per paper. The digest is a compact paper-local record used by the batch linker and the deterministic publisher. It must not contain wiki actions.

The processor owns the semantic fields. `paper.source_sha256`,
`paper.source_ref`, and every Topic seed's single-paper `papers` list are
system-owned identity fields: `finalize_paper_digest.py` replaces them from
`batch-manifest.json` and records the before/after values before audit. The
script never changes title, locator mode, paper type, analysis, seed identity,
seed name, or seed summary.

## Top-Level Fields

```json
{
  "schema_version": "3.0",
  "paper": {
    "title": "Paper title",
    "source_sha256": "hex digest",
    "source_ref": "wiki/sources/path/to/paper.md",
    "locator_mode": "page-grounded",
    "paper_type": "methods"
  },
  "analysis": {
    "one_sentence_summary": "One sentence covering the problem or motivation, core approach, and evidence-bounded result or contribution.",
    "problem": "Problem and research question.",
    "method": "Core method and mechanism.",
    "key_results": [],
    "limitations": [],
    "critical_observations": [],
    "unexplained_results": [],
    "open_questions": []
  },
  "topic_seeds": []
}
```

## Analysis

- `one_sentence_summary`, `problem`, and `method` are required strings.
- `one_sentence_summary` follows the reader-facing Section 02 contract: problem
  or motivation first, core approach second, and an evidence-bounded result or
  contribution last. It must not merely state what the paper did.
- Public datasets, benchmarks, model families, and metrics stay in the Paper Card's Sections 14-16 as plain text; the digest does not carry artifact lists and there are no entity pages.
- `key_results` records the main bounded results:

```json
{
  "claim": "What the paper reports.",
  "pointer": "[Paper: PDF p. 6, Table 2]",
  "confidence": "high|medium|low"
}
```

- `limitations` and `unexplained_results` use `statement` plus `pointer`;
  `critical_observations` uses `observation` plus `pointer`.
- `unexplained_results` records an observed result whose mechanism, boundary,
  reversal, or inconsistency the paper does not explain. Do not restate every
  result here.
- `open_questions` remains a paper-local reading aid. It is not an eligible
  research-gap input and must not be copied into a Topic seed.
- Keep the complete detail in `paper-card.md`. The digest supports linking, not replacement of the card.

## Topic Seed

```json
{
  "id": "topic-id",
  "name": "Candidate cross-paper comparison view",
  "papers": ["wiki/sources/current/paper.md"],
  "summary": "What cross-paper judgment this view supports, what is compared, and under which evidence boundary."
}
```

A topic seed is a paper-supported candidate comparison view for the linker,
not a publish action or an existing Topic assignment. Generate the views this
paper can support before considering existing page names. `kb-context.md` may
prevent duplicate terminology, but a processor must not copy an existing
Topic name merely to make later matching easier.

A paper may propose several seeds when each supports a different cross-paper
judgment. Candidate views may overlap in their eventual paper membership: a
paper can contribute to a shared problem view and also to a method, mechanism,
measurement, evaluation, or evidence-setting view. These are discovery prompts,
not required categories. Do not merge distinct views into one catch-all seed,
and do not create extra seeds to satisfy a count. `papers` contains only the
current paper; the linker decides cross-paper membership and `create_topic` /
`update_topic` actions.

Topic seeds carry comparison structure only: `id`, `name`, `papers`, and
`summary`. They never carry `open_questions` or `research_gaps`. The linker may
use a seed as one of the four research-gap signals, but the seed itself is not
a research gap.

## Return Protocol

The processor returns only status, output paths, paper type, locator mode, and topic-seed count.
