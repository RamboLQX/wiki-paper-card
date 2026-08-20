#!/usr/bin/env python3
"""Finalize a processor Paper Card with deterministic packaging checks."""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INLINE_MATH_RE = re.compile(r"(?<!\$)\$[^$]+?\$(?!\$)")
BLOCK_MATH_RE = re.compile(r"\$\$[^$]+?\$\$", re.S)
RAW_MATH_COMMANDS_RE = re.compile(r"\\(?:frac|sum|int|partial|mathbf|mathrm|alpha|beta|gamma)")
SCRIPT_MARK_RE = re.compile(r"[_^]\{?[A-Za-z0-9]")
MATH_OPERATOR_RE = re.compile(r"[=+<>≈≤≥]")
LOCATOR_MODE_RE = re.compile(r"^\s*>\s*Locator mode:\s*(.+?)\s*$", re.M)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
FRONTMATTER_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
SECTION_HEADING_RE = re.compile(r"^##\s+(\d{1,2})\s*(?:[.．:：]\s*)?(.*)$", re.M)
VISIBLE_EVIDENCE_LIST_RE = re.compile(
    r"(?im)^\s*(?:#{1,4}\s+)?"
    r"(?:\*\*)?"
    r"(?:(?:附录(?:证据|支撑项)?|证据)覆盖清单"
    r"|附录证据清单"
    r"|证据清单"
    r"|Evidence coverage list"
    r"|Coverage checklist)"
    r"(?:\*\*)?"
    r"(?:\s*[:：])?"
)
SECTION_BOUNDARY_TITLES = {
    "acknowledgment",
    "acknowledgments",
    "acknowledgement",
    "acknowledgements",
    "appendix",
    "references",
}


