#!/usr/bin/env python3
"""Report per-paper processor completion from the filesystem."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


WORKFLOW_MODES = ("card-only", "wiki-topic", "wiki-full")
REQUIRED_FILES = {
    "card-only": ("paper-card.md",),
    "wiki-topic": ("paper-card.md", "paper-digest.json"),
    "wiki-full": ("paper-card.md", "paper-digest.json"),
}
MARKER_FILES = ("source_bundle.json", "paper-card.md", "paper-digest.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report which paper work directories are missing mode-required outputs."
    )
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=WORKFLOW_MODES,
        default="wiki-full",
        help="Completion contract to apply (default: wiki-full).",
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def paper_dirs(work_dir: Path) -> list[Path]:
    if not work_dir.is_dir():
        return []
    return sorted(
        child
        for child in work_dir.iterdir()
        if child.is_dir() and any((child / marker).is_file() for marker in MARKER_FILES)
    )


def paper_status(paper_dir: Path, required_files: tuple[str, ...]) -> dict[str, object]:
    missing = [
        name
        for name in required_files
        if not (paper_dir / name).is_file() or (paper_dir / name).stat().st_size == 0
    ]
    return {
        "name": paper_dir.name,
        "dir": str(paper_dir),
        "complete": not missing,
        "missing": missing,
    }


def main() -> int:
    args = parse_args()
    work_dir = args.work_dir.expanduser().resolve()
    if not work_dir.is_dir():
        print(f"ERROR: --work-dir must point to an existing directory: {work_dir}", file=sys.stderr)
        return 2

    required_files = REQUIRED_FILES[args.mode]
    papers = [paper_status(path, required_files) for path in paper_dirs(work_dir)]
    if not papers:
        print("No paper work directories found under the batch work directory.", file=sys.stderr)
        return 1

    for paper in papers:
        if paper["complete"]:
            print(f"- {paper['name']}: complete")
        else:
            print(f"- {paper['name']}: INCOMPLETE (missing {', '.join(paper['missing'])})")

    total = len(papers)
    complete = sum(1 for paper in papers if paper["complete"])
    report = {
        "schema_version": "1.0",
        "workflow_mode": args.mode,
        "required_files": list(required_files),
        "papers": papers,
        "summary": {
            "total": total,
            "complete": complete,
            "incomplete": total - complete,
        },
    }
    print(f"summary: {complete}/{total} complete")

    if args.report:
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote status report: {output}")

    return 0 if complete == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
