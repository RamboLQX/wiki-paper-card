# Installation

`wiki-paper-card` currently supports Claude Code as the runtime host. The recommended Obsidian entry point is the Claudian plugin.

## Claudian / Claude Code

Prerequisites:

- [Claude Code](https://code.claude.com/docs/en/overview)
- [Obsidian](https://obsidian.md/download)
- [Claudian](https://community.obsidian.md/plugins/realclaudian) installed and enabled in Obsidian

1. Create or select a standalone Obsidian vault. For a new vault, initialize it from the repository template:

```bash
mkdir -p /path/to/vault
cp -R -n /path/to/wiki-paper-card/template/* /path/to/vault/
```

Open `/path/to/vault` in Obsidian as the active vault. Do not open the `wiki-paper-card` repository root directly; that directory also contains implementation files such as `vendor/`, `scripts/`, and `tests/`. The `-n` flag keeps files that already exist in the target vault.

2. Link the skill folders and install the Claude Code agents and vault instructions:

```bash
VAULT=/path/to/vault
mkdir -p "$VAULT/.claude/skills" "$VAULT/.claude/agents"
ln -s /path/to/wiki-paper-card/skills/wiki-paper-card "$VAULT/.claude/skills/wiki-paper-card"
ln -s /path/to/wiki-paper-card/skills/wiki-shared "$VAULT/.claude/skills/wiki-shared"
cp /path/to/wiki-paper-card/adapters/claude-code/agents/*.md "$VAULT/.claude/agents/"
cp /path/to/wiki-paper-card/template/CLAUDE.md "$VAULT/CLAUDE.md"
```

If the vault already has a `CLAUDE.md`, merge the relevant sections instead of overwriting it.

The template itself does not include the skills, subagents, or scripts. The links above make the skills and agents discoverable from the vault, and `WIKI_PAPER_CARD_ROOT` makes the repository scripts and pinned upstream files resolvable.

3. Set `WIKI_PAPER_CARD_ROOT` in the Claudian Claude Code environment or the launching shell:

```bash
export WIKI_PAPER_CARD_ROOT=/path/to/wiki-paper-card
```

This gives the workflow an unambiguous path to the pinned scripts when Claudian runs with the vault as its working directory.

4. Invoke from the vault:

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

Batch process all PDFs under a directory:

```text
Use wiki-paper-card to batch-process raw/papers/knowledge-conflict/.
```

Process a `nature-reader` source map:

```text
Use wiki-paper-card to process raw/papers/example.source-map.json.
```

Force regeneration of an unchanged PDF:

```text
Use wiki-paper-card to reprocess raw/papers/example.pdf.
```

A single paper creates its source page under `wiki/sources/`, and `publish_wiki.py` deterministically generates or updates entity stubs under `wiki/entities/` from the digest's public datasets, benchmarks, model families, and metrics. New topic pages require the cross-paper knowledge gates described in the main README. Batch processing runs up to three `wiki-processor` agents concurrently and starts the link and publish phase only after every card and digest passes.

## Optional: Anthropic-compatible model endpoint

Claudian talks to the model through the standard Anthropic API. To use a compatible gateway or provider, point the runtime at it with the usual environment variables:

```bash
ANTHROPIC_API_KEY=<your-api-key>
ANTHROPIC_BASE_URL=<provider-anthropic-endpoint>
ANTHROPIC_MODEL=<model-name>
```

The exact values are provider-specific and are not a compatibility or performance guarantee. In Claudian, set the context window to 1M and use Medium or High thinking effort. In one test setup, a single paper took about 5 to 6 minutes on average; this is a local observation, not a benchmark result.

Do not commit a real API key to this repository.

## Python

The upstream prepare script uses PyMuPDF for PDF input. Install it when PDF processing is required:

```bash
python3 -m pip install pymupdf
```

The audit wrapper uses only the Python standard library.
