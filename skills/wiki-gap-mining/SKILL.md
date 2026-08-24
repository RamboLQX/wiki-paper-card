---
name: wiki-gap-mining
description: Mine research gaps, open questions, and candidate directions across user-selected wiki domains or the whole knowledge base, and optionally write the mined items back into topic pages through the deterministic publisher. Use when the user asks to dig for research gaps, find candidate research directions or next topics, or synthesize which questions and gaps remain open and which have been resolved across already processed paper groups. The scope is existing wiki content only, never new papers. Do not use for paper processing (wiki-paper-card) or for plain retrieval and survey answers (follow retrieval-protocol).
---

# Wiki Gap Mining Router

Cross-group and whole-wiki mining of research gaps, open questions, and
candidate directions, built on content that earlier `wiki-paper-card` runs
already ingested.

Read and mine first, write back only after the user confirms.

## Required Reads

Before mining:

1. Read [../wiki-shared/references/retrieval-protocol.md](../wiki-shared/references/retrieval-protocol.md)
   completely — the read side follows its survey discipline.
2. Read [../wiki-shared/references/wiki-schema.md](../wiki-shared/references/wiki-schema.md)
   and [../wiki-shared/references/knowledge-model.md](../wiki-shared/references/knowledge-model.md).
3. Read [references/mining-brief.md](references/mining-brief.md) — the miner contract.
4. Before any write-back, read
   [../wiki-paper-card/references/link-plan-schema.md](../wiki-paper-card/references/link-plan-schema.md)
   and
   [../wiki-paper-card/references/wiki-integration.md](../wiki-paper-card/references/wiki-integration.md).

Do not proceed from this router alone.

## Scope Resolution

The mining scope is always a set of wiki domains (first directory under
`wiki/sources/papers/`, mirroring `raw/papers/`) or the whole wiki:

- User names specific groups → those domains only.
- User says 全库 / whole wiki / 整个知识库 → all domains.
- Unambiguous domain names start Phase A directly; do not ask for
  confirmation when the scope is clear.

Topic pages join the scope when their `sources` frontmatter intersects the
selected domains; cross-domain topic pages join when any source is inside.

## Workflow

### Phase A: Read And Mine (read-only)

1. Build the read map: read `wiki/meta/knowledge-tree.md` and
   `wiki/meta/research.md` to get the currently open questions and gaps.
2. Descend breadth-first over the scoped topic pages: 概述, 论文与方法对照,
   关键发现, 争议与不确定, 开放问题, 研究空白与候选方向, and the archive
   sections 已解决的问题 / 已解决的研究空白. Drill into source-page
   sections only for the evidence pointers you need.
3. Keep intermediate notes in `work/gap-mining-notes.md` (out-of-context).
4. Write `work/gap-mining-report.md` following the report contract in
   [references/mining-brief.md](references/mining-brief.md).
5. Return the report path and a one-paragraph summary. Never write to
   `wiki/` in this phase.

### Phase B: Write-Back (only after explicit user confirmation)

1. Emit one `link-plan.json` with `purpose: "mining"`:
   - `batch.source_pages` is empty;
   - `batch.label` names the mining run;
   - topic actions reference *existing* source pages in `papers`;
   - mined gaps and questions become `open_questions` / `research_gaps`
     entries on the confirmed target topics (open entries), while gaps the
     mining found to be already resolved by other groups become
     `status: "answered"` entries;
   - a cross-group candidate direction may `create_topic` when at least two
     existing source pages support it.
2. Run the deterministic audit and publisher:

```bash
python "<REPO_ROOT>/scripts/audit_link_plan.py" \
  --plan "<WORKDIR>/link-plan.json" \
  --report "<WORKDIR>/link-plan-report.json"
python "<REPO_ROOT>/scripts/publish_wiki.py" \
  --plan "<WORKDIR>/link-plan.json" \
  --wiki-root "<VAULT_ROOT>" \
  --report "<WORKDIR>/publish-report.json"
```

The miner never edits wiki pages directly.

## Budget Discipline

- Full paper text stays out of the session; mining reads topic pages,
  the two meta indexes, and targeted source-page sections.
- One miner agent per mining run; for a whole-wiki scope, the miner may
  fan out per-domain reading subagents and merge the notes itself.
- An empty result is a valid result: report "no genuine new gap" instead of
  padding the report.

## Output Language

Match the user's language. Preserve canonical technical terms.

## Platform Support

Supported hosts are Claude Code and DeepSeek Harness (DSH).

- Use one background miner subagent per mining run; it writes only
  `work/` files and the link plan.
- Claude Code: run the miner as a Task subagent.
- DeepSeek Harness: run the miner as a background subagent; see
  `adapters/dsh/dsh-mode.md` for the orchestration mapping.
- If subagents are unavailable, run serially and say that context usage
  will increase.