def finding(level: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if details:
        item["details"] = details
    return item


def report_summary(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "passes": sum(item["level"] == "pass" for item in findings),
        "warnings": sum(item["level"] == "warning" for item in findings),
        "errors": sum(item["level"] == "error" for item in findings),
    }


def strip_wrappers(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^#\s+Sections\s+\d{2}", line.strip()):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip() + "\n"


def normalize_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def yaml_field(name: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{name}: "{escaped}"'


def normalize_frontmatter(card_text: str, bundle_data: dict[str, Any] | None) -> str:
    """Ensure the local source-page frontmatter exists and has required fields."""
    match = FRONTMATTER_RE.match(card_text)
    fields: dict[str, str] = {}
    body = card_text
    if match:
        raw_fields, body = match.groups()
        for line in raw_fields.splitlines():
            field_match = FRONTMATTER_FIELD_RE.match(line.strip())
            if field_match:
                value = field_match.group(2).strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                fields[field_match.group(1)] = value

    today = datetime.date.today().isoformat()
    source_sha256 = (
        bundle_data.get("source_sha256")
        if bundle_data and isinstance(bundle_data.get("source_sha256"), str)
        else ""
    )
    defaults = {
        "tags": "[source, paper]",
        "created": fields.get("created") or today,
        "updated": today,
        "source_sha256": fields.get("source_sha256") or source_sha256,
        "arxiv": fields.get("arxiv") or "",
        "authors": fields.get("authors") or "",
        "published": fields.get("published") or "",
        "venue": fields.get("venue") or "",
        "status": fields.get("status") or "stub",
    }
    ordered = (
        "tags",
        "created",
        "updated",
        "source_sha256",
        "arxiv",
        "authors",
        "published",
        "venue",
        "status",
    )
    lines = ["---"]
    lines.extend(
        f"tags: {defaults[name]}" if name == "tags" else yaml_field(name, defaults[name])
        for name in ordered
    )
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def normalize_section_headings(card_text: str) -> str:
    return SECTION_HEADING_RE.sub(
        lambda match: f"## {int(match.group(1)):02d}. {match.group(2).strip()}",
        card_text,
    )


def split_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [
        cell.strip()
        for cell in re.split(r"(?<!\\)\|", stripped[1:-1])
    ]


def table_rows(text: str) -> list[tuple[int, list[str]]]:
    rows: list[tuple[int, list[str]]] = []
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = split_table_cells(line)
        if any(cell and set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append((line_number, cells))
    return rows


def raw_math_patterns(cell: str) -> list[str]:
    without_code = re.sub(r"`[^`]*`", "", cell)
    command_matches = [match.group(0) for match in RAW_MATH_COMMANDS_RE.finditer(without_code)]
    if command_matches:
        return command_matches

    script_marks = [match.group(0) for match in SCRIPT_MARK_RE.finditer(without_code)]
    if not script_marks:
        return []

    if any(mark.startswith(("_{", "^{")) for mark in script_marks):
        return script_marks
    if MATH_OPERATOR_RE.search(without_code):
        return script_marks
    return []


def audit_formulas(card_text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = table_rows(card_text)
    for line_number, cells in rows:
        for column, cell in enumerate(cells, start=1):
            if not cell:
                continue
            if BLOCK_MATH_RE.search(cell):
                findings.append(
                    finding(
                        "error",
                        "block_math_in_table",
                        "Display math is not allowed inside a Markdown table cell.",
                        line=line_number,
                        column=column,
                    )
                )
            if INLINE_MATH_RE.search(cell):
                findings.append(
                    finding(
                        "error",
                        "inline_math_in_table",
                        "Inline math is not allowed inside a Markdown table cell.",
                        line=line_number,
                        column=column,
                    )
                )
            raw_matches = raw_math_patterns(cell)
            if raw_matches:
                findings.append(
                    finding(
                        "error",
                        "raw_math_in_table",
                        "A table cell contains formula-like text without math delimiters.",
                        line=line_number,
                        column=column,
                        patterns=raw_matches,
                    )
                )

    if findings:
        findings.insert(
            0,
            finding(
                "error",
                "formula_table_contract",
                "Formulas must be moved outside Markdown tables.",
            ),
        )
    else:
        findings.append(
            finding("pass", "formula_table_contract", "No formula content was found in table cells.")
        )

    summary = report_summary(findings)
    return {
        "schema_version": "1.0",
        "summary": {
            **summary,
            "status": "fail" if summary["errors"] else ("pass_with_warnings" if summary["warnings"] else "pass"),
        },
        "metrics": {"table_rows": len(rows)},
        "findings": findings,
    }


def evidence_item_mentioned(card: str, item_id: str) -> bool:
    match = re.match(r"^(Figure|Table|Equation)\s+(\d+[A-Za-z]?)$", item_id)
    if not match:
        return item_id.lower() in card.lower()

    kind, number = match.groups()
    aliases = {
        "Figure": [
            f"Figure {number}",
            f"Fig. {number}",
            f"图{number}",
            f"图 {number}",
        ],
        "Table": [
            f"Table {number}",
            f"表{number}",
            f"表 {number}",
        ],
        "Equation": [
            f"Equation {number}",
            f"Eq. {number}",
            f"Eq.{number}",
            f"公式{number}",
            f"公式 {number}",
        ],
    }
    lower = card.lower()
    return any(alias.lower() in lower for alias in aliases[kind])


def body_text_cites_item(body_text: str, item_id: str) -> bool:
    match = re.match(r"^(Figure|Table|Equation)\s+(\d+[A-Za-z]?)$", item_id)
    if not match:
        normalized = re.sub(r"\s+", "", body_text).lower()
        return re.sub(r"\s+", "", item_id).lower() in normalized

    kind, number = match.groups()
    normalized = re.sub(r"\s+", "", body_text).lower()
    aliases = {
        "Figure": [
            f"figure{number.lower()}",
            f"fig.{number.lower()}",
            f"fig{number.lower()}",
            f"图{number}",
        ],
        "Table": [
            f"table{number.lower()}",
            f"表{number}",
        ],
        "Equation": [
            f"equation{number.lower()}",
            f"eq.{number.lower()}",
            f"eq{number.lower()}",
            f"公式{number}",
        ],
    }
    return any(alias in normalized for alias in aliases[kind])


def body_page_boundary(bundle: dict[str, Any]) -> int | None:
    pages = bundle.get("pages", [])
    if not isinstance(pages, list):
        return None
    if not pages:
        return None

    boundary: int | None = None
    for section in bundle.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title", "")).strip(" :").lower()
        if title in SECTION_BOUNDARY_TITLES:
            page = section.get("pdf_page")
            if isinstance(page, int) and page > 0:
                boundary = page if boundary is None else min(boundary, page)
    return boundary if boundary is not None else len(pages) + 1


def build_evidence_scope(bundle: dict[str, Any]) -> dict[str, Any]:
    pages = bundle.get("pages", [])
    boundary = body_page_boundary(bundle)
    body_text = (
        "\n".join(
            str(page.get("text", ""))
            for page in pages
            if isinstance(page, dict)
            and isinstance(page.get("pdf_page"), int)
            and page["pdf_page"] < boundary
        )
        if boundary is not None
        else ""
    )

    items: list[dict[str, Any]] = []
    inventory = bundle.get("evidence_inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    for kind in ("figures", "tables", "equations"):
        raw_items = inventory.get(kind, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            page = item.get("pdf_page")
            if boundary is None:
                role = "main"
            elif isinstance(page, int) and page > 0 and page < boundary:
                role = "main"
            else:
                role = "main" if body_text_cites_item(body_text, str(item["id"])) else "supplementary"
            items.append(
                {
                    "id": item["id"],
                    "kind": kind.rstrip("s"),
                    "pdf_page": page if isinstance(page, int) else None,
                    "role": role,
                }
            )
    return {
        "schema_version": "1.0",
        "body_page_boundary": boundary,
        "items": items,
    }


def audit_visible_evidence_lists(card_text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(card_text.splitlines(), start=1):
        if VISIBLE_EVIDENCE_LIST_RE.match(line.strip()):
            findings.append(
                finding(
                    "error",
                    "visible_evidence_list",
                    "The Paper Card must not contain a standalone evidence coverage list.",
                    line=line_number,
                    text=line.strip(),
                )
            )
    if not findings:
        findings.append(
            finding("pass", "visible_evidence_list", "No standalone evidence coverage list was found.")
        )
    summary = report_summary(findings)
    return {
        "schema_version": "1.0",
        "summary": {
            **summary,
            "status": "fail" if summary["errors"] else "pass",
        },
        "findings": findings,
    }


def build_evidence_coverage_report(card_text: str, scope: dict[str, Any]) -> dict[str, Any]:
    items = scope.get("items", [])
    missing_main = [
        item["id"]
        for item in items
        if item["role"] == "main" and not evidence_item_mentioned(card_text, item["id"])
    ]
    main_count = sum(item["role"] == "main" for item in items)
    supplementary_count = sum(item["role"] == "supplementary" for item in items)
    return {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if missing_main else "pass",
            "main_count": main_count,
            "supplementary_count": supplementary_count,
            "missing_main_count": len(missing_main),
        },
        "scope": scope,
        "missing_main": missing_main,
    }


def filtered_audit_bundle(bundle: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    filtered = copy.deepcopy(bundle)
    main_ids = {
        item["id"]
        for item in scope.get("items", [])
        if item["role"] == "main"
    }
    inventory = filtered.setdefault("evidence_inventory", {})
    for key in ("figures", "tables", "equations"):
        if not isinstance(inventory.get(key), list):
            inventory[key] = []
            continue
        inventory[key] = [
            item
            for item in inventory[key]
            if isinstance(item, dict) and item.get("id") in main_ids
        ]
    return filtered


def infer_locator_mode(card_text: str) -> str:
    match = LOCATOR_MODE_RE.search(card_text)
    if not match:
        raise ValueError("Paper Card must declare Locator mode.")
    return match.group(1).strip()


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(
    command: list[str],
    report_path: Path | None = None,
) -> tuple[int, dict[str, Any] | None]:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if report_path and report_path.is_file():
        return result.returncode, load_report(report_path)
    return result.returncode, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Finalize a processor Paper Card and run audits."
    )
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--wiki-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    card_path = args.card.expanduser().resolve()
    if not card_path.is_file():
        print("ERROR: --card must point to an existing file.", file=sys.stderr)
        return 2
    if args.bundle and not args.bundle.is_file():
        print("ERROR: --bundle does not exist.", file=sys.stderr)
        return 2

    bundle_data: dict[str, Any] | None = None
    if args.bundle:
        try:
            bundle_data = json.loads(args.bundle.resolve().read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"ERROR: unable to load source bundle: {exc}", file=sys.stderr)
            return 2

    try:
        card_text = card_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        locator_mode = infer_locator_mode(card_text)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    card_text = normalize_blank_lines(strip_wrappers(card_text))
    card_text = normalize_frontmatter(card_text, bundle_data)
    card_text = normalize_section_headings(card_text)
    formula_report = audit_formulas(card_text)
    evidence_list_report = audit_visible_evidence_lists(card_text)
    formula_path = card_path.parent / "formula-report.json"
    formula_path.write_text(
        json.dumps(formula_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    audit_bundle_path: Path | None = None
    evidence_coverage_report: dict[str, Any] | None = None
    if args.bundle:
        try:
            bundle_data = json.loads(args.bundle.resolve().read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"ERROR: unable to load source bundle: {exc}", file=sys.stderr)
            return 2
        scope = build_evidence_scope(bundle_data)
        evidence_coverage_report = build_evidence_coverage_report(card_text, scope)
        evidence_path = card_path.parent / "evidence-coverage-report.json"
        evidence_path.write_text(
            json.dumps(evidence_coverage_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        audit_bundle_path = card_path.parent / "audit-bundle.json"
        audit_bundle_path.write_text(
            json.dumps(filtered_audit_bundle(bundle_data, scope), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    audit_command = [
        sys.executable,
        str(args.repo_root / "vendor" / "nature-paper-card" / "scripts" / "audit_paper_card.py"),
        "--card",
        str(card_path),
        "--locator-mode",
        locator_mode,
        "--report",
        str(card_path.parent / "audit-report.json"),
    ]
    if audit_bundle_path:
        audit_command.extend(["--bundle", str(audit_bundle_path)])

    output_path = args.output.expanduser().resolve() if args.output else card_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(card_text, encoding="utf-8")

    if output_path != card_path:
        audit_command[audit_command.index("--card") + 1] = str(output_path)

    upstream_code, upstream_report = run_command(
        audit_command,
        card_path.parent / "audit-report.json",
    )
    wiki_command = [
        sys.executable,
        str(args.repo_root / "scripts" / "audit_wiki_paper_card.py"),
        "--card",
        str(output_path),
        "--report",
        str(output_path.parent / "wiki-audit-report.json"),
    ]
    if args.wiki_root:
        wiki_command.extend(["--wiki-root", str(args.wiki_root.resolve())])
    wiki_code, wiki_report = run_command(
        wiki_command,
        output_path.parent / "wiki-audit-report.json",
    )

    print(f"Formula status: {formula_report['summary']['status']}")
    print(f"Evidence list status: {evidence_list_report['summary']['status']}")
    if evidence_coverage_report:
        print(
            "Evidence coverage status: "
            f"{evidence_coverage_report['summary']['status']} "
            f"(missing main={evidence_coverage_report['summary']['missing_main_count']})"
        )
    formula_errors = formula_report["summary"]["errors"]
    evidence_list_errors = evidence_list_report["summary"]["errors"]
    upstream_errors = upstream_report["summary"]["errors"] if upstream_report else 0
    wiki_errors = wiki_report["summary"]["errors"] if wiki_report else 0
    total_errors = formula_errors + evidence_list_errors + upstream_errors + wiki_errors
    print(f"Total audit errors: {total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
