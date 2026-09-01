#!/usr/bin/env python3
"""Build a single processor-pack.md with every reference a wiki-processor must read.

The processor brief currently requires the processor to read about a dozen
pinned files (upstream router, manifest, always_load list, paper-type lens
fragments, knowledge model, digest schema, ...) once per paper. This script
merges them into one deterministic document so each processor performs a
single read of identical, hash-pinned content.

Outputs:
  PACK.md       the merged document (byte-identical for identical inputs)
  MANIFEST.json per-source paths and SHA-256, plus the pack SHA-256

Usage:
  python scripts/build_processor_pack.py \
      --repo-root ROOT --output PACK.md [--manifest MANIFEST.json]

Verification:
  python scripts/build_processor_pack.py \
      --repo-root ROOT --output PACK.md --manifest MANIFEST.json --verify

Exit codes: 0 ok, 1 verification failure, 2 usage or input error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"

# Source roles in pack order. Paths are relative to the repository root.
FIXED_SOURCES = [
    ("processor-brief", "skills/wiki-paper-card/references/processor-brief.md"),
    ("upstream-router", "vendor/nature-paper-card/SKILL.md"),
    ("upstream-manifest", "vendor/nature-paper-card/manifest.yaml"),
    ("knowledge-model", "skills/wiki-shared/references/knowledge-model.md"),
    ("writing-guide", "skills/wiki-shared/references/writing-guide.md"),
    ("digest-schema", "skills/wiki-paper-card/references/paper-digest-schema.md"),
]

MANIFEST_PATH = "vendor/nature-paper-card/manifest.yaml"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_manifest_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("manifest root is not a mapping")
        return data
    except ImportError:
        return parse_manifest_fallback(text)


def parse_manifest_fallback(text: str) -> dict[str, Any]:
    """Tolerant parser for the pinned manifest.yaml structure.

    Raises ValueError loudly on any shape it does not understand, so a
    future upstream change is caught by tests instead of silently producing
    a wrong pack.
    """
    data: dict[str, Any] = {
        "always_load": [],
        "references": {"on_demand": []},
        "axes": {"paper_type": {"values": {}}},
    }
    lines = text.splitlines()

    # always_load: `- path` lines between the header and the next top-level key.
    in_section = False
    for raw in lines:
        line = raw.rstrip()
        if re.match(r"^always_load:\s*$", line):
            in_section = True
            continue
        if in_section:
            if re.match(r"^\S", line):
                break
            match = re.match(r"^\s{2}-\s+(\S+)\s*$", line)
            if match:
                data["always_load"].append(match.group(1))

    # axes.paper_type.values: `key: path` lines at 6-space indent, until a
    # line with fewer than 6 leading spaces.
    in_values = False
    for raw in lines:
        line = raw.rstrip()
        if re.match(r"^\s{4}values:\s*$", line):
            in_values = True
            continue
        if in_values:
            if re.match(r"^\S", line) or re.match(r"^\s{1,5}\S", line):
                break
            match = re.match(r"^\s{6}([a-z]+)\s*:\s*(\S+)\s*$", line)
            if match:
                data["axes"]["paper_type"]["values"][match.group(1)] = match.group(2)

    # references.on_demand: `path:` lines until the next top-level key.
    in_on_demand = False
    for raw in lines:
        line = raw.rstrip()
        if re.match(r"^\s{2}on_demand:\s*$", line):
            in_on_demand = True
            continue
        if in_on_demand:
            if re.match(r"^\S", line):
                break
            match = re.match(r"^\s{6}path:\s*(\S+)\s*$", line)
            if match:
                data["references"]["on_demand"].append(match.group(1))

    if not data["always_load"]:
        raise ValueError("unable to parse always_load from manifest")
    if not data["axes"]["paper_type"]["values"]:
        raise ValueError("unable to parse paper_type values from manifest")
    return data


def collect_sources(repo_root: Path) -> list[tuple[str, str]]:
    """Return [(role, repo-relative path)] in pack order."""
    resolved_root = repo_root.resolve()

    def resolve_in_repo(rel: Path) -> str:
        absolute = (resolved_root / rel).resolve()
        return str(absolute.relative_to(resolved_root)).replace("\\", "/")

    sources: list[tuple[str, str]] = []
    for role, rel in FIXED_SOURCES:
        sources.append((role, rel))

    manifest_rel = Path(MANIFEST_PATH)
    manifest_path = resolved_root / manifest_rel
    if not manifest_path.is_file():
        raise ValueError(f"manifest not found: {manifest_path}")
    data = parse_manifest_yaml(manifest_path.read_text(encoding="utf-8"))

    manifest_dir = manifest_rel.parent
    always_load = data.get("always_load") or []
    if not isinstance(always_load, list):
        raise ValueError("manifest always_load is not a list")
    for item in always_load:
        sources.append((f"always_load:{item}", resolve_in_repo(manifest_dir / item)))

    axes = data.get("axes") or {}
    paper_type = axes.get("paper_type") or {}
    values = paper_type.get("values") or {}
    if not isinstance(values, dict):
        raise ValueError("manifest paper_type values is not a mapping")
    for lens in sorted(values):
        sources.append((f"lens:{lens}", resolve_in_repo(manifest_dir / values[lens])))

    references = data.get("references") or {}
    on_demand = (references.get("on_demand") or []) if isinstance(references, dict) else []
    if not isinstance(on_demand, list):
        raise ValueError("manifest on_demand is not a list")
    for entry in on_demand:
        if isinstance(entry, dict):
            item = entry.get("path")
        else:
            item = entry
        if not item:
            continue
        sources.append((f"reference:{item}", resolve_in_repo(manifest_dir / item)))

    return sources


def build_pack(repo_root: Path) -> tuple[str, list[dict[str, str]]]:
    sources = collect_sources(repo_root)
    manifest_records: list[dict[str, str]] = []
    sections: list[str] = ["# Processor Pack\n"]
    for role, rel in sources:
        path = repo_root / rel
        if not path.is_file():
            raise ValueError(f"source missing for {role}: {path}")
        text = path.read_text(encoding="utf-8").strip()
        manifest_records.append(
            {"role": role, "path": rel, "sha256": sha256_file(path)}
        )
        sections.append(f"## {role}\n\n{text}\n")
    pack = "\n".join(sections).rstrip() + "\n"
    return pack, manifest_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build or verify the wiki-processor context pack."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.expanduser().resolve()
    if not repo_root.is_dir():
        print(f"ERROR: --repo-root is not a directory: {repo_root}", file=sys.stderr)
        return 2

    if args.verify:
        if not args.output or not args.manifest:
            print("ERROR: --verify requires --output and --manifest.", file=sys.stderr)
            return 2
        output = args.output.expanduser().resolve()
        manifest_path = args.manifest.expanduser().resolve()
        if not output.is_file() or not manifest_path.is_file():
            print("ERROR: --verify requires existing pack and manifest files.", file=sys.stderr)
            return 2
        try:
            stored = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"ERROR: unable to load manifest: {exc}", file=sys.stderr)
            return 2
        try:
            pack, records = build_pack(repo_root)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        failures: list[str] = []
        stored_sources = {row["role"]: row for row in stored.get("sources", [])}
        for row in records:
            other = stored_sources.get(row["role"])
            if not other:
                failures.append(f"missing source record for {row['role']}")
                continue
            if other.get("path") != row["path"] or other.get("sha256") != row["sha256"]:
                failures.append(
                    f"source changed: {row['role']} "
                    f"(stored {other.get('sha256', '?')[:12]} != current {row['sha256'][:12]})"
                )
        pack_sha = hashlib.sha256(pack.encode("utf-8")).hexdigest()
        if stored.get("pack_sha256") != pack_sha:
            failures.append("pack content differs from manifest pack_sha256")
        if failures:
            print("VERIFY FAIL:", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1
        print("VERIFY OK: pack matches all pinned sources.")
        return 0

    if not args.output:
        print("ERROR: --output is required when not verifying.", file=sys.stderr)
        return 2
    try:
        pack, records = build_pack(repo_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(pack, encoding="utf-8")
    pack_sha = hashlib.sha256(pack.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pack_sha256": pack_sha,
        "sources": records,
    }
    print(f"Wrote processor pack: {output} ({len(records)} sources, sha256={pack_sha[:12]})")
    if args.manifest:
        manifest_path = args.manifest.expanduser().resolve()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote pack manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
