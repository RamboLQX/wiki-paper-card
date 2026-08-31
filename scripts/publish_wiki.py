#!/usr/bin/env python3
"""Publish an audited link-plan.json into the LLM Wiki."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
FRONTMATTER_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
FRONTMATTER_LIST_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:$")
FRONTMATTER_ITEM_RE = re.compile(r"^\s+-\s+(.+)$")
SECTION_BODY_RE = re.compile(
    r"(?ms)^(## 01\..*?)(?=^## (?!\d{2}\.)|\Z)"
)
H1_RE = re.compile(r"^#\s+(.+)$", re.M)
ITEM_METADATA_RE = re.compile(
    r"\s*%%\s*wiki-paper-card:item\s+id=([a-z][a-z0-9-]*)\s+origin=(ingest|mining)\s*%%\s*"
)
MANAGED_KEYS = ("overview", "synthesis", "controversies")
MINING_STUB_OVERVIEW = "当前仅记录经确认的研究空白，尚未形成跨论文综合。"


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_frontmatter(text: str) -> tuple[dict[str, str], dict[str, list[str]], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, {}, text

    raw_fields, body = match.groups()
    fields: dict[str, str] = {}
    lists: dict[str, list[str]] = {}
    current_list: str | None = None
    for line in raw_fields.splitlines():
        field_match = FRONTMATTER_FIELD_RE.match(line.strip())
        if field_match and field_match.group(2).strip():
            current_list = None
            value = field_match.group(2).strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            fields[field_match.group(1)] = value
            continue
        list_match = FRONTMATTER_LIST_RE.match(line.strip())
        if list_match:
            current_list = list_match.group(1)
            lists.setdefault(current_list, [])
            continue
        item_match = FRONTMATTER_ITEM_RE.match(line)
        if item_match and current_list:
            value = item_match.group(1).strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            lists[current_list].append(value)
    return fields, lists, body


def render_frontmatter(
    tags: list[str],
    created: str,
    updated: str,
    status: str,
    *,
    sources: list[str] | None = None,
    aliases: list[str] | None = None,
    extra: list[tuple[str, str]] | None = None,
) -> str:
    lines = [
        "---",
        f"tags: [{', '.join(tags)}]",
        f"created: {yaml_string(created)}",
        f"updated: {yaml_string(updated)}",
    ]
    if sources is not None:
        lines.append("sources:")
        lines.extend(f"  - {yaml_string(value)}" for value in sources)
    if aliases is not None:
        lines.append("aliases:")
        lines.extend(f"  - {yaml_string(value)}" for value in aliases)
    for name, value in extra or []:
        lines.append(f"{name}: {yaml_string(value)}")
    lines.extend([f"status: {yaml_string(status)}", "---", ""])
    return "\n".join(lines)


def safe_relative_path(root: Path, value: str) -> Path:
    root_path = root.expanduser().resolve()
    path = (root_path / value).resolve()
    if path != root_path and root_path not in path.parents:
        raise ValueError(f"Path escapes wiki root: {value}")
    return path


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", name).strip(" .-")
    return cleaned or "untitled"


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def action_fingerprint(action: dict[str, Any]) -> str:
    payload = json.dumps(
        action, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def item_metadata_suffix(item: dict[str, Any]) -> str:
    item_id = str(item.get("id", "")).strip()
    origin = str(item.get("origin", "")).strip()
    if not item_id or origin not in {"ingest", "mining"}:
        return ""
    return f" %% wiki-paper-card:item id={item_id} origin={origin} %%"


def strip_item_metadata(text: str) -> str:
    return ITEM_METADATA_RE.sub("", text).strip()


def item_id_from_text(text: str) -> str:
    match = ITEM_METADATA_RE.search(text)
    return match.group(1) if match else ""


def item_origin_from_text(text: str) -> str:
    match = ITEM_METADATA_RE.search(text)
    return match.group(2) if match else ""


def escape_table(value: Any) -> str:
    return str(value).replace("|", "\\|")


def source_label(source_ref: str, titles: dict[str, str]) -> str:
    return titles.get(source_ref) or Path(source_ref).stem


def wiki_link(path: str, label: str) -> str:
    return f"[[{Path(path).stem}|{label}]]"


def extract_source_body(card_text: str) -> str:
    _, _, body = parse_frontmatter(card_text)
    match = SECTION_BODY_RE.search(body)
    return (match.group(1) if match else body).strip()


def first_h1(text: str) -> str:
    _, _, body = parse_frontmatter(text)
    match = H1_RE.search(body)
    return match.group(1).strip() if match else ""


def source_page_text(
    page: dict[str, Any],
    card_text: str,
    existing_text: str | None,
    today: str,
) -> str:
    existing_fields, _, _ = parse_frontmatter(existing_text or "")
    fields, _, _ = parse_frontmatter(card_text)
    created = existing_fields.get("created") or fields.get("created") or today
    title = (
        first_h1(existing_text or "")
        or first_h1(card_text)
        or page.get("title", "")
    )
    source_sha256 = fields.get("source_sha256", "")
    extra = [
        ("source_sha256", source_sha256),
        ("arxiv", fields.get("arxiv", "")),
        ("authors", fields.get("authors", "")),
        ("published", fields.get("published", "")),
        ("venue", fields.get("venue", "")),
    ]
    frontmatter = render_frontmatter(
        ["source", "paper"],
        created,
        today,
        fields.get("status") or "stub",
        extra=extra,
    )
    return f"{frontmatter}# {title}\n\n{extract_source_body(card_text)}\n"


def render_backlinks(entries: list[tuple[str, str]]) -> str:
    if not entries:
        return ""
    lines = ["", "## 关联页面", ""]
    for name, kind in entries:
        lines.append(f"- [[{name}|{name}]] - {kind}")
    return "\n".join(lines)


def backlink_bullets(entries: list[tuple[str, str]]) -> list[str]:
    return [f"- [[{name}|{name}]] - {kind}" for name, kind in entries]


def append_backlinks_to_page(
    wiki_root: Path, source_ref: str, entries: list[tuple[str, str]]
) -> tuple[str, bool]:
    """Append topic backlinks to an existing source page (deduplicated).

    Returns (updated_text, changed). Missing or unreadable pages raise.
    """
    target = safe_relative_path(wiki_root, source_ref)
    if not target.is_file():
        raise FileNotFoundError(f"Missing source page: {source_ref}")
    existing = target.read_text(encoding="utf-8")
    _, _, body = parse_frontmatter(existing)
    additions = backlink_bullets(entries)
    updated_body = insert_before_next_section(body, "关联页面", additions)
    if updated_body == body:
        return existing, False
    head = existing[: len(existing) - len(body)]
    return head + updated_body, True


def render_contradictions(items: Any, titles: dict[str, str]) -> list[str]:
    if not isinstance(items, list):
        return []
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        position_a = item.get("position_a") or item.get("a") or ""
        position_b = item.get("position_b") or item.get("b") or ""
        source_a = (
            item.get("position_a_source_ref")
            or item.get("source_ref_a")
            or item.get("source_a")
            or ""
        )
        source_b = (
            item.get("position_b_source_ref")
            or item.get("source_ref_b")
            or item.get("source_b")
            or ""
        )
        pointer_a = item.get("position_a_pointer") or item.get("pointer_a") or ""
        pointer_b = item.get("position_b_pointer") or item.get("pointer_b") or ""
        resolve = item.get("resolving_evidence") or item.get("resolve") or ""
        if not position_a and not position_b and not resolve:
            continue
        if len(items) > 1:
            lines.append(f"**矛盾 {index}**")
        if position_a:
            lines.append(f"- 位置 A：{position_a}")
            if source_a:
                lines.append(f"  - 来源：{source_label(source_a, titles)}")
            if pointer_a:
                lines.append(f"  - 证据：{pointer_a}")
        if position_b:
            lines.append(f"- 位置 B：{position_b}")
            if source_b:
                lines.append(f"  - 来源：{source_label(source_b, titles)}")
            if pointer_b:
                lines.append(f"  - 证据：{pointer_b}")
        if resolve:
            lines.append(f"- 如何解决：{resolve}")
        lines.append("")
    return lines


def comparison_paper_name(item: dict[str, Any], titles: dict[str, str]) -> str:
    return (item.get("paper") or source_label(item.get("source_ref", ""), titles)).strip()


def comparison_row(row: dict[str, Any], titles: dict[str, str]) -> str:
    source_ref = row.get("source_ref", "")
    paper = row.get("paper") or source_label(source_ref, titles)
    paper_cell = escape_table(wiki_link(source_ref, paper)) if source_ref else escape_table(paper)
    return (
        "| "
        + " | ".join(
            [
                paper_cell,
                escape_table(row.get("method", "")),
                escape_table(
                    row.get("intervention_granularity", row.get("granularity", ""))
                ),
                escape_table(row.get("main_result", "")),
                escape_table(row.get("boundary", "")),
                escape_table(row.get("pointer", "")),
            ]
        )
        + " |"
    )


def render_flat_comparison_rows(items: list[dict[str, Any]], titles: dict[str, str]) -> list[str]:
    return [comparison_row(row, titles) for row in items if isinstance(row, dict)]


def render_flat_comparisons(items: list[dict[str, Any]], titles: dict[str, str]) -> list[str]:
    lines = [
        "| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(render_flat_comparison_rows(items, titles))
    return lines


def render_grouped_comparisons(items: list[dict[str, Any]], titles: dict[str, str]) -> list[str]:
    lines: list[str] = []
    for group in items:
        dimension = group.get("dimension") or group.get("name") or ""
        if dimension:
            lines.extend([f"### {dimension}", ""])
        entries = group.get("entries", [])
        if not isinstance(entries, list):
            continue
        lines.extend(["| 论文 | 断言 | 证据 |", "|---|---|---|"])
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_ref = entry.get("source_ref", "")
            paper = entry.get("paper") or source_label(source_ref, titles)
            paper_cell = escape_table(wiki_link(source_ref, paper)) if source_ref else escape_table(paper)
            lines.append(
                "| "
                + " | ".join(
                    [
                        paper_cell,
                        escape_table(entry.get("claim", "")),
                        escape_table(entry.get("pointer", "")),
                    ]
                )
                + " |"
            )
        lines.append("")
    return lines


KEY_FINDING_LABELS = {
    "consensus": "共识",
    "single": "单篇主张",
    "conflict": "分歧",
}

def source_wikilink(source_ref: str, short_names: dict[str, str], titles: dict[str, str]) -> str:
    label = short_names.get(source_ref) or titles.get(source_ref) or Path(source_ref).stem
    return wiki_link(source_ref, label)


def render_key_findings(
    items: Any,
    titles: dict[str, str],
    short_names: dict[str, str] | None = None,
) -> list[str]:
    if not isinstance(items, list) or not items:
        return []
    short = short_names or {}
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        if not claim:
            continue
        label = KEY_FINDING_LABELS.get(item.get("kind", ""), "")
        refs = "、".join(
            source_wikilink(ref, short, titles) for ref in string_list(item.get("source_refs"))
        )
        pointer = str(item.get("pointer", ""))
        suffix = "；".join(
            part for part in [f"来源：{refs}" if refs else "", pointer] if part
        )
        prefix = f"{label}：" if label else ""
        lines.append(f"- {prefix}{claim}" + (f"（{suffix}）" if suffix else ""))
    return lines


def normalize_questions(items: Any) -> list[dict[str, Any]]:
    """Normalize open_questions entries; strings become open items."""
    normalized: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if isinstance(item, str):
            question = item.strip()
            if question:
                normalized.append({"question": question, "status": "open"})
            continue
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        if not question:
            continue
        entry: dict[str, Any] = {
            "id": str(item.get("id", "")).strip(),
            "origin": str(item.get("origin", "")).strip(),
            "question": question,
            "source_refs": string_list(item.get("source_refs")),
            "status": item.get("status", "open"),
        }
        if entry["status"] == "answered":
            entry["answered_by"] = string_list(item.get("answered_by"))
            entry["answered_pointer"] = str(item.get("answered_pointer", "")).strip()
        normalized.append(entry)
    return normalized


def render_open_questions(
    items: Any,
    titles: dict[str, str],
    short_names: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Render open_questions into (open bullets, resolved bullets).

    Resolved bullets go to the `## 已解决的问题` archive section.
    """
    short = short_names or {}
    open_lines: list[str] = []
    resolved_lines: list[str] = []
    for entry in normalize_questions(items):
        if entry["status"] == "answered":
            refs = "、".join(
                source_wikilink(ref, short, titles)
                for ref in entry.get("answered_by", [])
            )
            pointer = entry.get("answered_pointer", "")
            suffix = "；".join(
                part
                for part in [f"已解决：{refs}" if refs else "", pointer]
                if part
            )
            resolved_lines.append(
                f"- {entry['question']}"
                + (f"（{suffix}）" if suffix else "")
                + item_metadata_suffix(entry)
            )
        else:
            open_lines.append(f"- {entry['question']}" + item_metadata_suffix(entry))
    return open_lines, resolved_lines


