# Installation

`wiki-paper-card` supports Claude Code, DeepSeek Harness (DSH), and Codex. Claude Code is commonly used inside Obsidian through Claudian; DSH and Codex sessions start from the Vault root.

## Recommended installation

Prerequisites:

- [Obsidian](https://obsidian.md/download)
- Python 3; PyMuPDF when processing PDFs
- at least one supported runtime host
- [Claudian](https://community.obsidian.md/plugins/realclaudian) only when using Claude Code inside Obsidian

Create or select a standalone Vault. Do not use the `wiki-paper-card` repository root as the Vault because the repository also contains `vendor/`, scripts, and tests.

Run the installer from the repository root:

```bash
mkdir -p /path/to/vault
./scripts/install.sh --host codex /path/to/vault
```

Host values:

| Value | Installed hosts |
|---|---|
| `claude` | Claude Code |
| `dsh` | DeepSeek Harness |
| `both` | Claude Code + DSH; this remains the default |
| `codex` | Codex |
| `all` | Claude Code + DSH + Codex |

The installer uses no-clobber behavior for Vault pages and entry files. An existing different `CLAUDE.md` or `AGENTS.md` is preserved and reported for manual merging. Existing conflicting Skill or resource paths cause exit code 1 and are never replaced.

After a conflict-free install, `.wiki-paper-card/runtime-version` records the
runtime code version. It does not describe or migrate Topic content.

## Installed host layouts

| Host | Skill directory | Vault entry | Repository pointer |
|---|---|---|---|
| Claude Code | `.claude/skills/` | `CLAUDE.md` | `.claude/WIKI_PAPER_CARD_ROOT` |
| DSH | `.dsh/skills/` | `CLAUDE.md` | `.dsh/WIKI_PAPER_CARD_ROOT` |
| Codex | `.agents/skills/` | `AGENTS.md` | `.agents/WIKI_PAPER_CARD_ROOT` |

Each host directory also contains `adapters`, `vendor`, and `scripts` symlinks. These make the Skills' `../../` references resolve from the installed Skill directory. `all` installs both Vault entry files from identical host-neutral templates; if pre-existing files leave them different, the installer warns because DSH may load both.

The optional environment variable takes precedence over the pointer:

```bash
export WIKI_PAPER_CARD_ROOT=/path/to/wiki-paper-card
```

Without it, each host reads only its own pointer and verifies that `vendor/nature-paper-card/SKILL.md` is readable. Resolution failure must stop the workflow rather than trigger path guessing.

## Manual installation notes

When manual installation is explicitly required, reproduce the selected row above: link all three repository Skills (`wiki-paper-card`, `wiki-shared`, and `wiki-gap-mining`), link `adapters`, `vendor`, and `scripts` beside the host `skills/` directory, write the host pointer, and copy only the matching Vault entry file if it is missing. Claude Code additionally copies `adapters/claude-code/agents/*.md` into `.claude/agents/`. The installer is preferred because its self-check verifies this layout.

## Upgrade an existing Vault

Start with read-only inspection:

```bash
python3 scripts/upgrade_vault.py inspect \
  --wiki-root /path/to/vault \
  --report /path/to/vault/work/upgrade/inspection.json
```

Update the repository and rerun `install.sh --runtime-only` only after checking that the Git
working tree is clean and the update can fast-forward. This updates linked
Skills and runtime resources without rewriting `raw/` or `wiki/`. Existing
different entry files remain untouched and require a reviewed merge.

```bash
./scripts/install.sh --host codex --runtime-only /path/to/vault
```

Legacy Topic migration is a separate, explicit workflow. The user may defer
it, migrate only Topics needed by the current operation, select individual
Topics, or approve all eligible Topics shown by inspection. The Agent writes a
complete schema 3.0 `purpose: "migration"` plan and preview; after approval,
the upgrade wrapper stages, audits, backs up, and applies it:

```bash
python3 scripts/upgrade_vault.py apply \
  --wiki-root /path/to/vault \
  --plan /path/to/vault/work/upgrade/RUN_ID/migration-plan.json \
  --run-dir /path/to/vault/work/upgrade/RUN_ID
```

Rollback is allowed only while every migrated file still matches its recorded
post-migration hash:

```bash
python3 scripts/upgrade_vault.py rollback \
  --wiki-root /path/to/vault \
  --run-dir /path/to/vault/work/upgrade/RUN_ID
```

See [the Agent upgrade guide](agent-upgrade.md) for the complete confirmation,
staging, and recovery workflow.

## Invoke from the Vault

```text
Use wiki-paper-card in wiki-full mode to process raw/papers/example.pdf.
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

A paper request first selects one processing scope. `card-only` leaves an audited Paper Card under `work/` and never writes `wiki/`; `wiki-topic` publishes cards and Topics without changing research gaps; `wiki-full` runs the complete workflow. New Topic pages require the cross-paper knowledge gates described in the main README. Claude Code and Codex keep at most three processors active; DSH defaults to six and allows at most eight. In the two Wiki modes, every host starts the linker only after every card and digest passes.

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
