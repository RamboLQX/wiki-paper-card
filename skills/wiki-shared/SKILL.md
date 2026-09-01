---
name: wiki-shared
description: Shared LLM Wiki schema, templates, and knowledge-crystallization rules for wiki-paper-card and wiki-gap-mining. Not a standalone task skill.
---

# Wiki Shared References

This package is read only by `wiki-paper-card` and `wiki-gap-mining`.

Before any wiki write:

1. Read [references/wiki-schema.md](references/wiki-schema.md).
2. Read [references/knowledge-model.md](references/knowledge-model.md) before deciding whether to create or update topic pages.

When answering questions over the wiki, follow [references/retrieval-protocol.md](references/retrieval-protocol.md): start from the shared knowledge tree and descend by lookup or survey mode.

Do not invoke `wiki-shared` as a standalone workflow.
