#!/usr/bin/env python3
"""Regression tests for deterministic wiki publication."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "publish_wiki.py"
SPEC = importlib.util.spec_from_file_location("publish_wiki", SCRIPT_PATH)
assert SPEC and SPEC.loader
PUBLISH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PUBLISH)


def source_card(title: str, source_ref: str) -> str:
    sections = []
    for number in range(1, 17):
        body = (
            "核心假设：可证伪。验证方式：对照实验。可能失败：假设错误。"
            if number == 16
            else "Test text."
        )
        sections.append(f"## {number:02d}. Section {number}\n\n{body}\n")
    return (
        "---\n"
        "tags: [source, paper]\n"
        'created: "2026-01-01"\n'
        'updated: "2026-01-01"\n'
        'source_sha256: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"\n'
        'arxiv: ""\n'
        'authors: "Test Author"\n'
        'published: "2026"\n'
        'venue: "Test Venue"\n'
        "status: stub\n"
        "---\n\n"
        f"# {title}\n\n"
        "> Source coverage: Full paper\n"
        "> Extraction confidence: High\n"
        "> Locator mode: page-grounded\n"
        "> Primary analytical lens: methods\n"
        "> Secondary analytical lens: None\n"
        "> Context verification: Paper-only\n"
        "> Card completeness: Complete relative to supplied source\n\n"
        f"[Paper: PDF p. 1]\n\n"
        + "\n".join(sections)
    )


def valid_plan() -> dict:
    return {
        "schema_version": "1.0",
        "batch": {
            "source_pages": [
                {
                    "source_ref": "wiki/sources/a.md",
                    "work_dir": "work/a",
                    "title": "Paper A",
                },
                {
                    "source_ref": "wiki/sources/b.md",
                    "work_dir": "work/b",
                    "title": "Paper B",
                },
            ]
        },
        "hub_actions": [
            {
                "action": "create_hub",
                "id": "hub-1",
                "name": "Shared Concept",
                "kind": "concept",
                "tier": "L2",
                "aliases": ["concept"],
                "definition": "A concept supported by both papers.",
                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "connect_existing": False,
                "existing_page": None,
                "evidence": [
                    {
                        "source_ref": "wiki/sources/a.md",
                        "pointer": "[Paper: PDF p. 3, Fig. 1]",
                        "claim": "Paper A reports the concept.",
                    },
                    {
                        "source_ref": "wiki/sources/b.md",
                        "pointer": "[Paper: PDF p. 4, Fig. 2]",
                        "claim": "Paper B reports the concept.",
                    },
                ],
                "relations": [],
                "contradictions": [],
                "open_questions": ["Open question"],
            }
        ],
        "topic_actions": [
            {
                "action": "create_topic",
                "id": "topic-1",
                "name": "Shared Topic",
                "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "summary": "Compare the two approaches.",
                "comparisons": [],
                "contradictions": [],
                "open_questions": ["Topic question"],
                "research_gaps": ["Missing benchmark"],
                "existing_page": None,
            }
        ],
    }


def prepare_vault(root: Path) -> None:
    for directory in (
        "wiki/entities",
        "wiki/concepts",
        "wiki/topics",
        "wiki/sources",
        "work/a",
        "work/b",
    ):
        (root / directory).mkdir(parents=True)
    for name, title in (("a", "Paper A"), ("b", "Paper B")):
        (root / "work" / name / "paper-card.md").write_text(
            source_card(title, f"wiki/sources/{name}.md"),
            encoding="utf-8",
        )
        (root / "work" / name / "paper-digest.json").write_text(
            json.dumps(
                {
                    "analysis": {
                        "one_sentence_summary": f"{title} summary.",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    (root / "wiki" / "index.md").write_text(
        "# Wiki 索引\n\n## 实体\n## 概念\n## 主题\n## 来源\n## 元页面\n",
        encoding="utf-8",
    )
    (root / "wiki" / "log.md").write_text("# 操作日志\n", encoding="utf-8")


class PublishWikiTests(unittest.TestCase):
    def test_source_page_removes_protocol_header(self) -> None:
        card = source_card("Paper A", "wiki/sources/a.md")
        page = {
            "source_ref": "wiki/sources/a.md",
            "title": "Paper A",
        }
        text = PUBLISH.source_page_text(page, card, None, "2026-08-16")
        self.assertNotIn("> Source coverage:", text)
        self.assertIn("## 01. Section 1", text)
        self.assertIn("## 16. Section 16", text)

    def test_source_page_update_preserves_existing_h1(self) -> None:
        card = source_card("Paper A", "wiki/sources/a.md")
        page = {
            "source_ref": "wiki/sources/a.md",
            "title": "English replacement title",
        }
        existing = (
            "---\n"
            'tags: [source, paper]\n'
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            'source_sha256: "a"\n'
            'arxiv: ""\n'
            'authors: ""\n'
            'published: ""\n'
            'venue: ""\n'
            'status: "stub"\n'
            "---\n\n"
            "# 中文标题\n\n"
            "## 01. Section 1\n"
        )
        text = PUBLISH.source_page_text(page, card, existing, "2026-08-16")
        self.assertIn("# 中文标题", text)
        self.assertNotIn("# English replacement title", text)

    def test_flat_comparisons_use_source_wikilinks(self) -> None:
        lines = PUBLISH.render_flat_comparisons(
            [
                {
                    "source_ref": "wiki/sources/a.md",
                    "paper": "Paper A",
                    "method": "Method A",
                    "granularity": "token",
                    "main_result": "result",
                    "boundary": "boundary",
                    "pointer": "[Paper: PDF p. 1]",
                }
            ],
            {"wiki/sources/a.md": "Paper A"},
        )
        self.assertIn("[[a|Paper A]]", lines[2])

    def test_topic_page_lists_related_hubs(self) -> None:
        text = PUBLISH.topic_page_text(
            valid_plan()["topic_actions"][0],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
            ["Shared Concept"],
        )
        self.assertIn("[[Shared Concept|Shared Concept]]", text)

    def test_cli_publishes_pages_index_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--plan",
                    str(plan_path),
                    "--wiki-root",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "wiki" / "sources" / "a.md").is_file())
            self.assertTrue((root / "wiki" / "concepts" / "Shared Concept.md").is_file())
            self.assertTrue((root / "wiki" / "topics" / "Shared Topic.md").is_file())
            index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
            source_a = (root / "wiki" / "sources" / "a.md").read_text(encoding="utf-8")
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertIn("[[wiki/sources/a.md|a]]", index)
            self.assertIn("[[wiki/concepts/Shared Concept.md|Shared Concept]]", index)
            self.assertIn("[[Shared Concept|Shared Concept]] - 概念枢纽", source_a)
            self.assertIn("[[Shared Topic|Shared Topic]] - 主题", source_a)
            self.assertIn("[[Shared Concept|Shared Concept]]", topic)
            self.assertIn("ingest | Paper A", log)
            self.assertIn("batch synthesis | Paper A、Paper B", log)

    def test_second_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--plan",
                str(plan_path),
                "--wiki-root",
                str(root),
                "--report",
                str(root / "publish-report.json"),
            ]
            first = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            page = root / "wiki" / "sources" / "a.md"
            original = page.read_text(encoding="utf-8")
            original_index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads((root / "publish-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["writes"], [])
            self.assertEqual(page.read_text(encoding="utf-8"), original)
            self.assertEqual((root / "wiki" / "index.md").read_text(encoding="utf-8"), original_index)

    def test_update_hub_requires_existing_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan = valid_plan()
            plan["hub_actions"][0]["action"] = "update_hub"
            plan["hub_actions"][0]["connect_existing"] = True
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--plan",
                    str(plan_path),
                    "--wiki-root",
                    str(root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Unable to locate existing hub", result.stderr)

    def test_flat_comparisons_render_intervention_granularity(self) -> None:
        lines = PUBLISH.render_flat_comparisons(
            [
                {
                    "paper": "Paper A",
                    "method": "Method A",
                    "intervention_granularity": "token 级解码",
                    "main_result": "result",
                    "boundary": "boundary",
                    "pointer": "[Paper: PDF p. 1]",
                }
            ],
            {},
        )
        self.assertIn("token 级解码", lines[2])

    def test_contradiction_renders_resolution_and_sources(self) -> None:
        lines = PUBLISH.render_contradictions(
            [
                {
                    "position_a": "A claims X.",
                    "position_a_source_ref": "wiki/sources/a.md",
                    "position_a_pointer": "[Paper: PDF p. 1]",
                    "position_b": "B claims Y.",
                    "position_b_source_ref": "wiki/sources/b.md",
                    "position_b_pointer": "[Paper: PDF p. 2]",
                    "resolving_evidence": "A unified benchmark would settle this.",
                }
            ],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
        )
        text = "\n".join(lines)
        self.assertIn("如何解决", text)
        self.assertIn("A unified benchmark would settle this.", text)
        self.assertIn("来源：Paper A", text)
        self.assertIn("证据：[Paper: PDF p. 1]", text)

    def test_topic_page_renders_key_findings(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["key_findings"] = [
            {
                "claim": "Both papers report X.",
                "kind": "consensus",
                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "pointer": "[Paper: PDF p. 1]",
            },
            {
                "claim": "Only A reports Y.",
                "kind": "single",
                "source_refs": ["wiki/sources/a.md"],
                "pointer": "[Paper: PDF p. 2]",
            },
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("共识：Both papers report X.", text)
        self.assertIn("单篇主张：Only A reports Y.", text)

    def test_research_gaps_render_as_bullets(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "缺统一基准",
                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "direction": "统一评测",
                "continuity": "可由未来论文承接",
            }
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("缺统一基准", text)
        self.assertIn("可检验方向：统一评测", text)
        self.assertIn("承接：可由未来论文承接", text)
        self.assertIn("[[a|Paper A]]", text)

    def test_legacy_research_gaps_render_as_list(self) -> None:
        lines = PUBLISH.render_research_gaps(["gap A", "gap B"], {}, None)
        self.assertEqual(lines, ["- gap A", "- gap B"])

    def test_topic_page_uses_short_name_wikilinks(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["key_findings"] = [
            {
                "claim": "X.",
                "kind": "consensus",
                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            }
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
            short_names={"wiki/sources/a.md": "A", "wiki/sources/b.md": "B"},
        )
        self.assertIn("[[a|A]]", text)
        self.assertIn("[[b|B]]", text)

    def test_merge_topic_adds_comparison_row_to_main_table(self) -> None:
        existing = (
            "---\n"
            "tags: [topic]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            '  - "wiki/sources/b.md"\n'
            "aliases:\n"
            'status: "stub"\n'
            "---\n\n"
            "# Shared Topic\n\n"
            "## 概述\n\n"
            "summary.\n\n"
            "## 论文与方法对照\n\n"
            "| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |\n"
            "|---|---|---|---|---|---|\n"
            "| [[a|Paper A]] | Method A | token | result | boundary | [Paper: PDF p. 1] |\n"
            "## 关键发现\n\n"
            "## 争议与不确定\n\n"
            "## 相关实体与概念\n\n"
            "## 开放问题\n\n"
            "## 研究空白与候选方向\n"
        )
        action = {
            "action": "update_topic",
            "id": "topic-1",
            "name": "Shared Topic",
            "papers": ["wiki/sources/c.md"],
            "summary": "New synthesis.",
            "comparisons": [
                {
                    "paper": "Paper C",
                    "method": "Method C",
                    "intervention_granularity": "head",
                    "main_result": "result C",
                    "boundary": "boundary C",
                    "pointer": "[Paper: PDF p. 2]",
                }
            ],
            "key_findings": [
                {
                    "claim": "C adds a finding.",
                    "kind": "single",
                    "source_refs": ["wiki/sources/c.md"],
                    "pointer": "[Paper: PDF p. 2]",
                }
            ],
            "contradictions": [],
            "open_questions": ["New question"],
            "research_gaps": ["New gap"],
            "existing_page": "wiki/topics/Shared Topic.md",
        }
        merged = PUBLISH.merge_topic_page(
            existing, action, {"wiki/sources/c.md": "Paper C"}, "2026-01-02", []
        )
        self.assertIn("| Paper C | Method C | head |", merged)
        self.assertNotIn("### Shared Topic 更新", merged)
        merged_again = PUBLISH.merge_topic_page(
            merged, action, {"wiki/sources/c.md": "Paper C"}, "2026-01-03", []
        )
        self.assertEqual(merged_again.count("| Paper C |"), 1)

    def test_merge_topic_skips_present_contradiction(self) -> None:
        existing = (
            "---\n"
            "tags: [topic]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            "aliases:\n"
            'status: "stub"\n'
            "---\n\n"
            "# Shared Topic\n\n"
            "## 概述\n\nsummary.\n\n"
            "## 论文与方法对照\n\n"
            "| 论文 | 方法 | 干预粒度 | 主要结果 | 边界 | 证据 |\n"
            "|---|---|---|---|---|---|\n"
            "| [[a|Paper A]] | Method A | token | result | b | [Paper: PDF p. 1] |\n"
            "## 关键发现\n\n"
            "## 争议与不确定\n\n"
            "- 位置 A：A claims X.\n"
            "- 位置 B：B claims Y.\n"
            "## 相关实体与概念\n\n"
            "## 开放问题\n\n"
            "## 研究空白与候选方向\n"
        )
        action = {
            "action": "update_topic",
            "id": "topic-1",
            "name": "Shared Topic",
            "papers": ["wiki/sources/a.md"],
            "summary": "New synthesis.",
            "comparisons": [],
            "key_findings": [],
            "contradictions": [
                {
                    "position_a": "A claims X.",
                    "position_a_source_ref": "wiki/sources/a.md",
                    "position_a_pointer": "[Paper: PDF p. 1]",
                    "position_b": "B claims Y.",
                    "position_b_source_ref": "wiki/sources/b.md",
                    "position_b_pointer": "[Paper: PDF p. 2]",
                    "resolving_evidence": "A benchmark settles this.",
                }
            ],
            "open_questions": [],
            "research_gaps": [],
            "existing_page": "wiki/topics/Shared Topic.md",
        }
        merged = PUBLISH.merge_topic_page(existing, action, {}, "2026-01-02", [])
        self.assertEqual(merged.count("位置 A：A claims X."), 1)
        self.assertNotIn("来源：", merged)

    def test_research_dashboard_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            (root / "work" / "a" / "paper-digest.json").write_text(
                json.dumps(
                    {
                        "analysis": {"one_sentence_summary": "Paper A summary."},
                        "candidates": [
                            {
                                "id": "reusable-concept",
                                "name": "可复用概念",
                                "kind": "concept",
                                "tier": "L1",
                                "definition": "A reusable definition.",
                                "source_refs": ["wiki/sources/a.md"],
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--plan", str(plan_path), "--wiki-root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            dashboard = root / "wiki" / "meta" / "research.md"
            self.assertTrue(dashboard.is_file())
            text = dashboard.read_text(encoding="utf-8")
            self.assertIn("# 研究仪表盘", text)
            self.assertIn("Topic question", text)
            self.assertIn("Missing benchmark", text)
            self.assertIn("reusable-concept", text)
            self.assertIn("可复用概念", text)
            self.assertFalse((root / "wiki" / "meta" / "candidates.md").exists())

    def test_research_page_groups_by_domain(self) -> None:
        buckets = {
            "rag": {
                "sources": [],
                "topics": [],
                "hubs": [],
                "questions": [("Q1", "T", "wiki/topics/t.md")],
                "gaps": [("gap1", "T", "wiki/topics/t.md")],
            }
        }
        candidates = [
            {
                "id": "c1",
                "name": "候选",
                "kind": "concept",
                "definition": "def",
                "source_refs": ["wiki/sources/papers/rag/x.md"],
            }
        ]
        text = PUBLISH.render_research_page(
            buckets, {}, candidates, {}, "2026-08-22", "2026-08-22"
        )
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("## 开放问题", text)
        self.assertIn("### rag", text)
        self.assertIn("Q1 — 来源：[[t|T]]", text)
        self.assertIn("## 研究空白", text)
        self.assertIn("gap1 — 来源：[[t|T]]", text)
        self.assertIn("## L1 候选", text)
        self.assertIn("| c1 | 候选 | concept | def | [[x|x]] |", text)

    def test_legacy_candidates_migrate_into_research_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            meta = root / "wiki" / "meta"
            meta.mkdir(parents=True, exist_ok=True)
            (meta / "candidates.md").write_text(
                "---\n"
                "tags: [meta]\n"
                'created: "2026-01-01"\n'
                'updated: "2026-01-01"\n'
                'status: "evergreen"\n'
                "---\n\n"
                "# L1 候选账本\n\n"
                "| id | 名称 | 类型 | 定义 | 来源 |\n"
                "|---|---|---|---|---|\n"
                "| legacy-1 | 旧候选 | concept | 旧定义 | [[a|A]] |\n",
                encoding="utf-8",
            )
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--plan", str(plan_path), "--wiki-root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            dashboard = root / "wiki" / "meta" / "research.md"
            text = dashboard.read_text(encoding="utf-8")
            self.assertIn("legacy-1", text)
            self.assertIn("旧候选", text)
            self.assertIn("## L1 候选", text)
            # legacy file is left in place, not deleted or rewritten
            self.assertIn("legacy-1", (meta / "candidates.md").read_text(encoding="utf-8"))

    def test_cli_writes_knowledge_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--plan", str(plan_path), "--wiki-root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            tree_path = root / "wiki" / "meta" / "knowledge-tree.md"
            self.assertTrue(tree_path.is_file())
            text = tree_path.read_text(encoding="utf-8")
            self.assertIn("# 知识树", text)
            self.assertIn("[[a|a]]", text)
            self.assertIn("[[Shared Topic|Shared Topic]]", text)
            self.assertIn("（别名：concept）", text)
            self.assertIn("Topic question — 来源：[[Shared Topic|Shared Topic]]", text)
            self.assertIn("Missing benchmark — 来源：[[Shared Topic|Shared Topic]]", text)

    def test_knowledge_tree_groups_by_domain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "sources/papers/llm-opt", "topics", "concepts"):
                (wiki / sub).mkdir(parents=True)
            (wiki / "sources" / "papers" / "rag" / "x.md").write_text(
                "# Paper X\n", encoding="utf-8"
            )
            (wiki / "sources" / "papers" / "llm-opt" / "y.md").write_text(
                "# Paper Y\n", encoding="utf-8"
            )
            (wiki / "topics" / "t.md").write_text(
                "---\n"
                "tags: [topic]\n"
                'sources:\n  - "wiki/sources/papers/rag/x.md"\n'
                "aliases:\n"
                "status: stub\n"
                "---\n\n"
                "# T\n\n"
                "## 开放问题\n\n- Q1\n\n"
                "## 研究空白与候选方向\n\n- gap1\n",
                encoding="utf-8",
            )
            (wiki / "concepts" / "h.md").write_text(
                "---\n"
                "tags: [concept]\n"
                'sources:\n  - "wiki/sources/papers/rag/x.md"\n  - "wiki/sources/papers/llm-opt/y.md"\n'
                'aliases:\n  - "foo"\n  - "bar"\n'
                "status: stub\n"
                "---\n\n"
                "# H\n\n"
                "definition.\n",
                encoding="utf-8",
            )
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "- [[wiki/sources/papers/llm-opt/y.md|y]] - paper y\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n"
                "## 概念\n"
                "- [[wiki/concepts/h.md|H]] - hub h\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            self.assertIsNotNone(tree)
            assert tree is not None
            self.assertIn("## rag", tree)
            self.assertIn("## llm-opt", tree)
            self.assertIn("（别名：foo、bar）", tree)
            self.assertIn("Q1 — 来源：[[t|T]]", tree)
            self.assertIn("gap1 — 来源：[[t|T]]", tree)
            self.assertLess(tree.index("## rag"), tree.index("## 跨领域"))

    def test_merge_hub_preserves_existing_sources_list(self) -> None:
        existing = (
            "---\n"
            "tags: [concept]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            '  - "wiki/sources/b.md"\n'
            "aliases:\n"
            '  - "old alias"\n'
            'status: "stub"\n'
            "---\n\n"
            "# Hub\n\n"
            "## 证据\n\n"
            "| 来源 | 断言 | 证据 | confidence |\n"
            "|---|---|---|---|\n"
            "## 关系\n\n"
            "## 争议与矛盾\n\n"
            "## 开放问题\n\n"
            "## 引用来源\n"
        )
        action = {
            "action": "update_hub",
            "id": "hub-1",
            "name": "Hub",
            "kind": "concept",
            "tier": "L2",
            "aliases": ["new alias"],
            "definition": "",
            "source_refs": ["wiki/sources/c.md"],
            "connect_existing": True,
            "existing_page": "wiki/concepts/Hub.md",
            "evidence": [],
            "relations": [],
            "contradictions": [],
            "open_questions": [],
        }
        merged = PUBLISH.merge_hub_page(existing, action, {}, "2026-01-02")
        fields, lists, _ = PUBLISH.parse_frontmatter(merged)
        self.assertEqual(
            lists["sources"],
            ["wiki/sources/a.md", "wiki/sources/b.md", "wiki/sources/c.md"],
        )
        self.assertEqual(lists["aliases"], ["old alias", "new alias"])

    def test_hub_page_has_no_evidence_relations_or_open_questions(self) -> None:
        action = valid_plan()["hub_actions"][0]
        text = PUBLISH.hub_page_text(
            action, {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"}, "2026-01-01", "2026-01-01"
        )
        self.assertNotIn("## 证据", text)
        self.assertNotIn("## 关系", text)
        self.assertNotIn("## 开放问题", text)
        self.assertIn("## 别名", text)
        self.assertIn("## 争议与矛盾", text)
        self.assertIn("## 引用来源", text)

    def test_merge_hub_ignores_relations_field(self) -> None:
        existing = (
            "---\n"
            "tags: [concept]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            "aliases:\n"
            'status: "stub"\n'
            "---\n\n"
            "# Hub\n\n"
            "A definition.\n\n"
            "## 别名\n\n"
            "## 争议与矛盾\n\n"
            "## 引用来源\n"
        )
        action = {
            "action": "update_hub",
            "id": "hub-1",
            "name": "Hub",
            "kind": "concept",
            "tier": "L2",
            "aliases": [],
            "definition": "",
            "source_refs": ["wiki/sources/c.md"],
            "connect_existing": True,
            "existing_page": "wiki/concepts/Hub.md",
            "evidence": [],
            "relations": [
                {
                    "type": "applied_to",
                    "target": "Task",
                    "pointer": "[Paper: PDF p. 2]",
                    "provenance": "Paper",
                    "confidence": "high",
                }
            ],
            "contradictions": [],
            "open_questions": [],
        }
        merged = PUBLISH.merge_hub_page(existing, action, {}, "2026-01-02")
        self.assertNotIn("applied_to", merged)
        self.assertNotIn("## 关系", merged)

    def test_merge_hub_replaces_definition_when_provided(self) -> None:
        existing = (
            "---\n"
            "tags: [concept]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            "aliases:\n"
            'status: "stub"\n'
            "---\n\n"
            "# Hub\n\n"
            "Old definition.\n\n"
            "## 证据\n\n"
            "| 来源 | 断言 | 证据 | confidence |\n"
            "|---|---|---|---|\n"
            "## 关系\n\n"
            "## 争议与矛盾\n\n"
            "## 开放问题\n\n"
            "## 引用来源\n"
        )
        action = {
            "action": "update_hub",
            "id": "hub-1",
            "name": "Hub",
            "kind": "concept",
            "tier": "L2",
            "aliases": [],
            "definition": "New definition.",
            "source_refs": ["wiki/sources/c.md"],
            "connect_existing": True,
            "existing_page": "wiki/concepts/Hub.md",
            "evidence": [],
            "relations": [],
            "contradictions": [],
            "open_questions": [],
        }
        merged = PUBLISH.merge_hub_page(existing, action, {}, "2026-01-02")
        self.assertIn("# Hub\n\nNew definition.\n\n## 证据", merged)
        self.assertNotIn("Old definition.", merged)

    def test_missed_entity_promotions_warns_without_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work" / "a"
            work.mkdir(parents=True)
            (work / "paper-digest.json").write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "tier": "L1",
                                "kind": "entity",
                                "name": "Public Benchmark",
                                "definition": "A public benchmark.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pages = [{"source_ref": "wiki/sources/a.md", "work_dir": "work/a"}]
            warnings = PUBLISH.missed_entity_promotions(pages, [], root)
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["name"], "Public Benchmark")

    def test_missed_entity_promotions_silent_when_planned_or_existing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / "work" / "a"
            work.mkdir(parents=True)
            (work / "paper-digest.json").write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "tier": "L1",
                                "kind": "entity",
                                "name": "Public Benchmark",
                                "definition": "A public benchmark.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            pages = [{"source_ref": "wiki/sources/a.md", "work_dir": "work/a"}]
            planned = [
                {
                    "action": "create_hub",
                    "kind": "entity",
                    "name": "Public Benchmark",
                }
            ]
            self.assertEqual(
                PUBLISH.missed_entity_promotions(pages, planned, root), []
            )
            entities = root / "wiki" / "entities"
            entities.mkdir(parents=True)
            (entities / "Public Benchmark.md").write_text("# Public Benchmark\n", encoding="utf-8")
            self.assertEqual(
                PUBLISH.missed_entity_promotions(pages, [], root), []
            )

    def test_find_name_variant_matches_alias_and_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            concepts = root / "wiki" / "concepts"
            concepts.mkdir(parents=True)
            page = (
                "---\n"
                "tags: [concept]\n"
                "aliases:\n"
                '  - "Knowledge Conflict"\n'
                "---\n\n"
                "# 知识冲突\n"
            )
            (concepts / "知识冲突.md").write_text(page, encoding="utf-8")
            (concepts / "LLaVA.md").write_text("# LLaVA\n", encoding="utf-8")
            self.assertEqual(
                PUBLISH.find_name_variant("知识冲突（Knowledge Conflict）", root),
                "知识冲突",
            )
            self.assertEqual(
                PUBLISH.find_name_variant("LLaVA（Large Language and Vision Assistant）", root),
                "LLaVA",
            )
            self.assertEqual(PUBLISH.find_name_variant("Knowledge Conflict", root), "知识冲突")
            # exact name goes through the merge path, not the variant guard
            self.assertIsNone(PUBLISH.find_name_variant("知识冲突", root))
            # short names are too ambiguous to flag
            self.assertIsNone(PUBLISH.find_name_variant("MR", root))

    def test_refused_variant_action_does_not_leak_backlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            (root / "wiki" / "concepts" / "Shared Concept.md").write_text(
                "---\n"
                "tags: [concept]\n"
                'created: "2026-01-01"\n'
                'updated: "2026-01-01"\n'
                "sources:\n"
                "aliases:\n"
                'status: "stub"\n'
                "---\n\n"
                "# Shared Concept\n\n"
                "A definition.\n\n"
                "## 别名\n\n"
                "## 争议与矛盾\n\n"
                "## 引用来源\n",
                encoding="utf-8",
            )
            plan = valid_plan()
            plan["hub_actions"].append(
                {
                    "action": "create_hub",
                    "id": "hub-2",
                    "name": "Shared Concept（扩展名）",
                    "kind": "concept",
                    "tier": "L2",
                    "aliases": [],
                    "definition": "A variant name.",
                    "source_refs": ["wiki/sources/a.md"],
                    "connect_existing": True,
                    "existing_page": None,
                    "evidence": [
                        {
                            "source_ref": "wiki/sources/a.md",
                            "pointer": "[Paper: PDF p. 1]",
                            "claim": "Paper A reports it.",
                        }
                    ],
                    "contradictions": [],
                    "open_questions": [],
                }
            )
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--plan",
                    str(plan_path),
                    "--wiki-root",
                    str(root),
                    "--report",
                    str(root / "publish-report.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(
                (root / "publish-report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(
                any("hub_name_variant" in error for error in report["errors"])
            )
            source_a = (root / "wiki" / "sources" / "a.md").read_text(encoding="utf-8")
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertNotIn("Shared Concept（扩展名）", source_a)
            self.assertNotIn("Shared Concept（扩展名）", topic)
            self.assertIn("[[Shared Concept|Shared Concept]] - 概念枢纽", source_a)

    def test_knowledge_tree_is_stable_between_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--plan",
                str(plan_path),
                "--wiki-root",
                str(root),
                "--report",
                str(root / "publish-report.json"),
            ]
            first = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            tree_path = root / "wiki" / "meta" / "knowledge-tree.md"
            original = tree_path.read_text(encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(tree_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
