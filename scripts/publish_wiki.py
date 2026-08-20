#!/usr/bin/env python3
"""Publish an audited link-plan.json into the LLM Wiki."""

from __future__ import annotations

import argparse
import datetime
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
        if field_match:
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


def relation_target(value: str) -> str:
    target = str(value)
    return f"[[{target}|{target}]]" if target else ""


def related_hub_names(papers: set[str], hub_actions: Any) -> list[str]:
    names: list[str] = []
    for action in hub_actions:
        if not isinstance(action, dict):
            continue
        if set(string_list(action.get("source_refs"))) & papers:
            name = action.get("name", "")
            if name:
                names.append(name)
    return names


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


def hub_page_text(
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    created: str,
) -> str:
    sources = string_list(action.get("source_refs"))
    aliases = string_list(action.get("aliases"))
    frontmatter = render_frontmatter(
        [action.get("kind") or "concept"],
        created,
        today,
        "stub",
        sources=sources,
        aliases=aliases,
    )
    lines = [
        frontmatter.rstrip(),
        f"# {action.get('name', '')}",
        "",
        action.get("definition", ""),
        "",
        "## 别名",
        "",
    ]
    lines.extend(f"- {alias}" for alias in aliases)
    lines.extend(["", "## 证据", "", "| 来源 | 断言 | 证据 | confidence |", "|---|---|---|---|"])
    evidence = action.get("evidence", [])
    if isinstance(evidence, list):
        for row in evidence:
            if not isinstance(row, dict):
                continue
            source_ref = row.get("source_ref", "")
            lines.append(
                "| "
                + " | ".join(
                    [
                        escape_table(source_label(source_ref, titles)),
                        escape_table(row.get("claim", "")),
                        escape_table(row.get("pointer", "")),
                        escape_table(row.get("confidence", "-")),
                    ]
                )
                + " |"
            )
    lines.extend(["", "## 关系", "", "| 类型 | 对象 | 证据 | 说明 |", "|---|---|---|---|"])
    relations = action.get("relations", [])
    if isinstance(relations, list):
        for row in relations:
            if not isinstance(row, dict):
                continue
            description = (
                f"provenance: {row.get('provenance', '-')}; "
                f"confidence: {row.get('confidence', '-')}"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        escape_table(row.get("type", "")),
                        relation_target(row.get("target", "")),
                        escape_table(row.get("pointer", "")),
                        escape_table(description),
                    ]
                )
                + " |"
            )
    lines.extend(["", "## 争议与矛盾", ""])
    lines.extend(render_contradictions(action.get("contradictions", []), titles))
    lines.extend(["## 开放问题", ""])
    for question in string_list(action.get("open_questions")):
        lines.append(f"- {question}")
    lines.extend(["", "## 引用来源", ""])
    for source_ref in sources:
        lines.append(f"- {wiki_link(source_ref, source_label(source_ref, titles))}")
    return "\n".join(lines).rstrip() + "\n"


def comparison_paper_name(item: dict[str, Any], titles: dict[str, str]) -> str:
    return (item.get("paper") or source_label(item.get("source_ref", ""), titles)).strip()


def comparison_row(row: dict[str, Any], titles: dict[str, str]) -> str:
    source_ref = row.get("source_ref", "")
    paper = row.get("paper") or source_label(source_ref, titles)
    paper_cell = wiki_link(source_ref, paper) if source_ref else escape_table(paper)
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
            paper_cell = wiki_link(source_ref, paper) if source_ref else escape_table(paper)
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


def render_research_gaps(
    items: Any,
    titles: dict[str, str],
    short_names: dict[str, str] | None = None,
) -> list[str]:
    if not isinstance(items, list) or not items:
        return []
    if all(isinstance(item, str) for item in items):
        return [f"- {gap}" for gap in string_list(items)]
    short = short_names or {}
    lines: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        gap = str(item.get("gap", "")).strip()
        if not gap:
            continue
        refs = "、".join(
            source_wikilink(ref, short, titles) for ref in string_list(item.get("source_refs"))
        )
        direction = str(item.get("direction", ""))
        continuity = str(item.get("continuity", ""))
        suffix = "；".join(
            part
            for part in [
                f"来源：{refs}" if refs else "",
                f"可检验方向：{direction}" if direction else "",
                f"承接：{continuity}" if continuity else "",
            ]
            if part
        )
        lines.append(f"- {gap}" + (f"（{suffix}）" if suffix else ""))
    return lines


