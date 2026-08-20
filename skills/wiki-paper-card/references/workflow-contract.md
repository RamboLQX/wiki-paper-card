# Workflow Contract

## Objective

Process one paper or one batch into:

```text
source_bundle.json
kb-context.md
paper-card.md
paper-digest.json
paper-digest-report.json
evidence-coverage-report.json
formula-report.json
audit-report.json
wiki-audit-report.json
link-plan.json
link-plan-report.json
publish-report.json
wiki source pages
L2 hub pages
optional topic pages
wiki/meta/candidates.md (L1 candidate ledger)
updated index and log
```

Paper cards are generated independently and concurrently. Cross-paper knowledge actions and topic pages are decided only after every card and digest in the batch passes its audits.

## Phase 0: Deterministic Preparation

Resolve `<REPO_ROOT>` once from the loaded skill directory or the
`WIKI_PAPER_CARD_ROOT` environment variable. Use absolute script and reference
paths in every subagent prompt. Do not ask a subagent to rediscover the pinned
`vendor/` location.

1. Identify every PDF or supported paper input.
2. Compute each source SHA-256.
3. Resolve each target path by mirroring the raw relative path under `wiki/sources/`.
4. Skip papers whose target report has the same SHA-256 unless the user asks to reprocess.
5. Run the pinned `prepare_paper.py` for every paper.
6. Build compact existing-wiki context for every paper:

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

## Phase 1: Paper Cards

Claude Code processor agent: `wiki-processor`.

One processor per paper:

1. Reads [processor-brief.md](processor-brief.md) and [paper-digest-schema.md](paper-digest-schema.md).
2. Reads the source bundle once.
3. Reads `kb-context.md`.
4. Writes the complete Sections 01-16 `paper-card.md`.
5. Writes the paper-local `paper-digest.json`.

The processor does not run audit scripts, read `raw/`, write `wiki/`, or return full paper text.

### Concurrency

- All paper-card processors are logically independent.
- Create a fresh processor subagent for each paper. Do not reuse a completed processor for a different paper.
- Claude Code starts up to three processors concurrently for a three-paper batch. For larger batches, keep at most three active and schedule the remaining papers as processors finish.
- Every paper writes to its own `work/<paper-name>/` directory.

### Completion And Recovery

- A processor is complete only when `paper-card.md` and `paper-digest.json` both exist and are non-empty.
- A subagent status message is not completion proof.
- A subagent return or wake is only a signal to re-check filesystem state, not a completion result. After every return or wake, run the deterministic status check and treat its exit status and `INCOMPLETE` lines as the only completion fact:

```bash
python "<REPO_ROOT>/scripts/workflow_status.py" --work-dir "<BATCH_WORKDIR>"
```

- If a return or wake leaves a free processor slot, emit the next action in the same turn (spawn the next processor or start finalize). Do not end the turn after only writing a sentence that describes the next step.
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
2. Verifies formula delimiters and table placement.
3. Classifies main and supplementary evidence, writes `evidence-coverage-report.json`, and creates a filtered `audit-bundle.json`.
4. Blocks visible standalone evidence coverage lists.
5. Runs the upstream paper audit and wiki audit.
6. Writes `formula-report.json`, `audit-report.json`, and `wiki-audit-report.json`.

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

2. Run the `wiki-linker` agent.

The linker:

1. Reads [linker-brief.md](linker-brief.md) and [link-plan-schema.md](link-plan-schema.md).
2. Reads every approved `paper-digest.json` once.
3. Reads the batch existing-wiki context.
4. Writes one `link-plan.json` in the batch work directory.

For a single paper, the linker may only update an existing hub or topic page that the paper directly connects to or answers. It cannot create a new hub or topic from one paper alone.

## Phase 4: Link Plan Audit

```bash
python "<REPO_ROOT>/scripts/audit_link_plan.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --report "<BATCH_WORKDIR>/link-plan-report.json"
```

Audit errors block wiki writes.

## Phase 5: Deterministic Wiki Publish

```bash
python "<REPO_ROOT>/scripts/publish_wiki.py" \
  --plan "<BATCH_WORKDIR>/link-plan.json" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<BATCH_WORKDIR>/publish-report.json"
```

The publisher:

1. Re-checks the link plan with the deterministic link-plan audit.
2. Writes every finalized current source page and appends its `## 关联页面` backlinks.
3. Applies only `create_hub`, `update_hub`, `create_topic`, and `update_topic` actions.
4. Updates explicit relationships, contradictions, `wiki/index.md`, and `wiki/log.md`.
5. Preserves `created` on updates, avoids duplicate index entries, and skips unchanged files.
6. Merges new comparison rows into the existing topic comparison table (dedup by paper) instead of appending per-batch sub-tables.
7. Appends pending L1 candidates to `wiki/meta/candidates.md` (dedup by id) so a later batch can promote them to L2.

Do not run a wiki-integrator agent. The publisher does not promote L0 or L1
candidates into hub pages, invent duplicate aliases, or rewrite unrelated prose.

## Return Protocol

The main session receives at most:

```text
status
report wiki-link
publish-report path
one-sentence contribution
created source/hub/topic page counts
updated page counts
```

On failure, report which phase failed. A partial file must not be described as a complete ingest.

## Context Budget

- Full paper text stays inside the processor.
- The main session never reads raw paper text, complete Paper Cards, or complete digests.
- Batch context contains only title, one-sentence contribution, and report path.
- `kb-context.md` and linker inputs are capped by deterministic scripts.
- The linker reads compact digests, not complete Paper Cards.
