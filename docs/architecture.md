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
prepare bundles + KB context
    -> independent wiki-processor per paper
    -> paper-card.md + paper-digest.json
    -> deterministic finalize, evidence, and digest audits
    -> one wiki-linker per batch
    -> schema 3.0 link-plan.json with complete narrative + evidence ledger
    -> deterministic link-plan audit
    -> publish_wiki.py publishes source pages and topic pages
```

Claude Code and Codex keep at most three processors active; Codex also obeys the current session's available subagent slots. DSH starts up to six by default and allows at most eight. Every host preserves the all-pass gate before creating the batch linker, and only the main session runs deterministic publishing.

## Knowledge Layer

- The Paper Card is the detailed record; paper-local terms and components stay there.
- Topic pages use managed overview, synthesis, and controversy prose backed by a structured evidence ledger; method comparisons and open items remain scan-friendly structures.
- The paper-card linker is the sole writer of Topic narrative and comparisons. Gap mining can only maintain stable-ID open questions and research gaps after user confirmation.
- Both producers submit plans to the same publisher. `base_topic_sha256` rejects stale concurrent plans before any Wiki write, and schema 2.0 remains readable for historical compatibility.
- There are no concept pages, no entity pages, and no promotion ladder; cross-paper synthesis happens on topic pages.

See `skills/wiki-paper-card/references/workflow-contract.md` for the current operating contract.
