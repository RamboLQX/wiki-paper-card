# wiki-gap-mining

**Status: Beta**

`wiki-gap-mining` analyzes an existing research Wiki to identify unresolved questions, missing evidence, and candidate research directions.

[Back to the project README](../../README.en.md)

## Use it for

- Mining open questions and research gaps within a selected topic.
- Comparing unresolved questions across multiple topics.
- Analyzing candidate directions across the whole Wiki.
- Checking whether later papers have answered earlier questions.

## Example prompts

```text
Use wiki-gap-mining to mine research gaps and candidate directions in <topic-name>.

Use wiki-gap-mining to compare unresolved questions across <topic-one> and <topic-two>.

Use wiki-gap-mining to mine research gaps and candidate directions across the whole research Wiki.
```

## Main outputs

- `work/gap-mining-notes.md`: structured mining notes.
- `work/gap-mining-report.md`: source-grounded gaps, testable directions, and suggested landing pages.
- A write-back plan after user confirmation.

## Processing rules

- It reads only content already present in the Wiki and does not process new papers.
- The first phase is read-only and never edits `wiki/`.
- Candidate gaps require evidence from existing Paper Cards or Topics.
- The deterministic publisher updates Topics only after the user confirms each item.
- Finding no reliable new gap is a valid result; the workflow does not pad the report.

See [`SKILL.md`](SKILL.md) and the [mining brief](references/mining-brief.md) for the full execution rules.

Plain questions, verification, and survey retrieval use the shared [`wiki-shared` retrieval protocol](../wiki-shared/references/retrieval-protocol.md) instead of this Skill.
