# Processor Brief

This brief defines the single-paper `wiki-processor` subagent contract.

Process only the paper supplied in the parent prompt. Do not accept or continue with a different paper in the same processor session.

## Required Reads

Before processing, read completely:

1. The processor pack supplied by the parent prompt: one generated
   `processor-pack.md` containing this brief, the pinned upstream router,
   the upstream manifest and every file under its `always_load`, all six
   paper-type lens fragments, the on-demand references, the local knowledge
   model, the reader-facing writing guide, and the paper digest schema.
2. The pack's `## digest-schema` section for the digest field definitions.

When no pack is supplied, read the individual sources listed under
"Processor pack" in `workflow-contract.md` Phase 0 instead. Do not mix a
pack with individually re-read sources for the same paper.

Follow the upstream router for source boundary, paper-type selection, evidence inventory, and Sections 01-16. The parent workflow runs the deterministic auditor after this subagent returns.

## Role

Read one prepared source bundle once and produce two complete work products:

```text
paper-card.md
paper-digest.json
```

Do not read `raw/`. Do not write `wiki/`. Do not run audit scripts. Do not return the full paper text to the parent agent.

## Inputs

The parent prompt supplies:

```text
source_bundle.json
kb-context.md
work directory
target source page path
```

The source bundle already contains page text, evidence inventory, metadata, page count, validation status, and recommended locator mode.

## Paper Card Output

Write Sections 01-16 in order using the user's language.

### Required File Shape

The file must start with frontmatter and use zero-padded section headings with a dot:

```markdown
---
tags: [source, paper]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_sha256: "<source SHA-256>"
arxiv: "<arXiv or empty>"
authors: "<authors or empty>"
published: "<year or empty>"
venue: "<venue or empty>"
status: stub
---

# <paper title>

> Source coverage: Full paper
> Extraction confidence: High
> Locator mode: page-grounded
> Primary analytical lens: methods
> Secondary analytical lens: None
> Context verification: Paper-only
> Card completeness: Complete relative to supplied source

## 01. 基本信息
## 02. 一句话总结
## 03. 研究问题
## 04. 研究背景与发展路径
## 05. 论文识别的核心痛点
## 06. 核心思想
## 07. 方法概览
## 08. 核心模块拆解
## 09. 关键公式与符号
## 10. 实验设计与证据链
## 11. 结论的准确解读
## 12. 作者明确承认的局限
## 13. 批判性分析
## 14. 学到的知识
## 15. 与已有知识连接
## 16. 研究想法
```

Use the exact seven status-header lines above, replacing only the values. The
section headings must contain `NN.`, for example `## 01.`, not `## 01`.

For every substantive paper-derived statement, use a source pointer such as:

```text
[Paper: PDF p. 3, Figure 2]
[Paper: PDF p. 7, Table 4]
[Paper: Eq. 6]
```

Use only pointers present in the source bundle. Separate `[Paper]`, `[External]`, `[Analysis]`, `[Hypothesis]`, and `[User]`.

Section 12 contains only limitations explicitly acknowledged by the authors. Section 13 contains Agent analysis.

### Reader-facing Structure

Apply the shared writing guide before drafting. The visible card must allow a
reader to understand the paper without reconstructing its argument from field
labels or one-line bullets.

- Section 03 contains two prose units labelled `**问题情境。**` and
  `**核心研究问句。**`. The first integrates the concrete problem, its
  importance, and why existing approaches are insufficient. The second states
  one precise, testable research question. Do not add a separate `精确问题`.
- Sections 04, 06, 07, and 11 use coherent paragraphs. Section 06 explains the
  surface method and core insight together, then gives the transferable lesson
  with an `[Analysis]` label where needed.
- Sections 05, 08, 10, 12, and 13 may use the upstream tables, but precede each
  table with a synthesis paragraph that explains what relationship the reader
  should inspect. Do not use the table as the only explanation.
