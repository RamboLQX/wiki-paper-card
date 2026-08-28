#!/usr/bin/env python3
"""Build compact wiki context for a wiki-paper-card processor."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


INDEX_ENTRY_RE = re.compile(r"^[-*]\s+\[\[([^\]|]+)(?:\|([^\]]+))?\]\](?:\s*[—-]\s*(.*))?$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
SECTION_RE = re.compile(
    r"^##\s+(开放问题|争议与不确定|争议与矛盾|研究空白与候选方向)\s*$\n(.*?)(?=^##\s|\Z)",
    re.M | re.S,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact KB context from a wiki index."
    )
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=1600)
    return parser.parse_args()


def ascii_tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_]+", value)}


def chinese_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^\u4e00-\u9fff]+", "", value)
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def token_overlap(query: str, text: str) -> int:
    query_tokens = ascii_tokens(query) | chinese_tokens(query)
    text_tokens = ascii_tokens(text) | chinese_tokens(text)
    return len(query_tokens & text_tokens)


def parse_index(index_path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
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


def page_aliases(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    match = FRONTMATTER_RE.match(text)
    if not match:
        return []
    raw = match.group(1)
    aliases: list[str] = []
    in_aliases = False
    for line in raw.splitlines():
        stripped = line.strip()
        if re.match(r"^aliases\s*:", stripped):
            in_aliases = True
            continue
        if in_aliases:
            item = re.match(r"^-\s+(.+)$", stripped)
            if item:
                value = item.group(1).strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                aliases.append(value)
            elif stripped and not stripped.startswith("-"):
                break
    return aliases


def page_notes(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    frontmatter_match = FRONTMATTER_RE.match(text)
    body = frontmatter_match.group(2) if frontmatter_match else text
    notes: list[str] = []
    for match in SECTION_RE.finditer(body):
        section = match.group(2).strip()
        compact = " ".join(section.split())
        if compact:
            notes.append(f"{match.group(1)}：{compact[:240]}")
    return notes


def entry_text(entry: dict[str, str]) -> str:
    return f"{entry['label']} {entry['description']}"


def score_entries(
    query: str,
    entries: list[dict[str, str]],
    wiki_root: Path,
    with_aliases: bool,
) -> list[tuple[int, dict[str, str]]]:
    """Rank entries by token overlap; alias-aware when with_aliases is set."""
    scored: list[tuple[int, dict[str, str]]] = []
    for entry in entries:
        text = entry_text(entry)
        if with_aliases:
            aliases = page_aliases(wiki_root / entry["path"])
            if aliases:
                text = f"{text} {' '.join(aliases)}"
        scored.append((token_overlap(query, text), entry))
    return scored


def build_context(wiki_root: Path, query: str, max_pages: int, max_chars: int) -> str:
    index_path = wiki_root / "wiki" / "index.md"
    if not index_path.is_file():
        return "当前 wiki 为空，没有可复用页面。"

    entries = parse_index(index_path)
    if not entries:
        return "当前 wiki 没有索引条目。"

    source_entries = [
        entry for entry in entries if entry["path"].startswith("wiki/sources/")
    ]
    topic_entries = [
        entry for entry in entries if entry["path"].startswith("wiki/topics/")
    ]
    all_scored = (
        score_entries(query, source_entries, wiki_root, with_aliases=False)
        + score_entries(query, topic_entries, wiki_root, with_aliases=True)
    )
    related_entries = [
        entry
        for _, entry in sorted(
            all_scored,
            key=lambda pair: pair[0],
            reverse=True,
        )[: max(0, max_pages)]
    ]
    related_sources = [
        entry for entry in related_entries if entry["path"].startswith("wiki/sources/")
    ]
    related_topics = [
        entry for entry in related_entries if entry["path"].startswith("wiki/topics/")
    ]
    zero_overlap = bool(all_scored) and all(pair[0] == 0 for pair in all_scored)

    notes: list[str] = []
    for entry in related_sources + related_topics:
        page_path = wiki_root / entry["path"]
        notes.extend(page_notes(page_path))

    lines: list[str] = ["# KB Context", ""]
    if zero_overlap:
        lines.append(
            "> 检索说明：查询与索引无关键词重合，候选按索引顺序给出，仅作参考。"
        )
        lines.append("")
    if related_sources:
        lines.append("## 相关论文")
        for entry in related_sources:
            lines.append(
                f"- [[{Path(entry['path']).stem}|{entry['label']}]] — {entry['description']}"
            )
        lines.append("")

    if notes:
        lines.append("## 当前开放问题与争议")
        lines.extend(f"- {note}" for note in notes[:10])
        lines.append("")

    if related_topics:
        lines.append("## 已有主题")
        for entry in related_topics:
            lines.append(
                f"- [[{Path(entry['path']).stem}|{entry['label']}]] — {entry['description']}"
            )
        lines.append("")

    output = "\n".join(lines).strip()
    if len(output) <= max_chars:
        return output

    kept_lines: list[str] = []
    for line in lines:
        candidate = "\n".join(kept_lines + [line]).strip()
        if len(candidate) <= max_chars:
            kept_lines.append(line)
        else:
            break
    return "\n".join(kept_lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    wiki_root = args.wiki_root.expanduser().resolve()
    if not wiki_root.is_dir():
        print("ERROR: --wiki-root must point to an existing directory.", file=sys.stderr)
        return 2
    if args.max_pages < 1:
        print("ERROR: --max-pages must be at least 1.", file=sys.stderr)
        return 2

    context = build_context(
        wiki_root,
        args.query,
        max_pages=args.max_pages,
        max_chars=args.max_chars,
    )
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(context, encoding="utf-8")
        print(f"Wrote KB context: {output}")
    else:
        print(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
