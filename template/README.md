# Minimal Wiki Vault

Use the repository installer to initialize a standalone Obsidian Vault for `wiki-paper-card`:

```bash
./scripts/install.sh --host codex /path/to/your/vault
```

Open `/path/to/your/vault/` in Obsidian, not the repository root. Choose `claude`, `dsh`, `both`, `codex`, or `all` as described in the main README. The installer links the Skills and shared resources, installs the matching Vault entry file, and writes a `WIKI_PAPER_CARD_ROOT` pointer. Copying this template directory alone does not make the Skills available.

Then place PDFs or `nature-reader` source-map JSON files under `raw/papers/` and invoke:

```text
Use wiki-paper-card in wiki-full mode to process raw/papers/example.pdf.
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

The Vault-level `CLAUDE.md` (Claude Code/DSH) or `AGENTS.md` (Codex) carries the same host-neutral runtime rules. The Skill expects `raw/` to be read-only and writes generated pages under `wiki/` only through the deterministic publisher.
