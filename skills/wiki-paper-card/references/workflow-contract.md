# Workflow Contract

## Objective

Process one paper or one batch under the scope selected once at the router:

| Mode | Required outputs | Terminal phase |
|---|---|---|
| `card-only` | finalized and audited `paper-card.md` plus its card audit reports | Phase 2; keep the card in `work/` and perform no `wiki/` writes |
| `wiki-topic` | Paper Cards, digests, source pages, Topic synthesis, index/log/tree/dashboard | Phase 5; preserve existing research gaps and forbid all gap mutations |
| `wiki-full` | the complete current output set, including research-gap synthesis and maintenance | Phase 5 |

The superset of possible outputs is:

```text
source_bundle.json
batch-manifest.json
kb-context.md
processor-pack.md
processor-pack.manifest.json
paper-card.md
paper-digest.json
paper-digest-finalize-report.json
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

Paper cards are generated independently and concurrently. Cross-paper knowledge actions and topic pages are decided only in `wiki-topic` and `wiki-full`, after every card and digest in the batch passes its audits. The selected mode is immutable for the batch.

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
2. Compute each source SHA-256 in `source_bundle.json`.
3. Resolve one work directory per paper. In the two Wiki modes, also resolve
   the target path by mirroring the raw relative path under `wiki/sources/`.
4. Skip unchanged work only when the mode's final target already carries the
   same SHA-256, unless the user asks to reprocess: the audited work card in
   `card-only`, or the published source page in either Wiki mode.
5. Run the pinned `prepare_paper.py` for every paper.
6. In `wiki-topic` and `wiki-full`, after all source bundles exist, build the batch identity manifest once. Skip this step in `card-only`:

```bash
python "<REPO_ROOT>/scripts/batch_manifest.py" \
  --wiki-root "<VAULT_ROOT>" \
  --work-root "<BATCH_WORKDIR>" \
  --output "<BATCH_WORKDIR>/batch-manifest.json"
```

The manifest recomputes each source SHA-256 and derives `source_ref` from the
path below `raw/`. It fails on changed source bytes, path escape, duplicate
target pages, or duplicate work directories. Treat its `source_path`,
`source_sha256`, `source_ref`, and `work_dir` as system-owned identity fields;
do not ask an Agent to infer them again.

7. Build the processor pack once per batch:

```bash
python "<REPO_ROOT>/scripts/build_processor_pack.py" \
  --output "<BATCH_WORKDIR>/processor-pack.md" \
  --manifest "<BATCH_WORKDIR>/processor-pack.manifest.json"
```

The pack merges every reference a processor must read into one document,
including the shared reader-facing writing guide.
Run it with `--verify` before spawning processors to assert the pinned
sources are unchanged since the pack was built.

8. Build compact existing-wiki context for every paper:

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
mode-required output path
```

In the two Wiki modes, read these values from `batch-manifest.json` and
`source_bundle.json`; do not retype or shorten paths in a subagent prompt. In
`card-only`, use `source_bundle.json` for source metadata and do not invent a
future Wiki target.

Full paper text must not enter the main conversation.

`build_kb_context.py --max-pages` is a global cap across source and topic
pages combined, not a separate allowance for each page type. Context notes
recognize the current `## 争议与不确定` heading and the historical
`## 争议与矛盾` spelling.

## Phase 1: Paper Cards

Processor role: `wiki-processor` under Claude Code; a fresh processor subagent using the shared processor brief under DSH or Codex.

One processor per paper:

1. Reads the processor pack once. If no pack was built, it reads the processor
   brief, upstream router and manifest dependencies, shared knowledge model,
   shared writing guide, and applicable paper-type lens individually. It also
   reads the paper digest schema in either Wiki mode.
2. Reads the source bundle once.
3. Reads `kb-context.md`.
4. Writes the complete Sections 01-16 `paper-card.md`.
5. In `wiki-topic` and `wiki-full`, writes the paper-local
   `paper-digest.json` (see the digest schema). In `card-only`, it must not
   spend time generating a digest.

The processor does not run audit scripts, read `raw/`, write `wiki/`, or return full paper text.

### Concurrency

- All paper-card processors are logically independent.
- Create a fresh processor subagent for each paper. Do not reuse a completed processor for a different paper.
- Claude Code: start up to three processors concurrently for a three-paper batch. For larger batches, keep at most three active and schedule the remaining papers as processors finish.
- DeepSeek Harness: start up to six processors concurrently by default, at most eight. Keep the same all-pass ordering gate regardless of host (see Phase 3).
- Codex: keep at most three processors active and never exceed the current session's available subagent slots. Keep the same all-pass ordering gate.
- Every paper writes to its own `work/<paper-name>/` directory.

