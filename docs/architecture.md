# Architecture

The project separates the analysis core, deterministic pipeline, and thin knowledge layer.

```text
Analysis core    pinned upstream nature-paper-card
Pipeline         deterministic prepare, KB context, finalize, audits
Wiki integration source pages, deterministic entity stubs, topic synthesis
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
    -> publish_wiki.py publishes source pages, entity stubs, and topic pages
```

Claude Code starts up to three processors for a three-paper batch. For larger batches, keep at most three active and schedule the remaining papers as processors finish.

## Knowledge Layer

- The Paper Card is the detailed record; paper-local terms and components stay there.
- Entity stubs for public datasets, benchmarks, model families, and metrics are generated deterministically by `publish_wiki.py` from the digests' `analysis.datasets/models/metrics` lists. No LLM decides them.
- Topic pages compare papers and expose contradictions, open questions, and research gaps.
- There are no concept pages and no promotion ladder; cross-paper synthesis happens on topic pages.

See `skills/wiki-paper-card/references/workflow-contract.md` for the current operating contract.
