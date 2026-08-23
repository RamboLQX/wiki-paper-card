<div align="center">
  <p>
    <img src="assets/readme-banner-en.svg" alt="wiki-paper-card —— Turn papers into a searchable, comparable, traceable research Wiki" width="100%">
  </p>
  <p>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-2ea44f"></a>
    <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.2.0-f59e0b"></a>
    <a href="#runtime-and-entry-points"><img alt="Runtime" src="https://img.shields.io/badge/runtime-Claude%20Code%20%7C%20DSH-111827"></a>
    <a href="#quick-start"><img alt="Install" src="https://img.shields.io/badge/install-scripts%2Finstall.sh-3776ab"></a>
    <a href="README.md"><img alt="Language" src="https://img.shields.io/badge/language-中文%20%7C%20English-1f6feb"></a>
  </p>
  <p>
    <a href="#what-it-does">What It Does</a>
    · <a href="#core-capabilities">Capabilities</a>
    · <a href="#quick-start">Quick Start</a>
    · <a href="#usage">Usage</a>
    · <a href="#workflow">Workflow</a>
    · <a href="#project-layout">Project Layout</a>
    · <a href="README.md">中文</a>
  </p>
</div>

---

**`wiki-paper-card` turns your paper collection into a research knowledge base that keeps growing.** The hard part of reading isn't finishing papers — it's remembering what you read and finding it again when you write a survey or start something new. wiki-paper-card reads each paper into a source-grounded "Paper Card", then automatically connects evidence that multiple papers corroborate into concept, entity, and topic pages. Keep adding papers and a traceable, comparable, ever-growing research Wiki builds itself — ready whenever you need it.

> Status: the core workflow is runnable, while workflow contracts, knowledge rules, and output formats will continue to evolve.

## Table Of Contents

