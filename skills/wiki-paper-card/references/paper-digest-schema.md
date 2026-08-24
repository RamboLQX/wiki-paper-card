# Paper Digest Schema

`wiki-processor` writes one `paper-digest.json` per paper. The digest is a compact paper-local record used by the batch linker and the deterministic publisher. It must not contain wiki actions.

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
    "one_sentence_summary": "One bounded sentence.",
    "problem": "Problem and research question.",
    "method": "Core method and mechanism.",
    "key_results": [],
    "limitations": [],
    "critical_observations": [],
    "open_questions": []
  },
  "topic_seeds": []
}
```

## Analysis

- `one_sentence_summary`, `problem`, and `method` are required strings.
- Public datasets, benchmarks, model families, and metrics stay in the Paper Card's Sections 14-16 as plain text; the digest does not carry artifact lists and there are no entity pages.
- `key_results` records the main bounded results:

```json
{
  "claim": "What the paper reports.",
  "pointer": "[Paper: PDF p. 6, Table 2]",
  "confidence": "high|medium|low"
}
```

- `limitations` and `critical_observations` use `statement` or `observation` plus `pointer`.
- Keep the complete detail in `paper-card.md`. The digest supports linking, not replacement of the card.

## Topic Seed

```json
{
  "id": "topic-id",
  "name": "Topic name",
  "papers": ["wiki/sources/current/paper.md"],
  "summary": "Short synthesis.",
  "open_questions": [],
  "research_gaps": []
}
```

A topic seed is a proposal for the linker, not a publish action.

## Return Protocol

The processor returns only status, output paths, paper type, locator mode, and topic-seed count.