- Sections 14 and 15 group knowledge by theme. If a list is genuinely clearer,
  each entry must be a self-contained mini-paragraph rather than a short label.
- Each Section 16 idea uses a descriptive heading and three prose paragraphs:
  source observation plus `核心假设`; relative difference, initial method, and
  `验证方式`; then `可能失败` and `创新状态`. Do not render the idea as seven
  field bullets.

Lists and tables are not forbidden. Use them only for material whose primary
value is scanning, comparison, or lookup. Do not impose a word-count target or
pad sections when the source does not support more detail.

### Literal Tag Format

Never write a raw inline HTML tag in card text. A literal token such as
`<image>` or `<CPLINK>` breaks Obsidian Live Preview: the parser treats it as
an unclosed HTML region and stops rendering Markdown from that point to the
end of the file. Always wrap literal tags in backticks:

```markdown
对比 `<image>` token 与文本 token
```

The deterministic finalizer blocks cards that contain raw tags, so an
unwrapped `<image>` fails the audit and must be corrected before linking.

### Formula Format

Do not place raw formulas in Markdown table cells.

Use this pattern in Section 09:

```markdown
**Eq.1 ...** [Paper: PDF p. 3, Eq.1]

$$P(v) = \ldots$$

式中，... 表示 ...。该式用于 ...，其直觉是 ...。它只在 ... 条件下支持
这一解释，不能据此推出 ...。[Paper: PDF p. 3, Eq.1]
```

The optional index table below the formula may contain only its number, symbol
meanings, purpose, and source pointer. Do not repeat information already clear
in the explanatory paragraph. Use `$...$` only for short inline references
outside a table. Escape a literal pipe inside inline math as `\|`.

Correct:

```markdown
**Eq.1 上下文感知归因**

$$Attr(n_i^l) = \ldots$$

式中，$n_i^l$ 表示第 $l$ 层的第 $i$ 个节点。该式量化上下文对节点输出的
贡献，用于比较不同输入条件下的归因变化。它描述的是关联贡献，而不是因果效应。
[Paper: PDF p. 4, Eq. 2]

| 编号 | 符号含义 | 目的 | 来源 |
|---|---|---|---|
| Eq.1 | 激活差、梯度积分 | 量化上下文贡献 | [Paper: PDF p. 4, Eq. 2] |
```

Incorrect:

```markdown
| 公式 | 含义 |
|---|---|
| x_i = a_i + b_i | 未使用数学分隔符 |
```

Before returning, inspect every Markdown table row. A table cell must not
contain `$`, raw scripts such as `x_i`, raw superscripts such as `x^2`, TeX
commands, or a formula-like `=` expression. Move such content outside the table
or describe it in plain language.

### Evidence Coverage

Place each main Figure, Table, and Equation in the analytical section where it supports a claim. Do not add a standalone evidence coverage list, appendix coverage list, or raw extracted caption inventory.

Appendix-only or supporting items should appear only when they materially support a specific claim. The deterministic finalizer tracks coverage in a machine-readable report and does not require a visible checklist.

### Sections 14-16

Keep detailed paper-local knowledge in Sections 14-16.

- Paper-local terms, components, and one-off names stay in the Paper Card.
- Reusable but not yet cross-paper verified terms stay in the Paper Card; there are no concept pages, no entity pages, and no promotion ladder.

Proposed topic comparisons and open questions belong in the topic plan.

Section 16 ideas must each trace to a concrete observation or limitation. Write
each idea as a readable argument, not a metadata form. If none, leave the
section sparse rather than padding it with generic ideas.

## Paper Digest

Follow [paper-digest-schema.md](paper-digest-schema.md).

Write only paper-local analysis and topic seeds. Do not include `action`, `create_topic`, or `update_topic` fields. `wiki-linker` decides all cross-paper topic actions after the batch.

Do not put full Paper Card content in the digest. Keep definitions, topic seeds, and open questions compact.

## Return Protocol

Return only:

```text
status
output paths
paper type
locator mode
number of topic seeds
```
