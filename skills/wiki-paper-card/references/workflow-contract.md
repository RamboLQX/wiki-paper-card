# Workflow Contract

## Objective

Process one paper or one batch into:

```text
source_bundle.json
kb-context.md
processor-pack.md
processor-pack.manifest.json
paper-card.md
paper-digest.json
paper-digest-report.json
evidence-coverage-report.json
formula-report.json
html-lint-report.json
audit-report.json
wiki-audit-report.json
link-plan.json
link-plan-report.json
publish-report.json
wiki source pages
optional topic pages
wiki/meta/research.md (research dashboard: currently open questions and gaps, question-type-first view of the same topic-page data the knowledge tree shows topic-first)
updated index and log
```

Paper cards are generated independently and concurrently. Cross-paper knowledge actions and topic pages are decided only after every card and digest in the batch passes its audits.

## Phase 0: Deterministic Preparation

Resolve `<REPO_ROOT>` once, deterministically, never by guessing: prefer the
`WIKI_PAPER_CARD_ROOT` environment variable, then the pointer file written by
`install.sh` (`<host-root>/WIKI_PAPER_CARD_ROOT`; DSH: `<VAULT_ROOT>/.dsh/`,
Claude Code: `<VAULT_ROOT>/.claude/`, Codex: `<VAULT_ROOT>/.agents/`), then for DSH the `readlink -f` rule in
`adapters/dsh/dsh-mode.md`. Verify `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md`
is readable before proceeding; if resolution fails, stop and report. Use absolute
script and reference paths in every subagent prompt. Do not ask a subagent to
rediscover the pinned `vendor/` location.

1. Identify every PDF or supported paper input.
2. Compute each source SHA-256.
3. Resolve each target path by mirroring the raw relative path under `wiki/sources/`.
4. Skip papers whose target report has the same SHA-256 unless the user asks to reprocess.
5. Run the pinned `prepare_paper.py` for every paper.
6. Build the processor pack once per batch:

```bash
python "<REPO_ROOT>/scripts/build_processor_pack.py" \
  --output "<BATCH_WORKDIR>/processor-pack.md" \
  --manifest "<BATCH_WORKDIR>/processor-pack.manifest.json"
```

The pack merges every reference a processor must read into one document.
Run it with `--verify` before spawning processors to assert the pinned
sources are unchanged since the pack was built.

7. Build compact existing-wiki context for every paper:

```bash
python "<REPO_ROOT>/scripts/build_kb_context.py" \
  --wiki-root "<VAULT_ROOT>" \
  --query "<PAPER_TITLE_OR_PATH>" \
  --output "<WORKDIR>/kb-context.md"
```

The main session receives only:

```text
source path
source SHA-256
page count
recommended locator mode
extraction confidence
target report path
```

Full paper text must not enter the main conversation.

`build_kb_context.py --max-pages` is a global cap across source and topic
pages combined, not a separate allowance for each page type. Context notes
recognize the current `## 争议与不确定` heading and the historical
`## 争议与矛盾` spelling.

## Phase 1: Paper Cards

Processor role: `wiki-processor` under Claude Code; a fresh processor subagent using the shared processor brief under DSH or Codex.

One processor per paper:

1. Reads the processor pack once (or, when no pack was built, the individual sources listed in Phase 0 step 6).
2. Reads the source bundle once.
3. Reads `kb-context.md`.
4. Writes the complete Sections 01-16 `paper-card.md`.
5. Writes the paper-local `paper-digest.json` (see the digest schema).

The processor does not run audit scripts, read `raw/`, write `wiki/`, or return full paper text.

### Concurrency

- All paper-card processors are logically independent.
- Create a fresh processor subagent for each paper. Do not reuse a completed processor for a different paper.
- Claude Code: start up to three processors concurrently for a three-paper batch. For larger batches, keep at most three active and schedule the remaining papers as processors finish.
- DeepSeek Harness: start up to six processors concurrently by default, at most eight. Keep the same all-pass ordering gate regardless of host (see Phase 3).
- Codex: keep at most three processors active and never exceed the current session's available subagent slots. Keep the same all-pass ordering gate.
- Every paper writes to its own `work/<paper-name>/` directory.