- [Runtime And Entry Points](#runtime-and-entry-points)
- [What It Does](#what-it-does)
- [Core Capabilities](#core-capabilities)
- [Relationship To Upstream nature-skills](#relationship-to-upstream-nature-skills)
- [Design Reference](#design-reference)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Agent Quick Setup](#agent-quick-setup)
- [Workflow](#workflow)
- [Output Layout](#output-layout)
- [Supported Scope](#supported-scope)
- [Project Layout](#project-layout)
- [Documentation](#documentation)
- [Verification](#verification)
- [Contributing](#contributing)
- [License](#license)

## Runtime And Entry Points

This project supports two runtime hosts:

- 🖥️ [Claude Code](https://code.claude.com/docs/en/overview): used inside [Obsidian](https://obsidian.md/download) with the [Claudian](https://community.obsidian.md/plugins/realclaudian) plugin. The official Claudian repository is on [GitHub](https://github.com/YishenTu/claudian).
- 🤖 [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness): start a DSH session inside the vault directory — no Obsidian plugin required. See [adapters/dsh/](adapters/dsh/) for the adapter and orchestration mapping.

Open a standalone vault initialized from `template/` in Obsidian, not this repository's root directory. The repository root also contains implementation files such as `vendor/`, `scripts/`, and `tests/`.

## What It Does

`wiki-paper-card` is designed for researchers who maintain a personal research Wiki over time. It separates the workflow into two stages: close reading of each paper, followed by cross-paper selection and connection of knowledge worth promoting.

1. 📖 **Read papers**: each paper is independently read into a structured card — from bibliographic info, the research question, the core idea, method modules, and the experiment-to-claim evidence chain, through to conclusion boundaries, author-stated limitations, critical analysis, and testable research ideas; every key claim is anchored to a page, figure, table, or equation so it can be checked against the original.
2. 🧠 **Crystallize knowledge**: after a batch completes, the project compares candidate concepts and entities across papers. A concept or entity hub page is created only when the same object is supported by at least two independent sources, or when it is directly needed to connect existing Wiki pages or answer an existing open question. Candidates seen in only one paper remain in that paper's Card.

To keep detailed arguments available while making cross-paper comparison and retrieval easier, the project separates paper-level detail from cross-paper knowledge: Paper Cards keep the full record; concept and entity pages keep only stable definitions, source evidence, relations, and contradictions as thin hubs; topic pages carry comparison and synthesis. This keeps the Wiki searchable, comparable, and traceable as it grows.

## Core Capabilities

In short: **it turns papers you have "read" into knowledge you actually own and can reuse.** It solves the problems every long-term researcher runs into:

| The problem you hit | How wiki-paper-card solves it |
|---|---|
| You finish a paper, then forget it and can't find it when writing a survey | Each paper becomes a structured card whose claims, formulas, and figures point back to the source for one-click verification |
| Papers pile up and knowledge stays scattered and disconnected | It automatically connects corroborated evidence across papers into concept, entity, and topic pages — a growing knowledge graph |
| You read a lot but never form your own judgment | Topic pages compare methods, evidence, and results across papers, marking consensus / conflict and keeping both sides of a disagreement |
| You worry AI output is padded or unreliable | Every claim must land on a page / figure / table / equation anchor, enforced by deterministic audits; sections stay empty when there is nothing of value |
| The knowledge base gets messy and tedious to maintain | Deterministic scripts write incrementally, repeated runs create no duplicates, and index / log stay maintained automatically |

To keep only what survives repeated verification, page creation is gated by three tiers:

| Tier | Meaning | Handling |
|---|---|---|
| L0 | A local name, component, or intermediate concept meaningful only in the current paper | Kept in the Paper Card; no standalone page |
| L1 | Independently definable, but not yet supported by a second independent source | Kept in the Paper Card as a candidate |
| L2 | Supported by at least two independent sources, or directly needed to connect existing Wiki pages or answer an existing open question | Creates or updates a concept/entity hub page |

## Relationship To Upstream nature-skills

The analysis core and shared rules come from the [nature-skills](https://github.com/Yuan1z0825/nature-skills) project. The upstream directories are pinned in `vendor/nature-paper-card` and `vendor/nature-shared`.

| Responsibility | Source |
|---|---|
| Sections 01-16 card structure, source bundles, evidence grounding, paper-type lenses, upstream audits | `nature-skills` |
| Obsidian path mapping, KB context, batch orchestration, digests, link plans, knowledge gates, Wiki publishing, idempotency | This project |

This project adds an orchestration and knowledge-crystallization layer for Obsidian LLM Wikis on top of the upstream paper-analysis core. See [UPSTREAM.md](UPSTREAM.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the pinned version, upstream commit, synchronization policy, and third-party notices.

## Design Reference

This project follows Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern, using Wiki layering, agent-maintained knowledge, and `index.md`/`log.md` to organize a long-lived knowledge base.

## Quick Start

Once installed, copy these prompts straight to your Agent:

| What you want | What to say |
|---|---|
| Process one paper | `Use wiki-paper-card to process raw/papers/example.pdf.` |
| Batch-process a directory | `Use wiki-paper-card to batch-process raw/papers/knowledge-conflict/.` |
| Regenerate an existing card | `Use wiki-paper-card to reprocess raw/papers/example.pdf.` |

Prerequisites:

- [Claude Code](https://code.claude.com/docs/en/overview) or [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (one or both)
- [Obsidian](https://obsidian.md/download) (the Claude Code host also needs the [Claudian](https://community.obsidian.md/plugins/realclaudian) plugin)
- Python 3
- PyMuPDF when processing PDF files

Create or select a standalone vault and link it with the install script:

```bash
git clone <repository-url> wiki-paper-card
cd wiki-paper-card

VAULT=/path/to/vault
mkdir -p "$VAULT"

# --host can be claude | dsh | both (default: both)
scripts/install.sh --host dsh "$VAULT"
# or connect both hosts at once:
scripts/install.sh --host both "$VAULT"

export WIKI_PAPER_CARD_ROOT="$PWD"
```

The install script is idempotent: it only creates missing directories, templates, and skill links, and never overwrites an existing `CLAUDE.md`, knowledge pages, or `raw/` files in the vault. The Claude Code host links skills into `$VAULT/.claude/skills/` and copies subagents; the DSH host links skills into `$VAULT/.dsh/skills/` (DSH auto-discovers that directory and the vault-root `CLAUDE.md`).

Open `$VAULT` in Obsidian (for the DSH host, start a DSH session in the vault directory), not this repository's root directory. After setting `WIKI_PAPER_CARD_ROOT`, the host can discover `wiki-paper-card`, `wiki-shared`, and the subagents from the vault, and resolve the repository scripts and pinned upstream files through that environment variable. Copying the template alone does not make the skills appear.

Place a paper under `raw/papers/` in the vault and invoke the skill:

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

See [docs/installation.md](docs/installation.md) for the full installation, environment configuration, and troubleshooting notes.

## Usage

Send `Use wiki-paper-card ...` directly in a Claudian session. If the plugin provides a skill picker, you can also select `wiki-paper-card` first and then give the processing target.

### 1. Place Inputs

- Place paper PDFs and `nature-reader` source-map JSON files under `raw/papers/` in the Obsidian vault.
- `raw/` is read-only. Do not move, overwrite, or delete source files during processing.
- Users must organize `raw/` into their own topic directories; the workflow does not classify papers automatically. For example, use `raw/papers/knowledge-conflict/`.

```text
vault/
├── raw/
│   └── papers/
│       ├── example.pdf
│       └── example.source-map.json
├── wiki/
│   ├── sources/
│   ├── concepts/
│   ├── entities/
│   ├── topics/
│   ├── index.md
│   └── log.md
└── work/
```

For example, `raw/papers/example.pdf` produces the source page `wiki/sources/papers/example.md`.

### 2. Process One Paper

```text
Use wiki-paper-card to process raw/papers/example.pdf.
```

Process a `nature-reader` source map:

```text
Use wiki-paper-card to process raw/papers/example.source-map.json.
```

A single paper produces at least a Paper Card source page under `wiki/sources/`. One paper alone does not create a new concept, entity, or topic.

### 3. Process A Batch

Process all PDFs under a specific directory:

```text
Use wiki-paper-card to batch-process raw/papers/knowledge-conflict/.
```

Process all PDFs under `raw/papers/`:

```text
Use wiki-paper-card to batch-process raw/papers/.
```

Batch processing creates all source pages first and performs cross-paper linking only after every audit passes. We recommend at most 15 papers per batch. The system runs at most three processors concurrently.

### 4. Topics And Cross-Paper Pages

A concept or entity is created only when at least two independent sources support it, or when it is directly needed to connect existing pages or answer an existing open question. A topic is created or updated only when at least two papers share the same problem, mechanism, or evidence space, or when a new paper answers or challenges an existing topic's open questions.

You can state the synthesis goal explicitly:

```text
Use wiki-paper-card to batch-process raw/papers/knowledge-conflict/ and create or update topic pages where at least two papers share the same problem, mechanism, or evidence space.
```

The framework does not force-create pages when the knowledge gates are not satisfied.

### 5. Updates And Reprocessing

Unchanged PDFs are skipped when the same path is processed again. To regenerate one:

```text
Use wiki-paper-card to reprocess raw/papers/example.pdf.
```

Processing updates `wiki/index.md`, `wiki/log.md`, and existing pages without deleting knowledge pages. Batch reports go under `work/`; final knowledge pages go under `wiki/`.

## Agent Quick Setup

Users can start the setup from their own Agent tool with one prompt instead of running every command manually:

```text
Read /path/to/wiki-paper-card/docs/agent-quick-setup.md and configure wiki-paper-card.
Project repository: /path/to/wiki-paper-card
Obsidian vault: /path/to/vault
```

The Agent creates missing vault directories, links the skills, merges `CLAUDE.md`, sets the environment variable, and runs the smoke test. See [docs/agent-quick-setup.md](docs/agent-quick-setup.md) for the execution rules and safety boundaries.

## Workflow

![Four-step workflow from papers to a research Wiki](assets/readme-workflow-en.svg)

From dropping in papers and reading them closely, to connecting evidence across papers and crystallizing a growing research Wiki. For the deterministic pipeline behind the scenes (prepare → finalize → audit → publish) and per-script details, see [docs/architecture.md](docs/architecture.md).

## Output Layout

```text
vault/
├── raw/
│   └── papers/
│       └── example.pdf
└── wiki/
    ├── sources/
    │   └── papers/
    │       └── example.md
    ├── concepts/
    ├── entities/
    ├── topics/
    ├── meta/
    ├── index.md
    └── log.md
```

Paper Cards keep the detailed record, concept and entity pages stay thin hubs, and topic pages carry cross-paper synthesis. Audit reports and intermediate files stay in the batch work directory.

## Supported Scope

| Area | Current support |
|---|---|
| Runtime host | Claude Code, DeepSeek Harness (DSH) |
| Obsidian entry point | Claudian (Claude Code host) |
| Primary inputs | PDF and `nature-reader` source maps |
| Wiki writes | Local vault only |
| Output language | Follows the user's language |

## Project Layout

```text
skills/wiki-paper-card/    Workflow entry point, contracts, and subagent briefs
skills/wiki-shared/        Wiki schema, templates, and knowledge rules
adapters/claude-code/      Claude Code subagent wrappers
adapters/dsh/              DeepSeek Harness adapter and orchestration mapping
vendor/nature-paper-card/  Pinned upstream analysis core
vendor/nature-shared/      Pinned upstream shared rules
template/                  Minimal Obsidian vault example
scripts/                   Local deterministic checks, packaging, install, and publishing
docs/                      Installation and architecture documentation
tests/                     Tests for local scripts
```

## Documentation

- [Installation](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Workflow contract](skills/wiki-paper-card/references/workflow-contract.md)
- [Wiki integration](skills/wiki-paper-card/references/wiki-integration.md)
- [Knowledge model](skills/wiki-shared/references/knowledge-model.md)
- [Retrieval protocol](skills/wiki-shared/references/retrieval-protocol.md)
- [DSH adapter](adapters/dsh/dsh-mode.md)
- [Changelog](CHANGELOG.md)

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/smoke_test.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s vendor/nature-paper-card/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s vendor/nature-shared/tests -v
```

## Contributing

Issues and pull requests are welcome.

- Do not commit personal paper PDFs, private vault content, or real API keys.
- Keep knowledge admission rule changes in `skills/wiki-shared/references/knowledge-model.md`.
- Record the reason and update `UPSTREAM.md` before changing `vendor/`.
- Define acceptance criteria in the relevant workflow contract before adding a new flow.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

`vendor/nature-paper-card` and `vendor/nature-shared` come from the Apache-2.0 licensed `nature-skills` project. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
