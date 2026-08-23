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


def related_entity_names(papers: set[str], entity_source_links: dict[str, list[str]]) -> list[str]:
    """Entity page stems that cite at least one paper of a topic action."""
    names: list[str] = []
    for stem, source_refs in entity_source_links.items():
        if set(source_refs) & papers:
            names.append(stem)
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


def entity_source_line(source_ref: str, titles: dict[str, str]) -> str:
    return f"- {wiki_link(source_ref, source_label(source_ref, titles))}"


def entity_stub_text(
    name: str,
    aliases: list[str],
    source_refs: list[str],
    titles: dict[str, str],
    today: str,
    created: str,
) -> str:
    frontmatter = render_frontmatter(
        ["entity"],
        created,
        today,
        "stub",
        sources=source_refs,
        aliases=aliases,
    )
    lines = [
        frontmatter.rstrip(),
        f"# {name}",
        "",
        "> 本页由 publish_wiki.py 确定性生成，只聚合引用本实体的论文；定义与评价见各来源论文页。",
        "",
        "## 别名",
        "",
    ]
    lines.extend(f"- {alias}" for alias in aliases)
    lines.extend(["", "## 引用来源", ""])
    for source_ref in source_refs:
        lines.append(entity_source_line(source_ref, titles))
    return "\n".join(lines).rstrip() + "\n"


def merge_entity_stub(
    existing_text: str,
    aliases: list[str],
    source_refs: list[str],
    titles: dict[str, str],
    today: str,
) -> str:
    fields, lists, body = parse_frontmatter(existing_text)
    fields, lists = merge_frontmatter_sets(fields, lists, source_refs, aliases, today)
    additions = missing_lines(
        [entity_source_line(ref, titles) for ref in source_refs],
        section_body(body, "引用来源"),
    )
    if additions:
        body = insert_before_next_section(body, "引用来源", additions)
    return rebuild_page(fields, lists, body, "entity")


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
    related_entities: list[str] | None = None,
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
    lines.extend(["## 相关实体", ""])
    for name in related_entities or []:
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


def merge_topic_page(
    existing_text: str,
    action: dict[str, Any],
    titles: dict[str, str],
    today: str,
    related_entities: list[str] | None = None,
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
        "相关实体",
        [f"- [[{name}|{name}]]" for name in related_entities or []],
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


def find_existing_entity(name: str, wiki_root: Path) -> Path | None:
    directory = wiki_root / "wiki" / "entities"
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


def normalize_entity_name(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value).lower())


MIN_NAME_VARIANT_LEN = 3