### Completion And Recovery

- A processor is complete only when `paper-card.md` and `paper-digest.json` both exist and are non-empty.
- A subagent status message is not completion proof.
- Checks are event-driven, not timer-driven. Run the deterministic status check only when a new completion signal arrives: a processor subagent settles, the host reports a finished background job, or a continuation instruction was just answered:

```bash
python "<REPO_ROOT>/scripts/workflow_status.py" --work-dir "<BATCH_WORKDIR>"
```

Treat its exit status and `INCOMPLETE` lines as the only completion fact.

- After spawning processors, do not poll. Do not re-run the status check on a timer, do not create a round-based re-check loop (for example a goal round that reconciles every few minutes), and do not compute or print elapsed-time or rounds-based estimates. A processor takes minutes to tens of minutes; intermediate checks add nothing. When all spawned processors are still running, end the turn and wait for their completion notices.
- If a completion signal leaves a free processor slot, emit the next action in the same turn (spawn the next processor or start finalize). Do not end the turn after only writing a sentence that describes the next step.
- If either output is missing, send a continuation instruction to the same subagent: `Continue until both output files exist. Do not return a summary before they are written.`
- Check files after each continuation. Allow at most three attempts before running that paper serially.
- A processor may continue only on the same paper. After that paper passes its audits, close or release the processor before creating one for another paper.
- Never describe a paper with missing outputs as complete.

## Phase 2: Deterministic Finalize

For every paper:

```bash
python "<REPO_ROOT>/scripts/finalize_paper_card.py" \
  --card "<WORKDIR>/paper-card.md" \
  --bundle "<WORKDIR>/source_bundle.json" \
  --repo-root "<REPO_ROOT>" \
  --wiki-root "<VAULT_ROOT>"
```

The finalizer:

1. Normalizes wrappers, frontmatter, and line endings.
2. Verifies formula delimiters, table placement, and that no raw inline HTML tags remain in card text (a literal like `<image>` breaks Obsidian Live Preview rendering; wrap literals in backticks).
3. Classifies main and supplementary evidence, writes `evidence-coverage-report.json`, and creates a filtered `audit-bundle.json`.
4. Blocks visible standalone evidence coverage lists.
5. Runs the upstream paper audit and wiki audit.
6. Writes `formula-report.json`, `html-lint-report.json`, `audit-report.json`, and `wiki-audit-report.json`.

Then validate the paper digest:

```bash
python "<REPO_ROOT>/scripts/audit_paper_digest.py" \
  --digest "<WORKDIR>/paper-digest.json" \
  --report "<WORKDIR>/paper-digest-report.json"
```

Audit errors block the link phase. If correction is needed, send only the exact error items to the same processor; do not ask it to reread all instructions, the full bundle, or run audit scripts.

## Phase 3: Batch Link

After every paper card and digest passes:

1. Build one compact existing-wiki context for the batch with the combined paper titles:

```bash
python "<REPO_ROOT>/scripts/build_kb_context.py" \
  --wiki-root "<VAULT_ROOT>" \
  --query "<COMBINED_PAPER_TITLES>" \
  --output "<BATCH_WORKDIR>/kb-context.md"
```

2. Run one `wiki-linker` agent. Under Codex, create one fresh linker subagent using the shared linker brief; do not start it before the all-pass gate.

The linker:

1. Reads [linker-brief.md](linker-brief.md) and [link-plan-schema.md](link-plan-schema.md).
2. Reads every approved `paper-digest.json` once.
3. Reads the batch existing-wiki context.
4. Reads the exact current bytes of every Topic it plans to update and records
   `base_topic_sha256` before composing the complete schema 3.0 narrative.
5. Writes one `link-plan.json` in the batch work directory.

For a single paper, the linker may only update an existing topic page that the paper directly connects to or answers. It cannot create a topic from one paper alone.

## Phase 4: Link Plan Audit

