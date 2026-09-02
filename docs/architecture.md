# Architecture

The project separates the analysis core, deterministic pipeline, and thin knowledge layer.

```text
Analysis core    pinned upstream nature-paper-card
Pipeline         deterministic prepare, KB context, finalize, audits
Wiki integration source pages, topic synthesis
Host adapters    Claude Code, DSH, and Codex orchestration mappings
```

## Runtime Flow

```text
select scope once
    -> card-only: prepare + KB context -> paper-card.md -> card audits -> stop in work/
    -> wiki-topic or wiki-full:
       prepare -> batch manifest + KB context
       -> paper-card.md + paper-digest.json per paper
       -> card/digest audits -> one linker
       -> schema 3.0 link-plan.json with workflow_mode
       -> manifest-aware link-plan audit -> deterministic publish
```

`wiki-topic` and `wiki-full` share the same Paper Card and Topic quality gates.
The difference is an enforced write boundary: `wiki-topic` rejects all
research-gap content and mutation fields while preserving existing gaps;
`wiki-full` applies the complete research-gap lifecycle.

The manifest owns only mechanically reproducible identity fields. The digest
identity finalizer records every replacement and does not change titles,
paper types, analysis, Topic seed names, or other semantic content.

Claude Code and Codex keep at most three processors active; Codex also obeys the current session's available subagent slots. DSH starts up to six by default and allows at most eight. Every host preserves the all-pass gate before creating the batch linker in the two Wiki modes, and only the main session runs deterministic publishing. `card-only` never creates a linker.

## Knowledge Layer

- The Paper Card is the detailed, reader-facing record. Explanations use coherent prose; formulas, modules, experiments, and limitations retain the structured views needed for evidence lookup.
- Topic pages use clean overview, synthesis, and optional controversy prose backed by a structured evidence ledger and Markdown footnotes. Method comparisons remain scan-friendly tables. Ingest research gaps are synthesized across papers from author limitations, Agent critical observations, unexplained results, and comparison-view seeds, then rendered as one or two reader-facing paragraphs; zero valid gaps is allowed.
- `wiki/meta/topic-state/*.json` stores stable open-item identity, annotations, and replay state so publisher protocol never appears in Topic Markdown.
- The paper-card linker and the bounded post-mining refresh linker are the only producers of Topic narrative and comparisons. Gap mining itself can only maintain stable-ID open questions and research gaps after user confirmation; answered items cause all affected Topics to be batched into one refresh run.
- Both producers submit plans to the same publisher. `base_topic_sha256` rejects stale concurrent plans before any Wiki write, and schema 2.0 remains readable for historical compatibility.
- There are no concept pages, no entity pages, and no promotion ladder; cross-paper synthesis happens on topic pages.

See `skills/wiki-paper-card/references/workflow-contract.md` for the current operating contract.
