# Minimal Wiki Vault

Use this directory to initialize a standalone Obsidian vault for `wiki-paper-card`:

```bash
cp -R -n template/* /path/to/your/vault/
```

Open `/path/to/your/vault/` in Obsidian, not the repository root. Before invoking the workflow, install the `.claude/skills` links and `.claude/agents` files described in the main README, and set `WIKI_PAPER_CARD_ROOT` to the repository root. Copying this template alone does not make the skills available.

Then place PDFs or `nature-reader` source-map JSON files under `raw/papers/` and invoke:

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

Batch process a topic directory:

```text
Use wiki-paper-card to batch-process raw/papers/example-topic/.
```

Force regeneration of an unchanged PDF:

```text
Use wiki-paper-card to reprocess raw/papers/example.pdf.
```

A single paper creates its source page under `wiki/sources/`. New topic pages are created or updated only when the cross-paper knowledge gates described in the main README are satisfied.

The vault-level `CLAUDE.md` carries the runtime behavior rules for Claude Code and Claudian. The skill expects `raw/` to be read-only and writes generated pages under `wiki/`.
