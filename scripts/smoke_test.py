#!/usr/bin/env python3
"""Smoke-test the template, card contract, and wiki audit wrapper."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build_card() -> str:
    sections = []
    for number in range(1, 17):
        if number == 16:
            body = "核心假设：可证伪。验证方式：对照实验。可能失败：假设错误。"
        else:
            body = "Placeholder evidence-backed text."
        sections.append(f"## {number:02d}. Section {number}\n\n{body}\n")
    return (
        "---\n"
        "tags: [source, paper]\n"
        'source_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"\n'
        'arxiv: ""\n'
        'authors: "Smoke Author"\n'
        'published: "2026"\n'
        'venue: "Smoke Venue"\n'
        "status: stub\n"
        "---\n\n"
        "# Smoke Paper\n\n"
        "> Source coverage: Full paper\n"
        "> Extraction confidence: High\n"
        "> Locator mode: page-grounded\n"
        "> Primary analytical lens: methods\n"
        "> Secondary analytical lens: None\n"
        "> Context verification: Paper-only\n"
        "> Card completeness: Complete relative to supplied source\n\n"
        "[Paper: PDF p. 1, Figure 1]\n\n"
        + "\n".join(sections)
    )


def build_digest() -> dict:
    return {
        "schema_version": "3.0",
        "paper": {
            "title": "Smoke Paper",
            "source_sha256": "a" * 64,
            "source_ref": "wiki/sources/smoke.md",
            "locator_mode": "page-grounded",
            "paper_type": "methods",
        },
        "analysis": {
            "one_sentence_summary": "A smoke paper.",
            "problem": "A smoke problem.",
            "method": "A smoke method.",
            "key_results": [],
            "limitations": [],
            "critical_observations": [],
            "open_questions": [],
        },
        "topic_seeds": [],
    }


def build_link_plan() -> dict:
    return {
        "schema_version": "2.0",
        "batch": {
            "source_pages": [
                {
                    "source_ref": "wiki/sources/smoke.md",
                    "work_dir": "work/smoke",
                    "title": "Smoke Paper",
                }
            ]
        },
        "topic_actions": [],
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(ROOT / "template", root, dirs_exist_ok=True)
        required_dirs = [
            root / "raw" / "papers",
            root / "wiki" / "topics",
            root / "wiki" / "sources",
        ]
        missing_dirs = [str(path) for path in required_dirs if not path.is_dir()]
        if missing_dirs:
            print(f"ERROR: template is missing required directories: {missing_dirs}")
            return 2
        card = root / "wiki" / "sources" / "smoke.md"
        card.write_text(build_card(), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_wiki_paper_card.py"),
                "--card",
                str(card),
                "--wiki-root",
                str(root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode:
            return result.returncode

        work = root / "work" / "smoke"
        work.mkdir(parents=True)
        card = root / "wiki" / "sources" / "smoke.md"
        (work / "paper-card.md").write_text(card.read_text(encoding="utf-8"), encoding="utf-8")
        digest = work / "paper-digest.json"
        plan = work / "link-plan.json"
        digest.write_text(
            json.dumps(build_digest(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        plan.write_text(
            json.dumps(build_link_plan(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        for script, argument, value in (
            ("audit_paper_digest.py", "--digest", digest),
            ("audit_link_plan.py", "--plan", plan),
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / script),
                    argument,
                    str(value),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode:
                return result.returncode

        publish_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "publish_wiki.py"),
                "--plan",
                str(plan),
                "--wiki-root",
                str(root),
                "--report",
                str(work / "publish-report.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        print(publish_result.stdout)
        if publish_result.stderr:
            print(publish_result.stderr, file=sys.stderr)
        if publish_result.returncode:
            return publish_result.returncode
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
