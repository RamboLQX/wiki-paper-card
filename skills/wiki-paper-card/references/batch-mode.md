# Batch Mode

Use only when the user explicitly asks to process a directory or batch of papers.

When the input path and scope are unambiguous, start scanning and Phase 0
immediately. Do not stop for a plan-confirmation turn unless the user asks for
one or the requested directory is ambiguous.

## Scan

1. Find PDF files under the requested `raw/papers/` path.
2. Compute each target report path.
3. Skip files whose target report already exists unless the user asks to reprocess.
4. Run all `prepare_paper.py` and `build_kb_context.py` steps outside the main conversation.
5. Build the processor pack once per batch with `build_processor_pack.py`; run `--verify` before spawning processors.

## Card Phase

All paper cards are independent. Do not make one card depend on another current card.

- Create a fresh processor for each paper. Do not reuse a completed processor for a different paper.
- Concurrency by host: Claude Code starts up to three processors concurrently for a batch of three and keeps at most three active for larger batches; DeepSeek Harness starts up to six concurrently by default, at most eight. Schedule remaining papers as processors finish.
- Every paper writes to its own `work/<paper-name>/` directory.
- Each paper has an independent checkpoint: source bundle, Paper Card, digest, evidence report, and audit reports.
- After a paper passes its audits, close or release its processor before using a new processor for another paper.
- Finalize and audit each card before starting the link phase.

## Link Phase

Only after every paper card and digest in the batch passes its audits:

1. Collect all `paper-digest.json` paths.
2. Build one compact existing-wiki context from the combined paper titles.
3. Run one `wiki-linker` agent.
4. Audit the resulting `link-plan.json`.
5. Run the deterministic `publish_wiki.py` command for source pages, L2 hubs, topic pages, index, and log.

The linker sees all current digests at the same time. Card generation order does not determine cross-paper conclusions.

## Recovery

- Resume by rescanning target report paths and processing only remaining papers.
- If a processor output is missing, continue the same processor for the same paper with a compact instruction.
- If a finalizer error is substantive, send only the reported error items back to the same processor for the same paper.
- Do not ask a processor to start a different paper after its current paper is complete.
- Do not link or publish until all current cards and digests pass.
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
created/updated hub pages
created/updated topic pages
report links
```
