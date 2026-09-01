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

## Intent Routing

Resolve what the user actually wants before mining:

- The user names a `raw/` path or says 处理 papers → check whether the wiki
  already has matching source pages. None yet → route to `wiki-paper-card`
  first. Some exist → ask one clarifying question: 补处理新论文 / 只挖掘已有
  内容的空白 / 两者.
- The user asks for a survey, verification, or plain answers → follow the
  retrieval protocol, not this skill.

## Scope Resolution

The mining scope is always a set of wiki domains (first directory under
`wiki/sources/papers/`, mirroring `raw/papers/`) or the whole wiki:

- User names specific groups → those domains only.
- User says 全库 / whole wiki / 整个知识库 → all domains.
- Unambiguous domain names start Phase A directly; do not ask for
  confirmation when the scope is clear.

Topic pages join the scope when their `sources` frontmatter intersects the
selected domains; cross-domain topic pages join when any source is inside.

When `wiki/sources/papers/` has no first-level domain directories, every
paper belongs to 未分类 and a per-domain scope degrades to the whole wiki:
state this in the report's 范围与日期 section and suggest organizing
`raw/papers/` into domain subdirectories to enable per-domain mining.

## Workflow

### Phase A: Read And Mine (read-only)

1. Build the read map: read `wiki/meta/knowledge-tree.md` and
   `wiki/meta/research.md` to get the scoped topics, papers, currently open questions, and gaps.
2. Descend breadth-first over the scoped topic pages: 概述, 综合认识,
   争议与不确定, 论文与方法对照, 开放问题, 研究空白与候选方向, and the archive
   sections 已解决的问题 / 已解决的研究空白. Drill into source-page
   sections only for the evidence pointers you need.
3. Keep intermediate notes in `work/gap-mining-notes.md` (out-of-context).
4. Write `work/gap-mining-report.md` following the report contract in
   [references/mining-brief.md](references/mining-brief.md).
5. Return the report path and a one-paragraph summary. Never write to
   `wiki/` in this phase.

### Phase B: Write-Back (only after explicit user confirmation)

1. Present the report's 待确认清单; the user confirms each candidate's
   采用 / 落点 / 知识状态 / 写入区块.
2. Read the matching `wiki/meta/topic-state/<topic-relative-path>.json` for
   every target Topic so existing open-item IDs and origins are preserved.
3. Resume the same miner with the user's confirmations (DSH:
   `send_message` to the miner subagent; Claude Code: continue the Task;
   Codex: use the current client's same-agent follow-up capability).
   The miner emits one `link-plan.json` with `purpose: "mining"`:
   - `schema_version` is `"3.0"`;
   - `batch.source_pages` is empty;
   - `batch.label` names the mining run;
   - topic actions reference *existing* source pages in `papers`;
   - every update carries the exact target page's `base_topic_sha256`;
   - mined gaps and questions become stable-ID `open_questions` /
     `research_gaps` entries on the confirmed target topics (`origin:
     "mining"`, open entries with the v2 detail fields), while gaps the mining
     found to be already resolved by other groups preserve the same ID/origin
     and become `status: "answered"` entries;
   - a cross-group candidate direction may `create_topic` only with explicit
     user confirmation and at least two existing source pages sharing the
     same problem, mechanism, or evidence space; such pages stay
     `status: stub`.
   The candidate fields keep the exact names of the report entries so the
   translation is mechanical; the miner never rewrites candidate text and
   never edits wiki pages directly.
4. Run the deterministic audit and publisher from the main agent:

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

## User-Facing Closing Summary

When the run settles, the main agent explains to the user, in the user's
language:

- where `work/gap-mining-report.md` is and what it contains in one paragraph;
- that `work/gap-mining-notes.md` is the miner's intermediate note and needs
  no reading;
- the top candidates from the report's 待确认清单, and that confirming them
  is what triggers the write-back into topic pages and the dashboard
  (nothing in `wiki/` changes without confirmation);
- when a write-back ran: the produced link plan and publish report, and the
  topic pages that changed.

When the user asks what a file means, point them to `docs/artifacts.md`.

## Platform Support

Supported hosts are Claude Code, DeepSeek Harness (DSH), and Codex.

- Use one background miner subagent per mining run; it writes only
  `work/` files and the link plan.
- Claude Code: run the miner as a Task subagent.
- DeepSeek Harness: run the miner as a background subagent; see
  `../../adapters/dsh/dsh-mode.md` for the orchestration mapping.
- Codex: create one miner subagent and continue that same subagent after user
  confirmation; see `../../adapters/codex/codex-mode.md` for the mapping.
- If subagents are unavailable, run serially and say that context usage
  will increase.