def topic_page_text(
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    created: str,
    related_hubs: list[str] | None = None,
    short_names: dict[str, str] | None = None,
) -> str:
    sources = string_list(action.get("papers"))
    frontmatter = render_frontmatter(
        ["topic"],
        created,
        today,
        "stub",
        sources=sources,
        aliases=[],
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
    lines.extend(["## 相关实体与概念", ""])
    for name in related_hubs or []:
        lines.append(f"- [[{name}|{name}]]")
    lines.extend(["", "## 开放问题", ""])
    for question in string_list(action.get("open_questions")):
        lines.append(f"- {question}")
    lines.extend(["", "## 研究空白与候选方向", ""])
    lines.extend(render_research_gaps(action.get("research_gaps", []), titles, short_names))
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
    frontmatter = render_frontmatter(
        [tag],
        fields.get("created", datetime.date.today().isoformat()),
        fields.get("updated", datetime.date.today().isoformat()),
        fields.get("status", "stub"),
        sources=lists.get("sources", []),
        aliases=lists.get("aliases", []),
    )
    return frontmatter + body.lstrip("\n")


def merge_hub_page(existing_text: str, action: dict[str, Any], titles: dict[str, str], today: str) -> str:
    fields, lists, body = parse_frontmatter(existing_text)
    evidence_rows: list[str] = []
    for row in action.get("evidence", []):
        if not isinstance(row, dict):
            continue
        evidence_rows.append(
            "| "
            + " | ".join(
                [
                    escape_table(source_label(row.get("source_ref", ""), titles)),
                    escape_table(row.get("claim", "")),
                    escape_table(row.get("pointer", "")),
                    escape_table(row.get("confidence", "-")),
                ]
            )
            + " |"
        )
    relation_rows: list[str] = []
    for row in action.get("relations", []):
        if not isinstance(row, dict):
            continue
        relation_rows.append(
            "| "
            + " | ".join(
                [
                    escape_table(row.get("type", "")),
                    relation_target(row.get("target", "")),
                    escape_table(row.get("pointer", "")),
                    escape_table(
                        f"provenance: {row.get('provenance', '-')}; "
                        f"confidence: {row.get('confidence', '-')}"
                    ),
                ]
            )
            + " |"
        )
    body = insert_before_next_section(body, "证据", evidence_rows)
    body = insert_before_next_section(body, "关系", relation_rows)
    body = insert_before_next_section(
        body,
        "争议与矛盾",
        render_contradictions(action.get("contradictions", []), titles),
    )
    body = insert_before_next_section(
        body,
        "开放问题",
        [f"- {question}" for question in string_list(action.get("open_questions"))],
    )
    fields, lists = merge_frontmatter_sets(
        fields,
        lists,
        string_list(action.get("source_refs")),
        string_list(action.get("aliases")),
        today,
    )
    return rebuild_page(fields, lists, body, action.get("kind") or "concept")


def merge_topic_page(
    existing_text: str,
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    related_hubs: list[str] | None = None,
    short_names: dict[str, str] | None = None,
) -> str:
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
    body = insert_before_next_section(
        body,
        "相关实体与概念",
        [f"- [[{name}|{name}]]" for name in related_hubs or []],
    )
    body = insert_before_next_section(
        body,
        "开放问题",
        [f"- {question}" for question in string_list(action.get("open_questions"))],
    )
    body = insert_before_next_section(
        body,
        "研究空白与候选方向",
        render_research_gaps(action.get("research_gaps", []), titles, short_names),
    )
    fields, lists = merge_frontmatter_sets(
        fields,
        lists,
        string_list(action.get("papers")),
        [],
        today,
    )
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
) -> str:
    result = index_text
    added = False
    for section, path, description in entries:
        if f"[[{path}" in result:
            continue
        marker = f"## {section}\n"
        line = f"- [[{path}|{Path(path).stem}]] - {description}\n"
        position = result.find(marker)
        if position < 0:
            result = result.rstrip() + f"\n\n{marker}{line}"
        else:
            insert_at = position + len(marker)
            result = result[:insert_at] + line + result[insert_at:]
        added = True
    return update_meta_frontmatter(result, today) if added else result


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


