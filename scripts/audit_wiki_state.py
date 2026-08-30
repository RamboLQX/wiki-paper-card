#!/usr/bin/env python3
"""Audit the current wiki state for structural invariants.

Deterministic and read-only. Run it after publishing or whenever the wiki
looks wrong; it turns "visually spotted pollution" into scripted findings:

- orphan table rows: pipe lines detached from their table by a blank line
  (Obsidian renders them as raw pipe text);
- raw inline HTML tags outside code spans and math (Obsidian Live Preview
  treats an unclosed tag as an HTML region and stops rendering Markdown
  from that point to the end of the file);
- unresolved wikilinks (error for source page `关联页面` backlinks, warning
  elsewhere, including alias resolution);
- duplicate consecutive log entries in wiki/log.md.

Exit code is 1 when errors are found, 0 otherwise.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

WIKILINK_RE = re.compile(r"!?\[\[([^\]|\\]+)(?:\\?\|[^\]]+)?\]\]")
RAW_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*\s*/?>")
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
BLOCK_MATH_RE = re.compile(r"\$\$[^$]+?\$\$", re.S)
INLINE_MATH_RE = re.compile(r"(?<!\$)\$[^$]+?\$(?!\$)")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")


def finding(level: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if details:
        item["details"] = details
    return item


def load_publish_wiki() -> Any:
    spec = importlib.util.spec_from_file_location(
        "publish_wiki", ROOT / "scripts" / "publish_wiki.py"
    )
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load publish_wiki.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exposed_text(text: str) -> str:
    """Text with code spans and math removed, mirroring the finalize lint."""
    text = CODE_SPAN_RE.sub(" ", text)
    text = BLOCK_MATH_RE.sub(" ", text)
    text = INLINE_MATH_RE.sub(" ", text)
    return text


def is_separator_line(stripped: str) -> bool:
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [cell.strip() for cell in stripped[1:-1].split("|")]
    return bool(cells) and all(SEPARATOR_CELL_RE.match(cell) for cell in cells)


def check_orphan_table_rows(
    path: Path, text: str, findings: list[dict[str, Any]]
) -> None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        previous = lines[index - 1].strip() if index > 0 else ""
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        prev_is_row = previous.startswith("|")
        next_is_separator = "---" in following and following.startswith("|")
        if prev_is_row or is_separator_line(stripped) or next_is_separator:
            continue
        findings.append(
            finding(
                "error",
                "orphan_table_row",
                "Table row is detached from its table by a blank line; Obsidian renders it as raw pipe text.",
                path=str(path),
                line=index + 1,
                text=stripped[:80],
            )
        )


def check_raw_html(
    path: Path, text: str, findings: list[dict[str, Any]]
) -> None:
    exposed = exposed_text(text)
    for line_number, line in enumerate(exposed.splitlines(), start=1):
        for match in RAW_HTML_TAG_RE.finditer(line):
            findings.append(
                finding(
                    "error",
                    "raw_html_tag",
                    "Raw inline HTML tag breaks Obsidian Live Preview rendering; wrap the literal in backticks.",
                    path=str(path),
                    line=line_number,
                    tag=match.group(0),
                )
            )
    if HTML_COMMENT_RE.search(exposed):
        findings.append(
            finding(
                "error",
                "raw_html_comment",
                "Raw HTML comment found; use a blockquote note instead.",
                path=str(path),
            )
        )


def resolve_link_target(target: str, files_by_stem: dict[str, Path], alias_map: dict[str, str]) -> str | None:
    normalized = target.strip()
    if normalized.startswith("!"):
        normalized = normalized[1:]
    stem = Path(normalized).stem if "/" in normalized else normalized
    if stem.endswith(".md"):
        stem = stem[:-3]
    if stem in files_by_stem:
        return stem
    return alias_map.get(stem)


def build_resolution_maps(
    wiki_root: Path, publish_wiki: Any
) -> tuple[dict[str, Path], dict[str, str]]:
    files_by_stem: dict[str, Path] = {}
    alias_map: dict[str, str] = {}
    for path in sorted((wiki_root / "wiki").rglob("*.md")):
        files_by_stem.setdefault(path.stem, path)
        try:
            _, lists, _ = publish_wiki.parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        for alias in lists.get("aliases", []):
            alias_map.setdefault(alias, path.stem)
    return files_by_stem, alias_map


def check_wikilinks(
    wiki_root: Path,
    files_by_stem: dict[str, Path],
    alias_map: dict[str, str],
    findings: list[dict[str, Any]],
) -> None:
    for path in sorted((wiki_root / "wiki").rglob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        relative = str(path.relative_to(wiki_root))
        is_source_page = relative.startswith("wiki/sources/")
        in_backlink_section = False
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## "):
                in_backlink_section = "关联页面" in stripped
                continue
            for match in WIKILINK_RE.finditer(line):
                target = match.group(1)
                if resolve_link_target(target, files_by_stem, alias_map) is not None:
                    continue
                level = "error" if is_source_page and in_backlink_section else "warning"
                code = "unresolved_backlink" if level == "error" else "unresolved_link"
                findings.append(
                    finding(
                        level,
                        code,
                        f"Wikilink target does not resolve: {target}",
                        path=str(path),
                        line=index + 1,
                        target=target,
                    )
                )


def check_log_duplicates(
    wiki_root: Path, findings: list[dict[str, Any]]
) -> None:
    log_path = wiki_root / "wiki" / "log.md"
    if not log_path.is_file():
        return
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for index in range(1, len(lines)):
        current = lines[index].strip()
        previous = lines[index - 1].strip()
        if current and current == previous and current.startswith("- "):
            findings.append(
                finding(
                    "warning",
                    "duplicate_log_entry",
                    "Duplicate consecutive log entry.",
                    path="wiki/log.md",
                    line=index + 1,
                    entry=current[:80],
                )
            )


def audit(wiki_root: Path) -> dict[str, Any]:
    publish_wiki = load_publish_wiki()
    findings: list[dict[str, Any]] = []
    files = sorted((wiki_root / "wiki").rglob("*.md"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        check_orphan_table_rows(path.relative_to(wiki_root), text, findings)
        check_raw_html(path.relative_to(wiki_root), text, findings)

    files_by_stem, alias_map = build_resolution_maps(wiki_root, publish_wiki)
    check_wikilinks(wiki_root, files_by_stem, alias_map, findings)
    check_log_duplicates(wiki_root, findings)

    errors = sum(item["level"] == "error" for item in findings)
    warnings = sum(item["level"] == "warning" for item in findings)
    return {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if errors else ("pass_with_warnings" if warnings else "pass"),
            "errors": errors,
            "warnings": warnings,
            "files_scanned": len(files),
        },
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the wiki state for structural invariants.")
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wiki_root = args.wiki_root.expanduser().resolve()
    if not wiki_root.is_dir():
        print("ERROR: --wiki-root must point to an existing directory.", file=sys.stderr)
        return 2
    report = audit(wiki_root)
    print(
        f"Wiki state status: {report['summary']['status']} "
        f"(errors={report['summary']['errors']}, "
        f"warnings={report['summary']['warnings']}, "
        f"files={report['summary']['files_scanned']})"
    )
    for item in report["findings"]:
        print(f"{item['level'].upper():7} {item['code']}: {item['message']}")
        if item.get("details"):
            print(f"        {json.dumps(item['details'], ensure_ascii=False)}")
    if args.report:
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote wiki state audit report: {output}")
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