def normalize_gaps(items: Any) -> list[dict[str, Any]]:
    """Normalize research_gaps entries; strings become open items.

    The optional v2 detail fields (significance, evidence_boundary,
    experiment, success_criterion, risk, priority) are carried through when
    present; entries without them render exactly as before.
    """
    normalized: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return normalized
    for item in items:
        if isinstance(item, str):
            gap = item.strip()
            if gap:
                normalized.append({"gap": gap, "status": "open"})
            continue
        if not isinstance(item, dict):
            continue
        gap = str(item.get("gap", "")).strip()
        if not gap:
            continue
        entry: dict[str, Any] = {
            "id": str(item.get("id", "")).strip(),
            "origin": str(item.get("origin", "")).strip(),
            "gap": gap,
            "source_refs": string_list(item.get("source_refs")),
            "direction": str(item.get("direction", "")).strip(),
            "continuity": str(item.get("continuity", "")).strip(),
            "significance": str(item.get("significance", "")).strip(),
            "evidence_boundary": str(item.get("evidence_boundary", "")).strip(),
            "experiment": str(item.get("experiment", "")).strip(),
            "success_criterion": str(item.get("success_criterion", "")).strip(),
            "risk": str(item.get("risk", "")).strip(),
            "priority": str(item.get("priority", "")).strip(),
            "status": item.get("status", "open"),
        }
        if entry["status"] == "answered":
            entry["answered_by"] = string_list(item.get("answered_by"))
            entry["answered_pointer"] = str(item.get("answered_pointer", "")).strip()
        normalized.append(entry)
    return normalized


GAP_DETAIL_FIELDS: tuple[tuple[str, str], ...] = (
    ("significance", "为什么值得做"),
    ("evidence_boundary", "现有方法卡在哪"),
    ("experiment", "怎么检验"),
    ("success_criterion", "做到什么算成"),
    ("risk", "可能行不通"),
    ("priority", "优先级"),
)


def gap_bullet(
    entry: dict[str, Any],
    titles: dict[str, str],
    short_names: dict[str, str] | None,
) -> str:
    """Render one open gap as a main bullet plus optional detail sub-bullets.

    Entries without any v2 detail field render byte-identically to the
    legacy single-line format. A v2 entry that lacks both
    ``evidence_boundary`` and ``experiment`` is a tentative direction and
    carries a [待验证] tag.
    """
    short = short_names or {}
    refs = "、".join(
        source_wikilink(ref, short, titles) for ref in entry.get("source_refs", [])
    )
    direction = entry.get("direction", "")
    continuity = entry.get("continuity", "")
    suffix = "；".join(
        part
        for part in [
            f"来源：{refs}" if refs else "",
            f"可检验方向：{direction}" if direction else "",
            f"承接：{continuity}" if continuity else "",
        ]
        if part
    )
    details = [
        f"  - {label}：{entry[field]}"
        for field, label in GAP_DETAIL_FIELDS
        if entry.get(field)
    ]
    has_v2 = any(entry.get(field) for field, _ in GAP_DETAIL_FIELDS)
    tentative = has_v2 and not (
        entry.get("evidence_boundary") and entry.get("experiment")
    )
    tag = " [待验证]" if tentative else ""
    line = (
        f"- {entry['gap']}{tag}"
        + (f"（{suffix}）" if suffix else "")
        + item_metadata_suffix(entry)
    )
    if details:
        return "\n".join([line] + details)
    return line


def gap_key(text: str) -> str:
    """Reduce a rendered gap root line to its plain gap text for dedup."""
    key = strip_item_metadata(text).split("（", 1)[0].strip()
    if key.endswith(" [待验证]"):
        key = key[: -len(" [待验证]")]
    return key


def section_bullet_blocks(body: str, section_name: str) -> list[str]:
    """Return top-level bullets with their indented sub-lines, in order."""
    blocks: list[str] = []
    current: list[str] = []
    for line in section_body(body, section_name).splitlines():
        if line.startswith("- "):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        elif current and (line.startswith("  ") or not line.strip()):
            current.append(line)
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def block_root_text(block: str) -> str:
    first = block.splitlines()[0].strip() if block else ""
    visible = first[2:].strip() if first.startswith("- ") else first
    return strip_item_metadata(visible)


def render_research_gaps(
    items: Any,
    titles: dict[str, str],
    short_names: dict[str, str] | None = None,
) -> list[str]:
    """Render the open research gaps of an action as bullets.

    Answered gaps are rendered separately by render_resolved_research_gaps.
    """
    lines: list[str] = []
    for entry in normalize_gaps(items):
        if entry["status"] == "open":
            lines.append(gap_bullet(entry, titles, short_names))
    return lines


def render_resolved_research_gaps(
    items: Any,
    titles: dict[str, str],
    short_names: dict[str, str] | None = None,
) -> list[str]:
    """Render answered research gaps as bullets for the archive section."""
    short = short_names or {}
    lines: list[str] = []
    for entry in normalize_gaps(items):
        if entry["status"] != "answered":
            continue
        refs = "、".join(
            source_wikilink(ref, short, titles) for ref in entry.get("source_refs", [])
        )
        answered_refs = "、".join(
            source_wikilink(ref, short, titles)
            for ref in entry.get("answered_by", [])
        )
        pointer = entry.get("answered_pointer", "")
        suffix = "；".join(
            part
            for part in [
                f"来源：{refs}" if refs else "",
                f"已解决：{answered_refs}" if answered_refs else "",
                pointer,
            ]
            if part
        )
        lines.append(
            f"- {entry['gap']}"
            + (f"（{suffix}）" if suffix else "")
            + item_metadata_suffix(entry)
        )
    return lines


def managed_block_lines(key: str, content: list[str]) -> list[str]:
    lines = [f"%% wiki-paper-card:managed-start {key} %%", ""]
    lines.extend(content)
    if content and content[-1] != "":
        lines.append("")
    lines.append(f"%% wiki-paper-card:managed-end {key} %%")
    return lines


def has_managed_blocks(body: str) -> bool:
    return all(
        f"%% wiki-paper-card:managed-start {key} %%" in body
        and f"%% wiki-paper-card:managed-end {key} %%" in body
        for key in MANAGED_KEYS
    )


def replace_managed_block(body: str, key: str, content: list[str]) -> str:
    pattern = re.compile(
        rf"(?ms)^%% wiki-paper-card:managed-start {re.escape(key)} %%\s*$.*?"
        rf"^%% wiki-paper-card:managed-end {re.escape(key)} %%\s*$"
    )
    replacement = "\n".join(managed_block_lines(key, content)) + "\n"
    if not pattern.search(body):
        raise ValueError(f"narrative_migration_required: missing managed block {key}")
    return pattern.sub(lambda _: replacement, body, count=1)


def paragraph_evidence(
    paragraph: dict[str, Any],
    findings: dict[str, dict[str, Any]],
    contradictions: dict[str, dict[str, Any]],
    titles: dict[str, str],
    short_names: dict[str, str] | None,
) -> str:
    short = short_names or {}
    evidence: list[str] = []
    for finding_id in string_list(paragraph.get("finding_refs")):
        item = findings.get(finding_id, {})
        pointers = item.get("pointers", [])
        if not isinstance(pointers, list):
            continue
        for pointer in pointers:
            if not isinstance(pointer, dict):
                continue
            source_ref = str(pointer.get("source_ref", "")).strip()
            locator = str(pointer.get("pointer", "")).strip()
            if not source_ref:
                continue
            value = source_wikilink(source_ref, short, titles)
            if locator:
                value += f" {locator}"
            if value not in evidence:
                evidence.append(value)
    for contradiction_id in string_list(paragraph.get("contradiction_refs")):
        item = contradictions.get(contradiction_id, {})
        for side in ("a", "b"):
            source_ref = str(item.get(f"position_{side}_source_ref", "")).strip()
            locator = str(item.get(f"position_{side}_pointer", "")).strip()
            if not source_ref:
                continue
            value = source_wikilink(source_ref, short, titles)
            if locator:
                value += f" {locator}"
            if value not in evidence:
                evidence.append(value)
    return f"*证据：{'；'.join(evidence)}。*" if evidence else ""


