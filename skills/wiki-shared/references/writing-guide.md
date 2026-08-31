# Topic And Report Writing Guide

This guide defines how topic pages and user-facing reports must be written.
It applies to the wiki-linker and the gap-mining miner. The goal is that a
researcher can read a topic page or a gap report and judge, without
re-reading the papers, what a problem is worth, where the field stands, and
what to do next.

## Core Rule: Motivation Before Detail

A topic page exists so a researcher can evaluate the value of a research
question. Every section must state the motivation before the detail.

- A research gap in 研究空白与候选方向 must answer why it is worth doing
  before anything else. State which judgment it would change or which
  choice it would affect. Empty praise such as 非常重要 or 值得进一步研究
  does not count as motivation and must not be written.
- A structured key finding must state what it changes for the reader. Say
  which belief about the field it revises or which decision it informs. A
  bare claim with a source pointer is not enough. The visible page integrates
  that finding into 综合认识 rather than repeating it as a bullet.
- The 概述 uses two short paragraphs. The first defines the problem and why
  it matters. The second states how far the field has come and where the main
  disagreement or evidence boundary sits.

Length is not the goal. Motivation present in every entry is the goal.
Write the shortest text that still carries the motivation.

## Sentence Style: One Sentence, One Claim

In prose sections (概述, 综合认识, 争议与不确定, and the report body):

- One sentence carries exactly one claim. Split compound sentences.
- Never join two full propositions with a semicolon. Write two sentences
  instead.
- Never insert a parenthetical clause with a dash. Write a separate
  sentence or drop the aside.
- Avoid empty lead-ins such as 值得注意的是, 显而易见, 需要指出的是.
- Never mention processing history such as 本批, 本次新增, or 追加证据.

## Narrative Paragraph Contract

Each 综合认识 or 争议与不确定 paragraph performs one argument in this order:

1. Topic sentence: the field-state judgment the paragraph establishes.
2. Evidence synthesis: combine papers by the shared question, not author order.
3. Boundary or difference: name the task, metric, dataset, or causal limit.
4. Implication: state what this changes for research judgment or method choice.
5. Evidence references: cite structured finding/contradiction IDs so the
   publisher can render the visible source-and-pointer line.

Use 3-5 claim-led synthesis subsections. A controversy subsection presents
both positions, explains why they may differ, and names the discriminating
evidence that would settle them. Do not write one paragraph per paper.

In compressed entries (comparison-table cells, the main line of a gap, and
the dashboard rows):

- One line carries one meaning.
- The gap main line stays the compact summary. Each detail sub-bullet
  (为什么值得做, 现有方法卡在哪, 怎么检验, 做到什么算成, 可能行不通)
  forms one complete sentence on its own.

The dash ban applies to sentence-level dashes in prose. It never applies to
hyphens inside canonical terms (cross-domain), to formulas, to code, or to
quoted source text.

## Terminology

- Keep canonical technical terms in the original language. Model names,
  metric names, and method names are not translated.
- Use the Chinese labels fixed by the schema (为什么值得做 and the other
  sub-bullets) exactly as the publisher renders them.

## What Never Counts As Content

- Restating an abstract.
- A statement no future work could pick up.
- A motivation phrase that names no judgment and no choice.
- An entry that merely rewords what an existing entry already says.
