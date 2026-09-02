# wiki-paper-card

**Status: Stable**

`wiki-paper-card` turns one paper or a topic folder into source-grounded Paper Cards and optionally connects them to a research Wiki.

[Back to the project README](../../README.en.md)

## Use it for

- Analyzing one PDF or `nature-reader` source map.
- Batch-processing a research-topic folder.
- Regenerating an existing Paper Card.
- Creating or updating cross-paper Topics when admission rules are met.
- Writing reader-facing Paper Cards and evidence-linked Topic prose, with clean Markdown footnotes and sidecar state instead of visible publisher protocol.

## Example prompts

```text
Use wiki-paper-card in card-only mode for raw/papers/example.pdf. I only need the Paper Card.

Use wiki-paper-card in wiki-topic mode for raw/papers/<topic-name>/. Maintain Topics without research-gap work.

Use wiki-paper-card in wiki-full mode for raw/papers/<topic-name>/, including research-gap maintenance.
```

When scope is omitted, the Agent asks once before starting and never once per paper.

## Main outputs

- `card-only` delivers audited Paper Cards under `work/` and does not write `wiki/`.
- The two Wiki modes publish Paper Cards under `wiki/sources/papers/`.
- Admitted Topics under `wiki/topics/`.
- Updated index, knowledge tree, and log.
- Intermediate reports and audits under `work/`.

See [docs/artifacts.md](../../docs/artifacts.md) (written in Chinese) for the meaning of every artifact and the complete workflows.

## Processing rules

- Paper Cards explain the research question, methods, experiments, conclusions, limitations, and research ideas in readable prose while preserving source locators and comparison tables.
- Every paper is analyzed and audited independently before cross-paper linking begins.
- `wiki-topic` preserves existing research gaps without creating, progressing, answering, annotating, or removing them; only `wiki-full` applies the complete gap lifecycle.
- A Topic requires at least two papers sharing a problem, mechanism, or evidence space.
- `raw/` remains read-only, and final knowledge pages are written through the deterministic publisher.

See [`SKILL.md`](SKILL.md) and the [workflow contract](references/workflow-contract.md) for the full execution rules.

Knowledge-base questions, verification, and survey retrieval use the shared [`wiki-shared` retrieval protocol](../wiki-shared/references/retrieval-protocol.md).