def find_name_variant(name: str, wiki_root: Path) -> str | None:
    """Find an existing entity page whose name or alias resembles `name`.

    Exact raw-name matches are handled by the normal merge path; this detects
    variants (punctuation differences, parenthetical expansions, family
    prefixes) that would otherwise create a duplicate page.
    """
    key = normalize_entity_name(name)
    if not key:
        return None
    folder = wiki_root / "wiki" / "entities"
    if not folder.is_dir():
        return None
    for page in folder.glob("*.md"):
        if page.stem == name:
            continue
        candidates = [page.stem]
        try:
            _, lists, _ = parse_frontmatter(page.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            lists = {}
        candidates.extend(lists.get("aliases", []))
        for candidate in candidates:
            candidate_key = normalize_entity_name(candidate)
            if len(candidate_key) < MIN_NAME_VARIANT_LEN:
                continue
            if (
                key == candidate_key
                or key.startswith(candidate_key)
                or candidate_key.startswith(key)
            ):
                return page.stem
    return None


def collect_entity_mentions(
    source_pages: list[Any], wiki_root: Path
) -> dict[str, list[tuple[str, str]]]:
    """Collect normalized entity mentions from the batch digests.

    Returns a mapping from normalized key to a list of `(raw_name, source_ref)`
    pairs across `analysis.datasets`, `analysis.models`, and `analysis.metrics`.
    """
    mentions: dict[str, list[tuple[str, str]]] = {}
    seen_pairs: set[tuple[str, str]] = set()
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
        analysis = digest.get("analysis", {})
        if not isinstance(analysis, dict):
            continue
        source_ref = page.get("source_ref", "")
        for field in ("datasets", "models", "metrics"):
            for name in string_list(analysis.get(field)):
                key = normalize_entity_name(name)
                if not key:
                    continue
                pair = (name, source_ref)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                mentions.setdefault(key, []).append((name, source_ref))
    return mentions


def resolve_entity_targets(
    mentions: dict[str, list[tuple[str, str]]], wiki_root: Path
) -> list[dict[str, Any]]:
    """Resolve collected mentions into entity page targets.

    For every normalized key: the shorter raw name becomes the canonical page
    title and other spellings become aliases. A name resembling an existing
    entity page (or its aliases) merges into that page instead of creating a
    variant. Names resembling each other within the batch also merge into the
    shorter canonical name. Returns one target per canonical page.
    """
    proposals: dict[str, dict[str, Any]] = {}
    for key in sorted(mentions):
        pairs = mentions[key]
        canonical, _ = min(pairs, key=lambda pair: (len(pair[0]), pair[0]))
        raw_names = sorted({name for name, _ in pairs})
        aliases = [name for name in raw_names if name != canonical]
        source_refs: list[str] = []
        for _, source_ref in pairs:
            if source_ref and source_ref not in source_refs:
                source_refs.append(source_ref)
        existing_path = find_existing_entity(canonical, wiki_root)
        if existing_path is None:
            variant = find_name_variant(canonical, wiki_root)
            if variant:
                existing_path = find_existing_entity(variant, wiki_root)
                if existing_path is not None:
                    aliases = sorted(set(aliases) | {canonical})
                    canonical = existing_path.stem
        proposals[key] = {
            "name": canonical,
            "aliases": aliases,
            "source_refs": source_refs,
            "path": existing_path,
        }

    # Merge within-batch proposals: a name that is a variant of an
    # already-claimed canonical name folds into that proposal, so one batch
    # never creates two pages for the same family (for example LLaVA and
    # LLaVA 1.5).
    index: dict[str, str] = {}  # normalized name -> proposal key
    merged_out: set[str] = set()

    def register(prop_key: str) -> None:
        prop = proposals[prop_key]
        for name in [prop["name"]] + prop["aliases"]:
            nkey = normalize_entity_name(name)
            if len(nkey) >= MIN_NAME_VARIANT_LEN:
                index.setdefault(nkey, prop_key)

    def merge_into(parent_key: str, child_key: str) -> None:
        parent = proposals[parent_key]
        child = proposals[child_key]
        merged_names = {child["name"], *child["aliases"]} - {parent["name"]}
        parent["aliases"] = sorted(set(parent["aliases"]) | merged_names)
        parent["source_refs"] = list(
            dict.fromkeys(parent["source_refs"] + child["source_refs"])
        )
        if parent["path"] is None and child["path"] is not None:
            parent["path"] = child["path"]
        merged_out.add(child_key)

    for key in sorted(proposals, key=lambda item: (len(item), item)):
        if key in merged_out:
            continue
        prop = proposals[key]
        parent_key: str | None = None
        for name in [prop["name"], *prop["aliases"]]:
            nkey = normalize_entity_name(name)
            if len(nkey) < MIN_NAME_VARIANT_LEN:
                continue
            for candidate_key in list(index):
                if (
                    nkey == candidate_key
                    or nkey.startswith(candidate_key)
                    or candidate_key.startswith(nkey)
                ):
                    parent_key = index[candidate_key]
                    break
            if parent_key:
                break
        if parent_key is not None and parent_key != key:
            merge_into(parent_key, key)
            register(parent_key)
            continue
        register(key)

    targets: list[dict[str, Any]] = []
    for key in sorted(proposals):
        if key in merged_out:
            continue
        prop = proposals[key]
        path = prop["path"]
        if path is None:
            directory = wiki_root / "wiki" / "entities"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{safe_filename(prop['name'])}.md"
        targets.append(
            {
                "name": prop["name"],
                "aliases": prop["aliases"],
                "source_refs": prop["source_refs"],
                "path": path,
            }
        )
    return targets


def render_research_page(
    buckets: dict[str, dict[str, list[Any]]] | None,
    today: str,
    created: str,
) -> str | None:
    """Render wiki/meta/research.md: domain-grouped dashboard of open
    questions and research gaps."""
    questions_by_domain: dict[str, list[tuple[str, str, str]]] = {}
    gaps_by_domain: dict[str, list[tuple[str, str, str]]] = {}
    if buckets:
        for domain in buckets:
            questions_by_domain[domain] = list(buckets[domain]["questions"])
            gaps_by_domain[domain] = list(buckets[domain]["gaps"])

    has_content = bool(
        any(questions_by_domain.values()) or any(gaps_by_domain.values())
    )
    if not has_content:
        return None

    lines = [
        render_frontmatter(["meta"], created, today, "evergreen").rstrip(),
        "# 研究仪表盘",
        "",
        "> 本页由 publish_wiki.py 确定性生成：按领域聚合主题页的开放问题与研究空白。不要手动编辑。",
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
            for text_item, label, path in sorted(items, key=lambda row: row[0]):
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
            bullets.append(stripped[2:].strip())
    return bullets


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
            {"sources": [], "topics": [], "entities": [], "questions": [], "gaps": []},
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
            for gap in section_bullets(body, "研究空白与候选方向"):
                bucket(domain)["gaps"].append((gap, label, path))
        elif path.startswith("wiki/entities/"):
            text = ""
            try:
                text = (wiki_root / path).read_text(encoding="utf-8")
            except OSError:
                pass
            _, lists, _ = parse_frontmatter(text)
            aliases = lists.get("aliases", [])
            domain = page_domains(wiki_root, path)
            bucket(domain)["entities"].append((path, label, description, aliases))
    return buckets


def ordered_domains(buckets: dict[str, dict[str, list[Any]]]) -> list[str]:
    special = {"跨领域", "未分类"}
    ordered = sorted(domain for domain in buckets if domain not in special)
    ordered += [domain for domain in ("跨领域", "未分类") if domain in buckets]
    return ordered


def render_knowledge_tree(buckets: dict[str, dict[str, list[Any]]]) -> str:
    """Render wiki/meta/knowledge-tree.md from collected buckets.

    Deterministic: identical buckets produce identical text.
    """
    lines = [
        "# 知识树",
        "",
        "> 本页由 publish_wiki.py 确定性生成，用于 LLM 树检索导航；不要手动编辑，每次发布后重建。检索协议见 wiki-shared 的 references/retrieval-protocol.md。",
        "",
    ]
    for domain in ordered_domains(buckets):
        data = buckets[domain]
        lines.append(f"## {domain}")
        lines.append("")
        for kind, title, key in (
            ("sources", "### 论文", "sources"),
            ("topics", "### 主题", "topics"),
            ("entities", "### 实体", "entities"),
        ):
            items = sorted(data[key], key=lambda row: row[1])
            if not items:
                continue
            lines.append(title)
            lines.append("")
            for row in items:
                stem = Path(row[0]).stem
                suffix = f" — {row[2]}" if row[2] else ""
                if kind == "entities" and row[3]:
                    alias_text = f"（别名：{'、'.join(row[3])}）"
                    lines.append(f"- [[{stem}|{row[1]}]]{alias_text}{suffix}")
                else:
                    lines.append(f"- [[{stem}|{row[1]}]]{suffix}")
            lines.append("")
        for title, key in (("### 开放问题", "questions"), ("### 研究空白", "gaps")):
            if not data[key]:
                continue
            lines.append(title)
            lines.append("")
            seen: set[str] = set()
            for text_item, label, path in sorted(data[key], key=lambda row: row[0]):
                line = f"- {text_item} — 来源：[[{Path(path).stem}|{label}]]"
                if line in seen:
                    continue
                seen.add(line)
                lines.append(line)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_knowledge_tree(wiki_root: Path) -> str | None:
    """Render wiki/meta/knowledge-tree.md from the current wiki state.

    Deterministic: identical wiki state produces identical text. Grouped by
    domain (first directory under wiki/sources/papers/), with per-domain
    open questions and research gaps aggregated from topic pages.
    """
    buckets = collect_tree_buckets(wiki_root)
    if buckets is None:
        return None
    return render_knowledge_tree(buckets)


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
    for directory in ("wiki", "wiki/entities", "wiki/topics", "wiki/sources"):
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
    entity_targets = resolve_entity_targets(collect_entity_mentions(source_pages, wiki_root), wiki_root)
    entity_source_links: dict[str, list[str]] = {}
    for target in entity_targets:
        entity_source_links[target["name"]] = target["source_refs"]
        for source_ref in target["source_refs"]:
            backlinks.setdefault(source_ref, []).append((target["name"], "实体"))
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

    for target in entity_targets:
        existing_path = target["path"]
        existing_text = existing_path.read_text(encoding="utf-8") if existing_path.is_file() else None
        try:
            if existing_text is None:
                content = entity_stub_text(
                    target["name"],
                    target["aliases"],
                    target["source_refs"],
                    titles,
                    today,
                    today,
                )
            else:
                content = merge_entity_stub(
                    existing_text,
                    target["aliases"],
                    target["source_refs"],
                    titles,
                    today,
                )
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            errors.append(f"Failed to prepare entity {target['name']}: {exc}")
            continue
        if existing_text != content:
            existing_path.write_text(content, encoding="utf-8")
            created = existing_text is None
            writes.append(
                {
                    "kind": "entity",
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
                "实体",
                str(existing_path.relative_to(wiki_root)),
                "公共数据集 / 基准 / 模型家族 / 指标",
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
        related_entities = related_entity_names(
            set(string_list(action.get("papers"))),
            entity_source_links,
        )
        try:
            if existing_text is None:
                content = topic_page_text(action, titles, today, today, related_entities, short_names)
            else:
                content = merge_topic_page(existing_text, action, titles, today, related_entities, short_names)
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
        index_path.write_text("# Wiki 索引\n\n## 实体\n## 主题\n## 来源\n## 元页面\n", encoding="utf-8")
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

    buckets = collect_tree_buckets(wiki_root)
    tree_path = wiki_root / "wiki" / "meta" / "knowledge-tree.md"
    try:
        tree_text = render_knowledge_tree(buckets) if buckets is not None else None
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

    report = {
        "schema_version": "1.0",
        "summary": {
            "status": "fail" if errors else "pass",
            "created_sources": sum(item["kind"] == "source" and item["action"] == "create" for item in writes),
            "updated_sources": sum(item["kind"] == "source" and item["action"] == "update" for item in writes),
            "created_entities": sum(item["kind"] == "entity" and item["action"] == "create" for item in writes),
            "updated_entities": sum(item["kind"] == "entity" and item["action"] == "update" for item in writes),
            "created_topics": sum(item["kind"] == "topic" and item["action"] == "create" for item in writes),
            "updated_topics": sum(item["kind"] == "topic" and item["action"] == "update" for item in writes),
            "errors": len(errors),
        },
        "writes": writes,
        "errors": errors,
        "warnings": [],
    }
    print(
        f"Publish status: {report['summary']['status']} "
        f"(sources={report['summary']['created_sources']} new/"
        f"{report['summary']['updated_sources']} updated, "
        f"entities={report['summary']['created_entities']} new/"
        f"{report['summary']['updated_entities']} updated, "
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