### Completion And Recovery

- A `card-only` processor is complete when `paper-card.md` exists and is non-empty. A processor in either Wiki mode is complete only when both `paper-card.md` and `paper-digest.json` exist and are non-empty.
- A subagent status message is not completion proof.
- Checks are event-driven, not timer-driven. Run the deterministic status check only when a new completion signal arrives: a processor subagent settles, the host reports a finished background job, or a continuation instruction was just answered:

```bash
python "<REPO_ROOT>/scripts/workflow_status.py" \
  --work-dir "<BATCH_WORKDIR>" \
  --mode "<card-only|wiki-topic|wiki-full>"
```

Treat its exit status and `INCOMPLETE` lines as the only completion fact.

- After spawning processors, do not poll. Do not re-run the status check on a timer, do not create a round-based re-check loop (for example a goal round that reconciles every few minutes), and do not compute or print elapsed-time or rounds-based estimates. A processor takes minutes to tens of minutes; intermediate checks add nothing. When all spawned processors are still running, end the turn and wait for their completion notices.
- If a completion signal leaves a free processor slot, emit the next action in the same turn (spawn the next processor or start finalize). Do not end the turn after only writing a sentence that describes the next step.
- If a required output is missing without a reported materialization failure,
  send a continuation instruction to the same subagent naming only the
  mode-required files. Never request a digest in `card-only`.
- A file-tool parser, escaping, serialization, or payload error is a
  materialization failure. Do not repeat the same failed serialization method.
  Ask the same processor for one alternative materialization attempt using
  smaller host-native file edits, then check the files immediately when it
  returns. If that attempt fails, run the remaining artifact serially in the
  main session without asking the processor to re-analyze the paper.
- A materialization failure does not consume a substantive audit-repair
  attempt. Allow at most three substantive content or audit repairs before
  running that paper serially. Never shorten a Paper Card to fit a file-edit
  operation or to recover time.
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

In `card-only`, the successful Paper Card finalizer and its audits end the
workflow. Return the finalized `work/<paper>/paper-card.md` path; do not run a
digest command, linker, publisher, or any command that writes `wiki/`.

In `wiki-topic` and `wiki-full`, inject the digest fields that are mechanically
determined by the batch manifest. This command changes only
`paper.source_sha256`, `paper.source_ref`, and each Topic seed's single-paper
`papers` list, and records every change:

```bash
python "<REPO_ROOT>/scripts/finalize_paper_digest.py" \
  --digest "<WORKDIR>/paper-digest.json" \
  --manifest "<BATCH_WORKDIR>/batch-manifest.json" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<WORKDIR>/paper-digest-finalize-report.json"
```

Then validate the paper digest against the same manifest:

```bash
python "<REPO_ROOT>/scripts/audit_paper_digest.py" \
  --digest "<WORKDIR>/paper-digest.json" \
  --manifest "<BATCH_WORKDIR>/batch-manifest.json" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<WORKDIR>/paper-digest-report.json"
```

Audit errors block the link phase. If correction is needed, send only the exact error items to the same processor; do not ask it to reread all instructions, the full bundle, or run audit scripts.

## Phase 3: Batch Link

Only in `wiki-topic` and `wiki-full`, after every Paper Card and digest passes:

1. Build one compact existing-wiki context for the batch with the combined paper titles:

```bash
python "<REPO_ROOT>/scripts/build_kb_context.py" \
  --wiki-root "<VAULT_ROOT>" \
  --query "<COMBINED_PAPER_TITLES>" \
  --output "<BATCH_WORKDIR>/kb-context.md"
```

2. Run one `wiki-linker` agent. Under Codex, create one fresh linker subagent using the shared linker brief; do not start it before the all-pass gate.

The linker receives the frozen `workflow_mode` and:

1. Reads [linker-brief.md](linker-brief.md) and [link-plan-schema.md](link-plan-schema.md).
2. Reads `batch-manifest.json` once and copies `batch.source_pages[].source_ref`
   and `work_dir` from it without editing.
3. Reads every approved `paper-digest.json` once.
4. Reads the batch existing-wiki context.
5. Reads the exact current bytes of every Topic it plans to update and records
   `base_topic_sha256` before composing the complete schema 3.0 narrative.
6. Writes one `link-plan.json` in the batch work directory with the same
   top-level `workflow_mode`.

