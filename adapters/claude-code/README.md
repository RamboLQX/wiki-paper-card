# Claude Code Adapter

This is the supported runtime adapter for Claude Code. The recommended Obsidian entry point is the Claudian plugin.

## Install

Link the skills from this repository into the target vault:

```bash
mkdir -p /path/to/vault/.claude/skills /path/to/vault/.claude/agents
ln -s /path/to/wiki-paper-card/skills/wiki-paper-card /path/to/vault/.claude/skills/wiki-paper-card
ln -s /path/to/wiki-paper-card/skills/wiki-shared /path/to/vault/.claude/skills/wiki-shared
cp /path/to/wiki-paper-card/adapters/claude-code/agents/*.md /path/to/vault/.claude/agents/
cp /path/to/wiki-paper-card/template/CLAUDE.md /path/to/vault/CLAUDE.md
```

Set `WIKI_PAPER_CARD_ROOT` in the Claudian Claude Code environment or the launching shell:

```bash
export WIKI_PAPER_CARD_ROOT=/path/to/wiki-paper-card
```

This keeps the workflow scripts resolvable when Claudian uses the vault as its working directory.

## Invoke

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

Use the agents named in `adapters/claude-code/agents/`.

Create a fresh `wiki-processor` for each paper. Start up to three processors concurrently for a three-paper batch; for larger batches keep at most three active. After a paper passes its audits, close or release its agent before starting a different paper. Run `wiki-linker` only after every Paper Card and digest audit passes. Run `scripts/publish_wiki.py` only after the link plan audit passes.

## Experimental Model Reference

The following settings were used in one test environment. They are optional and are not a compatibility or performance guarantee. Users can configure any other Anthropic-compatible model.

```bash
ANTHROPIC_API_KEY=<your-deepseek-api-key>
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-flash
```

In Claudian, set the context window to 1M and use Medium or High thinking effort. In the current test setup, one paper took about 5 to 6 minutes on average; this is a local observation, not a benchmark result.
