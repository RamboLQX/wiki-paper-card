#!/usr/bin/env python3
"""Regression tests for deterministic Paper Card finalization."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "finalize_paper_card.py"
SPEC = importlib.util.spec_from_file_location("finalize_paper_card", SCRIPT_PATH)
assert SPEC and SPEC.loader
FINALIZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINALIZE)
ROOT = Path(__file__).resolve().parents[1]


def finalizable_card() -> str:
    sections = []
    for number in range(1, 17):
        if number == 3:
            body = (
                "**问题情境。** 现有方法在该任务上仍有明确限制。\n\n"
                "**核心研究问句。** 该方法能否在对照实验中改善这一限制？"
            )
        elif number == 16:
            body = "核心假设：可证伪。验证方式：对照实验。可能失败：假设错误。"
        else:
            body = "Test text."
        if number == 1:
            body += (
                "\n\n### 术语规范表\n\n"
                "| 规范术语 | 首次定义或中文释义 | 原文变体 | 使用决策 | 来源 |\n"
                "|---|---|---|---|---|\n"
                "| Test method | A test method | 未发现显著变体 | 统一使用 Test method | [Paper: PDF p. 1] |"
            )
        sections.append(f"## {number:02d}. Section {number}\n\n{body}\n")
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


def make_wiki_root(root: Path) -> None:
    wiki = root / "wiki"
    for name in ("topics", "sources"):
        (wiki / name).mkdir(parents=True)
    (wiki / "index.md").write_text("# Index\n", encoding="utf-8")
    (wiki / "log.md").write_text("# Log\n", encoding="utf-8")


class FinalizePaperCardTests(unittest.TestCase):
    def test_formula_audit_rejects_raw_math_in_table(self) -> None:
        card = (
            "| 公式 | 含义 |\n"
            "|---|---|\n"
            "| x_i = a_i + b_i | 未标记数学 |\n"
        )
        report = FINALIZE.audit_formulas(card)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertIn("formula_table_contract", {
            item["code"] for item in report["findings"]
        })

    def test_formula_audit_rejects_display_math_in_table(self) -> None:
        card = (
            "| 公式 | 含义 |\n"
            "|---|---|\n"
            "| $$x_i$$ | 块公式 |\n"
        )
        report = FINALIZE.audit_formulas(card)
        self.assertTrue(any(item["code"] == "block_math_in_table" for item in report["findings"]))

    def test_formula_audit_passes_math_outside_tables(self) -> None:
        card = "## 09. 关键公式与符号\n\n$$x_i = a_i + b_i$$\n\n| 编号 | 含义 |\n|---|---|\n| Eq.1 | 无公式内容 |\n"
        report = FINALIZE.audit_formulas(card)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_formula_audit_allows_plain_identifier_with_underscore_in_table(self) -> None:
        card = (
            "| 数据集 | 类型 |\n"
            "|---|---|\n"
            "| COSE_KRE / ECARE_KRE × LLaMA-2-7B-Chat | 多项选择 |\n"
        )
        report = FINALIZE.audit_formulas(card)
        self.assertEqual(report["summary"]["errors"], 0)

    def test_strip_section_wrappers(self) -> None:
        card = "# Sections 01-10: Test\n\n> Source coverage: Full paper\n\n## 01. 基本信息\n"
        normalized = FINALIZE.strip_wrappers(card)
        self.assertNotIn("Sections 01-10", normalized)
        self.assertIn("## 01. 基本信息", normalized)

    def test_normalize_frontmatter_adds_missing_fields(self) -> None:
        card = "# Test Paper\n\n> Locator mode: page-grounded\n\n## 01. 基本信息\n"
        bundle = {"source_sha256": "a" * 64}
        normalized = FINALIZE.normalize_frontmatter(card, bundle)
        self.assertTrue(normalized.startswith("---\n"))
        self.assertIn('tags: [source, paper]', normalized)
        self.assertIn(f'source_sha256: "{"a" * 64}"', normalized)
        self.assertIn('status: "stub"', normalized)
        self.assertIn("# Test Paper", normalized)

    def test_normalize_frontmatter_preserves_existing_metadata(self) -> None:
        card = (
            "---\n"
            'tags: [source, paper]\n'
            'created: "2026-01-02"\n'
            'arxiv: "2406.18406"\n'
            "status: stub\n"
            "---\n\n"
            "# Test Paper\n"
        )
        bundle = {"source_sha256": "b" * 64}
        normalized = FINALIZE.normalize_frontmatter(card, bundle)
        self.assertIn('created: "2026-01-02"', normalized)
        self.assertIn('arxiv: "2406.18406"', normalized)
        self.assertIn(f'source_sha256: "{"b" * 64}"', normalized)

    def test_normalize_section_headings_adds_zero_padding_and_dot(self) -> None:
        card = "## 1 基本信息\n\n## 16 研究想法\n"
        normalized = FINALIZE.normalize_section_headings(card)
        self.assertIn("## 01. 基本信息", normalized)
        self.assertIn("## 16. 研究想法", normalized)

    def test_supplementary_evidence_is_not_required_in_card(self) -> None:
        bundle = {
            "schema_version": "1.0",
            "pages": [
                {"pdf_page": 1, "text": "Figure 1 is described in the body."},
                {"pdf_page": 2, "text": "Figure 3 is appendix-only."},
            ],
            "sections": [{"title": "Appendix", "pdf_page": 2}],
            "evidence_inventory": {
                "figures": [
                    {"id": "Figure 1", "pdf_page": 1},
                    {"id": "Figure 3", "pdf_page": 2},
                ],
                "tables": [],
                "equations": [],
            },
        }
        scope = FINALIZE.build_evidence_scope(bundle)
        roles = {item["id"]: item["role"] for item in scope["items"]}
        self.assertEqual(roles["Figure 1"], "main")
        self.assertEqual(roles["Figure 3"], "supplementary")

        filtered = FINALIZE.filtered_audit_bundle(bundle, scope)
        self.assertEqual(
            [item["id"] for item in filtered["evidence_inventory"]["figures"]],
            ["Figure 1"],
        )

    def test_appendix_item_cited_across_line_break_is_main(self) -> None:
        bundle = {
            "schema_version": "1.0",
            "pages": [
                {"pdf_page": 1, "text": "The ablation uses Figure\n13."},
                {"pdf_page": 2, "text": "Figure 13 is in the appendix."},
            ],
            "sections": [{"title": "Appendix", "pdf_page": 2}],
            "evidence_inventory": {
                "figures": [{"id": "Figure 13", "pdf_page": 2}],
                "tables": [],
                "equations": [],
            },
        }
        scope = FINALIZE.build_evidence_scope(bundle)
        self.assertEqual(scope["items"][0]["role"], "main")

    def test_visible_evidence_list_is_a_blocker(self) -> None:
        card = (
            "# Test\n\n"
            "## 10. 实验设计与证据链\n\n"
            "### 附录证据覆盖清单（仅编号与来源指针）\n\n"
            "- Figure 7 [Paper: PDF p. 17]\n"
            "**证据清单：**\n"
        )
        report = FINALIZE.audit_visible_evidence_lists(card)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertTrue(any(item["code"] == "visible_evidence_list" for item in report["findings"]))
        self.assertEqual(report["summary"]["errors"], 2)

    def test_cli_reports_missing_evidence_coverage_as_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            card = root / "paper-card.md"
            output = root / "final-paper-card.md"
            bundle_path = root / "source_bundle.json"
            card.write_text(finalizable_card(), encoding="utf-8")
            bundle_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "evidence_inventory": {
                            "figures": [
                                {
                                    "id": "Figure 2",
                                    "caption": "Test figure",
                                    "pdf_page": 2,
                                }
                            ],
                            "tables": [],
                            "equations": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            make_wiki_root(root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--card",
                    str(card),
                    "--bundle",
                    str(bundle_path),
                    "--repo-root",
                    str(ROOT),
                    "--wiki-root",
                    str(root),
                    "--output",
                    str(output),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn("机械补充证据索引", output.read_text(encoding="utf-8"))
            upstream = json.loads((root / "audit-report.json").read_text(encoding="utf-8"))
            wiki = json.loads((root / "wiki-audit-report.json").read_text(encoding="utf-8"))
            self.assertGreater(upstream["summary"]["errors"], 0)
            self.assertEqual(wiki["summary"]["errors"], 0)


    def test_raw_html_lint_blocks_bare_tag(self) -> None:
        card = finalizable_card().replace(
            "Test text.", "对比 <image> token 与文本 token [Paper: PDF p. 8]"
        )
        report = FINALIZE.audit_raw_html(card)
        self.assertEqual(report["summary"]["status"], "fail")
        self.assertTrue(
            any(item["code"] == "raw_html_tag" for item in report["findings"])
        )

    def test_raw_html_lint_allows_code_span_and_math(self) -> None:
        card = finalizable_card().replace(
            "Test text.", "对比 `<image>` token；公式 $y_{<i}$ 与 $$x_{<n}$$"
        )
        report = FINALIZE.audit_raw_html(card)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_raw_html_lint_ignores_unclosed_angle(self) -> None:
        # `y_<i` has no closing `>` and never triggered Obsidian's HTML region.
        card = finalizable_card().replace("Test text.", "符号 y_<i 为第 i 步生成")
        report = FINALIZE.audit_raw_html(card)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_raw_html_lint_blocks_closing_tag_and_comment(self) -> None:
        card = finalizable_card().replace(
            "Test text.", "结束标记 </image> 与注释 <!-- x -->"
        )
        report = FINALIZE.audit_raw_html(card)
        self.assertEqual(report["summary"]["status"], "fail")
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("raw_html_tag", codes)
        self.assertIn("raw_html_comment", codes)


if __name__ == "__main__":
    unittest.main()
