# Paper Digest Schema

`wiki-processor` writes one `paper-digest.json` per paper. The digest is a compact paper-local record used by the batch linker. It must not contain wiki actions.

## Top-Level Fields

```json
{
  "schema_version": "1.0",
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
    "datasets": [],
    "models": [],
    "metrics": [],
    "key_results": [],
    "limitations": [],
    "critical_observations": [],
    "open_questions": []
  },
  "candidates": [],
  "topic_seeds": []
}
```

## Analysis

- `one_sentence_summary`, `problem`, and `method` are required strings.
- `datasets`, `models`, and `metrics` are compact string lists.
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

## Candidate

```json
{
  "id": "stable-id",
  "name": "Canonical name",
  "kind": "concept|entity",
  "tier": "L0|L1|L2",
  "aliases": [],
  "definition": "One or two sentences.",
  "passed_gates": [1, 3, 4, 5],
  "source_refs": ["wiki/sources/current/paper.md"],
  "evidence": [
    {
      "pointer": "[Paper: PDF p. 3, Fig. 2]",
      "claim": "What the source reports."
    }
  ],
  "relations": []
}
```

- Candidate records do not have `action`. Promotion is decided by `wiki-linker` after the batch.
- `tier` is a provisional local classification.
- `passed_gates` must contain at least three values from `1` through `5`.
- Every evidence row needs `pointer` and `claim`.

## Relation

```json
{
  "type": "supports",
  "target": "Canonical target name",
  "pointer": "[Paper: PDF p. 5]",
  "provenance": "Paper|External|Analysis|Hypothesis|User",
  "confidence": "high|medium|low"
}
```

`type` must come from the knowledge model relationship list.

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

The processor returns only status, output paths, paper type, locator mode, candidate counts, and topic-seed count.
