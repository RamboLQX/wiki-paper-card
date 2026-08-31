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

- `work/gap-mining-notes.md`: the mining agent's working notes. This is an intermediate artifact; you do not need to read it.
- `work/gap-mining-report.md`: the gap report for you, with source evidence, testable directions, and suggested landing pages. The 待确认清单 at the end lists each candidate for your confirmation.
- After you confirm, the deterministic publisher writes the results back into the 开放问题 and 研究空白与候选方向 sections of topic pages and refreshes the research dashboard.

Without your confirmation nothing in `wiki/` changes. See [docs/artifacts.md](../../docs/artifacts.md) (written in Chinese) for the complete explanation of every artifact.

## Processing rules

- It reads only content already present in the Wiki and does not process new papers.
- The first phase is read-only and never edits `wiki/`.
- Candidate gaps require evidence from existing Paper Cards or Topics.
- The deterministic publisher updates Topics only after the user confirms each item.
- Write-back maintains only stable-ID open questions and research gaps; it cannot rewrite Topic narrative or comparisons, and stale plans are rejected before writes.
- Finding no reliable new gap is a valid result; the workflow does not pad the report.

See [`SKILL.md`](SKILL.md) and the [mining brief](references/mining-brief.md) for the full execution rules.

Plain questions, verification, and survey retrieval use the shared [`wiki-shared` retrieval protocol](../wiki-shared/references/retrieval-protocol.md) instead of this Skill.
