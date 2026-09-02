<div align="center">
  <h1>wiki-paper-card</h1>
  <p><strong>Turn paper reading into a personal research Wiki that keeps accumulating, answering questions, and revealing research directions.</strong></p>
  <p>
    <img src="assets/readme-hero-v2.png" alt="wiki-paper-card turns papers into Paper Cards, connected topics, grounded answers, and research gaps" width="100%">
  </p>
  <p>
    <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-2ea44f"></a>
    <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.10.0-f59e0b"></a>
    <a href="#31-requirements"><img alt="Runtime" src="https://img.shields.io/badge/runtime-Claude%20Code%20%7C%20DSH%20%7C%20Codex-111827"></a>
    <a href="#3-installation"><img alt="Install" src="https://img.shields.io/badge/install-scripts%2Finstall.sh-3776ab"></a>
    <a href="README.md"><img alt="Language" src="https://img.shields.io/badge/language-中文%20%7C%20English-1f6feb"></a>
  </p>
</div>

---

In the age of Agents, research accumulation is moving from file storage to the digital accumulation of knowledge and experience.

`wiki-paper-card` turns research questions, methods, evidence, conclusions, and limitations into verifiable knowledge pages, then connects findings across papers. Researchers can ask the knowledge base questions and use the accumulated Wiki to identify open questions and research gaps.

## Contents