def render_v3_paragraphs(
    paragraphs: Any,
    findings: dict[str, dict[str, Any]],
    contradictions: dict[str, dict[str, Any]],
    titles: dict[str, str],
    short_names: dict[str, str] | None,
) -> list[str]:
    lines: list[str] = []
    if not isinstance(paragraphs, list):
        return lines
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        text = str(paragraph.get("text", "")).strip()
        if not text:
            continue
        if lines:
            lines.append("")
        lines.append(text)
        evidence = paragraph_evidence(
            paragraph, findings, contradictions, titles, short_names
        )
        if evidence:
            lines.extend(["", evidence])
    return lines


def render_v3_narrative(
    action: dict[str, Any],
    titles: dict[str, str],
    short_names: dict[str, str] | None,
) -> dict[str, list[str]]:
    findings = {
        str(item.get("id")): item
        for item in action.get("key_findings", [])
        if isinstance(item, dict) and item.get("id")
    }
    contradictions = {
        str(item.get("id")): item
        for item in action.get("contradictions", [])
        if isinstance(item, dict) and item.get("id")
    }
    narrative = action.get("narrative", {})
    if not isinstance(narrative, dict):
        narrative = {}
    overview = narrative.get("overview", {})
    overview_paragraphs = overview.get("paragraphs", []) if isinstance(overview, dict) else []
    rendered: dict[str, list[str]] = {
        "overview": render_v3_paragraphs(
            overview_paragraphs, findings, contradictions, titles, short_names
        ),
        "synthesis": [],
        "controversies": [],
    }
    for field, key in (
        ("synthesis_blocks", "synthesis"),
        ("controversy_blocks", "controversies"),
    ):
        blocks = narrative.get(field, [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if rendered[key]:
                rendered[key].append("")
            rendered[key].extend([f"### {str(block.get('heading', '')).strip()}", ""])
            rendered[key].extend(
                render_v3_paragraphs(
                    block.get("paragraphs", []),
                    findings,
                    contradictions,
                    titles,
                    short_names,
                )
            )
    return rendered


def topic_page_text_v3(
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    created: str,
    short_names: dict[str, str] | None,
    purpose: str,
) -> str:
    sources = string_list(action.get("papers"))
    category = str(action.get("category", "")).strip()
    extra: list[tuple[str, str]] = []
    if category:
        extra.append(("category", category))
    extra.append(("last_topic_action_sha256", action_fingerprint(action)))
    status = "stub" if purpose == "mining" else str(action.get("page_status", "stub"))
    frontmatter = render_frontmatter(
        ["topic"],
        created,
        today,
        status,
        sources=sources,
        aliases=[],
        extra=extra,
    )
    if purpose == "mining":
        rendered = {
            "overview": [MINING_STUB_OVERVIEW],
            "synthesis": [],
            "controversies": [],
        }
    else:
        rendered = render_v3_narrative(action, titles, short_names)
    lines = [
        frontmatter.rstrip(),
        f"# {action.get('name', '')}",
        "",
        "## 概述",
        "",
        *managed_block_lines("overview", rendered["overview"]),
        "",
        "## 综合认识",
        "",
        *managed_block_lines("synthesis", rendered["synthesis"]),
        "",
        "## 争议与不确定",
        "",
        *managed_block_lines("controversies", rendered["controversies"]),
        "",
        "## 论文与方法对照",
        "",
    ]
    comparisons = action.get("comparisons", [])
    if isinstance(comparisons, list) and comparisons:
        if any(isinstance(item, dict) and "dimension" in item for item in comparisons):
            lines.extend(render_grouped_comparisons(comparisons, titles))
        else:
            lines.extend(render_flat_comparisons(comparisons, titles))
    lines.extend(["", "## 开放问题", ""])
    q_open, q_resolved = render_open_questions(
        action.get("open_questions", []), titles, short_names
    )
    lines.extend(q_open)
    lines.extend(["", "## 研究空白与候选方向", ""])
    lines.extend(
        render_research_gaps(action.get("research_gaps", []), titles, short_names)
    )
    if q_resolved:
        lines.extend(["", "## 已解决的问题", ""])
        lines.extend(q_resolved)
    resolved_gaps = render_resolved_research_gaps(
        action.get("research_gaps", []), titles, short_names
    )
    if resolved_gaps:
        lines.extend(["", "## 已解决的研究空白", ""])
        lines.extend(resolved_gaps)
    return "\n".join(lines).rstrip() + "\n"


def topic_page_text(
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    created: str,
    short_names: dict[str, str] | None = None,
    *,
    schema_version: str = "2.0",
    purpose: str = "ingest",
) -> str:
    if schema_version == "3.0":
        return topic_page_text_v3(
            action, titles, today, created, short_names, purpose
        )
    sources = string_list(action.get("papers"))
    category = str(action.get("category", "")).strip()
    extra = [("category", category)] if category else None
    frontmatter = render_frontmatter(
        ["topic"],
        created,
        today,
        "stub",
        sources=sources,
        aliases=[],
        extra=extra,
    )
    lines = [
        frontmatter.rstrip(),
        f"# {action.get('name', '')}",
        "",
        "## 概述",
        "",
        action.get("summary", ""),
        "",
        "## 论文与方法对照",
        "",
    ]
    comparisons = action.get("comparisons", [])
    if isinstance(comparisons, list) and comparisons:
        if any(isinstance(item, dict) and "dimension" in item for item in comparisons):
            lines.extend(render_grouped_comparisons(comparisons, titles))
        else:
            lines.extend(render_flat_comparisons(comparisons, titles))
    lines.extend(["## 关键发现", ""])
    lines.extend(render_key_findings(action.get("key_findings", []), titles, short_names))
    lines.extend(["## 争议与不确定", ""])
    lines.extend(render_contradictions(action.get("contradictions", []), titles))
    lines.extend(["## 开放问题", ""])
    q_open, q_resolved = render_open_questions(
        action.get("open_questions", []), titles, short_names
    )
    lines.extend(q_open)
    lines.extend(["", "## 研究空白与候选方向", ""])
    lines.extend(render_research_gaps(action.get("research_gaps", []), titles, short_names))
    if q_resolved:
        lines.extend(["", "## 已解决的问题", ""])
        lines.extend(q_resolved)
    resolved_gaps = render_resolved_research_gaps(
        action.get("research_gaps", []), titles, short_names
    )
    if resolved_gaps:
        lines.extend(["", "## 已解决的研究空白", ""])
        lines.extend(resolved_gaps)
    return "\n".join(lines).rstrip() + "\n"


def missing_lines(addition: list[str], existing: str) -> list[str]:
    normalized_existing = re.sub(r"\s+", " ", existing)
    return [
        line
        for line in addition
        if re.sub(r"\s+", " ", line) not in normalized_existing
    ]


def insert_before_next_section(body: str, section_name: str, addition: list[str]) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(section_name)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    if not match:
        return f"{body.rstrip()}\n\n## {section_name}\n\n" + "\n".join(addition) + "\n"
    additions = missing_lines(addition, match.group(1))
    if not additions:
        return body
    insert_at = match.end(1)
    if body[insert_at : insert_at + 1] != "\n":
        prefix = "\n"
    else:
        prefix = ""
    return (
        body[:insert_at]
        + prefix
        + "\n".join(additions)
        + "\n"
        + body[insert_at:]
    )


FLAT_COMPARISON_HEADER = [
    "| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |",
    "|---|---|---|---|---|---|",
]


def section_body(body: str, section_name: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(section_name)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    return match.group(1) if match else ""


def bullet_text(line: str) -> str:
    """Strip a leading '- ' marker from a section bullet."""
    stripped = line.strip()
    return stripped[2:].strip() if stripped.startswith("- ") else stripped


def replace_section_body(body: str, section_name: str, new_lines: list[str]) -> str:
    """Replace a section's body with new_lines, preserving the section title.

    Appends the section when it is absent. An empty new_lines keeps the
    section title in place (possibly empty).
    """
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(section_name)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    if not match:
        return insert_before_next_section(body, section_name, new_lines)
    content = "\n".join(new_lines)
    if content:
        result = body[: match.start(1)] + content + "\n\n" + body[match.end(1):]
    else:
        result = body[: match.start(1)] + body[match.end(1):]
    return result.rstrip("\n") + "\n"


def merge_table_rows(body: str, section_name: str, new_rows: list[str]) -> str:
    if not new_rows:
        return body
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(section_name)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    if not match:
        return (
            body.rstrip()
            + f"\n\n## {section_name}\n\n"
            + "\n".join(FLAT_COMPARISON_HEADER + new_rows)
            + "\n"
        )
    head = body[: match.start(1)]
    tail = match.group(1)
    rest = body[match.end(1) :]
    rows = "\n".join(new_rows)
    if "|---" in tail:
        return head + tail.rstrip("\n") + "\n" + rows + "\n" + rest
    return (
        head
        + tail.rstrip("\n")
        + "\n"
        + "\n".join(FLAT_COMPARISON_HEADER)
        + "\n"
        + rows
        + "\n"
        + rest
    )


def merge_frontmatter_sets(
    fields: dict[str, str],
    lists: dict[str, list[str]],
    sources: list[str],
    aliases: list[str],
    today: str,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    merged_fields = dict(fields)
    merged_fields["updated"] = today
    merged_fields.setdefault("created", today)
    merged_fields.setdefault("status", "stub")
    merged_lists = {key: list(value) for key, value in lists.items()}
    merged_sources = list(dict.fromkeys(merged_lists.get("sources", []) + sources))
    merged_aliases = list(dict.fromkeys(merged_lists.get("aliases", []) + aliases))
    merged_lists["sources"] = merged_sources
    merged_lists["aliases"] = merged_aliases
    return merged_fields, merged_lists


def rebuild_page(
    fields: dict[str, str],
    lists: dict[str, list[str]],
    body: str,
    tag: str,
) -> str:
    category = fields.get("category", "")
    extra: list[tuple[str, str]] = []
    if category:
        extra.append(("category", category))
    last_action = fields.get("last_topic_action_sha256", "")
    if last_action:
        extra.append(("last_topic_action_sha256", last_action))
    frontmatter = render_frontmatter(
        [tag],
        fields.get("created", datetime.date.today().isoformat()),
        fields.get("updated", datetime.date.today().isoformat()),
        fields.get("status", "stub"),
        sources=lists.get("sources", []),
        aliases=lists.get("aliases", []),
        extra=extra or None,
    )
    return frontmatter + body.lstrip("\n")


def annotate_gap_block(block: str, note: str) -> str:
    """Append a cross-reference note to a gap's 承接 in place.

    The note is inserted before the trailing 承接 period (。), so the gap
    main line, source wikilinks, and any detail sub-bullets are preserved.
    Blocks without the trailing marker fall back to a sub-bullet note.
    """
    lines = block.splitlines()
    if not lines:
        return block
    main = lines[0].rstrip()
    suffix = "。）"
    if main.endswith(suffix):
        lines[0] = main[: -len(suffix)] + f"；{note}" + suffix
        return "\n".join(lines)
    return block + f"\n  - 相关空白：{note}"


def block_item_id(block: str) -> str:
    first = block.splitlines()[0] if block else ""
    return item_id_from_text(first)


def block_item_origin(block: str) -> str:
    first = block.splitlines()[0] if block else ""
    return item_origin_from_text(first)


def section_exists(body: str, section_name: str) -> bool:
    return bool(re.search(rf"(?m)^##\s+{re.escape(section_name)}\s*$", body))


def preserve_existing_origins(
    entries: list[dict[str, Any]], existing_blocks: list[str]
) -> None:
    origins = {
        block_item_id(block): block_item_origin(block)
        for block in existing_blocks
        if block_item_id(block) and block_item_origin(block)
    }
    for entry in entries:
        item_id = str(entry.get("id", ""))
        if item_id in origins:
            entry["origin"] = origins[item_id]


def merge_v3_open_items(
    body: str,
    action: dict[str, Any],
    titles: dict[str, str],
    short_names: dict[str, str] | None,
) -> str:
    questions = normalize_questions(action.get("open_questions", []))
    q_open_existing = section_bullet_blocks(body, "开放问题")
    q_archive_existing = section_bullet_blocks(body, "已解决的问题")
    preserve_existing_origins(questions, q_open_existing + q_archive_existing)
    incoming_q_ids = {entry["id"] for entry in questions if entry.get("id")}
    removed_q_ids = set(string_list(action.get("remove_open_question_ids")))
    q_open_kept = [
        block
        for block in q_open_existing
        if block_item_id(block) not in incoming_q_ids | removed_q_ids
    ]
    q_archive_kept = [
        block
        for block in q_archive_existing
        if block_item_id(block) not in incoming_q_ids | removed_q_ids
    ]
    q_open_new, q_archive_new = render_open_questions(
        questions, titles, short_names
    )
    body = replace_section_body(body, "开放问题", q_open_kept + q_open_new)
    if q_archive_kept or q_archive_new or section_exists(body, "已解决的问题"):
        body = replace_section_body(
            body, "已解决的问题", q_archive_kept + q_archive_new
        )

    gaps = normalize_gaps(action.get("research_gaps", []))
    g_open_existing = section_bullet_blocks(body, "研究空白与候选方向")
    g_archive_existing = section_bullet_blocks(body, "已解决的研究空白")
    preserve_existing_origins(gaps, g_open_existing + g_archive_existing)
    incoming_g_ids = {entry["id"] for entry in gaps if entry.get("id")}
    removed_g_ids = set(string_list(action.get("remove_research_gap_ids")))
    g_open_kept = [
        block
        for block in g_open_existing
        if block_item_id(block) not in incoming_g_ids | removed_g_ids
    ]
    g_archive_kept = [
        block
        for block in g_archive_existing
        if block_item_id(block) not in incoming_g_ids | removed_g_ids
    ]
    g_open_new = render_research_gaps(gaps, titles, short_names)
    g_archive_new = render_resolved_research_gaps(gaps, titles, short_names)
    merged_open = g_open_kept + g_open_new
    annotations = action.get("annotate_research_gaps", [])
    if isinstance(annotations, list):
        notes = {
            str(item.get("id", "")).strip(): str(item.get("note", "")).strip()
            for item in annotations
            if isinstance(item, dict) and item.get("id") and item.get("note")
        }
        merged_open = [
            annotate_gap_block(block, notes[block_item_id(block)])
            if block_item_id(block) in notes
            else block
            for block in merged_open
        ]
    body = replace_section_body(body, "研究空白与候选方向", merged_open)
    if g_archive_kept or g_archive_new or section_exists(body, "已解决的研究空白"):
        body = replace_section_body(
            body,
            "已解决的研究空白",
            g_archive_kept + g_archive_new,
        )
    return body


def merge_topic_page_v3(
    existing_text: str,
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    short_names: dict[str, str] | None,
    purpose: str,
) -> str:
    fields, lists, body = parse_frontmatter(existing_text)
    fingerprint = action_fingerprint(action)
    if fields.get("last_topic_action_sha256") == fingerprint:
        return existing_text

    if purpose == "ingest":
        rendered = render_v3_narrative(action, titles, short_names)
        for key in MANAGED_KEYS:
            body = replace_managed_block(body, key, rendered[key])
        comparisons = action.get("comparisons", [])
        if isinstance(comparisons, list) and comparisons:
            if any(
                isinstance(item, dict) and "dimension" in item
                for item in comparisons
            ):
                body = replace_section_body(
                    body,
                    "论文与方法对照",
                    render_grouped_comparisons(comparisons, titles),
                )
            else:
                existing_section = section_body(body, "论文与方法对照")
                new_rows: list[str] = []
                for item in comparisons:
                    if not isinstance(item, dict):
                        continue
                    name = comparison_paper_name(item, titles)
                    if name and name in existing_section:
                        continue
                    new_rows.append(comparison_row(item, titles))
                body = merge_table_rows(body, "论文与方法对照", new_rows)

    body = merge_v3_open_items(body, action, titles, short_names)
    fields, lists = merge_frontmatter_sets(
        fields,
        lists,
        string_list(action.get("papers")),
        [],
        today,
    )
    if purpose == "ingest":
        category = str(action.get("category", "")).strip()
        if category:
            fields["category"] = category
        page_status = str(action.get("page_status", "")).strip()
        if page_status:
            fields["status"] = page_status
    fields["last_topic_action_sha256"] = fingerprint
    return rebuild_page(fields, lists, body, "topic")


def merge_topic_page(
    existing_text: str,
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    short_names: dict[str, str] | None = None,
    *,
    schema_version: str = "2.0",
    purpose: str = "ingest",
) -> str:
    if schema_version == "3.0":
        return merge_topic_page_v3(
            existing_text, action, titles, today, short_names, purpose
        )
    fields, lists, body = parse_frontmatter(existing_text)
    summary = str(action.get("summary", ""))
    normalized_body = re.sub(r"\s+", " ", body)
    if summary and summary not in normalized_body:
        body = insert_before_next_section(body, "概述", [summary])
    comparisons = action.get("comparisons", [])
    if isinstance(comparisons, list) and comparisons:
        if any(isinstance(item, dict) and "dimension" in item for item in comparisons):
            body = insert_before_next_section(
                body,
                "论文与方法对照",
                render_grouped_comparisons(comparisons, titles),
            )
        else:
            existing_section = section_body(body, "论文与方法对照")
            new_rows: list[str] = []
            for item in comparisons:
                if not isinstance(item, dict):
                    continue
                name = comparison_paper_name(item, titles)
                if name and name in existing_section:
                    continue
                new_rows.append(comparison_row(item, titles))
            body = merge_table_rows(body, "论文与方法对照", new_rows)
    body = insert_before_next_section(
        body,
        "关键发现",
        render_key_findings(action.get("key_findings", []), titles, short_names),
    )
    contradictions = action.get("contradictions", [])
    if isinstance(contradictions, list) and contradictions:
        existing_contra = section_body(body, "争议与不确定")
        normalized_contra = re.sub(r"\s+", " ", existing_contra)
        pending: list[Any] = []
        for item in contradictions:
            if not isinstance(item, dict):
                continue
            pos_a = item.get("position_a") or item.get("a") or ""
            if pos_a and re.sub(r"\s+", " ", pos_a) in normalized_contra:
                continue
            pending.append(item)
        body = insert_before_next_section(
            body,
            "争议与不确定",
            render_contradictions(pending, titles),
        )
    q_open, q_resolved = render_open_questions(
        action.get("open_questions", []), titles, short_names
    )
    existing_q = section_bullets(body, "开放问题")
    answered_q = [
        entry["question"]
        for entry in normalize_questions(action.get("open_questions", []))
        if entry["status"] == "answered"
    ]
    remove_q = [
        re.sub(r"\s+", " ", text)
        for text in string_list(action.get("remove_open_questions"))
    ]
    kept_q = [
        line
        for line in existing_q
        if not any(line.startswith(text) for text in answered_q)
        and not any(text in re.sub(r"\s+", " ", line) for text in remove_q)
    ]
    merged_q = [f"- {line}" for line in kept_q] + [
        line for line in q_open if bullet_text(line) not in kept_q
    ]
    body = replace_section_body(body, "开放问题", merged_q)
    if q_resolved:
        existing_rq = section_bullets(body, "已解决的问题")
        merged_rq = [f"- {line}" for line in existing_rq] + [
            line for line in q_resolved if bullet_text(line) not in existing_rq
        ]
        body = replace_section_body(body, "已解决的问题", merged_rq)
    g_open = render_research_gaps(action.get("research_gaps", []), titles, short_names)
    g_resolved = render_resolved_research_gaps(
        action.get("research_gaps", []), titles, short_names
    )
    existing_blocks = section_bullet_blocks(body, "研究空白与候选方向")
    answered_keys = {
        gap_key(entry["gap"])
        for entry in normalize_gaps(action.get("research_gaps", []))
        if entry["status"] == "answered"
    }
    remove_g = [
        re.sub(r"\s+", " ", text)
        for text in string_list(action.get("remove_research_gaps"))
    ]
    kept_blocks = [
        block
        for block in existing_blocks
        if gap_key(block_root_text(block)) not in answered_keys
        and not any(
            text in re.sub(r"\s+", " ", block_root_text(block))
            for text in remove_g
        )
    ]
    annotations = action.get("annotate_research_gaps")
    if isinstance(annotations, list):
        for annotation in annotations:
            if not isinstance(annotation, dict):
                continue
            match = re.sub(r"\s+", " ", str(annotation.get("match", ""))).strip()
            note = str(annotation.get("note", "")).strip()
            if not match or not note:
                continue
            kept_blocks = [
                annotate_gap_block(block, note)
                if match in re.sub(r"\s+", " ", block_root_text(block))
                else block
                for block in kept_blocks
            ]
    existing_keys = {gap_key(block_root_text(block)) for block in existing_blocks}
    merged_g = kept_blocks + [
        line for line in g_open if gap_key(block_root_text(line)) not in existing_keys
    ]
    body = replace_section_body(body, "研究空白与候选方向", merged_g)
    if g_resolved:
        existing_rg = section_bullets(body, "已解决的研究空白")
        merged_rg = [f"- {line}" for line in existing_rg] + [
            line for line in g_resolved if bullet_text(line) not in existing_rg
        ]
        body = replace_section_body(body, "已解决的研究空白", merged_rg)
    fields, lists = merge_frontmatter_sets(
        fields,
        lists,
        string_list(action.get("papers")),
        [],
        today,
    )
    category = str(action.get("category", "")).strip()
    if category:
        fields["category"] = category
    return rebuild_page(fields, lists, body, "topic")


def update_meta_frontmatter(text: str, today: str) -> str:
    fields, lists, body = parse_frontmatter(text)
    if not fields:
        return text
    fields["updated"] = today
    fields.setdefault("created", today)
    frontmatter = render_frontmatter(
        ["meta"],
        fields.get("created", today),
        today,
        fields.get("status", "evergreen"),
        sources=lists.get("sources"),
        aliases=lists.get("aliases"),
    )
    return frontmatter + body.lstrip("\n")


def update_index(
    index_text: str,
    entries: list[tuple[str, str, str]],
    today: str,
    replace_descriptions: set[str] | None = None,
) -> str:
    result = index_text
    changed = False
    replace_paths = replace_descriptions or set()
    for section, path, description in entries:
        if f"[[{path}" in result:
            if path in replace_paths:
                pattern = re.compile(
                    rf"(?m)^- \[\[{re.escape(path)}(?:\|([^\]]+))?\]\](?:\s+-\s+.*)?$"
                )
                match = pattern.search(result)
                if match:
                    label = match.group(1) or Path(path).stem
                    replacement = f"- [[{path}|{label}]] - {description}"
                    if match.group(0) != replacement:
                        result = result[: match.start()] + replacement + result[match.end() :]
                        changed = True
            continue
        marker = f"## {section}\n"
        line = f"- [[{path}|{Path(path).stem}]] - {description}\n"
        position = result.find(marker)
        if position < 0:
            result = result.rstrip() + f"\n\n{marker}{line}"
        else:
            insert_at = position + len(marker)
            result = result[:insert_at] + line + result[insert_at:]
        changed = True
    return update_meta_frontmatter(result, today) if changed else result


def append_log(
    log_text: str,
    source_entries: list[dict[str, Any]],
    synthesis_entries: list[dict[str, Any]],
    batch_title: str,
    today: str,
) -> str:
    additions: list[str] = []
    for entry in source_entries:
        additions.extend(
            [
                f"## [{today}] ingest | {entry['title']}",
                f"- 新建：{entry['path']}" if entry["created"] else f"- 更新：{entry['path']}",
                f"- 摘要：{entry['summary']}",
                "",
            ]
        )
    if synthesis_entries:
        additions.append(f"## [{today}] batch synthesis | {batch_title}")
        for entry in synthesis_entries:
            action = "新建" if entry["created"] else "更新"
            additions.append(f"- {action}：{entry['path']}")
        additions.append(f"- 摘要：{batch_title}")
        additions.append("")
    if not additions:
        return log_text
    updated = update_meta_frontmatter(log_text, today)
    return updated.rstrip() + "\n\n" + "\n".join(additions).rstrip() + "\n"


def audit_plan(plan: dict[str, Any]) -> dict[str, Any] | None:
    spec = importlib.util.spec_from_file_location(
        "audit_link_plan",
        ROOT / "scripts" / "audit_link_plan.py",
    )
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load audit_link_plan.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.audit(plan)
    if report["summary"]["errors"]:
        for item in report["findings"]:
            if item["level"] == "error":
                print(f"ERROR {item['code']}: {item['message']}", file=sys.stderr)
        return None
    return report


def resolve_work_dir(value: str, wiki_root: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (wiki_root / path).resolve()


def find_existing_topic(action: dict[str, Any], wiki_root: Path) -> Path | None:
    existing_page = action.get("existing_page")
    if isinstance(existing_page, str) and existing_page:
        return safe_relative_path(wiki_root, existing_page)
    name = safe_filename(action.get("name", ""))
    directory = wiki_root / "wiki" / "topics"
    if not directory.is_dir():
        return None
    for path in directory.glob("*.md"):
        if path.stem == name:
            return path
    return None


def preflight_errors(plan: dict[str, Any], wiki_root: Path) -> list[str]:
    """Verify every plan reference before any wiki write.

    Checks, before any file is written:
    - every source page referenced by topic papers, research-gap sources, or
      answered evidence is either part of the current batch (written by this
      run) or an existing page under ``wiki/sources/``;
    - every batch source page has a finalized ``paper-card.md`` to publish.

    Missing, escaping, or non-``wiki/sources/`` references block the whole
    publish instead of producing a partial write with a success report.
    Returns a list of human-readable error strings (empty when clean).
    """
    errors: list[str] = []
    source_pages = (
        plan.get("batch", {}).get("source_pages", [])
        if isinstance(plan.get("batch"), dict)
        else []
    )
    batch_refs = {
        page["source_ref"]
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref")
    }

    referenced: dict[str, list[str]] = {}
    for action in plan.get("topic_actions", []):
        if not isinstance(action, dict):
            continue
        label = action.get("id") or action.get("name") or "<unnamed>"
        for source_ref in string_list(action.get("papers")):
            referenced.setdefault(source_ref, []).append(f"topic action {label} papers")
        for gap in action.get("research_gaps", []):
            if not isinstance(gap, dict):
                continue
            for source_ref in string_list(gap.get("source_refs")):
                referenced.setdefault(source_ref, []).append(f"research gap sources in {label}")
            if gap.get("status") == "answered":
                for source_ref in string_list(gap.get("answered_by")):
                    referenced.setdefault(source_ref, []).append(f"answered gap evidence in {label}")
        for question in action.get("open_questions", []):
            if not isinstance(question, dict):
                continue
            for source_ref in string_list(question.get("source_refs")):
                referenced.setdefault(source_ref, []).append(
                    f"open question sources in {label}"
                )
            if question.get("status") == "answered":
                for source_ref in string_list(question.get("answered_by")):
                    referenced.setdefault(source_ref, []).append(
                        f"answered question evidence in {label}"
                    )
        for item in action.get("key_findings", []):
            if not isinstance(item, dict):
                continue
            for source_ref in string_list(item.get("source_refs")):
                referenced.setdefault(source_ref, []).append(
                    f"key finding sources in {label}"
                )
        for item in action.get("contradictions", []):
            if not isinstance(item, dict):
                continue
            for field in ("position_a_source_ref", "position_b_source_ref"):
                source_ref = str(item.get(field, "")).strip()
                if source_ref:
                    referenced.setdefault(source_ref, []).append(
                        f"contradiction evidence in {label}"
                    )

    for source_ref in sorted(referenced):
        if source_ref in batch_refs:
            continue
        where = "; ".join(sorted(set(referenced[source_ref])))
        if not source_ref.startswith("wiki/sources/"):
            errors.append(
                f"Source reference is not a source page: {source_ref} (referenced by {where})"
            )
            continue
        try:
            target = safe_relative_path(wiki_root, source_ref)
        except ValueError as exc:
            errors.append(f"Invalid source page {source_ref}: {exc} (referenced by {where})")
            continue
        if not target.is_file():
            errors.append(f"Missing source page: {source_ref} (referenced by {where})")

    schema_version = str(plan.get("schema_version", "2.0"))
    purpose = str(plan.get("purpose", "ingest"))
    for action in plan.get("topic_actions", []):
        if not isinstance(action, dict):
            continue
        label = action.get("id") or action.get("name") or "<unnamed>"
        try:
            existing_path = find_existing_topic(action, wiki_root)
        except ValueError as exc:
            errors.append(f"Invalid topic target for {label}: {exc}")
            continue
        existing_text = None
        if existing_path is not None and existing_path.is_file():
            try:
                existing_text = existing_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"Unable to read topic target for {label}: {exc}")
                continue
        if schema_version == "3.0":
            fingerprint = action_fingerprint(action)
            existing_fields, _, existing_body = parse_frontmatter(existing_text or "")
            replay = existing_fields.get("last_topic_action_sha256") == fingerprint
            if action.get("action") == "create_topic":
                if existing_text is not None and not replay:
                    errors.append(
                        f"topic_create_conflict: topic already exists for {label}"
                    )
                continue
            if existing_text is None:
                errors.append(f"Unable to locate existing topic for {label}")
                continue
            actual_hash = hashlib.sha256(existing_text.encode("utf-8")).hexdigest()
            expected_hash = str(action.get("base_topic_sha256", ""))
            if actual_hash != expected_hash and not replay:
                errors.append(
                    f"stale_topic_plan: {label} expected {expected_hash} but found {actual_hash}"
                )
            if purpose == "ingest" and not has_managed_blocks(existing_body):
                errors.append(
                    f"narrative_migration_required: {label} has no complete managed narrative blocks"
                )
            existing_question_blocks = section_bullet_blocks(
                existing_body, "开放问题"
            ) + section_bullet_blocks(existing_body, "已解决的问题")
            existing_gap_blocks = section_bullet_blocks(
                existing_body, "研究空白与候选方向"
            ) + section_bullet_blocks(existing_body, "已解决的研究空白")
            question_ids = [block_item_id(block) for block in existing_question_blocks]
            gap_ids = [block_item_id(block) for block in existing_gap_blocks]
            for item_id in sorted({item for item in question_ids + gap_ids if item}):
                if question_ids.count(item_id) + gap_ids.count(item_id) > 1:
                    errors.append(
                        f"duplicate_existing_item_id: {label} contains {item_id} more than once"
                    )
            question_origins = {
                block_item_id(block): block_item_origin(block)
                for block in existing_question_blocks
                if block_item_id(block)
            }
            gap_origins = {
                block_item_id(block): block_item_origin(block)
                for block in existing_gap_blocks
                if block_item_id(block)
            }
            for question in action.get("open_questions", []):
                if not isinstance(question, dict):
                    continue
                item_id = str(question.get("id", ""))
                origin = str(question.get("origin", ""))
                if item_id in gap_origins:
                    errors.append(
                        f"item_type_conflict: {label} {item_id} is an existing research gap"
                    )
                if item_id in question_origins and question_origins[item_id] != origin:
                    errors.append(
                        f"item_origin_conflict: {label} {item_id} origin is immutable"
                    )
            for gap in action.get("research_gaps", []):
                if not isinstance(gap, dict):
                    continue
                item_id = str(gap.get("id", ""))
                origin = str(gap.get("origin", ""))
                if item_id in question_origins:
                    errors.append(
                        f"item_type_conflict: {label} {item_id} is an existing open question"
                    )
                if item_id in gap_origins and gap_origins[item_id] != origin:
                    errors.append(
                        f"item_origin_conflict: {label} {item_id} origin is immutable"
                    )
            for item_id in string_list(action.get("remove_open_question_ids")):
                if item_id not in question_origins:
                    errors.append(
                        f"unknown_open_question_id: {label} cannot remove {item_id}"
                    )
            for item_id in string_list(action.get("remove_research_gap_ids")):
                if item_id not in gap_origins:
                    errors.append(
                        f"unknown_research_gap_id: {label} cannot remove {item_id}"
                    )
            for annotation in action.get("annotate_research_gaps", []):
                if not isinstance(annotation, dict):
                    continue
                item_id = str(annotation.get("id", ""))
                if item_id not in gap_origins:
                    errors.append(
                        f"unknown_research_gap_id: {label} cannot annotate {item_id}"
                    )
        elif existing_text is not None:
            _, _, existing_body = parse_frontmatter(existing_text)
            if has_managed_blocks(existing_body):
                errors.append(
                    f"schema2_cannot_update_schema3_topic: {label} uses managed narrative blocks"
                )

    # Every batch source page must have a finalized card before this run writes it.
    for page in source_pages:
        if not isinstance(page, dict):
            continue
        work_dir = resolve_work_dir(page.get("work_dir", ""), wiki_root)
        card_path = work_dir / "paper-card.md"
        if not card_path.is_file():
            errors.append(f"Missing finalized card: {card_path}")

    return errors


def render_research_page(
    buckets: dict[str, dict[str, list[Any]]] | None,
    today: str,
    created: str,
) -> str | None:
    """Render wiki/meta/research.md: domain-grouped dashboard of open
    questions and research gaps.

    This is the question-type-first view of the same topic-page data that
    knowledge-tree.md shows domain-first. It aggregates only *currently
    open* questions and gaps; answered items live in the topic pages'
    `## 已解决的问题` / `## 已解决的研究空白` archive sections and are
    deliberately not aggregated here.
    """
    questions_by_domain: dict[str, list[tuple[str, str, str]]] = {}
    gaps_by_domain: dict[str, list[tuple[str, str, str]]] = {}
    if buckets:
        for domain in buckets:
            questions_by_domain[domain] = list(buckets[domain]["questions"])
            gaps_by_domain[domain] = list(buckets[domain]["gaps"])

    has_content = bool(
        any(questions_by_domain.values()) or any(gaps_by_domain.values())
    )
    if buckets is None:
        return None
    if not has_content:
        return (
            render_frontmatter(["meta"], created, today, "evergreen").rstrip()
            + "\n"
            + "# 研究仪表盘\n\n"
            + "> 本页由 publish_wiki.py 确定性生成：按领域聚合主题页的当前开放问题与研究空白（问题类型优先视图，只含仍开放的条目；已解决的归档在各主题页）。不要手动编辑。\n\n"
            + "当前没有待解决的开放问题与研究空白；已解决的条目归档在各主题页的 `## 已解决的问题` / `## 已解决的研究空白` 小节。\n"
        )

    lines = [
        render_frontmatter(["meta"], created, today, "evergreen").rstrip(),
        "# 研究仪表盘",
        "",
        "> 本页由 publish_wiki.py 确定性生成：按领域聚合主题页的当前开放问题与研究空白（问题类型优先视图，只含仍开放的条目；已解决的归档在各主题页）。不要手动编辑。",
        "",
    ]

    def domain_list(
        title: str,
        grouped: dict[str, list[tuple[str, str, str]]],
    ) -> None:
        if not any(grouped.values()):
            return
        lines.append(f"## {title}")
        lines.append("")
        for domain in ordered_domains({d: {} for d in grouped}):
            items = grouped.get(domain, [])
            if not items:
                continue
            lines.append(f"### {domain}")
            lines.append("")
            seen: set[str] = set()
            for row in sorted(items, key=priority_sort_key):
                text_item, label, path = row[0], row[1], row[2]
                line = f"- {text_item} — 来源：[[{Path(path).stem}|{label}]]"
                if line in seen:
                    continue
                seen.add(line)
                lines.append(line)
            lines.append("")

    domain_list("开放问题", questions_by_domain)
    domain_list("研究空白", gaps_by_domain)
    return "\n".join(lines).rstrip() + "\n"


INDEX_ENTRY_RE = re.compile(r"^[-*]\s+\[\[([^\]|]+)(?:\|([^\]]+))?\]\](?:\s*[—-]\s*(.*))?$")


def parse_index_entries(index_text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in index_text.splitlines():
        match = INDEX_ENTRY_RE.match(line.strip())
        if not match:
            continue
        path, label, description = match.groups()
        entries.append(
            {
                "path": path,
                "label": label or path.rsplit("/", 1)[-1],
                "description": (description or "").strip(),
            }
        )
    return entries


def source_domain(source_ref: str) -> str:
    """Domain = first directory under wiki/sources/papers/ (mirrors raw/papers/)."""
    parts = [part for part in source_ref.split("/") if part]
    if len(parts) >= 3 and parts[:2] == ["wiki", "sources"]:
        rest = parts[2:]
        if rest and rest[0] == "papers":
            rest = rest[1:]
        if rest and not rest[0].endswith(".md"):
            return rest[0]
    return "未分类"


def section_bullets(body: str, section_name: str) -> list[str]:
    bullets: list[str] = []
    for line in section_body(body, section_name).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(strip_item_metadata(stripped[2:].strip()))
    return bullets


def gap_priority(block: str) -> str:
    """Extract the optional `- 优先级：…` sub-bullet from a gap block."""
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("- 优先级："):
            return stripped[len("- 优先级：") :].strip()
    return ""


def page_domains(wiki_root: Path, path: str) -> str:
    try:
        text = (wiki_root / path).read_text(encoding="utf-8")
    except OSError:
        return "未分类"
    _, lists, _ = parse_frontmatter(text)
    domains = {source_domain(source) for source in lists.get("sources", [])}
    if not domains:
        return "未分类"
    if len(domains) > 1:
        return "跨领域"
    return domains.pop()


def collect_tree_buckets(wiki_root: Path) -> dict[str, dict[str, list[Any]]] | None:
    """Collect wiki pages grouped by domain for the knowledge tree and the
    research dashboard. Returns None when the wiki has no index yet."""
    index_path = wiki_root / "wiki" / "index.md"
    if not index_path.is_file():
        return None
    try:
        entries = parse_index_entries(index_path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if not entries:
        return None

    buckets: dict[str, dict[str, list[Any]]] = {}

    def bucket(domain: str) -> dict[str, list[Any]]:
        return buckets.setdefault(
            domain,
            {"sources": [], "topics": [], "questions": [], "gaps": []},
        )

    for entry in entries:
        path, label, description = entry["path"], entry["label"], entry["description"]
        if path.startswith("wiki/sources/"):
            bucket(source_domain(path))["sources"].append((path, label, description))
        elif path.startswith("wiki/topics/"):
            text = ""
            try:
                text = (wiki_root / path).read_text(encoding="utf-8")
            except OSError:
                pass
            _, _, body = parse_frontmatter(text)
            domain = page_domains(wiki_root, path)
            bucket(domain)["topics"].append((path, label, description))
            for question in section_bullets(body, "开放问题"):
                bucket(domain)["questions"].append((question, label, path))
            for block in section_bullet_blocks(body, "研究空白与候选方向"):
                root = block_root_text(block)
                priority = gap_priority(block)
                bucket(domain)["gaps"].append((root, label, path, priority))
    return buckets


def collect_topic_categories(wiki_root: Path) -> dict[str, list[tuple[str, str, str]]]:
    """Collect topic pages grouped by their optional frontmatter category.

    Topics without a category land in the 未分类 bucket. This is the
    category-first view rendered by render_knowledge_tree; it is orthogonal
    to the source-domain grouping of collect_tree_buckets.
    """
    index_path = wiki_root / "wiki" / "index.md"
    if not index_path.is_file():
        return {}
    try:
        entries = parse_index_entries(index_path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    categories: dict[str, list[tuple[str, str, str]]] = {}
    for entry in entries:
        path = entry["path"]
        if not path.startswith("wiki/topics/"):
            continue
        category = ""
        try:
            text = (wiki_root / path).read_text(encoding="utf-8")
        except OSError:
            continue
        fields, _, _ = parse_frontmatter(text)
        category = fields.get("category", "").strip()
        categories.setdefault(category or "未分类", []).append(
            (path, entry["label"], entry["description"])
        )
    return categories


def collect_topic_tree(
    wiki_root: Path,
) -> dict[str, dict[str, list[Any]]] | None:
    """Collect topic-first tree nodes for the knowledge tree.

    Each domain holds its topic signpost nodes (path, label, index one-line
    description, papers assigned through the topic frontmatter `sources`,
    and the topic's currently open questions and research gaps) plus the
    papers no topic assigns (per-domain unassigned group). A paper assigned
    by any topic is never repeated in the unassigned group. Returns None
    when the wiki has no index yet.
    """
    index_path = wiki_root / "wiki" / "index.md"
    if not index_path.is_file():
        return None
    try:
        entries = parse_index_entries(index_path.read_text(encoding="utf-8"))
    except OSError:
        return None
    if not entries:
        return None

    paper_index: dict[str, tuple[str, str]] = {}
    topic_entries: list[tuple[str, str, str]] = []
    for entry in entries:
        path, label, description = entry["path"], entry["label"], entry["description"]
        if path.startswith("wiki/sources/"):
            paper_index[path] = (label, description)
        elif path.startswith("wiki/topics/"):
            topic_entries.append((path, label, description))

    nodes: dict[str, dict[str, list[Any]]] = {}

    def bucket(domain: str) -> dict[str, list[Any]]:
        return nodes.setdefault(domain, {"topics": [], "unassigned": []})

    assigned: set[str] = set()
    for path, label, description in topic_entries:
        text = ""
        try:
            text = (wiki_root / path).read_text(encoding="utf-8")
        except OSError:
            pass
        _, lists, body = parse_frontmatter(text)
        sources = lists.get("sources", [])
        assigned.update(sources)
        papers = [
            (source, *paper_index[source])
            for source in sources
            if source in paper_index
        ]
        questions = section_bullets(body, "开放问题")
        gaps = [
            (block_root_text(block), gap_priority(block))
            for block in section_bullet_blocks(body, "研究空白与候选方向")
        ]
        if not papers and not questions and not gaps:
            continue
        bucket(page_domains(wiki_root, path))["topics"].append(
            {
                "path": path,
                "label": label,
                "description": description,
                "papers": papers,
                "questions": questions,
                "gaps": gaps,
            }
        )

    for path, (label, description) in paper_index.items():
        if path not in assigned:
            bucket(source_domain(path))["unassigned"].append(
                (path, label, description)
            )
    return nodes


def ordered_domains(buckets: dict[str, dict[str, list[Any]]]) -> list[str]:
    special = {"跨领域", "未分类"}
    ordered = sorted(domain for domain in buckets if domain not in special)
    ordered += [domain for domain in ("跨领域", "未分类") if domain in buckets]
    return ordered


PRIORITY_ORDER = {"高": 0, "中": 1, "低": 2}


def priority_sort_key(row: tuple[Any, ...]) -> tuple[int, str]:
    """Sort gap rows by priority (高 < 中 < 低 < unmarked), then text.

    Rows without a priority element (e.g. open-question rows) rank last.
    """
    priority = row[3] if len(row) > 3 else ""
    return (PRIORITY_ORDER.get(str(priority), 3), str(row[0]))


def render_knowledge_tree(
    nodes: dict[str, dict[str, list[Any]]],
    categories: dict[str, list[tuple[str, str, str]]] | None = None,
) -> str:
    """Render wiki/meta/knowledge-tree.md from collected topic nodes.

    Deterministic: identical nodes produce identical text. Topic-first
    navigation view: each domain groups its topics as intermediate signpost
    nodes (one-line index description) with the topic's papers, currently
    open questions, and research gaps nested under them; papers assigned to
    no topic land in the per-domain unassigned group. When categories are
    supplied, a category-first topic view is appended after the domain view.
    Questions and gaps are open-only; answered items stay in the topic
    pages' archive sections.
    """
    lines = [
        "# 知识树",
        "",
        "> 本页由 publish_wiki.py 确定性生成，用于 LLM 树检索导航（主题优先视图：每个主题节点带一句话摘要，其论文、开放问题与研究空白嵌套其下；未归入任何主题的论文在领域级单独分组；按主题分类视图随后。开放问题与研究空白与 research.md 为同一批数据的另一透视，只含仍开放的条目）。不要手动编辑，每次发布后重建。检索协议见 wiki-shared 的 references/retrieval-protocol.md。",
        "",
    ]
    for domain in ordered_domains(nodes):
        data = nodes[domain]
        topics = sorted(data["topics"], key=lambda row: row["label"])
        unassigned = sorted(data["unassigned"], key=lambda row: row[1])
        if not topics and not unassigned:
            continue
        lines.append(f"## {domain}")
        lines.append("")
        for node in topics:
            lines.append(f"### {node['label']}")
            lines.append("")
            if node["description"]:
                lines.append(node["description"])
                lines.append("")
            if node["papers"]:
                lines.append("#### 论文")
                lines.append("")
                for path, label, description in sorted(
                    node["papers"], key=lambda row: row[1]
                ):
                    stem = Path(path).stem
                    suffix = f" — {description}" if description else ""
                    lines.append(f"- [[{stem}|{label}]]{suffix}")
                lines.append("")
            if node["questions"]:
                lines.append("#### 开放问题")
                lines.append("")
                for question in sorted(node["questions"]):
                    lines.append(f"- {question}")
                lines.append("")
            if node["gaps"]:
                lines.append("#### 研究空白")
                lines.append("")
                for root, priority in sorted(
                    node["gaps"],
                    key=lambda row: (
                        PRIORITY_ORDER.get(str(row[1]), 3),
                        str(row[0]),
                    ),
                ):
                    lines.append(f"- {root}")
                lines.append("")
        if unassigned:
            lines.append("### 未归入主题的论文")
            lines.append("")
            for path, label, description in unassigned:
                stem = Path(path).stem
                suffix = f" — {description}" if description else ""
                lines.append(f"- [[{stem}|{label}]]{suffix}")
            lines.append("")
    if categories:
        lines.append("## 按主题分类")
        lines.append("")
        ordered_categories = sorted(
            category for category in categories if category != "未分类"
        )
        if "未分类" in categories:
            ordered_categories.append("未分类")
        for category in ordered_categories:
            lines.append(f"### {category}")
            lines.append("")
            for row in sorted(categories[category], key=lambda row: row[1]):
                stem = Path(row[0]).stem
                suffix = f" — {row[2]}" if row[2] else ""
                lines.append(f"- [[{stem}|{row[1]}]]{suffix}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_knowledge_tree(wiki_root: Path) -> str | None:
    """Render wiki/meta/knowledge-tree.md from the current wiki state.

    Deterministic: identical wiki state produces identical text. Topic-first:
    each domain groups its topics as signpost nodes with nested papers and
    open items, followed by unassigned papers, then the category-first topic
    view.
    """
    nodes = collect_topic_tree(wiki_root)
    if nodes is None:
        return None
    return render_knowledge_tree(nodes, collect_topic_categories(wiki_root))


def render_agent_tree(
    nodes: dict[str, dict[str, list[Any]]],
) -> str:
    """Render wiki/meta/agent-tree.md: the signpost-only retrieval index.

    This is the agent-facing counterpart of knowledge-tree.md. It contains
    only domain names and their topic signposts (one-line index
    descriptions) plus unassigned papers, with no nested leaf lists, so the
    first retrieval hop stays small and the descent opens pages level by
    level (progressive disclosure; see retrieval-protocol.md). Deterministic:
    identical nodes produce identical text.
    """
    lines = [
        "# Agent 检索索引",
        "",
        "> 本页由 publish_wiki.py 确定性生成，是 Agent 检索的第一跳：只含领域与主题 signpost（一句话摘要）及未归入主题的论文，不含叶子明细。检索时先读本页选分支，再打开候选页面逐层展开（见 wiki-shared 的 references/retrieval-protocol.md）。人读导航用 wiki/meta/knowledge-tree.md。不要手动编辑，每次发布后重建。",
        "",
    ]
    for domain in ordered_domains(nodes):
        data = nodes[domain]
        topics = sorted(data["topics"], key=lambda row: row["label"])
        unassigned = sorted(data["unassigned"], key=lambda row: row[1])
        if not topics and not unassigned:
            continue
        lines.append(f"## {domain}")
        lines.append("")
        for node in topics:
            stem = Path(node["path"]).stem
            suffix = f" — {node['description']}" if node["description"] else ""
            lines.append(f"- [[{stem}|{node['label']}]]{suffix}")
        for path, label, description in unassigned:
            stem = Path(path).stem
            suffix = f" — {description}" if description else ""
            lines.append(f"- [[{stem}|{label}]]{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_agent_tree(wiki_root: Path) -> str | None:
    """Render wiki/meta/agent-tree.md from the current wiki state.

    Deterministic: identical wiki state produces identical text. Signposts
    only: domain names, topic one-line descriptions, and unassigned papers.
    """
    nodes = collect_topic_tree(wiki_root)
    if nodes is None:
        return None
    return render_agent_tree(nodes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish an audited link-plan.json.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = args.plan.expanduser().resolve()
    wiki_root = args.wiki_root.expanduser().resolve()
    if not plan_path.is_file():
        print("ERROR: --plan must point to an existing file.", file=sys.stderr)
        return 2
    if not wiki_root.is_dir():
        print("ERROR: --wiki-root must point to an existing directory.", file=sys.stderr)
        return 2

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if audit_plan(plan) is None:
        return 1

    blockers = preflight_errors(plan, wiki_root)
    if blockers:
        for error in blockers:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    today = datetime.date.today().isoformat()
    schema_version = str(plan.get("schema_version", "2.0"))
    purpose = str(plan.get("purpose", "ingest"))
    for directory in ("wiki", "wiki/topics", "wiki/sources"):
        (wiki_root / directory).mkdir(parents=True, exist_ok=True)

    source_pages = plan.get("batch", {}).get("source_pages", [])
    titles = {
        page["source_ref"]: page["title"]
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref") and page.get("title")
    }
    batch_titles = dict(titles)
    short_names = {
        page["source_ref"]: page["short"]
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref") and page.get("short")
    }
    action_source_refs = {
        source_ref
        for action in plan.get("topic_actions", [])
        if isinstance(action, dict)
        for source_ref in string_list(action.get("papers"))
    }
    for source_ref in sorted(action_source_refs - set(titles)):
        try:
            source_path = safe_relative_path(wiki_root, source_ref)
            source_title = (
                first_h1(source_path.read_text(encoding="utf-8"))
                if source_path.is_file()
                else ""
            )
        except (OSError, UnicodeDecodeError, ValueError):
            source_title = ""
        if source_title:
            titles[source_ref] = source_title
    batch = plan.get("batch", {})
    batch_label = str(batch.get("label", "")).strip() if isinstance(batch, dict) else ""
    batch_title = "、".join(batch_titles.values()) or batch_label or "batch"
    writes: list[dict[str, str]] = []
    errors: list[str] = []
    source_log_entries: list[dict[str, Any]] = []
    synthesis_log_entries: list[dict[str, Any]] = []
    index_entries: list[tuple[str, str, str]] = []
    replace_index_descriptions: set[str] = set()
    backlinks: dict[str, list[tuple[str, str]]] = {}
    for action in plan.get("topic_actions", []):
        if not isinstance(action, dict):
            continue
        for source_ref in string_list(action.get("papers")):
            backlinks.setdefault(source_ref, []).append((action.get("name", ""), "主题"))

    for page in source_pages:
        if not isinstance(page, dict):
            continue
        work_dir = resolve_work_dir(page.get("work_dir", ""), wiki_root)
        card_path = work_dir / "paper-card.md"
        target_path = safe_relative_path(wiki_root, page["source_ref"])
        if not card_path.is_file():
            errors.append(f"Missing finalized card: {card_path}")
            continue
        try:
            card_text = card_path.read_text(encoding="utf-8")
            existing_text = (
                target_path.read_text(encoding="utf-8") if target_path.is_file() else None
            )
            content = source_page_text(page, card_text, existing_text, today)
            content += render_backlinks(backlinks.get(page["source_ref"], []))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            errors.append(f"Failed to prepare source page {page['source_ref']}: {exc}")
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        summary = ""
        digest_path = work_dir / "paper-digest.json"
        if digest_path.is_file():
            try:
                digest = json.loads(digest_path.read_text(encoding="utf-8"))
                summary = digest.get("analysis", {}).get("one_sentence_summary", "")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                summary = ""
        if existing_text != content:
            target_path.write_text(content, encoding="utf-8")
            created = existing_text is None
            writes.append(
                {
                    "kind": "source",
                    "path": str(target_path.relative_to(wiki_root)),
                    "action": "create" if created else "update",
                }
            )
            source_log_entries.append(
                {
                    "title": page.get("title", ""),
                    "path": str(target_path.relative_to(wiki_root)),
                    "summary": summary,
                    "created": created,
                }
            )
        index_entries.append(
            (
                "来源",
                str(target_path.relative_to(wiki_root)),
                summary or "来源论文",
            )
        )

    for action in plan.get("topic_actions", []):
        if not isinstance(action, dict):
            continue
        existing_path = find_existing_topic(action, wiki_root)
        if action.get("action") == "update_topic" and existing_path is None:
            errors.append(f"Unable to locate existing topic for {action.get('name', '')}")
            continue
        if existing_path is None:
            directory = wiki_root / "wiki" / "topics"
            directory.mkdir(parents=True, exist_ok=True)
            existing_path = directory / f"{safe_filename(action.get('name', ''))}.md"
        existing_text = existing_path.read_text(encoding="utf-8") if existing_path.is_file() else None
        try:
            if existing_text is None:
                content = topic_page_text(
                    action,
                    titles,
                    today,
                    today,
                    short_names,
                    schema_version=schema_version,
                    purpose=purpose,
                )
            else:
                content = merge_topic_page(
                    existing_text,
                    action,
                    titles,
                    today,
                    short_names,
                    schema_version=schema_version,
                    purpose=purpose,
                )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            errors.append(f"Failed to prepare topic {action.get('name', '')}: {exc}")
            continue
        if existing_text != content:
            existing_path.write_text(content, encoding="utf-8")
            created = existing_text is None
            writes.append(
                {
                    "kind": "topic",
                    "path": str(existing_path.relative_to(wiki_root)),
                    "action": "create" if created else "update",
                }
            )
            synthesis_log_entries.append(
                {
                    "path": str(existing_path.relative_to(wiki_root)),
                    "created": created,
                }
            )
        topic_path = str(existing_path.relative_to(wiki_root))
        description = (
            str(action.get("index_summary", ""))
            if schema_version == "3.0"
            else str(action.get("summary", ""))
        )
        index_entries.append(("主题", topic_path, description))
        if schema_version == "3.0" and description:
            replace_index_descriptions.add(topic_path)

    # Mining plans reference existing source pages instead of writing new
    # ones: append the topic backlinks to those pages.
    batch_page_refs = {
        page.get("source_ref")
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref")
    }
    for action in plan.get("topic_actions", []):
        if not isinstance(action, dict):
            continue
        name = action.get("name", "")
        for source_ref in string_list(action.get("papers")):
            if source_ref in batch_page_refs:
                continue
            try:
                text, changed = append_backlinks_to_page(
                    wiki_root, source_ref, [(name, "主题")]
                )
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                errors.append(f"Failed to update source backlinks for {source_ref}: {exc}")
                continue
            if changed:
                target = safe_relative_path(wiki_root, source_ref)
                target.write_text(text, encoding="utf-8")
                writes.append(
                    {
                        "kind": "source-backlinks",
                        "path": str(target.relative_to(wiki_root)),
                        "action": "update",
                    }
                )

    research_path = wiki_root / "wiki" / "meta" / "research.md"
    research_existing = (
        research_path.read_text(encoding="utf-8") if research_path.is_file() else None
    )
    research_created = today
    if research_existing is not None:
        research_fields, _, _ = parse_frontmatter(research_existing)
        research_created = research_fields.get("created", today)

    index_path = wiki_root / "wiki" / "index.md"
    log_path = wiki_root / "wiki" / "log.md"
    if not index_path.is_file():
        index_path.write_text("# Wiki 索引\n\n## 主题\n## 来源\n## 元页面\n", encoding="utf-8")
    if not log_path.is_file():
        log_path.write_text("# 操作日志\n", encoding="utf-8")
    try:
        index_text = index_path.read_text(encoding="utf-8")
        updated_index = update_index(
            index_text,
            index_entries,
            today,
            replace_descriptions=replace_index_descriptions,
        )
        if updated_index != index_text:
            index_path.write_text(updated_index, encoding="utf-8")
            writes.append({"kind": "index", "path": "wiki/index.md", "action": "update"})

        log_text = log_path.read_text(encoding="utf-8")
        updated_log = append_log(log_text, source_log_entries, synthesis_log_entries, batch_title, today)
        if updated_log != log_text:
            log_path.write_text(updated_log, encoding="utf-8")
            writes.append({"kind": "log", "path": "wiki/log.md", "action": "update"})
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Failed to update index or log: {exc}")

    buckets = collect_tree_buckets(wiki_root)
    categories = collect_topic_categories(wiki_root)
    tree_nodes = collect_topic_tree(wiki_root)
    tree_path = wiki_root / "wiki" / "meta" / "knowledge-tree.md"
    try:
        tree_text = (
            render_knowledge_tree(tree_nodes, categories)
            if tree_nodes is not None
            else None
        )
        if tree_text is not None:
            tree_path.parent.mkdir(parents=True, exist_ok=True)
            existing_tree = (
                tree_path.read_text(encoding="utf-8") if tree_path.is_file() else None
            )
            if existing_tree != tree_text:
                tree_path.write_text(tree_text, encoding="utf-8")
                writes.append(
                    {
                        "kind": "knowledge-tree",
                        "path": "wiki/meta/knowledge-tree.md",
                        "action": "create" if existing_tree is None else "update",
                    }
                )
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Failed to update knowledge tree: {exc}")

    agent_tree_path = wiki_root / "wiki" / "meta" / "agent-tree.md"
    try:
        agent_tree_text = (
            render_agent_tree(tree_nodes) if tree_nodes is not None else None
        )
        if agent_tree_text is not None:
            agent_tree_path.parent.mkdir(parents=True, exist_ok=True)
            existing_agent_tree = (
                agent_tree_path.read_text(encoding="utf-8")
                if agent_tree_path.is_file()
                else None
            )
            if existing_agent_tree != agent_tree_text:
                agent_tree_path.write_text(agent_tree_text, encoding="utf-8")
                writes.append(
                    {
                        "kind": "agent-tree",
                        "path": "wiki/meta/agent-tree.md",
                        "action": (
                            "create" if existing_agent_tree is None else "update"
                        ),
                    }
                )
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Failed to update agent tree: {exc}")

    try:
        research_text = render_research_page(buckets, today, research_created)
        if research_text is not None and research_text != research_existing:
            research_path.parent.mkdir(parents=True, exist_ok=True)
            research_path.write_text(research_text, encoding="utf-8")
            writes.append(
                {
                    "kind": "research",
                    "path": "wiki/meta/research.md",
                    "action": "create" if research_existing is None else "update",
                }
            )
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"Failed to update research dashboard: {exc}")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    warnings: list[str] = []
    if purpose == "mining" and any(
        isinstance(item, dict) and item.get("status") == "answered"
        for action in plan.get("topic_actions", [])
        if isinstance(action, dict)
        for field in ("open_questions", "research_gaps")
        for item in action.get(field, [])
        if isinstance(action.get(field, []), list)
    ):
        warnings.append(
            "narrative_refresh_recommended: mining archived an answered item; "
            "refresh the topic narrative in a later ingest or explicit topic rebuild."
        )

    report = {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if errors else "pass",
            "created_sources": sum(item["kind"] == "source" and item["action"] == "create" for item in writes),
            "updated_sources": sum(item["kind"] == "source" and item["action"] == "update" for item in writes),
            "created_topics": sum(item["kind"] == "topic" and item["action"] == "create" for item in writes),
            "updated_topics": sum(item["kind"] == "topic" and item["action"] == "update" for item in writes),
            "errors": len(errors),
        },
        "writes": writes,
        "errors": errors,
        "warnings": warnings,
    }
    print(
        f"Publish status: {report['summary']['status']} "
        f"(sources={report['summary']['created_sources']} new/"
        f"{report['summary']['updated_sources']} updated, "
        f"topics={report['summary']['created_topics']} new/"
        f"{report['summary']['updated_topics']} updated)"
    )
    if args.report:
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote publish report: {output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
