# Reader-facing Wiki Writing Guide

This guide defines the writing contract for Paper Cards, Topic pages, and
user-facing research reports. These artifacts are read by both people and
agents, but the visible Markdown must first work as a complete human-readable
explanation. Structured JSON keeps machine-oriented fields; visible prose must
not make the reader reconstruct missing context from isolated fragments.

## Core Rule: Complete Before Concise

Write the shortest version only after the reasoning is complete. A useful
passage normally makes five things recoverable without a follow-up question:

1. the problem or concept being discussed;
2. the claim or relationship being established;
3. the evidence and comparison that support it;
4. the boundary, limitation, or competing explanation;
5. the implication for interpretation, method choice, or future work.

Not every paragraph needs five separate sentences. It must, however, contain
the parts needed for its claim. Do not replace missing reasoning with labels,
one-line bullets, or generic praise such as 非常重要 or 值得进一步研究.

## Paragraph, List, And Table Responsibilities

- Use paragraphs for explanation, causal reasoning, synthesis, interpretation,
  and judgment. A paragraph should develop one coherent point rather than act
  as a container for unrelated facts.
- Use lists only when the entries are genuinely parallel and a reader benefits
  from scanning them independently. Every visible list entry must still be a
  complete sentence or self-contained mini-paragraph.
- Use tables for comparison, indexing, and evidence lookup. Introduce a table
  with prose that explains what the reader should compare and why it matters.
  A table must not be the only explanation of a complex result.
- Do not duplicate the same content in a paragraph, list, and table. Let prose
  carry the interpretation and structured elements carry precise lookup data.
- Do not impose a mechanical word or character minimum. Add content only when
  it restores context, logic, evidence boundaries, or decision value.

## Sentence And Paragraph Style

- Prefer one principal claim per sentence. Split sentences when two claims need
  different evidence or qualifications.
- Do not join two full propositions with a semicolon. Use separate sentences.
- Do not insert a sentence-level aside with a dash. Use a separate sentence or
  remove the aside. Hyphens inside canonical terms, formulas, code, or quoted
  source text are unaffected.
- Avoid empty lead-ins such as 值得注意的是, 显而易见, and 需要指出的是.
- Never mention processing history such as 本批, 本次新增, or 追加证据 in a
  knowledge page.
- Preserve canonical model, dataset, metric, and method names in their original
  language. Define an unfamiliar term when the surrounding text cannot make its
  role clear.

## Evidence In Reader-facing Markdown

Every substantive paper-derived claim remains traceable to a structured source
reference and precise pointer. Evidence references support the prose; they do
not replace it. Prefer compact footnote references when long pointer strings
would interrupt reading. Keep the full source and pointer in the same page's
footnote definition or in the structured plan used to publish that page.

Internal ownership markers, replay fingerprints, stable IDs, and other
publisher protocol are application state. They must not appear in the visible
Markdown. Store them in structured plans or sidecar state.

## Paper Card Contract

A Paper Card explains one paper as an evidence-grounded argument. It keeps the
fixed Sections 01-16, but each section uses the form suited to its job.

- Sections 01-02 stay compact: metadata belongs in a table and the one-sentence
  summary remains one bounded sentence.
- Section 03 uses two prose units: 问题情境 explains the concrete problem, why
  it matters, and why existing approaches are insufficient; 核心研究问句
  states the precise, testable question. Do not create a second overlapping
  label such as 精确问题.
- Sections 04, 06, 07, and 11 are narrative-first. Explain the development
  path, surface method and core insight, end-to-end method, and bounded
  conclusion in coherent paragraphs rather than field bullets.
- Sections 05, 08, 10, 12, and 13 may keep their schema tables. Add an
  orientation or synthesis paragraph before a table so the reader knows what
  relationship the rows establish.
- In Section 09, place each display formula outside tables. Follow it with one
  cohesive paragraph that explains the symbols, purpose, intuition, and
  boundary. Do not split that explanation into 符号, 目的, and 直觉 bullets.
- Sections 14-15 group transferable knowledge and prior-knowledge connections
  by theme. A short list is acceptable only when every item is a self-contained
  mini-paragraph rather than a label plus fragment.
- In Section 16, each research idea is a titled unit with three prose
  paragraphs: the source observation and 核心假设; the relative difference,
  method, and 验证方式; then 可能失败 and 创新状态. Preserve these field labels
  in natural prose so deterministic audits can still find them.

## Topic Page Contract

A Topic page synthesizes multiple papers by research question, not by paper
order. It is a long-lived judgment surface rather than a batch report.

- 概述 uses two or three complete paragraphs. Define the problem and value,
  state what the field can currently support, then name the central evidence
  boundary or disagreement.
- 综合认识 uses three to five claim-led subsections when the evidence supports
  them. Each subsection normally uses two paragraphs: the first establishes the
  cross-paper relationship; the second explains comparability, limitations,
  alternatives, and research implications.
- 争议与不确定 appears only when a real disagreement exists. Present both
  positions, explain why they may differ, and name evidence that could
  distinguish them. Do not render an empty section.
- 论文与方法对照 remains a table because comparison is its primary purpose.
- 开放问题 remains a short list of self-contained questions.
- Each 研究空白 uses a heading and prose rather than a main bullet with many
  nested fields. Explain why the gap matters and where current evidence stops,
  then describe a test, success condition, and meaningful failure risk. The
  structured link plan retains the individual fields for agents and dashboards.

## What Never Counts As Content

- Restating an abstract without interpretation.
- A source pointer presented as if it were an explanation.
- A fragment whose relationship to the section claim is left implicit.
- A motivation phrase that names no judgment or choice.
- A future-work statement that no experiment or analysis could pick up.
- Repeating the same claim in several display forms without adding a new role.
