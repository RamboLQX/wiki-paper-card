---
name: wiki-paper-card
description: Build a source-grounded 01-16 Paper Card, optionally integrate it into an Obsidian LLM Wiki, and optionally maintain cross-paper Topics and research gaps. Use when the user asks to read, analyze, ingest, or batch-process academic papers. Do not use for full-text translation, peer review, or slide generation.
---

# Wiki Paper Card Router

Turn one paper into one of three user-selected scopes:

1. a source-grounded Sections 01-16 Paper Card only;
2. the Paper Card plus Topic/index/log maintenance without research-gap changes;
3. the complete Wiki workflow, including research-gap synthesis and maintenance.

The analysis core comes from the pinned upstream `nature-paper-card`. The wiki integration and knowledge-crystallization rules are local.

## Required Reads

Before processing:

1. Read [the pinned upstream router](../../vendor/nature-paper-card/SKILL.md) and [its manifest](../../vendor/nature-paper-card/manifest.yaml) completely.
2. Read [manifest.yaml](manifest.yaml).
3. Read every file listed under `always_load`.
4. Resolve the wiki root and confirm `raw/` and `wiki/` exist. Resolve the processing scope once using the rules below. When both the input and scope are explicit, start Phase 0 directly.
5. Resolve `<REPO_ROOT>` deterministically, never by guessing: prefer the `WIKI_PAPER_CARD_ROOT` environment variable, then the pointer file written by `install.sh` (`<host-root>/WIKI_PAPER_CARD_ROOT`; Claude Code: `<VAULT_ROOT>/.claude/`, DSH: `<VAULT_ROOT>/.dsh/`, Codex: `<VAULT_ROOT>/.agents/`). Under DSH and Codex, the corresponding adapter (`../../adapters/dsh/dsh-mode.md` or `../../adapters/codex/codex-mode.md`) defines the exact order and verification gate. Verify `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md` is readable before proceeding; if resolution fails, stop and report rather than guessing other paths. The pinned scripts live under `<REPO_ROOT>/vendor/`.

Do not proceed from this router alone.

## Processing Scope

Freeze one scope for the complete request or batch:

| Mode | User intent | Required result | Forbidden work |
|---|---|---|---|
| `card-only` | Only read/analyze the paper or produce a Paper Card | finalized and audited `work/<paper>/paper-card.md` | digest, linker, link plan, and every `wiki/` write |
| `wiki-topic` | Publish Paper Cards and maintain cross-paper Topics, without research-gap work | source pages, Topic synthesis, index, log, and Wiki audits | creating, updating, answering, annotating, or removing research gaps |
| `wiki-full` | Complete Wiki ingestion, including research-gap work | the existing full workflow | none beyond the normal evidence and audit boundaries |

Infer the mode only when the request is explicit. “只要 Paper Card” selects
`card-only`; “入库并整理 Topic，但不研究空白” selects `wiki-topic`; “完整处理”
or an explicit request to identify/maintain research gaps selects `wiki-full`.
If the user only says “处理/分析这些论文” and does not state the desired
scope, ask once before Phase 0:

```text
这次需要哪种处理范围：仅 Paper Card、Paper Card + Topic（不维护研究空白），还是完整 Wiki（含研究空白）？
```

Do not ask once per paper. Do not silently choose `wiki-full`. A later request
to run `wiki-gap-mining` remains a separate explicit workflow.

## Source Boundary

Determine what is available:

- full PDF;
- full paper text;
- metadata or abstract only.

For a PDF or nature-reader source map, run the pinned prepare script:

```text
python "<WIKI_PAPER_CARD_ROOT>/vendor/nature-paper-card/scripts/prepare_paper.py" INPUT \
  --output "<WORKDIR>/source_bundle.json"
```

Use the bundle's recommended locator mode. Never invent pages, figures, tables, or experiments.

## Paper Type Lens

Use the upstream manifest to select one primary lens:

```text
methods
discovery
resource
clinical
materials
review
```

Use at most one secondary lens for a genuinely hybrid paper.

## Workflow

Follow [references/workflow-contract.md](references/workflow-contract.md):

1. Prepare source, processor pack, and KB context with deterministic scripts. Build a batch identity manifest only for the two Wiki modes.
2. Generate every Paper Card independently, with bounded concurrency. Generate digests only for the two Wiki modes.
3. Run deterministic packaging, evidence, formula, structural, and Paper Card audits. Run digest finalization/audit only for the two Wiki modes.
4. In `card-only`, stop after every Paper Card passes and return its `work/` path.
5. In `wiki-topic` or `wiki-full`, link all approved digests only after the whole batch passes, then audit and publish the approved topic actions.

For batch input, read [references/batch-mode.md](references/batch-mode.md). For single input, do not load batch-mode. Under DeepSeek Harness, also read [the DSH adapter reference](../../adapters/dsh/dsh-mode.md); under Codex, read [the Codex adapter reference](../../adapters/codex/codex-mode.md).

The local workflow wraps the upstream skill; it must not replace or summarize away the upstream source-boundary, evidence-base, paper-type, and QA checks.

## Output Language

Match the user's language. Preserve canonical technical terms, formulas, model names, and dataset names.

## Knowledge Boundaries

Before creating a page, apply [../wiki-shared/references/knowledge-model.md](../wiki-shared/references/knowledge-model.md):

- keep paper-local terms and candidates inside the Paper Card (Sections 14-15);
- there are no concept pages, no entity pages, and no promotion ladder;
- never use mention frequency as a promotion signal;
- preserve contradictions instead of overwriting them;
- in the two Wiki modes, treat topic pages as the cross-paper synthesis surface;
- only `wiki-full` may synthesize or maintain research gaps during ingest.

## Platform Support

The supported runtime hosts are Claude Code, DeepSeek Harness (DSH), and Codex. The recommended Obsidian entry point for Claude Code is the Claudian plugin; Codex runs from the Vault root.

- Use a fresh `wiki-processor` per paper. Use one `wiki-linker` per batch only in `wiki-topic` and `wiki-full`. Approved wiki writes are handled by `publish_wiki.py`, not an agent.
- Claude Code: close or release a completed processor before starting a different paper. Start up to three processors for a three-paper batch; for larger batches keep at most three active.
- DeepSeek Harness: run each processor as a background subagent. Keep up to six processors active by default, at most eight. See `../../adapters/dsh/dsh-mode.md` for the phase mapping.
- Codex: create a fresh subagent for each paper, keep at most three processors active and never exceed the current session's available subagent slots. See `../../adapters/codex/codex-mode.md` for the phase mapping.
- If subagents are unavailable, run phases serially and explicitly say that context usage will increase.
- `card-only` is a first-class mode on every host, not merely a light-host fallback.
