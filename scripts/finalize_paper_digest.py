#!/usr/bin/env python3
"""Inject only deterministic paper identity fields into a processor digest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from batch_manifest import ManifestError, entry_for_work_dir, load_manifest, relative_posix
except ModuleNotFoundError:  # Imported as scripts.finalize_paper_digest in tests.
    from scripts.batch_manifest import ManifestError, entry_for_work_dir, load_manifest, relative_posix


def finalize_digest(digest: Any, expected: dict[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(digest, dict):
        raise ManifestError("paper digest must be a JSON object")
    paper = digest.get("paper")
    if not isinstance(paper, dict):
        raise ManifestError("paper digest must already define paper as an object")
    topic_seeds = digest.get("topic_seeds")
    if not isinstance(topic_seeds, list) or any(not isinstance(seed, dict) for seed in topic_seeds):
        raise ManifestError("paper digest must already define topic_seeds as a list of objects")

    changes: list[dict[str, Any]] = []

    def replace(container: dict[str, Any], field: str, value: Any, path: str) -> None:
        previous = container.get(field)
        if previous != value:
            changes.append({"field": path, "before": previous, "after": value})
            container[field] = value

    replace(paper, "source_sha256", expected["source_sha256"], "paper.source_sha256")
    replace(paper, "source_ref", expected["source_ref"], "paper.source_ref")
    for index, seed in enumerate(topic_seeds):
        replace(seed, "papers", [expected["source_ref"]], f"topic_seeds[{index}].papers")
    return digest, changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize deterministic fields in paper-digest.json.")
    parser.add_argument("--digest", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--wiki-root", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    digest_path = args.digest.expanduser().resolve()
    wiki_root = args.wiki_root.expanduser().resolve()
    if not digest_path.is_file():
        print("ERROR: --digest must point to an existing file.", file=sys.stderr)
        return 2
    try:
        manifest = load_manifest(args.manifest.expanduser().resolve())
        work_dir = f"work/{relative_posix(digest_path.parent, wiki_root / 'work', 'digest work_dir')}"
        expected = entry_for_work_dir(manifest, work_dir)
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        finalized, changes = finalize_digest(digest, expected)
    except (ManifestError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    digest_path.write_text(json.dumps(finalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": "1.0",
        "status": "changed" if changes else "unchanged",
        "work_dir": expected["work_dir"],
        "allowed_fields": ["paper.source_sha256", "paper.source_ref", "topic_seeds[*].papers"],
        "changes": changes,
    }
    report_path = (
        args.report.expanduser().resolve()
        if args.report
        else digest_path.with_name("paper-digest-finalize-report.json")
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Finalized paper digest: {digest_path}")
    print(f"Deterministic field changes: {len(changes)}")
    print(f"Wrote digest finalize report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
