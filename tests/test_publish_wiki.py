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


def digest(analysis: dict) -> dict:
    base = {
        "one_sentence_summary": "Summary.",
    }
    base.update(analysis)
    return {"analysis": base}


def valid_plan() -> dict:
    return {
        "schema_version": "2.0",
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
                "research_gaps": [
                    {
                        "gap": "Missing benchmark",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "direction": "Evaluate both papers on one benchmark.",
                        "continuity": "A future paper can run the comparison.",
                    }
                ],
                "existing_page": None,
            }
        ],
    }


def prepare_vault(root: Path) -> None:
    for directory in (
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
                digest(
                    {
                        "one_sentence_summary": f"{title} summary.",
                    }
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    (root / "wiki" / "index.md").write_text(
        "# Wiki 索引\n\n## 主题\n## 来源\n## 元页面\n",
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
        self.assertIn("[[a\\|Paper A]]", lines[2])
        self.assertNotIn("[[a|Paper A]]", lines[2])

    def test_grouped_comparisons_escape_wikilink_pipe(self) -> None:
        lines = PUBLISH.render_grouped_comparisons(
            [
                {
                    "dimension": "干预粒度",
                    "entries": [
                        {
                            "source_ref": "wiki/sources/a.md",
                            "paper": "Paper A",
                            "claim": "claim A",
                            "pointer": "[Paper: PDF p. 1]",
                        }
                    ],
                }
            ],
            {"wiki/sources/a.md": "Paper A"},
        )
        table = "\n".join(lines)
        self.assertIn("[[a\\|Paper A]]", table)
        self.assertNotIn("[[a|Paper A]]", table)

    def test_topic_page_has_no_related_entities_section(self) -> None:
        text = PUBLISH.topic_page_text(
            valid_plan()["topic_actions"][0],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertNotIn("## 相关实体", text)

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
            self.assertFalse((root / "wiki" / "entities").exists())
            self.assertTrue((root / "wiki" / "topics" / "Shared Topic.md").is_file())
            self.assertFalse((root / "wiki" / "concepts").exists())
            index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
            source_a = (root / "wiki" / "sources" / "a.md").read_text(encoding="utf-8")
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertIn("[[wiki/sources/a.md|a]]", index)
            self.assertNotIn("实体", index)
            self.assertIn("[[Shared Topic|Shared Topic]] - 主题", source_a)
            self.assertNotIn("## 相关实体", topic)
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

    def test_gap_without_v2_fields_renders_legacy_line(self) -> None:
        bullet = PUBLISH.gap_bullet(
            PUBLISH.normalize_gaps(
                [
                    {
                        "gap": "缺统一基准",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "direction": "统一评测",
                        "continuity": "可由未来论文承接",
                    }
                ]
            )[0],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            None,
        )
        self.assertEqual(
            bullet,
            "- 缺统一基准（来源：[[a|Paper A]]、[[b|Paper B]]；可检验方向：统一评测；承接：可由未来论文承接）",
        )

    def test_gap_v2_fields_render_sub_bullets(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "缺统一基准",
                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "direction": "统一评测",
                "continuity": "可由未来论文承接",
                "significance": "解决了会改变评估结论",
                "evidence_boundary": "现有方法只测英文",
                "experiment": "在中文基准上重跑",
                "success_criterion": "排名稳定",
                "risk": "基准可能失效",
                "priority": "高",
            }
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("  - 为什么值得做：解决了会改变评估结论", text)
        self.assertIn("  - 现有方法卡在哪：现有方法只测英文", text)
        self.assertIn("  - 怎么检验：在中文基准上重跑", text)
        self.assertIn("  - 做到什么算成：排名稳定", text)
        self.assertIn("  - 可能行不通：基准可能失效", text)
        self.assertIn("  - 优先级：高", text)
        self.assertNotIn("[待验证]", text)

    def test_gap_v2_tentative_direction_gets_tag(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "缺统一基准",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "统一评测",
                "continuity": "可由未来论文承接",
                "significance": "重要",
            }
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("[待验证]", text)

    def test_merge_keeps_existing_gap_sub_bullets(self) -> None:
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
            "## 关键发现\n\n"
            "## 争议与不确定\n\n"
            "## 开放问题\n\n"
            "## 研究空白与候选方向\n\n"
            "- gap1（来源：[[a|a]]）\n"
            "  - 为什么值得做：重要\n"
            "  - 怎么检验：跑基准\n"
        )
        action = {
            "action": "update_topic",
            "id": "topic-1",
            "name": "Shared Topic",
            "papers": ["wiki/sources/a.md"],
            "summary": "",
            "comparisons": [],
            "key_findings": [],
            "contradictions": [],
            "open_questions": [],
            "research_gaps": [
                {
                    "gap": "gap2",
                    "source_refs": ["wiki/sources/a.md"],
                    "direction": "d2",
                    "continuity": "c2",
                }
            ],
            "existing_page": "wiki/topics/Shared Topic.md",
        }
        merged = PUBLISH.merge_topic_page(
            existing,
            action,
            {"wiki/sources/a.md": "Paper A"},
            "2026-01-02",
            {"wiki/sources/a.md": "A"},
        )
        self.assertIn("- gap1（来源：[[a|a]]）\n  - 为什么值得做：重要", merged)
        self.assertIn("  - 怎么检验：跑基准", merged)
        self.assertIn("- gap2（来源：[[a|A]]", merged)

    def test_topic_create_with_category(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["category"] = "评估框架"
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn('category: "评估框架"', text)

    def test_topic_update_sets_and_preserves_category(self) -> None:
        existing = (
            "---\n"
            "tags: [topic]\n"
            'created: "2026-01-01"\n'
            'updated: "2026-01-01"\n'
            'category: "模型优化"\n'
            "sources:\n"
            '  - "wiki/sources/a.md"\n'
            "aliases:\n"
            'status: "stub"\n'
            "---\n\n"
            "# Shared Topic\n\n"
            "## 概述\n\nsummary.\n\n"
            "## 论文与方法对照\n\n"
            "## 关键发现\n\n"
            "## 争议与不确定\n\n"
            "## 开放问题\n\n"
            "## 研究空白与候选方向\n\n"
        )
        action = {
            "action": "update_topic",
            "id": "topic-1",
            "name": "Shared Topic",
            "papers": ["wiki/sources/a.md"],
            "summary": "",
            "comparisons": [],
            "key_findings": [],
            "contradictions": [],
            "open_questions": [],
            "research_gaps": [],
            "existing_page": "wiki/topics/Shared Topic.md",
        }
        merged = PUBLISH.merge_topic_page(
            existing, action, {"wiki/sources/a.md": "Paper A"}, "2026-01-02"
        )
        self.assertIn('category: "模型优化"', merged)
        action["category"] = "评估框架"
        merged = PUBLISH.merge_topic_page(
            existing, action, {"wiki/sources/a.md": "Paper A"}, "2026-01-02"
        )
        self.assertIn('category: "评估框架"', merged)
        self.assertNotIn('category: "模型优化"', merged)

    def test_research_page_sorts_gaps_by_priority(self) -> None:
        buckets = {
            "rag": {
                "sources": [],
                "topics": [],
                "questions": [],
                "gaps": [
                    ("gap 低", "T", "wiki/topics/t.md", "低"),
                    ("gap 高", "T", "wiki/topics/t.md", "高"),
                    ("gap 中", "T", "wiki/topics/t.md", "中"),
                    ("gap 无", "T", "wiki/topics/t.md", ""),
                ],
            }
        }
        text = PUBLISH.render_research_page(buckets, "2026-08-22", "2026-08-22")
        assert text is not None
        self.assertLess(text.index("gap 高"), text.index("gap 中"))
        self.assertLess(text.index("gap 中"), text.index("gap 低"))
        self.assertLess(text.index("gap 低"), text.index("gap 无"))

    def test_knowledge_tree_renders_category_view(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "topics"):
                (wiki / sub).mkdir(parents=True)
            (wiki / "sources" / "papers" / "rag" / "x.md").write_text(
                "# Paper X\n", encoding="utf-8"
            )
            (wiki / "topics" / "t.md").write_text(
                "---\n"
                "tags: [topic]\n"
                'sources:\n  - "wiki/sources/papers/rag/x.md"\n'
                'category: "评估框架"\n'
                "aliases:\n"
                "status: stub\n"
                "---\n\n"
                "# T\n\n",
                encoding="utf-8",
            )
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            assert tree is not None
            self.assertIn("## 按主题分类", tree)
            self.assertIn("### 评估框架", tree)
            self.assertIn("[[t|T]]", tree)
            self.assertLess(tree.index("## rag"), tree.index("## 按主题分类"))

    def test_legacy_research_gaps_render_as_list(self) -> None:
        lines = PUBLISH.render_research_gaps(["gap A", "gap B"], {}, None)
        self.assertEqual(lines, ["- gap A", "- gap B"])

    def test_open_question_objects_render_open_and_archive(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["open_questions"] = [
            "Plain question",
            {"question": "Structured question", "status": "open"},
            {
                "question": "Resolved question",
                "status": "answered",
                "answered_by": ["wiki/sources/a.md"],
                "answered_pointer": "[Paper: PDF p. 3]",
            },
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
            short_names={"wiki/sources/a.md": "A"},
        )
        self.assertIn("## 开放问题\n\n- Plain question\n- Structured question", text)
        self.assertIn(
            "## 已解决的问题\n\n- Resolved question（已解决：[[a|A]]；[Paper: PDF p. 3]）",
            text,
        )
        self.assertNotIn("Resolved question", text.split("## 已解决的问题")[0])

    def test_answered_gaps_render_in_archive_section(self) -> None:
        action = valid_plan()["topic_actions"][0]
        action["research_gaps"] = [
            {"gap": "Open gap", "status": "open"},
            {
                "gap": "Resolved gap",
                "source_refs": ["wiki/sources/a.md"],
                "status": "answered",
                "answered_by": ["wiki/sources/b.md"],
                "answered_pointer": "[Paper: PDF p. 4]",
            },
        ]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("## 研究空白与候选方向\n\n- Open gap", text)
        self.assertIn(
            "## 已解决的研究空白\n\n- Resolved gap（来源：[[a|Paper A]]；已解决：[[b|Paper B]]；[Paper: PDF p. 4]）",
            text,
        )
        self.assertNotIn("Resolved gap", text.split("## 已解决的研究空白")[0])

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
            "## 相关实体\n\n"
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
            "## 相关实体\n\n"
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
            self.assertNotIn("## L1 候选", text)
            self.assertFalse((root / "wiki" / "meta" / "candidates.md").exists())

    def test_research_page_groups_by_domain(self) -> None:
        buckets = {
            "rag": {
                "sources": [],
                "topics": [],
                "questions": [("Q1", "T", "wiki/topics/t.md")],
                "gaps": [("gap1", "T", "wiki/topics/t.md")],
            }
        }
        text = PUBLISH.render_research_page(buckets, "2026-08-22", "2026-08-22")
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("## 开放问题", text)
        self.assertIn("### rag", text)
        self.assertIn("Q1 — 来源：[[t|T]]", text)
        self.assertIn("## 研究空白", text)
        self.assertIn("gap1 — 来源：[[t|T]]", text)
        self.assertNotIn("## L1 候选", text)

    def test_research_page_none_without_index(self) -> None:
        self.assertIsNone(PUBLISH.render_research_page(None, "2026-08-22", "2026-08-22"))

    def test_research_page_placeholder_when_no_content(self) -> None:
        text = PUBLISH.render_research_page({}, "2026-08-22", "2026-08-22")
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("# 研究仪表盘", text)
        self.assertIn("当前没有待解决的开放问题与研究空白", text)
        self.assertNotIn("## 开放问题", text)

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
            self.assertNotIn("### 实体", text)
            self.assertIn("Topic question — 来源：[[Shared Topic|Shared Topic]]", text)
            self.assertIn("Missing benchmark", text)
            self.assertIn("来源：[[Shared Topic|Shared Topic]]", text)

    def test_merge_topic_moves_resolved_items_to_archive(self) -> None:
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
            "## 关键发现\n\n"
            "## 争议与不确定\n\n"
            "## 开放问题\n\n- Q1\n- Q2\n\n"
            "## 研究空白与候选方向\n\n- gap1（来源：[[a|a]]；可检验方向：d；承接：c）\n"
        )
        action = {
            "action": "update_topic",
            "id": "topic-1",
            "name": "Shared Topic",
            "papers": ["wiki/sources/b.md"],
            "summary": "",
            "comparisons": [],
            "key_findings": [],
            "contradictions": [],
            "open_questions": [
                {
                    "question": "Q1",
                    "status": "answered",
                    "answered_by": ["wiki/sources/b.md"],
                    "answered_pointer": "[Paper: PDF p. 2]",
                },
                "Q3",
            ],
            "research_gaps": [
                {
                    "gap": "gap1",
                    "source_refs": ["wiki/sources/a.md"],
                    "status": "answered",
                    "answered_by": ["wiki/sources/b.md"],
                    "answered_pointer": "[Paper: PDF p. 3]",
                }
            ],
            "existing_page": "wiki/topics/Shared Topic.md",
        }
        merged = PUBLISH.merge_topic_page(
            existing,
            action,
            {"wiki/sources/b.md": "Paper B"},
            "2026-01-02",
            {"wiki/sources/b.md": "B"},
        )
        open_section = merged.split("## 已解决的问题")[0]
        self.assertIn("- Q2\n- Q3", open_section)
        self.assertNotIn("Q1", open_section)
        self.assertIn(
            "## 已解决的问题\n\n- Q1（已解决：[[b|B]]；[Paper: PDF p. 2]）", merged
        )
        self.assertIn(
            "## 已解决的研究空白\n\n- gap1（来源：[[a|a]]；已解决：[[b|B]]；[Paper: PDF p. 3]）",
            merged,
        )
        self.assertNotIn("gap1", merged.split("## 已解决的研究空白")[0])

    def test_resolved_items_leave_dashboards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(
                json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8"
            )
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--plan",
                str(plan_path),
                "--wiki-root",
                str(root),
            ]
            first = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            dashboard = (root / "wiki" / "meta" / "research.md").read_text(encoding="utf-8")
            self.assertIn("Topic question", dashboard)
            # second batch answers the open question and the gap
            c_dir = root / "work" / "c"
            c_dir.mkdir(parents=True)
            (c_dir / "paper-card.md").write_text(
                source_card("Paper C", "wiki/sources/c.md"), encoding="utf-8"
            )
            (c_dir / "paper-digest.json").write_text(
                json.dumps(
                    digest({"one_sentence_summary": "Paper C summary."}),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            plan2 = {
                "schema_version": "2.0",
                "batch": {
                    "source_pages": [
                        {
                            "source_ref": "wiki/sources/c.md",
                            "work_dir": "work/c",
                            "title": "Paper C",
                        }
                    ]
                },
                "topic_actions": [
                    {
                        "action": "update_topic",
                        "id": "topic-1",
                        "name": "Shared Topic",
                        "papers": ["wiki/sources/c.md"],
                        "summary": "C answers the open question.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [
                            {
                                "question": "Topic question",
                                "status": "answered",
                                "answered_by": ["wiki/sources/c.md"],
                                "answered_pointer": "[Paper: PDF p. 3]",
                            }
                        ],
                        "research_gaps": [
                            {
                                "gap": "Missing benchmark",
                                "source_refs": ["wiki/sources/a.md"],
                                "direction": "Evaluate the missing benchmark.",
                                "continuity": "Paper C closes the recorded gap.",
                                "status": "answered",
                                "answered_by": ["wiki/sources/c.md"],
                                "answered_pointer": "[Paper: PDF p. 4]",
                            }
                        ],
                        "existing_page": "wiki/topics/Shared Topic.md",
                    }
                ],
            }
            plan_path.write_text(json.dumps(plan2, ensure_ascii=False), encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertIn("## 已解决的问题", topic)
            self.assertNotIn("Topic question", topic.split("## 已解决的问题")[0])
            dashboard2 = (root / "wiki" / "meta" / "research.md").read_text(encoding="utf-8")
            self.assertNotIn("Topic question", dashboard2)
            self.assertNotIn("Missing benchmark", dashboard2)
            tree = (root / "wiki" / "meta" / "knowledge-tree.md").read_text(encoding="utf-8")
            self.assertNotIn("Topic question", tree)
            self.assertNotIn("Missing benchmark", tree)
            # third run is idempotent
            third = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(third.returncode, 0, third.stderr)
            self.assertEqual(
                (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8"),
                topic,
            )

    def test_mining_plan_updates_existing_and_creates_topic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan_path = root / "link-plan.json"
            plan_path.write_text(
                json.dumps(valid_plan(), ensure_ascii=False), encoding="utf-8"
            )
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
            # mining plan: no batch source pages, references existing pages
            mining = {
                "schema_version": "2.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "gap mining 2026-08"},
                "topic_actions": [
                    {
                        "action": "update_topic",
                        "id": "mining-1",
                        "name": "Shared Topic",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "summary": "Cross-group gap: common benchmark missing.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [
                            {
                                "question": "Are results robust across both groups?",
                                "status": "open",
                            }
                        ],
                        "research_gaps": [
                            {
                                "gap": "跨组统一基准缺失",
                                "source_refs": [
                                    "wiki/sources/a.md",
                                    "wiki/sources/b.md",
                                ],
                                "direction": "在同一基准上重跑两组方法",
                                "continuity": "未来论文可承接",
                                "status": "open",
                            }
                        ],
                        "existing_page": "wiki/topics/Shared Topic.md",
                    },
                    {
                        "action": "create_topic",
                        "id": "mining-2",
                        "name": "Cross Group Direction",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "summary": "Cross-group candidate direction.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [],
                        "research_gaps": [
                            {
                                "gap": "跨组候选方向",
                                "source_refs": ["wiki/sources/a.md"],
                                "direction": "d",
                                "continuity": "c",
                            }
                        ],
                        "existing_page": None,
                    },
                ],
            }
            plan_path.write_text(json.dumps(mining, ensure_ascii=False), encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads(
                (root / "publish-report.json").read_text(encoding="utf-8")
            )
            kinds = {(item["kind"], item["path"]) for item in report["writes"]}
            self.assertIn(("topic", "wiki/topics/Cross Group Direction.md"), kinds)
            self.assertIn(("source-backlinks", "wiki/sources/a.md"), kinds)
            self.assertIn(("source-backlinks", "wiki/sources/b.md"), kinds)
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertIn("跨组统一基准缺失", topic)
            self.assertIn("Are results robust across both groups?", topic)
            source_a = (root / "wiki" / "sources" / "a.md").read_text(encoding="utf-8")
            self.assertIn("[[Cross Group Direction|Cross Group Direction]] - 主题", source_a)
            self.assertIn("[[Shared Topic|Shared Topic]] - 主题", source_a)
            log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
            self.assertIn("gap mining 2026-08", log)
            dashboard = (root / "wiki" / "meta" / "research.md").read_text(encoding="utf-8")
            self.assertIn("跨组统一基准缺失", dashboard)
            # rerun is idempotent
            third = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(third.returncode, 0, third.stderr)
            report3 = json.loads(
                (root / "publish-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report3["writes"], [])

    def test_mining_missing_source_blocks_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "wiki" / "sources"
            source_dir.mkdir(parents=True)
            (source_dir / "a.md").write_text("# Paper A\n", encoding="utf-8")
            plan = {
                "schema_version": "2.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "missing source probe"},
                "topic_actions": [
                    {
                        "action": "create_topic",
                        "id": "mining-missing",
                        "name": "Must Not Be Written",
                        "papers": [
                            "wiki/sources/a.md",
                            "wiki/sources/missing.md",
                        ],
                        "summary": "This plan has a missing source page.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [],
                        "research_gaps": [],
                        "existing_page": None,
                    }
                ],
            }
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
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
            self.assertIn(
                "Missing source page: wiki/sources/missing.md", result.stderr
            )
            self.assertFalse(
                (root / "wiki" / "topics" / "Must Not Be Written.md").exists()
            )

    def test_gap_source_ref_missing_blocks_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "wiki" / "sources"
            source_dir.mkdir(parents=True)
            (source_dir / "a.md").write_text("# Paper A\n", encoding="utf-8")
            (source_dir / "b.md").write_text("# Paper B\n", encoding="utf-8")
            plan = {
                "schema_version": "2.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "gap source probe"},
                "topic_actions": [
                    {
                        "action": "create_topic",
                        "id": "mining-gap",
                        "name": "Gap Topic",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "summary": "This plan has a gap tracing to a missing page.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [],
                        "research_gaps": [
                            {
                                "gap": "A gap traced to a missing page.",
                                "source_refs": ["wiki/sources/gone.md"],
                                "direction": "Run a probe.",
                                "continuity": "A future paper can answer it.",
                            }
                        ],
                        "existing_page": None,
                    }
                ],
            }
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
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
            self.assertIn(
                "Missing source page: wiki/sources/gone.md", result.stderr
            )
            self.assertFalse((root / "wiki" / "topics" / "Gap Topic.md").exists())

    def test_ingest_missing_card_blocks_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a", "b"):
                (root / "work" / name).mkdir(parents=True)
            # Batch pages a.md and b.md declared, but neither work dir has a
            # finalized paper-card.md.
            plan = {
                "schema_version": "2.0",
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
                "topic_actions": [
                    {
                        "action": "create_topic",
                        "id": "topic-1",
                        "name": "Must Not Be Written",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "summary": "This plan has no finalized cards.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [],
                        "research_gaps": [],
                        "existing_page": None,
                    }
                ],
            }
            plan_path = root / "link-plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
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
            self.assertIn("Missing finalized card", result.stderr)
            self.assertFalse(
                (root / "wiki" / "topics" / "Must Not Be Written.md").exists()
            )

    def test_gap_referencing_existing_historical_page_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_dir = root / "wiki" / "sources"
            source_dir.mkdir(parents=True)
            (source_dir / "a.md").write_text("# Paper A\n", encoding="utf-8")
            (source_dir / "c.md").write_text("# Paper C\n", encoding="utf-8")
            (root / "work" / "c").mkdir(parents=True)
            (root / "work" / "c" / "paper-card.md").write_text(
                "# Paper C card\n", encoding="utf-8"
            )
            plan = {
                "schema_version": "2.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "historical trace"},
                "topic_actions": [
                    {
                        "action": "create_topic",
                        "id": "mining-historical",
                        "name": "Historical Trace",
                        "papers": ["wiki/sources/a.md", "wiki/sources/c.md"],
                        "summary": "Gap traces to an existing earlier page.",
                        "comparisons": [],
                        "key_findings": [],
                        "contradictions": [],
                        "open_questions": [],
                        "research_gaps": [
                            {
                                "gap": "A gap rooted in an earlier page.",
                                "source_refs": ["wiki/sources/a.md"],
                                "direction": "d",
                                "continuity": "c",
                            }
                        ],
                        "existing_page": None,
                    }
                ],
            }
            # Direct unit check of the preflight: refs outside the current
            # batch are allowed when they already exist on disk.
            self.assertEqual(PUBLISH.preflight_errors(plan, root), [])

    def test_knowledge_tree_groups_by_domain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "sources/papers/llm-opt", "topics"):
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
                'sources:\n  - "wiki/sources/papers/rag/x.md"\n  - "wiki/sources/papers/llm-opt/y.md"\n'
                "aliases:\n"
                "status: stub\n"
                "---\n\n"
                "# T\n\n"
                "## 开放问题\n\n- Q1\n\n"
                "## 研究空白与候选方向\n\n- gap1\n",
                encoding="utf-8",
            )
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "- [[wiki/sources/papers/llm-opt/y.md|y]] - paper y\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            self.assertIsNotNone(tree)
            assert tree is not None
            self.assertIn("## rag", tree)
            self.assertIn("## llm-opt", tree)
            self.assertIn("Q1 — 来源：[[t|T]]", tree)
            self.assertIn("gap1 — 来源：[[t|T]]", tree)
            self.assertLess(tree.index("## rag"), tree.index("## 跨领域"))

    def test_legacy_concepts_dir_is_not_written_or_listed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            concepts = root / "wiki" / "concepts"
            concepts.mkdir(parents=True)
            (concepts / "Legacy.md").write_text(
                "---\n"
                "tags: [concept]\n"
                'created: "2026-01-01"\n'
                'updated: "2026-01-01"\n'
                "sources:\n"
                '  - "wiki/sources/a.md"\n'
                "aliases:\n"
                'status: "archived"\n'
                "---\n\n"
                "# Legacy\n",
                encoding="utf-8",
            )
            legacy_entities = root / "wiki" / "entities"
            legacy_entities.mkdir(parents=True)
            (legacy_entities / "LegacyEntity.md").write_text(
                "---\n"
                "tags: [entity]\n"
                'created: "2026-01-01"\n'
                'updated: "2026-01-01"\n'
                "sources:\n"
                '  - "wiki/sources/a.md"\n'
                "aliases:\n"
                'status: "archived"\n'
                "---\n\n"
                "# LegacyEntity\n",
                encoding="utf-8",
            )
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
            # legacy page files are left untouched
            self.assertIn("# Legacy", (concepts / "Legacy.md").read_text(encoding="utf-8"))
            self.assertIn(
                "# LegacyEntity",
                (legacy_entities / "LegacyEntity.md").read_text(encoding="utf-8"),
            )
            # the regenerated tree and index do not list legacy pages
            tree = (root / "wiki" / "meta" / "knowledge-tree.md").read_text(encoding="utf-8")
            self.assertNotIn("Legacy", tree)
            index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            self.assertNotIn("Legacy", index)

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
