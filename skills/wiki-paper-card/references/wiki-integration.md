# Wiki Integration Contract

## Target Mapping

| Artifact | Destination |
|---|---|
| Full Sections 01-16 | `wiki/sources/<raw-relative-path>.md` |
| L2 concept hub | `wiki/concepts/<canonical-name>.md` |
| L2 entity hub | `wiki/entities/<canonical-name>.md` |
| Cross-paper synthesis | `wiki/topics/<topic-name>.md` |

## Plan Boundary

The deterministic publisher reads `link-plan.json` and applies only actions already recorded there.

- `create_hub`: create a thin L2 page.
- `update_hub`: read the existing page and add only missing evidence, relations, or contradictions.
- `create_topic` / `update_topic`: create or update a cross-paper synthesis page.

Do not invent additional promotions, duplicate aliases, or change unrelated prose.

## Source Page Write

1. Read the source page records from `link-plan.json`.
2. Create missing source directories.
3. Preserve `created` on updates and set `updated` to today.
4. Write `source_sha256` for PDF inputs.
5. Copy all 16 numbered sections in order from the finalized Paper Card.
6. Do not include internal protocol markers, formula reports, evidence coverage lists, or audit artifacts.
7. Keep formulas in the finalized format.

## Hub Page Write

Hub pages stay short:

```markdown
# 页面名

一句话定义。

## 别名

## 证据

## 关系

## 争议与矛盾

## 开放问题

## 引用来源
```

Use `status: stub` for a new page. Include the current source report in `sources`. Link back to the source Paper Card instead of copying its module tables or ablations.

The publisher renders the evidence, relation, contradiction, open-question, and source sections directly from the audited action. It preserves existing page content and only appends missing rows.

## Existing Hub Page Rules

1. Read the target page before editing.
2. Compare aliases and canonical names.
3. Add only missing evidence and relations.
4. Add the current source report link once.
5. If a conflict exists, preserve the old position and add a contradiction entry.

## Topic Page Write

Create or update a topic page when:

- at least two source pages share the same problem, mechanism, or evidence space;
- the batch plan marks the topic for synthesis;
- an existing topic page contains an open question that a new paper answers or challenges.

Include:

```markdown
## 论文与方法对照

## 关键发现

## 争议与不确定

## 开放问题

## 研究空白与候选方向
```

Do not create a topic page merely because a paper discusses a subject.

The publisher renders grouped or flat comparison records, key findings (共识/单篇主张/分歧), contradictions, open questions, and research gaps from the audited action. On update, new comparison rows are merged into the existing comparison table instead of appending a sub-table.

## Index And Log

`wiki/index.md`:

- add missing page identity only;
- use a one-sentence description for each entry.

`wiki/log.md`:

- append one operation entry for source and hub writes;
- append one batch synthesis entry after topic pages are published;
- do not change earlier entries.

## Idempotency

- Same PDF SHA-256 and unchanged target: no writes.
- Changed PDF: update report while preserving `created`.
- Legacy report without SHA-256: treat as changed and add the fingerprint.
- Re-running the same link plan and cards must not rewrite unchanged pages, index entries, or log entries.