```bash
python "<REPO_ROOT>/scripts/audit_link_plan.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --report "<BATCH_WORKDIR>/link-plan-report.json"
```

Audit errors block wiki writes.

New ingest plans use schema 3.0. The audit verifies that paper-card actions own
the complete narrative and evidence ledger, while mining actions cannot write
those fields. Both entrances use stable open-item IDs and the Topic hash;
answered questions and gaps additionally require source-bound `answered_by`
and `answered_pointer` evidence. Schema 2.0 remains available for historical
plans only.

## Phase 5: Deterministic Wiki Publish

```bash
python "<REPO_ROOT>/scripts/publish_wiki.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<BATCH_WORKDIR>/publish-report.json"
```

The publisher:

1. Re-checks the link plan with the deterministic link-plan audit.
2. Preflights every reference before any write: each source page named by topic `papers`, research-gap `source_refs`, or answered evidence must be either part of the current batch or an existing page under `wiki/sources/`, and every batch source page must have a finalized `paper-card.md`. Any missing, escaping, or non-`wiki/sources/` reference blocks the whole publish.
3. Writes every finalized current source page and appends its `## 关联页面` backlinks.
4. Applies only `create_topic` and `update_topic` actions.
5. Updates `wiki/index.md` and `wiki/log.md`.
6. Preserves `created` on updates, avoids duplicate index entries, and skips unchanged files.
7. Merges new comparison rows into the existing topic comparison table (dedup by paper) instead of appending per-batch sub-tables.
8. Rebuilds `wiki/meta/knowledge-tree.md` (human navigation tree: per domain, topics as signpost nodes with nested papers and open items, plus unassigned papers, then the category-first topic view), `wiki/meta/agent-tree.md` (agent retrieval first hop: domain and topic signposts only), and `wiki/meta/research.md` (domain-grouped dashboard: currently open questions and research gaps) from the current wiki state. All three aggregate only open items; answered items are archived on the topic pages and excluded.

For schema 3.0, ingest replaces the three managed narrative blocks as complete
units and merges comparison/open-item state deterministically. Mining preserves
the managed narrative and comparison table byte-for-byte, changing only
stable-ID open items and monotonic source/backlink membership. A stale Topic
hash blocks the complete plan before any write; an exact action replay is a
no-op. A mining answer emits `narrative_refresh_recommended` so the next ingest
can absorb that evidence into the reader-facing synthesis.

After publishing, run the deterministic wiki-state audit. The Obsidian render
smoke check is optional and soft-failing by default:

```bash
python "<REPO_ROOT>/scripts/audit_wiki_state.py" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<BATCH_WORKDIR>/wiki-state-report.json"

# Optional: verify rendering in a running Obsidian (skipped when the
# Obsidian CLI is unavailable; add --strict to make it a hard gate).
python "<REPO_ROOT>/scripts/smoke_obsidian.py" \
  --report "<BATCH_WORKDIR>/publish-report.json" \
  --output "<BATCH_WORKDIR>/smoke-obsidian-report.json"
```

Do not run a wiki-integrator agent. The publisher does not promote local candidates into pages, invent duplicate aliases, or rewrite unrelated prose.

## Return Protocol

The main session receives at most:

```text
status
report wiki-link
publish-report path
one-sentence contribution
created source/topic page counts
updated page counts
```

On failure, report which phase failed. A partial file must not be described as a complete ingest.

### User-Facing Closing Summary

When the run settles, the main agent explains to the user, in the user's
language:

- which pages were created or updated under `wiki/`, listed with wikilinks;
- which `work/` files were produced, one line each, and which intermediate
  files the user does not need to read;
- whether anything awaits the user's decision (an ingest run normally has
  none).

When the user asks what a file means, point them to `docs/artifacts.md`.

## Context Budget

- Full paper text stays inside the processor.
- The main session never reads raw paper text, complete Paper Cards, or complete digests.
- Batch context contains only title, one-sentence contribution, and report path.
- `kb-context.md` and linker inputs are capped by deterministic scripts.
- The linker reads compact digests, not complete Paper Cards.
