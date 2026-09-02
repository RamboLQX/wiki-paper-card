#!/usr/bin/env python3
"""Audit a wiki-paper-card Markdown artifact against wiki-local constraints."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SECTION_RE = re.compile(r"^##\s+(\d{2})\.", re.M)
SECTION_BLOCK_RE = re.compile(
    r"^##\s+(\d{2})\.[^\n]*\n(.*?)(?=^##\s+\d{2}\. |\Z)",
    re.M | re.S,
)
TOP_LEVEL_LIST_RE = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
POINTER_ONLY_RE = re.compile(r"^(?:\[(?:Paper|External|Analysis|Hypothesis|User):?[^\]]*\]\s*)+$")
FORMULA_FIELD_BULLET_RE = re.compile(r"^\s*[-*+]\s*(?:符号|目的|直觉)\s*[:：]", re.M)
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
EXPECTED_FIELDS = {
    "source_sha256",
    "arxiv",
    "authors",
    "published",
    "venue",
    "status",
}
NARRATIVE_SECTIONS = ("03", "04", "06", "07", "11")
TABLE_SECTIONS = ("05", "08", "10", "12", "13")
PAPER_FRAMED_MARKER = "[Paper-framed; external verification not performed]"


def finding(level: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if details:
        item["details"] = details
    return item


def parse_frontmatter(card: str) -> tuple[dict[str, str], str]:
    if not card.startswith("---\n"):
        return {}, card
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", card, re.S)
    if not match:
        return {}, card

    raw_fields, body = match.groups()
    fields: dict[str, str] = {}
    for line in raw_fields.splitlines():
        field_match = FIELD_RE.match(line.strip())
        if field_match:
            fields[field_match.group(1)] = field_match.group(2).strip()
    return fields, body


def parse_tags(raw_tags: str) -> set[str]:
    value = raw_tags.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return {
        part.strip()
        for part in value.split(",")
        if part.strip()
    }


def split_sections(body: str) -> dict[str, str]:
    return {number: content.strip() for number, content in SECTION_BLOCK_RE.findall(body)}


def prose_paragraphs(text: str) -> list[str]:
    """Return reader-facing prose blocks, excluding structural Markdown."""
    cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
    cleaned = re.sub(r"\$\$.*?\$\$", "", cleaned, flags=re.S)
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            paragraphs.append(" ".join(current).strip())
            current.clear()

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        structural = (
            not line
            or line.startswith("#")
            or line.startswith(">")
            or TABLE_ROW_RE.match(line)
            or TOP_LEVEL_LIST_RE.match(raw_line)
            or POINTER_ONLY_RE.match(line)
            or re.fullmatch(r"\*\*[^*]+\*\*(?:\s*\[Paper:[^\]]+\])?", line)
        )
        if structural:
            flush()
            continue
        current.append(line)
    flush()
    return paragraphs


def top_level_list_count(text: str) -> int:
    return sum(bool(TOP_LEVEL_LIST_RE.match(line)) for line in text.splitlines())


def audit_readability(sections: dict[str, str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    narrative_errors: list[dict[str, Any]] = []

    research_question = sections.get("03", "")
    missing_question_labels = [
        label
        for label in ("问题情境", "核心研究问句")
        if label not in research_question
    ]
    if missing_question_labels or "精确问题" in research_question:
        findings.append(
            finding(
                "error",
                "research_question_structure",
                "Section 03 must use 问题情境 and 核心研究问句 without a duplicate 精确问题 field.",
                missing=missing_question_labels,
                duplicate_precise_question="精确问题" in research_question,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "research_question_structure",
                "Section 03 distinguishes the problem context from one core research question.",
            )
        )

    for number in NARRATIVE_SECTIONS:
        content = sections.get(number, "")
        paragraphs = prose_paragraphs(content)
        list_items = top_level_list_count(content)
        if not paragraphs:
            narrative_errors.append(
                {"section": number, "reason": "missing_prose"}
            )
        elif list_items >= 2 and list_items >= len(paragraphs):
            narrative_errors.append(
                {
                    "section": number,
                    "reason": "top_level_list_dominates",
                    "list_items": list_items,
                    "paragraphs": len(paragraphs),
                }
            )

    if narrative_errors:
        findings.append(
            finding(
                "error",
                "reader_facing_narrative",
                "Sections 03, 04, 06, 07, and 11 must use prose and must not be dominated by top-level lists.",
                sections=narrative_errors,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "reader_facing_narrative",
                "Narrative-first Paper Card sections contain readable prose.",
            )
        )

    missing_table_context: list[str] = []
    for number in TABLE_SECTIONS:
        content = sections.get(number, "")
        table_match = re.search(r"^\s*\|.*\|\s*$", content, re.M)
        if table_match and not prose_paragraphs(content[: table_match.start()]):
            missing_table_context.append(number)
    if missing_table_context:
        findings.append(
            finding(
                "error",
                "table_context",
                "A comparison table must be introduced by prose that explains what the reader should inspect.",
                sections=missing_table_context,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "table_context",
                "Structured evidence tables have reader-facing context where present.",
            )
        )

    formula_section = sections.get("09", "")
    formula_issues: list[str] = []
    if FORMULA_FIELD_BULLET_RE.search(formula_section):
        formula_issues.append("field_bullets")
    formula_blocks = list(re.finditer(r"\$\$.*?\$\$", formula_section, re.S))
    for index, block in enumerate(formula_blocks, start=1):
        next_start = (
            formula_blocks[index].start()
            if index < len(formula_blocks)
            else len(formula_section)
        )
        if not prose_paragraphs(formula_section[block.end() : next_start]):
            formula_issues.append(f"formula_{index}_missing_explanation")
    if formula_issues:
        findings.append(
            finding(
                "error",
                "formula_explanation",
                "Each display formula needs one cohesive explanatory paragraph; do not use symbol/purpose/intuition bullets.",
                issues=formula_issues,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "formula_explanation",
                "Formula explanations follow the reader-facing paragraph contract.",
            )
        )

    idea_section = sections.get("16", "")
    idea_paragraphs = prose_paragraphs(idea_section)
    idea_list_items = top_level_list_count(idea_section)
    if not idea_paragraphs or (idea_list_items >= 3 and idea_list_items >= len(idea_paragraphs)):
        findings.append(
            finding(
                "error",
                "research_idea_narrative",
                "Section 16 research ideas must be readable prose units rather than field-bullet forms.",
                paragraphs=len(idea_paragraphs),
                list_items=idea_list_items,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "research_idea_narrative",
                "Section 16 presents research ideas as readable prose units.",
            )
        )

    return findings


def audit(card_text: str, wiki_root: Path | None) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    fields, body = parse_frontmatter(card_text)

    tags = parse_tags(fields.get("tags", ""))
    if {"source", "paper"} <= tags:
        findings.append(finding("pass", "tags", "Source page tags are present."))
    else:
        findings.append(
            finding(
                "error",
                "tags",
                "Frontmatter must include both source and paper tags.",
                found=sorted(tags),
            )
        )

    missing_fields = sorted(EXPECTED_FIELDS - set(fields))
    if missing_fields:
        findings.append(
            finding(
                "error",
                "frontmatter_fields",
                "Required paper metadata fields are missing.",
                missing=missing_fields,
            )
        )
    else:
        findings.append(finding("pass", "frontmatter_fields", "Required metadata fields are present."))

    sections = SECTION_RE.findall(body)
    section_blocks = split_sections(body)
    expected = [f"{number:02d}" for number in range(1, 17)]
    if sections == expected:
        findings.append(finding("pass", "sections", "Sections 01-16 are present in order."))
    else:
        findings.append(
            finding(
                "error",
                "sections",
                "Sections 01-16 are missing, duplicated, or out of order.",
                expected=expected,
                found=sections,
            )
        )

    forbidden = [number for number in sections if number not in expected]
    if forbidden:
        findings.append(
            finding(
                "error",
                "forbidden_sections",
                "Sections outside 01-16 are not allowed.",
                found=forbidden,
            )
        )
    else:
        findings.append(finding("pass", "forbidden_sections", "No unexpected numbered sections found."))

    header_lines = body.split("## 01.", 1)[0].splitlines()
    status_lines = [line for line in header_lines if line.lstrip().startswith(">")]
    if len(status_lines) >= 7:
        findings.append(finding("pass", "status_header", "Evidence-status header is present."))
    else:
        findings.append(
            finding(
                "error",
                "status_header",
                "Evidence-status header must contain at least seven blockquote fields.",
                found=len(status_lines),
            )
        )

    pointers = re.findall(r"\[Paper:\s*([^\]]+)\]", body)
    if pointers:
        findings.append(
            finding("pass", "paper_pointers", "Paper source pointers are present.", count=len(pointers))
        )
    else:
        findings.append(finding("error", "paper_pointers", "No [Paper: ...] source pointers found."))

    for placeholder in ("{{title}}", "{{name}}", "{{date:"):
        if placeholder in body:
            findings.append(
                finding(
                    "error",
                    "template_placeholder",
                    "The card still contains a template placeholder.",
                    placeholder=placeholder,
                )
            )
            break
    else:
        findings.append(finding("pass", "template_placeholder", "No template placeholders found."))

    if PAPER_FRAMED_MARKER in body:
        findings.append(
            finding(
                "error",
                "internal_reader_marker",
                "An internal provenance protocol label must not appear in reader-facing Markdown.",
                marker=PAPER_FRAMED_MARKER,
            )
        )
    else:
        findings.append(
            finding(
                "pass",
                "internal_reader_marker",
                "No internal provenance protocol label is visible.",
            )
        )

    findings.extend(audit_readability(section_blocks))

    section_16 = re.search(r"^##\s+16\..*?\n(.*?)(?=^##\s|\Z)", body, re.M | re.S)
    if section_16:
        idea_text = section_16.group(1)
        required_idea_terms = ["核心假设", "验证方式", "可能失败"]
        missing_idea_terms = [term for term in required_idea_terms if term not in idea_text]
        if missing_idea_terms:
            findings.append(
                finding(
                    "warning",
                    "research_idea_fields",
                    "Section 16 may be missing required research-idea fields.",
                    missing=missing_idea_terms,
                )
            )
        else:
            findings.append(finding("pass", "research_idea_fields", "Section 16 idea fields are present."))
    else:
        findings.append(finding("error", "research_idea_section", "Section 16 was not found."))

    if wiki_root is None:
        findings.append(
            finding(
                "warning",
                "wiki_root_unavailable",
                "No wiki root was supplied; filesystem integration was not audited.",
            )
        )
    else:
        wiki_root = wiki_root.expanduser().resolve()
        required_paths = {
            "index": wiki_root / "wiki" / "index.md",
            "log": wiki_root / "wiki" / "log.md",
            "topics": wiki_root / "wiki" / "topics",
            "sources": wiki_root / "wiki" / "sources",
        }
        missing_paths = sorted(
            label for label, path in required_paths.items() if not path.exists()
        )
        if missing_paths:
            findings.append(
                finding(
                    "error",
                    "wiki_structure",
                    "The wiki root is missing required paths.",
                    missing=missing_paths,
                )
            )
        else:
            findings.append(finding("pass", "wiki_structure", "Required wiki paths exist."))

    errors = sum(item["level"] == "error" for item in findings)
    warnings = sum(item["level"] == "warning" for item in findings)
    passes = sum(item["level"] == "pass" for item in findings)
    return {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if errors else ("pass_with_warnings" if warnings else "pass"),
            "passes": passes,
            "warnings": warnings,
            "errors": errors,
        },
        "metrics": {
            "sections": sections,
            "paper_pointer_count": len(pointers),
            "required_frontmatter_fields": len(EXPECTED_FIELDS - set(missing_fields)),
        },
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a wiki-paper-card Markdown file.")
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--wiki-root", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.card.is_file():
        print("ERROR: --card must point to an existing file.", file=sys.stderr)
        return 2
    if args.wiki_root and not args.wiki_root.is_dir():
        print("ERROR: --wiki-root must point to an existing directory.", file=sys.stderr)
        return 2

    try:
        card_text = args.card.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = audit(card_text, args.wiki_root)
    print(
        f"Audit status: {report['summary']['status']} "
        f"(passes={report['summary']['passes']}, "
        f"warnings={report['summary']['warnings']}, "
        f"errors={report['summary']['errors']})"
    )
    for item in report["findings"]:
        print(f"{item['level'].upper():7} {item['code']}: {item['message']}")
        if item.get("details"):
            print(f"        {json.dumps(item['details'], ensure_ascii=False)}")

    if args.report:
        output = args.report.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote audit report: {output}")

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