In `wiki-topic`, every action must use `research_gaps: []` and must omit
`remove_research_gap_ids`, legacy `remove_research_gaps`, and
`annotate_research_gaps`. It must not convert a rejected gap candidate into an
open question. Existing Topic research gaps are preserved by the publisher.
In `wiki-full`, the existing research-gap synthesis and lifecycle rules apply.

For a single paper, the linker may only update an existing topic page that the paper directly connects to or answers. It cannot create a topic from one paper alone.

## Phase 4: Link Plan Audit

```bash
python "<REPO_ROOT>/scripts/audit_link_plan.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --manifest "<BATCH_WORKDIR>/batch-manifest.json" \
  --report "<BATCH_WORKDIR>/link-plan-report.json"
```

Audit errors block wiki writes.

New ingest plans use schema 3.0 and must define `workflow_mode` as
`wiki-topic` or `wiki-full`. The audit verifies that paper-card actions own
the complete narrative and evidence ledger, while mining actions cannot write
those fields. In `wiki-topic`, it additionally rejects any research-gap
content or mutation field. Both entrances use stable open-item IDs and the Topic hash;
answered questions and gaps additionally require source-bound `answered_by`
and `answered_pointer` evidence. Schema 2.0 remains available for historical
plans only.

## Phase 5: Deterministic Wiki Publish

```bash
python "<REPO_ROOT>/scripts/publish_wiki.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --wiki-root "<VAULT_ROOT>" \
  --manifest "<BATCH_WORKDIR>/batch-manifest.json" \
  --report "<BATCH_WORKDIR>/publish-report.json"
```

The publisher:

1. Re-checks the link plan with the deterministic link-plan audit and requires
   exact batch membership, `work_dir`, and `source_ref` agreement with the
   supplied manifest.
2. Preflights every reference before any write: each source page named by topic `papers`, research-gap/progress `source_refs`, or answered evidence must be either part of the current batch or an existing page under `wiki/sources/`, and every batch source page must have a finalized `paper-card.md`. Any missing, escaping, or non-`wiki/sources/` reference blocks the whole publish.
3. Writes every finalized current source page and appends its `## 关联页面` backlinks.
4. Applies only `create_topic` and `update_topic` actions.
5. Updates `wiki/index.md` and `wiki/log.md`.
6. Preserves `created` on updates, avoids duplicate index entries, and skips unchanged files.
7. Upserts flat comparison rows by stable `source_ref` instead of display name, preserving existing order and unrelated rows; grouped comparison sections remain complete replacements.
8. Rebuilds `wiki/meta/knowledge-tree.md` (shared human/Agent tree: per domain, topics as signpost nodes with nested papers and open items, plus unassigned papers, then the category-first topic view) and `wiki/meta/research.md` (domain-grouped dashboard: currently open questions and research gaps) from the current wiki state. Both aggregate only open items; answered items are archived on the topic pages and excluded. Legacy `wiki/meta/agent-tree.md` files are left untouched and may be deleted after upgrading.

For schema 3.0, ingest replaces the publisher-owned narrative sections as
complete units and merges comparison/open-item state deterministically.
`wiki-topic` supplies no gap changes, so prior research gaps remain unchanged;
`wiki-full` may apply the normal gap lifecycle. Stable
IDs, origins, research-gap progress/resolution records, annotations, narrative-refresh state, and the replay fingerprint live in
`wiki/meta/topic-state/*.json`; no publisher protocol appears in Topic
Markdown. Mining preserves narrative and comparison content byte-for-byte,
changing only stable-ID open items and monotonic source/backlink membership. A stale Topic
hash blocks the complete plan before any write; an exact action replay is a
no-op. A mining answer emits structured `narrative_refresh` targets and adds a
visible, deterministic refresh notice. The gap-mining orchestrator batches
those targets into one fresh `purpose: "refresh"` linker run without rerunning
paper processors. A successful refresh absorbs the answer into the complete
reader-facing synthesis and clears the notice; failure preserves it for retry.
New schema 3.0 Topics include `## 研究者备注`; ingest, mining, and refresh preserve its
contents byte-for-byte. Existing Topics are not force-migrated merely to add it.

Refresh plans are schema 3.0 only. They have no batch source pages and may only
update Topics whose sidecars have a pending narrative refresh. They own the
same complete narrative/evidence/comparison fields as ingest, but cannot
create Topics or mutate open items, category, or page status. Exact replays are
no-ops and stale hashes block the complete refresh before any write.

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
