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
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
EXPECTED_FIELDS = {
    "source_sha256",
    "arxiv",
    "authors",
    "published",
    "venue",
    "status",
}


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
