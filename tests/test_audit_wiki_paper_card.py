#!/usr/bin/env python3
"""Regression tests for the wiki paper-card audit wrapper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_wiki_paper_card.py"
SPEC = importlib.util.spec_from_file_location("audit_wiki_paper_card", SCRIPT_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def valid_card() -> str:
    sections = []
    for number in range(1, 17):
        section_text = (
            "**问题情境。** Placeholder context.\n\n**核心研究问句。** Can the claim be tested?"
            if number == 3
            else "Placeholder text."
            if number != 16
            else "核心假设：可以证伪。验证方式：对照实验。可能失败：假设错误。"
        )
        sections.append(f"## {number:02d}. Section {number}\n\n{section_text}\n")
    return (
        "---\n"
        "tags: [source, paper]\n"
        'source_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"\n'
        'arxiv: ""\n'
        'authors: "Test Author"\n'
        'published: "2026"\n'
        'venue: "Test Venue"\n'
        "status: stub\n"
        "---\n\n"
        "# Test Paper\n\n"
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


def make_wiki_root(root: Path) -> Path:
    wiki = root / "wiki"
    for directory in ("topics", "sources"):
        (wiki / directory).mkdir(parents=True)
    (wiki / "index.md").write_text("# Index\n", encoding="utf-8")
    (wiki / "log.md").write_text("# Log\n", encoding="utf-8")
    return root


class WikiAuditTests(unittest.TestCase):
    def test_valid_card_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = AUDIT.audit(valid_card(), make_wiki_root(Path(directory)))
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_missing_section_fails(self) -> None:
        card = valid_card().replace("## 09. Section 9\n", "")
        report = AUDIT.audit(card, None)
        self.assertGreater(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "fail")

    def test_missing_tags_fail(self) -> None:
        card = valid_card().replace("tags: [source, paper]", "tags: [source]")
        report = AUDIT.audit(card, None)
        self.assertTrue(any(item["code"] == "tags" for item in report["findings"]))

    def test_fragmented_narrative_section_fails(self) -> None:
        card = valid_card().replace(
            "## 03. Section 3\n\n**问题情境。** Placeholder context.\n\n**核心研究问句。** Can the claim be tested?",
            "## 03. Section 3\n\n- 问题：上下文冲突。\n- 精确问题：能否消解？\n- 意义：提高准确率。",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"]
            if item["code"] == "reader_facing_narrative"
        )
        self.assertEqual(finding["level"], "error")

    def test_duplicate_precise_question_label_fails(self) -> None:
        card = valid_card().replace(
            "**核心研究问句。** Can the claim be tested?",
            "**核心研究问句。** Can the claim be tested?\n\n**精确问题。** Can the claim be tested?",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"]
            if item["code"] == "research_question_structure"
        )
        self.assertEqual(finding["level"], "error")

    def test_internal_reader_marker_fails(self) -> None:
        card = valid_card().replace(
            "## 04. Section 4\n\nPlaceholder text.",
            "## 04. Section 4\n\n"
            "[Paper-framed; external verification not performed] Placeholder text.",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"]
            if item["code"] == "internal_reader_marker"
        )
        self.assertEqual(finding["level"], "error")

    def test_table_requires_reader_facing_introduction(self) -> None:
        card = valid_card().replace(
            "## 05. Section 5\n\nPlaceholder text.",
            "## 05. Section 5\n\n| 痛点 | 表现 |\n|---|---|\n| 冲突 | 失败 |",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"] if item["code"] == "table_context"
        )
        self.assertEqual(finding["level"], "error")
        self.assertIn("05", finding["details"]["sections"])

    def test_formula_field_bullets_fail(self) -> None:
        card = valid_card().replace(
            "## 09. Section 9\n\nPlaceholder text.",
            "## 09. Section 9\n\n$$x = y$$\n\n- 符号：x 是输出。\n- 目的：计算结果。\n- 直觉：保持一致。",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"]
            if item["code"] == "formula_explanation"
        )
        self.assertEqual(finding["level"], "error")

    def test_research_idea_field_list_fails(self) -> None:
        card = valid_card().replace(
            "核心假设：可以证伪。验证方式：对照实验。可能失败：假设错误。",
            "- 来源观察：现有方法不稳定。\n- 核心假设：可以证伪。\n- 验证方式：对照实验。\n- 可能失败：假设错误。",
        )
        report = AUDIT.audit(card, None)
        finding = next(
            item for item in report["findings"]
            if item["code"] == "research_idea_narrative"
        )
        self.assertEqual(finding["level"], "error")

    def test_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_wiki_root(root)
            card = root / "paper-card.md"
            report_path = root / "audit-report.json"
            card.write_text(valid_card(), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--card",
                    str(card),
                    "--wiki-root",
                    str(root),
                    "--report",
                    str(report_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