- [1. Project Value](#1-project-value)
  - [1.1 Common Research Problems](#11-common-research-problems)
  - [1.2 What the Framework Produces](#12-what-the-framework-produces)
  - [1.3 From Papers to a Research Wiki](#13-from-papers-to-a-research-wiki)
  - [1.4 Skill Index](#14-skill-index)
- [2. Quick Start](#2-quick-start)
- [3. Installation](#3-installation)
- [4. Framework Structure and Operating Rules](#4-framework-structure-and-operating-rules)
  - [4.3 Artifacts and Workflows](#43-artifacts-and-workflows)
- [5. Technical Design](#5-technical-design)
- [6. Contributing](#6-contributing)
- [7. License](#7-license)

## 1. Project Value

### 1.1 Common Research Problems

**Reading does not remain reusable**

After finishing a paper, researchers often remember only its main conclusion. The research question, method assumptions, experimental support, and applicability boundaries gradually fade. Writing a survey, planning an experiment, or checking a citation still requires reopening the original paper. The time spent reading has not become knowledge that can be called upon directly.

**Multiple papers do not form a systematic view**

A research problem is usually advanced by many papers. Some reach similar findings under different datasets or experimental conditions. Some report different results. Others extend, revise, or limit earlier methods. Researchers need to know which findings receive support from multiple papers, where results disagree, which experimental conditions cause the difference, and where each method applies. Folders and isolated notes do not maintain these relationships.

**Research questions and gaps are not maintained over time**

Open questions are questions raised by existing papers that remain insufficiently answered. Research gaps are areas where evidence is still missing from methods, data, evaluation, or scope. New papers may answer an existing question or reveal a new limitation. Without continued maintenance, researchers must inspect the field again before writing a survey or choosing a direction.

`wiki-paper-card` addresses these problems by organizing paper analysis, knowledge connections, knowledge-base questions, and research-gap mining into a continuously updated research Wiki.

### 1.2 What the Framework Produces

<p align="center">
  <img src="assets/readme-product-demo-v2.png" alt="Product concept with Obsidian-style pages, paper analysis, cross-paper relations, knowledge-base questions, and research gaps" width="100%">
</p>

<p align="center"><sub>The concept uses landmark AI paper titles and substitute content to show the product experience. It contains no real vault or private research material.</sub></p>

| Core capability | What you get | Research value |
|---|---|---|
| **Deep paper analysis** | A structured Paper Card with the research question, method conditions, experimental evidence, key conclusions, limitations, and source locations | Restore the paper's context quickly and verify a claim at its source |
| **Cross-paper knowledge connections** | A Topic organized around a shared research problem, including method comparisons, evidence relations, disagreements, and applicability boundaries | View the state of a research direction without rebuilding the comparison |
| **Knowledge-base questions** | Answers, comparisons, or surveys grounded in relevant Paper Cards and Topics located through the shared reader-and-agent knowledge tree | Reuse accumulated research knowledge and reduce repeated reading and organization |
| **Research-gap mining** | A Gap Report with open questions, missing evidence, and candidate research directions | Identify questions that still need evidence and inform the next reading, experiment, or topic decision |

Paper Cards preserve the full context of individual papers. Topics maintain the understanding formed across papers around a shared question. The knowledge tree connects existing pages and supports retrieval, questions, and gap mining. Key claims retain page, figure, table, or equation locators for source verification.

### 1.3 From Papers to a Research Wiki

![The complete flow from paper input to accumulated knowledge, questions, and research-gap mining](assets/readme-workflow-en.svg)

Each paper first enters an independent analysis workflow and produces an audited Paper Card. When related papers meet the admission rules, the framework creates or updates a Topic and refreshes the index, knowledge tree, and log. Researchers can ask questions, verify findings, retrieve survey material, and mine gaps across existing topics.

Source papers stay under `raw/`. Intermediate reports go to `work/`. Audited knowledge pages are published to `wiki/`. This layout keeps source material, processing artifacts, and final knowledge separate.

### 1.4 Skill Index

The following triggerable Skills are available under `skills/`. `skills/wiki-shared/` is a shared-content directory and is not included in the Skill index. Select a Skill name or its Details link for the dedicated page.

| Skill | Status | Purpose | Trigger phrases | Details |
|---|---|---|---|---|
| [`wiki-paper-card`](skills/wiki-paper-card/README.en.md) | **Stable** | Analyze one paper or batch-process a topic folder, generate Paper Cards, and update admitted Topics, the index, and the log | `process this paper`, `analyze this paper`, `batch-process this topic`, `regenerate this card` | [View details](skills/wiki-paper-card/README.en.md) |
| [`wiki-gap-mining`](skills/wiki-gap-mining/README.en.md) | **Beta** | Mine open questions, research gaps, and candidate directions from the existing Wiki | `mine research gaps`, `find research directions`, `analyze the whole knowledge base` | [View details](skills/wiki-gap-mining/README.en.md) |

Knowledge-base questions, verification, and survey retrieval use the shared [`wiki-shared` retrieval protocol](skills/wiki-shared/references/retrieval-protocol.md). It is shared by both Skills and is not indexed as a standalone Skill.

**Planned Skill**

| Skill | Status | Planned purpose |
|---|---|---|
| `wiki-literature-review` | **Planned** | Generate traceable literature reviews from audited Paper Cards, Topics, method comparisons, and evidence boundaries in the Wiki; its writing contract and publishing format will be defined during implementation |

## 2. Quick Start

After installation, send one of the following prompts to your Agent. Replace the example path or question with your own.

| What you want | What to say |
|---|---|
| Analyze one paper | `Use wiki-paper-card to process raw/papers/example.pdf.` |
| Batch-process a research topic | `Use wiki-paper-card to batch-process every paper under raw/papers/<topic-name>/.` |
| Ask the knowledge base | `Using the existing research Wiki, answer: ... Include the relevant Paper Cards, Topics, and source evidence.` |
| Review a research direction | `Using the existing research Wiki, compare the main methods, experimental results, and applicability boundaries for this topic.` |
| Mine research gaps | `Use wiki-gap-mining to mine research gaps and candidate directions across the whole research Wiki.` |
| Regenerate an existing card | `Use wiki-paper-card to reprocess raw/papers/example.pdf.` |

Questions and survey retrieval are read-only by default. Gap mining first creates a read-only report and writes back to Topics only after researcher confirmation.

## 3. Installation

### 3.1 Requirements

| Item | Requirement |
|---|---|
| Runtime host | [Claude Code](https://code.claude.com/docs/en/overview), [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), or [Codex](https://learn.chatgpt.com/docs/app); all three may be configured together |
| Knowledge base | An [Obsidian](https://obsidian.md/download) vault |
| Claude Code inside Obsidian | The [Claudian](https://community.obsidian.md/plugins/realclaudian) plugin |
| Local environment | Python 3. PyMuPDF is required for PDF processing |

The project formally supports all three hosts. Claude Code uses `.claude/skills/` with `CLAUDE.md`, DSH uses `.dsh/skills/` with `CLAUDE.md`, and Codex uses `.agents/skills/` with `AGENTS.md`. All three share the same workflow contracts, deterministic audits, and publisher. The installer creates the matching entry files and repository pointers without modifying global Codex configuration.

Use a standalone vault. Do not open this repository root as the vault because it also contains scripts, tests, and pinned upstream implementation files.

### 3.2 Manual Installation

```bash
git clone https://github.com/RamboLQX/wiki-paper-card.git wiki-paper-card
cd wiki-paper-card

VAULT=/path/to/vault
mkdir -p "$VAULT"

# --host accepts claude | dsh | both | codex | all (default: both = Claude + DSH)
scripts/install.sh --host both "$VAULT"

export WIKI_PAPER_CARD_ROOT="$PWD"
```

The installer creates only missing directories, templates, and Skill links. It does not overwrite an existing `CLAUDE.md`, `AGENTS.md`, knowledge page, or source file under `raw/`. It writes the repository root to the selected host pointer: `$VAULT/.claude/WIKI_PAPER_CARD_ROOT`, `$VAULT/.dsh/WIKI_PAPER_CARD_ROOT`, or `$VAULT/.agents/WIKI_PAPER_CARD_ROOT`. Sessions read their own host pointer when the environment variable is unset, so the `export` is optional (still recommended).

Open `$VAULT` in Obsidian after installation. For DSH or Codex, start the session from the vault root. Place papers under `raw/papers/` and use a prompt from [Quick Start](#2-quick-start).

### 3.3 Agent-Assisted Installation

An Agent with network, terminal, and local filesystem access can follow the project setup guide. Replace the paths and runtime host first:

```text
Read /absolute/path/to/wiki-paper-card/docs/agent-quick-setup.md and configure wiki-paper-card.

Project repository: /absolute/path/to/wiki-paper-card
Obsidian vault: /absolute/path/to/vault
Runtime host: claude / dsh / both / codex / all

Check the paths and runtime first, then run the installer and smoke test.
Do not overwrite existing files in the vault. Report completed items separately from steps that still require user action.
```

For a first-time clone, use the [remote setup guide](https://raw.githubusercontent.com/RamboLQX/wiki-paper-card/main/docs/agent-quick-setup.md).

### 3.4 Verification and Troubleshooting

Run this from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/smoke_test.py
```

See the [installation guide](docs/installation.md) for environment variables, host differences, and troubleshooting.

## 4. Framework Structure and Operating Rules

### 4.1 Vault Layout

```text
vault/
├── raw/
│   └── papers/
│       ├── example.pdf
│       └── <topic-name>/
├── work/
└── wiki/
    ├── sources/
    │   └── papers/
    ├── topics/
    ├── meta/
    │   ├── knowledge-tree.md
    │   └── research.md
    ├── index.md
    └── log.md
```

Researchers organize the topic directories under `raw/papers/`. The framework does not move or classify source papers automatically. `raw/` remains read-only during processing.

### 4.2 Knowledge Pages

| Page or view | What it is for |
|---|---|
| **Paper Card** | Read and revisit one paper |
| **Topic** | Bring related papers together to understand progress on a research problem |
| **Knowledge Tree** | Browse and find existing knowledge pages by research topic |
| **Research Dashboard** | Review unanswered questions and research gaps |
| **Index / Log** | Find all knowledge pages and review the Wiki's update history |

A Paper Card covers one paper. A Topic brings together multiple related papers; one paper does not create a Topic by itself.

### 4.3 Artifacts and Workflows

Each run produces three kinds of files. `wiki/` holds the published knowledge pages, `work/` holds drafts, audit reports, and plans, and `raw/` always stays your untouched source material. For the meaning of every artifact, who generates it, and which ones you need to look at, plus the complete flows of both workflows (paper processing and gap mining), see [docs/artifacts.md](docs/artifacts.md) (written in Chinese).

<p align="center">
  <a href="https://rambolqx.github.io/wiki-paper-card/">
    <img src="assets/wiki-paper-card-workflow-preview.png" alt="The complete wiki-paper-card workflow from paper ingestion and audited publishing to knowledge reuse and research-gap mining" width="100%">
  </a>
</p>

<p align="center">
  <strong><a href="https://rambolqx.github.io/wiki-paper-card/">Open the interactive workflow</a></strong>
  · Choose a guided view
  · Play the workflow
  · Search and zoom
</p>

The interactive version is hosted on GitHub Pages. You can also download the [self-contained HTML file](docs/wiki-paper-card-workflow.html) and open it directly. GitHub displays the static preview above in the README. The editable source is [`docs/wiki-paper-card-workflow.json`](docs/wiki-paper-card-workflow.json).

Two essentials:

- Paper processing requires no decisions from you. Topics are created or updated automatically by the admission rules, and the agent reports the produced pages when the run finishes.
- Gap mining requires your decisions. The confirmation checklist at the end of the report lists each candidate, and Topic pages change only after you confirm them. `work/gap-mining-notes.md` is the miner's intermediate notes and needs no reading.

At the end of every run the agent explains which files were produced and whether anything awaits your decision.

## 5. Technical Design

### 5.1 Applying LLM Wiki to Research Knowledge

[Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) proposes that an LLM continuously build and maintain an interlinked Markdown Wiki. Each new source updates existing pages, cross-references, contradictions, and synthesis. The Wiki becomes a persistent artifact that compounds over time.

`wiki-paper-card` applies this idea to academic research:

- Source papers remain traceable under `raw/`.
- Paper Cards preserve paper-level analysis and evidence.
- Topics maintain synthesis across papers.
- One knowledge tree supports both human navigation and progressive agent questions, retrieval, verification, and surveys.
- Open questions and research gaps evolve as new papers arrive; partial advances retain their method, result, evidence, and remaining boundary, and only fully resolved gaps move to the archive.
- When gap mining archives an answer, it batches all affected Topics into one dedicated narrative-refresh linker without rerunning paper processors. A failed refresh leaves the notice intact for safe retry.
- New Topics include a researcher-notes safe zone whose contents are preserved by automated updates.

Researchers select sources, ask questions, and judge research value. Agents organize pages, maintain relationships, and run consistency checks.

### 5.2 Relationship to nature-skills

The paper-analysis core and shared rules come from [nature-skills](https://github.com/Yuan1z0825/nature-skills). Pinned upstream snapshots live under `vendor/nature-paper-card/` and `vendor/nature-shared/`.

nature-skills provides the Sections 01–16 paper-analysis structure, evidence constraints, source boundaries, and quality checks. `wiki-paper-card` adds Obsidian Wiki integration, topic-folder batch processing, cross-paper Topics, knowledge-base questions, gap mining, and deterministic publishing.

See [UPSTREAM.md](UPSTREAM.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the pinned version, synchronization policy, and third-party notices.

## 6. Contributing

Issues and pull requests are welcome.

- Do not commit personal paper PDFs, private vault content, or real API keys.
- Keep knowledge-admission rule changes in `skills/wiki-shared/references/knowledge-model.md`.
- Record the reason and update `UPSTREAM.md` before changing `vendor/`.
- Define acceptance criteria in the relevant workflow contract before adding a new flow.

## 7. License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

`vendor/nature-paper-card` and `vendor/nature-shared` come from the Apache-2.0 licensed nature-skills project. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
