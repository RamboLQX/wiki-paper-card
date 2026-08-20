# Architecture

The project separates the analysis core, deterministic pipeline, and thin knowledge layer.

```text
Analysis core    pinned upstream nature-paper-card
Pipeline         deterministic prepare, KB context, finalize, audits
Wiki integration source pages, L2 hubs, topic synthesis
Host adapters    Claude Code subagent wrappers, Claudian recommended
```

## Runtime Flow

```text
prepare bundles + KB context
    -> independent wiki-processor per paper
    -> paper-card.md + paper-digest.json
    -> deterministic finalize, evidence, and digest audits
    -> one wiki-linker per batch
    -> link-plan.json
    -> deterministic link-plan audit
    -> publish_wiki.py publishes source, hub, and topic pages
```

Claude Code starts up to three processors for a three-paper batch. For larger batches, keep at most three active and schedule the remaining papers as processors finish.

## Knowledge Layer

- The Paper Card is the detailed record.
- L0 and L1 candidates stay in the source page.
- L2 candidates become thin concept or entity hubs after cross-paper support or a direct connection requirement.
- Topic pages compare papers and expose contradictions, open questions, and research gaps.

See `skills/wiki-paper-card/references/workflow-contract.md` for the current operating contract.
