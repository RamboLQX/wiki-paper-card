# wiki-paper-card

**Status: Stable**

`wiki-paper-card` turns one paper or a topic folder into a source-grounded, connected research Wiki.

[Back to the project README](../../README.en.md)

## Use it for

- Analyzing one PDF or `nature-reader` source map.
- Batch-processing a research-topic folder.
- Regenerating an existing Paper Card.
- Creating or updating cross-paper Topics when admission rules are met.

## Example prompts

```text
Use wiki-paper-card to process raw/papers/example.pdf.

Use wiki-paper-card to batch-process every paper under raw/papers/<topic-name>/.

Use wiki-paper-card to reprocess raw/papers/example.pdf.
```

## Main outputs

- Paper Cards under `wiki/sources/papers/`.
- Admitted Topics under `wiki/topics/`.
- Updated index, knowledge tree, and log.
- Intermediate reports and audits under `work/`.

## Processing rules

- Paper Cards preserve the research question, methods, experiments, conclusions, limitations, and source locators.
- Every paper is analyzed and audited independently before cross-paper linking begins.
- A Topic requires at least two papers sharing a problem, mechanism, or evidence space.
- `raw/` remains read-only, and final knowledge pages are written through the deterministic publisher.

See [`SKILL.md`](SKILL.md) and the [workflow contract](references/workflow-contract.md) for the full execution rules.

Knowledge-base questions, verification, and survey retrieval use the shared [`wiki-shared` retrieval protocol](../wiki-shared/references/retrieval-protocol.md).