def find_existing_hub(action: dict[str, Any], wiki_root: Path) -> Path | None:
    existing_page = action.get("existing_page")
    if isinstance(existing_page, str) and existing_page:
        return safe_relative_path(wiki_root, existing_page)
    name = safe_filename(action.get("name", ""))
    directory = wiki_root / "wiki" / ("entities" if action.get("kind") == "entity" else "concepts")
    if not directory.is_dir():
        return None
    for path in directory.glob("*.md"):
        if path.stem == name:
            return path
    return None


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


def collect_l1_candidates(source_pages: list[Any], wiki_root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in source_pages:
        if not isinstance(page, dict):
            continue
        work_dir = resolve_work_dir(page.get("work_dir", ""), wiki_root)
        digest_path = work_dir / "paper-digest.json"
        if not digest_path.is_file():
            continue
        try:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        for cand in digest.get("candidates", []):
            if not isinstance(cand, dict):
                continue
            if cand.get("tier") != "L1":
                continue
            cid = str(cand.get("id", "")).strip()
            name = str(cand.get("name", "")).strip()
            if not cid or not name or cid in seen:
                continue
            seen.add(cid)
            candidates.append(
                {
                    "id": cid,
                    "name": name,
                    "kind": cand.get("kind") or "concept",
                    "definition": str(cand.get("definition", "")).strip(),
                    "source_refs": string_list(cand.get("source_refs")),
                }
            )
    return candidates


def candidates_page(
    existing_text: str | None,
    new_candidates: list[dict[str, Any]],
    titles: dict[str, str],
    today: str,
) -> str | None:
    existing_ids: set[str] = set()
    existing_rows: list[str] = []
    if existing_text:
        _, _, body = parse_frontmatter(existing_text)
        for line in body.splitlines():
            stripped = line.strip()
            if (
                stripped.startswith("|")
                and not stripped.startswith("|---")
                and not stripped.startswith("| id")
            ):
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if cells and cells[0]:
                    existing_ids.add(cells[0])
                existing_rows.append(stripped)
    additions: list[str] = []
    for cand in new_candidates:
        if cand["id"] in existing_ids:
            continue
        source_ref = cand["source_refs"][0] if cand["source_refs"] else ""
        source_cell = (
            wiki_link(source_ref, source_label(source_ref, titles))
            if source_ref
            else ""
        )
        additions.append(
            "| "
            + " | ".join(
                [
                    escape_table(cand["id"]),
                    escape_table(cand["name"]),
                    escape_table(cand["kind"]),
                    escape_table(cand["definition"]),
                    source_cell,
                ]
            )
            + " |"
        )
    if not additions:
        return existing_text
    created = today
    if existing_text:
        fields, _, _ = parse_frontmatter(existing_text)
        created = fields.get("created", today)
    header = [
        render_frontmatter(["meta"], created, today, "evergreen").rstrip(),
        "# L1 候选账本",
        "",
        "尚未获得第二独立来源、暂不建页的可复用候选。后续论文独立支持时，linker 可升级为 L2 枢纽页。",
        "",
        "| id | 名称 | 类型 | 定义 | 来源 |",
        "|---|---|---|---|---|",
    ]
    return "\n".join(header + existing_rows + additions).rstrip() + "\n"


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

    today = datetime.date.today().isoformat()
    for directory in ("wiki", "wiki/entities", "wiki/concepts", "wiki/topics", "wiki/sources"):
        (wiki_root / directory).mkdir(parents=True, exist_ok=True)

    source_pages = plan.get("batch", {}).get("source_pages", [])
    titles = {
        page["source_ref"]: page["title"]
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref") and page.get("title")
    }
    short_names = {
        page["source_ref"]: page["short"]
        for page in source_pages
        if isinstance(page, dict) and page.get("source_ref") and page.get("short")
    }
    batch_title = "、".join(titles.values()) or "batch"
    writes: list[dict[str, str]] = []
    errors: list[str] = []
    source_log_entries: list[dict[str, Any]] = []
    synthesis_log_entries: list[dict[str, Any]] = []
    index_entries: list[tuple[str, str, str]] = []
    backlinks: dict[str, list[tuple[str, str]]] = {}
    for action in plan.get("hub_actions", []):
        if not isinstance(action, dict):
            continue
        kind = "实体枢纽" if action.get("kind") == "entity" else "概念枢纽"
        for source_ref in string_list(action.get("source_refs")):
            backlinks.setdefault(source_ref, []).append((action.get("name", ""), kind))
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

    for action in plan.get("hub_actions", []):
        if not isinstance(action, dict):
            continue
        existing_path = find_existing_hub(action, wiki_root)
        if action.get("action") == "update_hub" and existing_path is None:
            errors.append(f"Unable to locate existing hub for {action.get('name', '')}")
            continue
        if existing_path is None:
            directory = wiki_root / "wiki" / ("entities" if action.get("kind") == "entity" else "concepts")
            directory.mkdir(parents=True, exist_ok=True)
            existing_path = directory / f"{safe_filename(action.get('name', ''))}.md"
        existing_text = existing_path.read_text(encoding="utf-8") if existing_path.is_file() else None
        try:
            if existing_text is None:
                content = hub_page_text(action, titles, today, today)
            else:
                content = merge_hub_page(existing_text, action, titles, today)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            errors.append(f"Failed to prepare hub {action.get('name', '')}: {exc}")
            continue
        if existing_text != content:
            existing_path.write_text(content, encoding="utf-8")
            created = existing_text is None
            writes.append(
                {
                    "kind": "hub",
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
        index_entries.append(
            (
                "实体" if action.get("kind") == "entity" else "概念",
                str(existing_path.relative_to(wiki_root)),
                action.get("definition", ""),
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
        related_hubs = related_hub_names(
            set(string_list(action.get("papers"))),
            plan.get("hub_actions", []),
        )
        try:
            if existing_text is None:
                content = topic_page_text(action, titles, today, today, related_hubs, short_names)
            else:
                content = merge_topic_page(existing_text, action, titles, today, related_hubs, short_names)
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
        index_entries.append(
            (
                "主题",
                str(existing_path.relative_to(wiki_root)),
                action.get("summary", ""),
            )
        )

    candidates_path = wiki_root / "wiki" / "meta" / "candidates.md"
    candidates_path.parent.mkdir(parents=True, exist_ok=True)
    l1_candidates = collect_l1_candidates(source_pages, wiki_root)
    candidates_text = (
        candidates_path.read_text(encoding="utf-8")
        if candidates_path.is_file()
        else None
    )
    updated_candidates = candidates_page(candidates_text, l1_candidates, titles, today)
    if updated_candidates != candidates_text:
        candidates_path.write_text(updated_candidates, encoding="utf-8")
        writes.append(
            {
                "kind": "candidates",
                "path": "wiki/meta/candidates.md",
                "action": "create" if candidates_text is None else "update",
            }
        )

    index_path = wiki_root / "wiki" / "index.md"
    log_path = wiki_root / "wiki" / "log.md"
    if not index_path.is_file():
        index_path.write_text("# Wiki 索引\n\n## 实体\n## 概念\n## 主题\n## 来源\n## 元页面\n", encoding="utf-8")
    if not log_path.is_file():
        log_path.write_text("# 操作日志\n", encoding="utf-8")
    try:
        index_text = index_path.read_text(encoding="utf-8")
        updated_index = update_index(index_text, index_entries, today)
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

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    report = {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if errors else "pass",
            "created_sources": sum(item["kind"] == "source" and item["action"] == "create" for item in writes),
            "updated_sources": sum(item["kind"] == "source" and item["action"] == "update" for item in writes),
            "created_hubs": sum(item["kind"] == "hub" and item["action"] == "create" for item in writes),
            "updated_hubs": sum(item["kind"] == "hub" and item["action"] == "update" for item in writes),
            "created_topics": sum(item["kind"] == "topic" and item["action"] == "create" for item in writes),
            "updated_topics": sum(item["kind"] == "topic" and item["action"] == "update" for item in writes),
            "errors": len(errors),
        },
        "writes": writes,
        "errors": errors,
    }
    print(
        f"Publish status: {report['summary']['status']} "
        f"(sources={report['summary']['created_sources']} new/"
        f"{report['summary']['updated_sources']} updated, "
        f"hubs={report['summary']['created_hubs']} new/"
        f"{report['summary']['updated_hubs']} updated, "
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
