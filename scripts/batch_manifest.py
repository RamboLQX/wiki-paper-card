#!/usr/bin/env python3
"""Build and validate deterministic batch identity metadata from source bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """Raised when batch identity metadata is incomplete or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_posix(path: Path, root: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ManifestError(f"{label} must stay under {root.resolve()}: {path.resolve()}") from exc


def canonical_source_ref(source_path: Path, wiki_root: Path) -> str:
    raw_relative = relative_posix(source_path, wiki_root / "raw", "source_path")
    return (Path("wiki/sources") / Path(raw_relative)).with_suffix(".md").as_posix()


def validate_entry(entry: Any, index: int) -> dict[str, str]:
    if not isinstance(entry, dict):
        raise ManifestError(f"papers[{index}] must be an object")
    result: dict[str, str] = {}
    for field in ("source_path", "source_sha256", "source_ref", "work_dir"):
        value = entry.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ManifestError(f"papers[{index}].{field} must be a non-empty string")
        result[field] = value.strip()
    if not SHA256_RE.fullmatch(result["source_sha256"]):
        raise ManifestError(f"papers[{index}].source_sha256 must be 64 lowercase hex characters")
    if not result["source_path"].startswith("raw/"):
        raise ManifestError(f"papers[{index}].source_path must stay under raw/")
    if not result["source_ref"].startswith("wiki/sources/"):
        raise ManifestError(f"papers[{index}].source_ref must stay under wiki/sources/")
    if not result["work_dir"].startswith("work/"):
        raise ManifestError(f"papers[{index}].work_dir must stay under work/")
    for field in ("source_path", "source_ref", "work_dir"):
        parts = Path(result[field]).parts
        if Path(result[field]).is_absolute() or ".." in parts:
            raise ManifestError(f"papers[{index}].{field} must be a safe relative path")
    expected_ref = (Path("wiki/sources") / Path(result["source_path"]).relative_to("raw")).with_suffix(
        ".md"
    ).as_posix()
    if result["source_ref"] != expected_ref:
        raise ManifestError(
            f"papers[{index}].source_ref must mirror source_path: expected {expected_ref}"
        )
    return result


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ManifestError("batch manifest must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"unsupported batch manifest schema: {manifest.get('schema_version')!r}")
    papers = manifest.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ManifestError("batch manifest must contain at least one paper")

    normalized = [validate_entry(entry, index) for index, entry in enumerate(papers)]
    for field in ("source_path", "source_ref", "work_dir"):
        values = [entry[field] for entry in normalized]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise ManifestError(f"duplicate {field}: {', '.join(duplicates)}")
    work_root = str(manifest.get("work_root", "")).strip()
    if not work_root.startswith("work/") or Path(work_root).is_absolute() or ".." in Path(work_root).parts:
        raise ManifestError("batch manifest work_root must be a safe path under work/")
    return {
        "schema_version": SCHEMA_VERSION,
        "work_root": work_root,
        "paper_count": len(normalized),
        "papers": normalized,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"unable to read batch manifest: {exc}") from exc
    return validate_manifest(raw)


def entry_for_work_dir(manifest: dict[str, Any], work_dir: str) -> dict[str, str]:
    matches = [entry for entry in manifest["papers"] if entry["work_dir"] == work_dir]
    if len(matches) != 1:
        raise ManifestError(f"manifest has no unique paper for work_dir: {work_dir}")
    return matches[0]


def build_manifest(wiki_root: Path, work_root: Path) -> dict[str, Any]:
    wiki_root = wiki_root.expanduser().resolve()
    work_root = work_root.expanduser().resolve()
    if not wiki_root.is_dir():
        raise ManifestError(f"wiki root does not exist: {wiki_root}")
    if not work_root.is_dir():
        raise ManifestError(f"work root does not exist: {work_root}")
    relative_work_root = relative_posix(work_root, wiki_root / "work", "work_root")

    bundle_paths = sorted(work_root.rglob("source_bundle.json"))
    if not bundle_paths:
        raise ManifestError(f"no source_bundle.json found under {work_root}")

    papers: list[dict[str, str]] = []
    for bundle_path in bundle_paths:
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ManifestError(f"unable to read {bundle_path}: {exc}") from exc
        if not isinstance(bundle, dict):
            raise ManifestError(f"source bundle must be an object: {bundle_path}")
        source_value = bundle.get("source_path")
        bundle_sha = bundle.get("source_sha256")
        if not isinstance(source_value, str) or not source_value.strip():
            raise ManifestError(f"source_path is missing: {bundle_path}")
        if not isinstance(bundle_sha, str) or not SHA256_RE.fullmatch(bundle_sha.strip()):
            raise ManifestError(f"source_sha256 is invalid: {bundle_path}")
        source_path = Path(source_value).expanduser().resolve()
        if not source_path.is_file():
            raise ManifestError(f"source file does not exist: {source_path}")
        actual_sha = sha256_file(source_path)
        if actual_sha != bundle_sha.strip():
            raise ManifestError(
                f"source SHA-256 changed after preparation: {source_path} "
                f"(bundle={bundle_sha.strip()}, actual={actual_sha})"
            )
        papers.append(
            {
                "source_path": f"raw/{relative_posix(source_path, wiki_root / 'raw', 'source_path')}",
                "source_sha256": actual_sha,
                "source_ref": canonical_source_ref(source_path, wiki_root),
                "work_dir": f"work/{relative_posix(bundle_path.parent, wiki_root / 'work', 'work_dir')}",
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "work_root": f"work/{relative_work_root}",
        "paper_count": len(papers),
        "papers": sorted(papers, key=lambda entry: entry["work_dir"]),
    }
    return validate_manifest(manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build batch-manifest.json from prepared source_bundle.json files."
    )
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest = build_manifest(args.wiki_root, args.work_root)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote batch manifest: {output}")
    print(f"Papers: {manifest['paper_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
