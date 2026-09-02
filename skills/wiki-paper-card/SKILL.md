---
name: wiki-paper-card
description: Build a source-grounded 01-16 paper card and integrate it into an Obsidian LLM Wiki. Use when the user asks to read, analyze, ingest, or batch-process academic papers, and when the result should update wiki sources, topics, index, and log. Do not use for full-text translation, peer review, slide generation, or standalone paper cards that should not modify a wiki.
---

# Wiki Paper Card Router

Turn one paper into:

1. a source-grounded Sections 01-16 Paper Card;
2. topic pages that compare papers and expose research gaps;
3. updated index and log entries.

The analysis core comes from the pinned upstream `nature-paper-card`. The wiki integration and knowledge-crystallization rules are local.

## Required Reads

Before processing:

1. Read [the pinned upstream router](../../vendor/nature-paper-card/SKILL.md) and [its manifest](../../vendor/nature-paper-card/manifest.yaml) completely.
2. Read [manifest.yaml](manifest.yaml).
3. Read every file listed under `always_load`.
4. Resolve the wiki root and confirm `raw/` and `wiki/` exist. For an explicit single-file or batch request, start Phase 0 directly; do not ask for confirmation when the input path and scope are unambiguous.
5. Resolve `<REPO_ROOT>` deterministically, never by guessing: prefer the `WIKI_PAPER_CARD_ROOT` environment variable, then the pointer file written by `install.sh` (`<host-root>/WIKI_PAPER_CARD_ROOT`; Claude Code: `<VAULT_ROOT>/.claude/`, DSH: `<VAULT_ROOT>/.dsh/`, Codex: `<VAULT_ROOT>/.agents/`). Under DSH and Codex, the corresponding adapter (`../../adapters/dsh/dsh-mode.md` or `../../adapters/codex/codex-mode.md`) defines the exact order and verification gate. Verify `<REPO_ROOT>/vendor/nature-paper-card/SKILL.md` is readable before proceeding; if resolution fails, stop and report rather than guessing other paths. The pinned scripts live under `<REPO_ROOT>/vendor/`.

Do not proceed from this router alone.

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

1. Prepare source, batch identity manifest, and KB context with deterministic scripts.
2. Generate every paper card and paper digest independently, with bounded concurrency.
3. Run deterministic packaging, evidence, formula, structural, wiki, and digest audits.
4. Link all approved digests only after the whole batch passes.
5. Apply only approved topic actions.

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
- treat topic pages as the primary synthesis surface for research gaps.

## Platform Support

The supported runtime hosts are Claude Code, DeepSeek Harness (DSH), and Codex. The recommended Obsidian entry point for Claude Code is the Claudian plugin; Codex runs from the Vault root.

- Use a fresh `wiki-processor` per paper and one `wiki-linker` per batch. Approved wiki writes are handled by `publish_wiki.py`, not an agent.
- Claude Code: close or release a completed processor before starting a different paper. Start up to three processors for a three-paper batch; for larger batches keep at most three active.
- DeepSeek Harness: run each processor as a background subagent. Keep up to six processors active by default, at most eight. See `../../adapters/dsh/dsh-mode.md` for the phase mapping.
- Codex: create a fresh subagent for each paper, keep at most three processors active and never exceed the current session's available subagent slots. See `../../adapters/codex/codex-mode.md` for the phase mapping.
- If subagents are unavailable, run phases serially and explicitly say that context usage will increase.
- Light hosts may generate only the Paper Card and skip wiki writes.
