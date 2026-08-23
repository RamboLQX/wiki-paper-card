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
        "datasets": [],
        "models": [],
        "metrics": [],
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
                "research_gaps": ["Missing benchmark"],
                "existing_page": None,
            }
        ],
    }


def prepare_vault(root: Path) -> None:
    for directory in (
        "wiki/entities",
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
                        "datasets": ["CONFLICTVIS"],
                        "models": ["LLaVA", "LLaVA 1.5"],
                        "metrics": ["ROUGE"],
                    }
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    (root / "wiki" / "index.md").write_text(
        "# Wiki 索引\n\n## 实体\n## 主题\n## 来源\n## 元页面\n",
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

    def test_topic_page_lists_related_entities(self) -> None:
        text = PUBLISH.topic_page_text(
            valid_plan()["topic_actions"][0],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-16",
            "2026-08-16",
            ["LLaVA"],
        )
        self.assertIn("[[LLaVA|LLaVA]]", text)
        self.assertIn("## 相关实体", text)

    def test_entity_stub_text_shape(self) -> None:
        text = PUBLISH.entity_stub_text(
            "LLaVA",
            ["LLaVA 1.5"],
            ["wiki/sources/a.md"],
            {"wiki/sources/a.md": "Paper A"},
            "2026-08-16",
            "2026-08-16",
        )
        self.assertIn("tags: [entity]", text)
        self.assertIn("status: \"stub\"", text)
        self.assertIn("# LLaVA", text)
        self.assertIn("本页由 publish_wiki.py 确定性生成", text)
        self.assertIn("- LLaVA 1.5", text)
        self.assertIn("- [[a|Paper A]]", text)
        self.assertNotIn("## 证据", text)

    def test_collect_entity_mentions_from_digest_lists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            pages = [
                {"source_ref": "wiki/sources/a.md", "work_dir": "work/a"},
                {"source_ref": "wiki/sources/b.md", "work_dir": "work/b"},
            ]
            mentions = PUBLISH.collect_entity_mentions(pages, root)
            key_llava = PUBLISH.normalize_entity_name("LLaVA")
            key_variant = PUBLISH.normalize_entity_name("LLaVA 1.5")
            self.assertIn(key_llava, mentions)
            self.assertIn(key_variant, mentions)
            self.assertEqual(
                {name for name, _ in mentions[key_llava]}, {"LLaVA"}
            )
            self.assertEqual(
                {name for name, _ in mentions[key_variant]}, {"LLaVA 1.5"}
            )
            refs = {ref for _, ref in mentions[key_llava]}
            self.assertEqual(refs, {"wiki/sources/a.md", "wiki/sources/b.md"})

    def test_resolve_entity_targets_merges_variants(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "wiki" / "entities").mkdir(parents=True)
            mentions = {
                "llava": [
                    ("LLaVA", "wiki/sources/a.md"),
                    ("LLaVA", "wiki/sources/b.md"),
                ],
                "llava15": [("LLaVA 1.5", "wiki/sources/a.md")],
            }
            targets = PUBLISH.resolve_entity_targets(mentions, root)
            self.assertEqual(len(targets), 1)
            target = targets[0]
            self.assertEqual(target["name"], "LLaVA")
            self.assertEqual(target["aliases"], ["LLaVA 1.5"])
            self.assertEqual(
                target["source_refs"], ["wiki/sources/a.md", "wiki/sources/b.md"]
            )
            self.assertEqual(target["path"], root / "wiki" / "entities" / "LLaVA.md")

    def test_resolve_entity_targets_merges_into_existing_variant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entities = root / "wiki" / "entities"
            entities.mkdir(parents=True)
            (entities / "LLaVA.md").write_text("# LLaVA\n", encoding="utf-8")
            mentions = {
                "llavanext": [("LLaVA-NeXT", "wiki/sources/a.md")],
            }
            targets = PUBLISH.resolve_entity_targets(mentions, root)
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0]["name"], "LLaVA")
            self.assertIn("LLaVA-NeXT", targets[0]["aliases"])

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
            self.assertTrue((root / "wiki" / "entities" / "LLaVA.md").is_file())
            self.assertTrue((root / "wiki" / "entities" / "CONFLICTVIS.md").is_file())
            self.assertTrue((root / "wiki" / "entities" / "ROUGE.md").is_file())
            self.assertFalse((root / "wiki" / "entities" / "LLaVA 1.5.md").exists())
            self.assertTrue((root / "wiki" / "topics" / "Shared Topic.md").is_file())
            self.assertFalse((root / "wiki" / "concepts").exists())
            index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
            source_a = (root / "wiki" / "sources" / "a.md").read_text(encoding="utf-8")
            entity = (root / "wiki" / "entities" / "LLaVA.md").read_text(encoding="utf-8")
            topic = (root / "wiki" / "topics" / "Shared Topic.md").read_text(encoding="utf-8")
            self.assertIn("[[wiki/sources/a.md|a]]", index)
            self.assertIn("[[wiki/entities/LLaVA.md|LLaVA]]", index)
            self.assertIn("[[LLaVA|LLaVA]] - 实体", source_a)
            self.assertIn("[[Shared Topic|Shared Topic]] - 主题", source_a)
            self.assertIn("[[LLaVA|LLaVA]]", topic)
            self.assertIn("- [[a|Paper A]]", entity)
            self.assertIn("- [[b|Paper B]]", entity)
            self.assertIn("ingest | Paper A", log)
            self.assertIn("batch synthesis | Paper A、Paper B", log)

    def test_entity_stub_appends_to_existing_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entities = root / "wiki" / "entities"
            entities.mkdir(parents=True)
            existing = (
                "---\n"
                "tags: [entity]\n"
                'created: "2026-01-01"\n'
                'updated: "2026-01-01"\n'
                "sources:\n"
                '  - "wiki/sources/old.md"\n'
                "aliases:\n"
                '  - "LLaVA 1.5"\n'
                'status: "stub"\n'
                "---\n\n"
                "# LLaVA\n\n"
                "> 本页由 publish_wiki.py 确定性生成，只聚合引用本实体的论文；定义与评价见各来源论文页。\n\n"
                "## 别名\n\n"
                "- LLaVA 1.5\n\n"
                "## 引用来源\n\n"
                "- [[old|Old Paper]]\n"
            )
            (entities / "LLaVA.md").write_text(existing, encoding="utf-8")
            merged = PUBLISH.merge_entity_stub(
                existing,
                ["LLaVA 1.5"],
                ["wiki/sources/a.md"],
                {"wiki/sources/a.md": "Paper A"},
                "2026-01-02",
            )
            fields, lists, _ = PUBLISH.parse_frontmatter(merged)
            self.assertEqual(
                lists["sources"],
                ["wiki/sources/old.md", "wiki/sources/a.md"],
            )
            self.assertEqual(lists["aliases"], ["LLaVA 1.5"])
            self.assertIn("- [[a|Paper A]]", merged)
            merged_again = PUBLISH.merge_entity_stub(
                merged,
                [],
                ["wiki/sources/a.md"],
                {"wiki/sources/a.md": "Paper A"},
                "2026-01-03",
            )
            self.assertEqual(merged_again.count("[[a|Paper A]]"), 1)

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
            entity = root / "wiki" / "entities" / "LLaVA.md"
            original = page.read_text(encoding="utf-8")
            original_entity = entity.read_text(encoding="utf-8")
            original_index = (root / "wiki" / "index.md").read_text(encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads((root / "publish-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["writes"], [])
            self.assertEqual(page.read_text(encoding="utf-8"), original)
            self.assertEqual(entity.read_text(encoding="utf-8"), original_entity)
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
                "entities": [],
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

    def test_research_page_empty_when_no_content(self) -> None:
        buckets: dict = {}
        self.assertIsNone(PUBLISH.render_research_page(buckets, "2026-08-22", "2026-08-22"))

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
            self.assertIn("### 实体", text)
            self.assertIn("（别名：LLaVA 1.5）", text)
            self.assertIn("Topic question — 来源：[[Shared Topic|Shared Topic]]", text)
            self.assertIn("Missing benchmark — 来源：[[Shared Topic|Shared Topic]]", text)

    def test_knowledge_tree_groups_by_domain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "sources/papers/llm-opt", "topics", "entities"):
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
            (wiki / "entities" / "h.md").write_text(
                "---\n"
                "tags: [entity]\n"
                'sources:\n  - "wiki/sources/papers/rag/x.md"\n  - "wiki/sources/papers/llm-opt/y.md"\n'
                'aliases:\n  - "foo"\n  - "bar"\n'
                "status: stub\n"
                "---\n\n"
                "# H\n\n"
                "> 本页由 publish_wiki.py 确定性生成。\n",
                encoding="utf-8",
            )
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "- [[wiki/sources/papers/llm-opt/y.md|y]] - paper y\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n"
                "## 实体\n"
                "- [[wiki/entities/h.md|H]] - entity h\n",
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

    def test_find_name_variant_matches_alias_and_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entities = root / "wiki" / "entities"
            entities.mkdir(parents=True)
            page = (
                "---\n"
                "tags: [entity]\n"
                "aliases:\n"
                '  - "Knowledge Conflict"\n'
                "---\n\n"
                "# 知识冲突\n"
            )
            (entities / "知识冲突.md").write_text(page, encoding="utf-8")
            (entities / "LLaVA.md").write_text("# LLaVA\n", encoding="utf-8")
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
            # legacy page file is left untouched
            self.assertIn("# Legacy", (concepts / "Legacy.md").read_text(encoding="utf-8"))
            # the regenerated tree does not list concepts
            tree = (root / "wiki" / "meta" / "knowledge-tree.md").read_text(encoding="utf-8")
            self.assertNotIn("Legacy", tree)

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
