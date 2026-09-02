# Batch Mode

Use only when the user explicitly asks to process a directory or batch of papers.

Resolve one processing mode for the whole batch before scanning. When the user
explicitly requests `card-only`, `wiki-topic`, or `wiki-full`, start Phase 0
immediately. If the user gives only a directory plus “处理/分析” and does not
state whether Topic and research-gap work are wanted, ask the router's single
scope question once. Never ask per paper.

## Scan

1. Find PDF files under the requested `raw/papers/` path.
2. Compute each target report path.
3. Skip files whose target report already exists unless the user asks to reprocess.
4. Run all `prepare_paper.py` and `build_kb_context.py` steps outside the main conversation.
5. In `wiki-topic` and `wiki-full`, build `batch-manifest.json` from all
   prepared bundles and use it as the only source for SHA, target page, work
   directory, and batch membership. Skip it in `card-only`.
6. Build the processor pack once per batch with `build_processor_pack.py`; run `--verify` before spawning processors.

## Card Phase

All paper cards are independent. Do not make one card depend on another current card.

- Create a fresh processor for each paper. Do not reuse a completed processor for a different paper.
- Concurrency by host: Claude Code starts up to three processors concurrently for a batch of three and keeps at most three active for larger batches; DeepSeek Harness starts up to six concurrently by default, at most eight; Codex keeps at most three active and also obeys the current session's available subagent slots. Schedule remaining papers as processors finish.
- Every paper writes to its own `work/<paper-name>/` directory.
- Each paper has an independent checkpoint: source bundle, Paper Card,
  evidence report, and card audit reports. The two Wiki modes also require a
  digest and digest reports.
- After a paper passes its audits, close or release its processor before using a new processor for another paper.
- Finalize and audit each card before starting the link phase.

In `card-only`, finish after every Paper Card passes its card audits and return
the `work/` paths. Do not generate digests, link, publish, or write `wiki/`.

## Link Phase

Only for `wiki-topic` and `wiki-full`, after every Paper Card and digest in the batch passes its audits:

1. Finalize and audit all `paper-digest.json` files against the batch manifest.
2. Build one compact existing-wiki context from the combined paper titles.
3. Run one `wiki-linker` agent to compose a schema 3.0 ingest plan from all
   approved digests, the exact current Topic bytes, and the frozen
   `workflow_mode`.
4. Audit the resulting `link-plan.json` against the same manifest.
5. Run `publish_wiki.py` with the same manifest for source pages, topic pages,
   index, and log.

The linker sees all current digests at the same time. Card generation order does not determine cross-paper conclusions.

For `wiki-topic`, the plan must keep every action's `research_gaps` empty and
omit all research-gap mutation fields; the audit enforces this and the
publisher preserves existing gaps. `wiki-full` keeps the complete gap behavior.

## Recovery

- Resume by rescanning target report paths and processing only remaining papers.
- Checks are event-driven: reconcile with `workflow_status.py` only when a processor settles or on session resume. Do not poll on a timer or create round-based re-check loops, and do not print time or round estimates.
- If a processor output is missing without a reported file-tool error, continue
  the same processor for the same paper with a compact instruction.
- Classify parser, escaping, serialization, and payload errors as
  materialization failures rather than content failures. Do not repeat the same
  failed serialization method. Give the same processor one alternative attempt
  with smaller host-native file edits; if it fails, complete the remaining
  artifact serially in the main session. Reuse valid partial outputs and do not
  ask that processor for another full re-analysis.
- Materialization recovery must preserve the complete drafted content and does
  not consume the substantive audit-repair budget. Never shorten a Paper Card
  because a file-edit operation is large.
- If a finalizer error is substantive, send only the reported error items back to the same processor for the same paper.
- Do not ask a processor to start a different paper after its current paper is complete.
- Do not link or publish until all mode-required current outputs pass.
- Recommend at most 15 papers per batch. For larger batches, keep the linker input within the host context limit or split linking by related groups.

## Batch Context

Maintain at most:

```text
title | one-sentence contribution | report path
```

Cap this context at 2000 Chinese characters. The full paper text, complete Paper Cards, and complete digests never enter the main conversation.

## Completion Report

Return:

```text
total
processed
skipped unchanged
failed or needs OCR
created/updated source pages
created/updated topic pages
report links
```

For `card-only`, replace the Wiki counters with the finalized Paper Card paths
and explicitly report that no Wiki write occurred.
