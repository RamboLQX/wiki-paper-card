#!/usr/bin/env python3
"""Regression tests for deterministic wiki publication."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import re
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
                        "significance": "It would change which benchmark the field trusts.",
                    }
                ],
                "existing_page": None,
            }
        ],
    }


def valid_v3_plan() -> dict:
    plan = valid_plan()
    plan["schema_version"] = "3.0"
    plan["purpose"] = "ingest"
    action = plan["topic_actions"][0]
    action.pop("summary")
    action["index_summary"] = "The papers support a shared result with an unresolved boundary."
    action["page_status"] = "draft"
    action["comparisons"] = [
        {
            "source_ref": "wiki/sources/a.md",
            "paper": "Paper A",
            "method": "Method A",
            "intervention_granularity": "sample",
            "main_result": "Shared result",
            "boundary": "One benchmark",
            "pointer": "[Paper: PDF p. 3]",
        }
    ]
    action["key_findings"] = [
        {
            "id": "kf-shared-result",
            "claim": "Both papers support the shared result.",
            "kind": "consensus",
            "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            "pointers": [
                {
                    "source_ref": "wiki/sources/a.md",
                    "pointer": "[Paper: PDF p. 3]",
                },
                {
                    "source_ref": "wiki/sources/b.md",
                    "pointer": "[Paper: PDF p. 4]",
                },
            ],
        }
    ]
    action["contradictions"] = []
    action["narrative"] = {
        "overview": {
            "paragraphs": [
                {
                    "id": "overview-scope",
                    "text": "This topic studies whether the shared result transfers across settings.",
                    "finding_refs": ["kf-shared-result"],
                },
                {
                    "id": "overview-state",
                    "text": "Current evidence supports the result in two settings, while benchmark comparability remains unresolved.",
                    "finding_refs": ["kf-shared-result"],
                }
            ]
        },
        "synthesis_blocks": [
            {
                "id": "synthesis-shared-result",
                "heading": "The result is supported across two settings",
                "paragraphs": [
                    {
                        "text": "The two papers support the result under different settings, but they do not use one benchmark.",
                        "finding_refs": ["kf-shared-result"],
                    },
                    {
                        "text": "The evidence therefore supports a bounded comparison rather than a general claim of transfer.",
                        "finding_refs": ["kf-shared-result"],
                    }
                ],
            }
        ],
        "controversy_blocks": [],
    }
    action["open_questions"] = [
        {
            "id": "oq-transfer",
            "origin": "ingest",
            "question": "Does the result transfer to a shared benchmark?",
            "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            "status": "open",
        }
    ]
    action["research_gaps"] = [
        {
            "id": "rg-unified-benchmark",
            "origin": "ingest",
            "gap": "A unified benchmark is missing.",
            "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            "direction": "Run both methods on one benchmark.",
            "continuity": "A later paper can perform the comparison.",
            "significance": "It would change which method is preferred.",
            "status": "open",
        }
    ]
    return plan


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


def publish_plan(
    root: Path, plan: dict, name: str = "link-plan.json"
) -> subprocess.CompletedProcess[str]:
    plan_path = root / name
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--plan",
            str(plan_path),
            "--wiki-root",
            str(root),
            "--report",
            str(root / f"{Path(name).stem}-report.json"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


class PublishWikiTests(unittest.TestCase):
    def test_schema_v3_create_renders_clean_narrative_with_footnotes(self) -> None:
        action = valid_v3_plan()["topic_actions"][0]
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-31",
            "2026-08-31",
            {"wiki/sources/a.md": "A", "wiki/sources/b.md": "B"},
            schema_version="3.0",
            purpose="ingest",
        )
        self.assertNotIn("wiki-paper-card:", text)
        self.assertNotIn("last_topic_action_sha256", text)
        self.assertIn("## 综合认识", text)
        self.assertIn("### The result is supported across two settings", text)
        self.assertIn("[^topic-evidence-1]", text)
        self.assertIn(
            "[^topic-evidence-1]: [[a|A]] [Paper: PDF p. 3]", text
        )
        self.assertNotIn("## 争议与不确定", text)
        self.assertIn("### A unified benchmark is missing. [待验证]", text)
        self.assertNotIn("## 关键发现", text)
        self.assertNotIn("共识：Both papers support", text)
        self.assertLess(text.index("## 综合认识"), text.index("## 论文与方法对照"))

    def test_schema_v3_empty_open_questions_render_explanatory_placeholder(self) -> None:
        action = valid_v3_plan()["topic_actions"][0]
        action["open_questions"] = []
        text = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-31",
            "2026-08-31",
            {"wiki/sources/a.md": "A", "wiki/sources/b.md": "B"},
            schema_version="3.0",
            purpose="ingest",
        )
        question_section = PUBLISH.section_body(text, "开放问题")
        self.assertIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, question_section)
        self.assertFalse(PUBLISH.section_bullet_blocks(text, "开放问题"))
        self.assertIn("### A unified benchmark is missing.", text)

    def test_schema_v3_open_question_placeholder_tracks_empty_transitions(self) -> None:
        action = valid_v3_plan()["topic_actions"][0]
        action["open_questions"] = []
        empty = PUBLISH.topic_page_text(
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-08-31",
            "2026-08-31",
            schema_version="3.0",
            purpose="ingest",
        )

        action["open_questions"] = [
            {
                "id": "oq-new",
                "origin": "ingest",
                "question": "Does the result transfer?",
                "source_refs": ["wiki/sources/a.md"],
                "status": "open",
            }
        ]
        nonempty = PUBLISH.merge_topic_page(
            empty,
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-09-01",
            schema_version="3.0",
            purpose="ingest",
        )
        self.assertIn("- Does the result transfer?", nonempty)
        self.assertNotIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, nonempty)

        action["open_questions"] = []
        empty_again = PUBLISH.merge_topic_page(
            nonempty,
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-09-02",
            schema_version="3.0",
            purpose="ingest",
        )
        self.assertNotIn("Does the result transfer?", empty_again)
        self.assertIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, empty_again)
        idempotent = PUBLISH.merge_topic_page(
            empty_again,
            action,
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
            "2026-09-02",
            schema_version="3.0",
            purpose="ingest",
        )
        self.assertEqual(idempotent, empty_again)

    def test_schema_v3_mining_update_preserves_narrative_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "ingest-v3.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            before = topic_path.read_text(encoding="utf-8")
            _, _, before_body = PUBLISH.parse_frontmatter(before)
            narrative_before = {
                section: PUBLISH.section_body(before_body, section)
                for section in ("概述", "综合认识", "证据注释")
            }
            mining = {
                "schema_version": "3.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "gap mining 2026-08"},
                "topic_actions": [
                    {
                        "action": "update_topic",
                        "id": "topic-1-mining",
                        "name": "Shared Topic",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "existing_page": "wiki/topics/Shared Topic.md",
                        "base_topic_sha256": hashlib.sha256(before.encode("utf-8")).hexdigest(),
                        "open_questions": [],
                        "research_gaps": [
                            {
                                "id": "rg-cross-group",
                                "origin": "mining",
                                "gap": "A cross-group control is missing.",
                                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                                "direction": "Add the same control to both settings.",
                                "continuity": "A later comparison can close the gap.",
                                "significance": "It would change whether the results are comparable.",
                                "status": "open",
                            }
                        ],
                    }
                ],
            }
            second = publish_plan(root, mining, "mining-v3.json")
            self.assertEqual(second.returncode, 0, second.stderr)
            after = topic_path.read_text(encoding="utf-8")
            _, _, after_body = PUBLISH.parse_frontmatter(after)
            for section, expected in narrative_before.items():
                actual = PUBLISH.section_body(after_body, section)
                self.assertEqual(actual, expected)
            self.assertNotIn("wiki-paper-card:", after)
            state_path = root / "wiki" / "meta" / "topic-state" / "Shared Topic.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            cross_group = next(
                item for item in state["research_gaps"]
                if item["id"] == "rg-cross-group"
            )
            self.assertEqual(cross_group["origin"], "mining")
            dashboard = (root / "wiki" / "meta" / "research.md").read_text(encoding="utf-8")
            self.assertIn("A cross-group control is missing.", dashboard)
            self.assertNotIn("wiki-paper-card:item", dashboard)

    def test_schema_v3_gap_progress_merges_and_remains_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "progress-initial.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"

            first_update = valid_v3_plan()
            action = first_update["topic_actions"][0]
            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(
                topic_path.read_bytes()
            ).hexdigest()
            action["research_gaps"][0]["progress_updates"] = [
                {
                    "id": "progress-shared-benchmark",
                    "source_refs": ["wiki/sources/b.md"],
                    "method": "Run both methods on one shared benchmark.",
                    "result": "The shared benchmark removes one comparison confound.",
                    "pointer": "[Paper: PDF p. 8, Table 3]",
                    "remaining_boundary": "Cross-domain transfer remains untested.",
                }
            ]
            second = publish_plan(root, first_update, "progress-first.json")
            self.assertEqual(second.returncode, 0, second.stderr)
            topic = topic_path.read_text(encoding="utf-8")
            self.assertIn("**已有进展 1。**", topic)
            self.assertIn("The shared benchmark removes one comparison confound.", topic)
            self.assertIn("**仍未解决。** Cross-domain transfer remains untested.", topic)
            self.assertIn("A unified benchmark is missing.", PUBLISH.section_body(topic, "研究空白与候选方向"))
            self.assertNotIn("A unified benchmark is missing.", PUBLISH.section_body(topic, "已解决的研究空白"))
            dashboard = (root / "wiki" / "meta" / "research.md").read_text(
                encoding="utf-8"
            )
            tree = (root / "wiki" / "meta" / "knowledge-tree.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("[已有进展] A unified benchmark is missing.", dashboard)
            self.assertIn("[已有进展] A unified benchmark is missing.", tree)

            second_update = valid_v3_plan()
            action = second_update["topic_actions"][0]
            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(
                topic_path.read_bytes()
            ).hexdigest()
            action["research_gaps"][0]["progress_updates"] = [
                {
                    "id": "progress-transfer-probe",
                    "source_refs": ["wiki/sources/a.md"],
                    "method": "Probe one shifted domain.",
                    "result": "The result transfers under a bounded shift.",
                    "pointer": "[Paper: PDF p. 9]",
                    "remaining_boundary": "Long-tail shifts remain untested.",
                }
            ]
            third = publish_plan(root, second_update, "progress-second.json")
            self.assertEqual(third.returncode, 0, third.stderr)
            state = json.loads(
                (root / "wiki" / "meta" / "topic-state" / "Shared Topic.json").read_text(
                    encoding="utf-8"
                )
            )
            gap = next(item for item in state["research_gaps"] if item["id"] == "rg-unified-benchmark")
            self.assertEqual(
                [item["id"] for item in gap["progress_updates"]],
                ["progress-shared-benchmark", "progress-transfer-probe"],
            )
            replay = publish_plan(root, second_update, "progress-second.json")
            self.assertEqual(replay.returncode, 0, replay.stderr)
            report = json.loads(
                (root / "progress-second-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["writes"], [])

    def test_gap_progress_upsert_preserves_order_and_updates_same_id(self) -> None:
        existing = [
            {
                "id": "progress-first",
                "source_refs": ["wiki/sources/a.md"],
                "method": "Old method.",
                "result": "Old result.",
                "pointer": "[Paper: PDF p. 2]",
                "remaining_boundary": "Boundary one.",
            },
            {
                "id": "progress-second",
                "source_refs": ["wiki/sources/b.md"],
                "method": "Second method.",
                "result": "Second result.",
                "pointer": "[Paper: PDF p. 3]",
                "remaining_boundary": "Boundary two.",
            },
        ]
        incoming = [
            {
                "id": "progress-first",
                "source_refs": ["wiki/sources/a.md"],
                "method": "Corrected method.",
                "result": "Corrected result.",
                "pointer": "[Paper: PDF p. 4]",
                "remaining_boundary": "Corrected boundary.",
            }
        ]
        merged = PUBLISH.merge_progress_updates(existing, incoming)
        self.assertEqual(
            [item["id"] for item in merged],
            ["progress-first", "progress-second"],
        )
        self.assertEqual(merged[0]["method"], "Corrected method.")
        self.assertEqual(merged[1]["result"], "Second result.")

    def test_schema_v3_stale_plan_blocks_all_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "ingest-v3.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            base = topic_path.read_text(encoding="utf-8")

            def mining_plan(item_id: str, question: str) -> dict:
                return {
                    "schema_version": "3.0",
                    "purpose": "mining",
                    "batch": {"source_pages": [], "label": item_id},
                    "topic_actions": [
                        {
                            "action": "update_topic",
                            "id": item_id,
                            "name": "Shared Topic",
                            "papers": ["wiki/sources/a.md"],
                            "existing_page": "wiki/topics/Shared Topic.md",
                            "base_topic_sha256": hashlib.sha256(base.encode("utf-8")).hexdigest(),
                            "open_questions": [
                                {
                                    "id": item_id,
                                    "origin": "mining",
                                    "question": question,
                                    "source_refs": ["wiki/sources/a.md"],
                                    "status": "open",
                                }
                            ],
                            "research_gaps": [],
                        }
                    ],
                }

            accepted = publish_plan(root, mining_plan("oq-first", "First question?"), "first.json")
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            after_first = topic_path.read_text(encoding="utf-8")
            stale = publish_plan(root, mining_plan("oq-second", "Second question?"), "second.json")
            self.assertEqual(stale.returncode, 1)
            self.assertIn("stale_topic_plan", stale.stderr)
            self.assertEqual(topic_path.read_text(encoding="utf-8"), after_first)
            self.assertNotIn("Second question?", after_first)

    def test_schema_v3_answer_keeps_item_id_and_archives_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            initial = valid_v3_plan()
            initial["topic_actions"][0]["research_gaps"][0]["origin"] = "mining"
            first = publish_plan(root, initial, "initial.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            existing = topic_path.read_text(encoding="utf-8")
            update = valid_v3_plan()
            action = update["topic_actions"][0]
            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(existing.encode("utf-8")).hexdigest()
            action["research_gaps"] = [
                {
                    "id": "rg-unified-benchmark",
                    "origin": "mining",
                    "gap": "A unified benchmark is missing.",
                    "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                    "direction": "Run both methods on one benchmark.",
                    "continuity": "The current evidence closes the recorded gap.",
                    "status": "answered",
                    "answered_by": ["wiki/sources/b.md"],
                    "answered_pointer": "[Paper: PDF p. 6]",
                    "resolution_method": "Run both methods under one controlled benchmark.",
                    "resolution_summary": "The controlled comparison closes the recorded comparability gap.",
                    "resolution_scope": "The conclusion covers two matched settings.",
                }
            ]
            action["narrative"]["synthesis_blocks"][0]["paragraphs"][0]["text"] = (
                "The two papers now provide a unified comparison that answers the recorded gap."
            )
            second = publish_plan(root, update, "answered.json")
            self.assertEqual(second.returncode, 0, second.stderr)
            topic = topic_path.read_text(encoding="utf-8")
            open_part, archive_part = topic.split("## 已解决的研究空白", 1)
            self.assertNotIn("A unified benchmark is missing.", open_part)
            self.assertIn("A unified benchmark is missing.", archive_part)
            self.assertNotIn("wiki-paper-card:", topic)
            state = json.loads(
                (root / "wiki" / "meta" / "topic-state" / "Shared Topic.json").read_text(
                    encoding="utf-8"
                )
            )
            archived = next(
                item for item in state["research_gaps"]
                if item["id"] == "rg-unified-benchmark"
            )
            self.assertEqual(archived["origin"], "mining")
            self.assertEqual(archived["status"], "answered")
            self.assertIn("answers the recorded gap", topic)
            self.assertIn("**解决方法。** Run both methods under one controlled benchmark.", archive_part)
            self.assertIn("**解决结果。** The controlled comparison closes the recorded comparability gap.", archive_part)
            self.assertIn("**适用范围。** The conclusion covers two matched settings.", archive_part)

    def test_schema_v3_old_answered_gap_renders_available_fields(self) -> None:
        lines = PUBLISH.render_v3_resolved_research_gaps(
            [
                {
                    "id": "rg-legacy-answer",
                    "origin": "ingest",
                    "gap": "Legacy gap",
                    "source_refs": ["wiki/sources/a.md"],
                    "direction": "Legacy direction",
                    "continuity": "Legacy continuity",
                    "status": "answered",
                    "answered_by": ["wiki/sources/b.md"],
                    "answered_pointer": "[Paper: PDF p. 8]",
                }
            ],
            {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
        )
        rendered = "\n".join(lines)
        self.assertIn("### Legacy gap", rendered)
        self.assertIn("**解决论文。** [[b|Paper B]]", rendered)
        self.assertIn("**证据位置。** [Paper: PDF p. 8]", rendered)
        self.assertNotIn("历史记录未提供", rendered)

    def test_schema_v3_mining_create_is_stub_and_plan_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            ingest = publish_plan(root, valid_v3_plan(), "ingest.json")
            self.assertEqual(ingest.returncode, 0, ingest.stderr)
            mining = {
                "schema_version": "3.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "candidate topic"},
                "topic_actions": [
                    {
                        "action": "create_topic",
                        "id": "candidate-topic",
                        "name": "Candidate Topic",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "index_summary": "A candidate cross-paper evidence space.",
                        "open_questions": [],
                        "research_gaps": [
                            {
                                "id": "rg-candidate",
                                "origin": "mining",
                                "gap": "A candidate comparison is missing.",
                                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                                "direction": "Run a shared comparison.",
                                "continuity": "A later ingest can substantiate the topic.",
                                "significance": "It would determine whether the topic should be promoted.",
                                "status": "open",
                            }
                        ],
                    }
                ],
            }
            first = publish_plan(root, mining, "candidate.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Candidate Topic.md"
            topic = topic_path.read_text(encoding="utf-8")
            self.assertIn('status: "stub"', topic)
            self.assertIn(PUBLISH.MINING_STUB_OVERVIEW, topic)
            self.assertIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, topic)
            self.assertNotIn("wiki-paper-card:", topic)
            self.assertNotIn("### ", PUBLISH.section_body(topic, "综合认识"))
            dashboard = (root / "wiki" / "meta" / "research.md").read_text(
                encoding="utf-8"
            )
            tree = (root / "wiki" / "meta" / "knowledge-tree.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, dashboard)
            self.assertNotIn(PUBLISH.NO_OPEN_QUESTIONS_TEXT, tree)
            second = publish_plan(root, mining, "candidate.json")
            self.assertEqual(second.returncode, 0, second.stderr)
            report = json.loads((root / "candidate-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["writes"], [])
            self.assertEqual(topic_path.read_text(encoding="utf-8"), topic)

    def test_schema_v3_second_batch_rewrites_narrative_and_preserves_other_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "first-batch.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            first_text = topic_path.read_text(encoding="utf-8")
            custom_section = "\n## 人工维护笔记\n\n这一节不属于 publisher 的受控区域。\n"
            topic_path.write_text(first_text + custom_section, encoding="utf-8")

            for name, title in (("c", "Paper C"), ("d", "Paper D"), ("e", "Paper E")):
                (root / "work" / name).mkdir(parents=True)
                (root / "work" / name / "paper-card.md").write_text(
                    source_card(title, f"wiki/sources/{name}.md"), encoding="utf-8"
                )
                (root / "work" / name / "paper-digest.json").write_text(
                    json.dumps(digest({"one_sentence_summary": f"{title} summary."})),
                    encoding="utf-8",
                )

            update = valid_v3_plan()
            update["batch"]["source_pages"] = [
                {
                    "source_ref": f"wiki/sources/{name}.md",
                    "work_dir": f"work/{name}",
                    "title": title,
                }
                for name, title in (("c", "Paper C"), ("d", "Paper D"), ("e", "Paper E"))
            ]
            action = update["topic_actions"][0]
            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(
                topic_path.read_bytes()
            ).hexdigest()
            action["papers"] = [
                f"wiki/sources/{name}.md" for name in ("a", "b", "c", "d", "e")
            ]
            action["key_findings"][0]["source_refs"] = list(action["papers"])
            action["key_findings"][0]["pointers"] = [
                {
                    "source_ref": f"wiki/sources/{name}.md",
                    "pointer": f"[Paper: PDF p. {index}]",
                }
                for index, name in enumerate(("a", "b", "c", "d", "e"), start=3)
            ]
            action["key_findings"].append(
                {
                    "id": "kf-transfer-challenge",
                    "claim": "Paper C reports a failure under a shifted evaluation setting.",
                    "kind": "conflict",
                    "source_refs": ["wiki/sources/c.md"],
                    "pointers": [
                        {
                            "source_ref": "wiki/sources/c.md",
                            "pointer": "[Paper: PDF p. 8]",
                        }
                    ],
                }
            )
            action["contradictions"] = [
                {
                    "id": "ct-transfer-boundary",
                    "position_a": "The shared result transfers across the original settings.",
                    "position_a_source_ref": "wiki/sources/a.md",
                    "position_a_pointer": "[Paper: PDF p. 3]",
                    "position_b": "The result fails after the evaluation setting shifts.",
                    "position_b_source_ref": "wiki/sources/c.md",
                    "position_b_pointer": "[Paper: PDF p. 8]",
                    "resolving_evidence": "Evaluate all methods under one controlled shift.",
                }
            ]
            action["narrative"]["overview"]["paragraphs"][0]["text"] = (
                "Five papers now delimit where the shared result transfers and where it fails."
            )
            action["narrative"]["synthesis_blocks"][0]["heading"] = (
                "The five-paper evidence narrows the transfer boundary"
            )
            action["narrative"]["synthesis_blocks"][0]["paragraphs"][0]["text"] = (
                "Across five settings, the result is consistent only under a shared evaluation condition."
            )
            action["narrative"]["synthesis_blocks"].extend(
                [
                    {
                        "id": "synthesis-evaluation-shift",
                        "heading": "Evaluation shifts expose the main failure mode",
                        "paragraphs": [
                            {
                                "text": "Paper C shows that the shared result can fail after the evaluation setting changes.",
                                "finding_refs": ["kf-transfer-challenge"],
                            },
                            {
                                "text": "This separates evidence about the original settings from evidence about transfer under controlled shift.",
                                "finding_refs": ["kf-transfer-challenge"],
                            },
                        ],
                    },
                    {
                        "id": "synthesis-comparability",
                        "heading": "A common protocol is needed for method choice",
                        "paragraphs": [
                            {
                                "text": "The five papers cannot yet support a direct method ranking because their evaluation conditions differ.",
                                "finding_refs": ["kf-shared-result", "kf-transfer-challenge"],
                            },
                            {
                                "text": "A controlled shared protocol would distinguish method effects from setting effects and change which method is preferred.",
                                "finding_refs": ["kf-shared-result", "kf-transfer-challenge"],
                            },
                        ],
                    },
                ]
            )
            action["narrative"]["controversy_blocks"] = [
                {
                    "id": "controversy-transfer-boundary",
                    "heading": "Transfer depends on how the evaluation setting shifts",
                    "paragraphs": [
                        {
                            "text": "The original studies support transfer, whereas Paper C reports failure after a controlled shift. Evaluate all methods under one controlled shift to distinguish setting effects from method effects.",
                            "finding_refs": [
                                "kf-shared-result",
                                "kf-transfer-challenge",
                            ],
                            "contradiction_refs": ["ct-transfer-boundary"],
                        },
                        {
                            "text": "The disagreement may therefore reflect evaluation design rather than an intrinsic conflict between methods.",
                            "finding_refs": [
                                "kf-shared-result",
                                "kf-transfer-challenge",
                            ],
                            "contradiction_refs": ["ct-transfer-boundary"],
                        }
                    ],
                }
            ]
            action["comparisons"] = [
                {
                    "source_ref": f"wiki/sources/{name}.md",
                    "paper": title,
                    "method": f"Method {name.upper()}",
                    "intervention_granularity": "sample",
                    "main_result": "Boundary evidence",
                    "boundary": "One setting",
                    "pointer": "[Paper: PDF p. 5]",
                }
                for name, title in (("c", "Paper C"), ("d", "Paper D"), ("e", "Paper E"))
            ]
            action["open_questions"] = []
            action["research_gaps"] = []

            second = publish_plan(root, update, "second-batch.json")
            self.assertEqual(second.returncode, 0, second.stderr)
            updated = topic_path.read_text(encoding="utf-8")
            self.assertNotIn(
                "This topic studies whether the shared result transfers across settings.",
                updated,
            )
            self.assertIn("Five papers now delimit", updated)
            self.assertEqual(updated.count("The five-paper evidence narrows"), 1)
            self.assertIn("[[a|Paper A]] [Paper: PDF p. 3]", updated)
            self.assertIn("[[b|Paper B]] [Paper: PDF p. 4]", updated)
            self.assertIn("Transfer depends on how the evaluation setting shifts", updated)
            self.assertIn(
                "Evaluate all methods under one controlled shift to distinguish",
                updated,
            )
            self.assertNotIn("wiki-paper-card:", updated)
            self.assertLess(
                updated.index("## 争议与不确定"),
                updated.index("## 论文与方法对照"),
            )
            self.assertRegex(updated, r"\[\^topic-evidence-\d+\]:")
            self.assertIn(custom_section.strip(), updated)
            comparison = PUBLISH.section_body(updated, "论文与方法对照")
            for title in ("Paper A", "Paper C", "Paper D", "Paper E"):
                self.assertIn(title, comparison)
            fields, lists, _ = PUBLISH.parse_frontmatter(updated)
            self.assertEqual(
                lists["sources"],
                [f"wiki/sources/{name}.md" for name in ("a", "b", "c", "d", "e")],
            )

    def test_schema_v3_old_topic_requires_explicit_migration_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            old_plan = valid_plan()
            first = publish_plan(root, old_plan, "legacy.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            legacy_text = topic_path.read_text(encoding="utf-8")
            wiki_before = {
                path.relative_to(root / "wiki"): path.read_bytes()
                for path in (root / "wiki").rglob("*")
                if path.is_file()
            }

            update = valid_v3_plan()
            action = update["topic_actions"][0]
            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(
                legacy_text.encode("utf-8")
            ).hexdigest()
            result = publish_plan(root, update, "migration-required.json")
            self.assertEqual(result.returncode, 1)
            self.assertIn("narrative_migration_required", result.stderr)
            self.assertEqual(topic_path.read_text(encoding="utf-8"), legacy_text)
            wiki_after = {
                path.relative_to(root / "wiki"): path.read_bytes()
                for path in (root / "wiki").rglob("*")
                if path.is_file()
            }
            self.assertEqual(wiki_after, wiki_before)

    def test_schema_v3_managed_page_migrates_to_clean_markdown_and_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            plan = valid_v3_plan()
            action = plan["topic_actions"][0]
            rendered = PUBLISH.render_v3_narrative(
                action,
                {"wiki/sources/a.md": "Paper A", "wiki/sources/b.md": "Paper B"},
                {"wiki/sources/a.md": "A", "wiki/sources/b.md": "B"},
            )
            frontmatter = PUBLISH.render_frontmatter(
                ["topic"],
                "2026-08-31",
                "2026-08-31",
                "draft",
                sources=action["papers"],
                aliases=[],
                extra=[("last_topic_action_sha256", PUBLISH.action_fingerprint(action))],
            )
            question = PUBLISH.render_open_questions(
                action["open_questions"], {}, {}
            )[0]
            gap = PUBLISH.render_research_gaps(
                action["research_gaps"], {}, {}
            )
            legacy_lines = [
                frontmatter.rstrip(),
                "# Shared Topic",
                "",
                "## 概述",
                "",
                *PUBLISH.managed_block_lines("overview", rendered["overview"]),
                "",
                "## 综合认识",
                "",
                *PUBLISH.managed_block_lines("synthesis", rendered["synthesis"]),
                "",
                "## 争议与不确定",
                "",
                *PUBLISH.managed_block_lines("controversies", []),
                "",
                "## 论文与方法对照",
                "",
                "## 开放问题",
                "",
                *question,
                "",
                "## 研究空白与候选方向",
                "",
                *gap,
            ]
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            legacy = "\n".join(legacy_lines).rstrip() + "\n"
            topic_path.write_text(legacy, encoding="utf-8")

            action["action"] = "update_topic"
            action["existing_page"] = "wiki/topics/Shared Topic.md"
            action["base_topic_sha256"] = hashlib.sha256(
                legacy.encode("utf-8")
            ).hexdigest()
            result = publish_plan(root, plan, "migrate-legacy-v3.json")
            self.assertEqual(result.returncode, 0, result.stderr)

            migrated = topic_path.read_text(encoding="utf-8")
            self.assertNotIn("wiki-paper-card:", migrated)
            self.assertNotIn("last_topic_action_sha256", migrated)
            self.assertIn("### A unified benchmark is missing. [待验证]", migrated)
            state = json.loads(
                (root / "wiki" / "meta" / "topic-state" / "Shared Topic.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(state["open_questions"][0]["id"], "oq-transfer")
            self.assertEqual(state["research_gaps"][0]["origin"], "ingest")

    def test_schema2_cannot_update_clean_schema3_topic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "v3.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            before = topic_path.read_text(encoding="utf-8")

            legacy_plan = valid_plan()
            legacy_action = legacy_plan["topic_actions"][0]
            legacy_action["action"] = "update_topic"
            legacy_action["existing_page"] = "wiki/topics/Shared Topic.md"
            second = publish_plan(root, legacy_plan, "schema2-update.json")
            self.assertEqual(second.returncode, 1)
            self.assertIn("schema2_cannot_update_schema3_topic", second.stderr)
            self.assertEqual(topic_path.read_text(encoding="utf-8"), before)

    def test_schema_v3_mining_answer_emits_narrative_refresh_warning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_vault(root)
            first = publish_plan(root, valid_v3_plan(), "ingest.json")
            self.assertEqual(first.returncode, 0, first.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            before = topic_path.read_text(encoding="utf-8")
            mining = {
                "schema_version": "3.0",
                "purpose": "mining",
                "batch": {"source_pages": [], "label": "answer audit"},
                "topic_actions": [
                    {
                        "action": "update_topic",
                        "id": "topic-1-mining-answer",
                        "name": "Shared Topic",
                        "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "existing_page": "wiki/topics/Shared Topic.md",
                        "base_topic_sha256": hashlib.sha256(
                            before.encode("utf-8")
                        ).hexdigest(),
                        "open_questions": [
                            {
                                "id": "oq-transfer",
                                "origin": "ingest",
                                "question": "Does the result transfer to a shared benchmark?",
                                "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                                "status": "answered",
                                "answered_by": ["wiki/sources/b.md"],
                                "answered_pointer": "[Paper: PDF p. 7]",
                            }
                        ],
                        "research_gaps": [],
                    }
                ],
            }
            result = publish_plan(root, mining, "mining-answer.json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (root / "mining-answer-report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(
                any("narrative_refresh_recommended" in item for item in report["warnings"])
            )

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

    def test_merge_removes_named_questions_and_gaps(self) -> None:
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
            "## 开放问题\n\n- Q1 完整问题句\n- Q2\n\n"
            "## 研究空白与候选方向\n\n"
            "- gap A（来源：[[a|a]]；可检验方向：d；承接：未来可答。）\n"
            "- gap B\n"
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
            "remove_open_questions": ["Q1"],
            "remove_research_gaps": ["gap B"],
            "annotate_research_gaps": [
                {"match": "gap A", "note": "同类空白见 [[X]]"}
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
        self.assertNotIn("Q1", merged)
        self.assertIn("- Q2", merged)
        self.assertNotIn("gap B", merged)
        self.assertIn("未来可答；同类空白见 [[X]]。）", merged)

    def test_annotate_falls_back_to_sub_bullet(self) -> None:
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
            "## 研究空白与候选方向\n\n- gap C\n"
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
            "annotate_research_gaps": [
                {"match": "gap C", "note": "同类空白见 [[Y]]"}
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
        self.assertIn("- gap C", merged)
        self.assertIn("相关空白：同类空白见 [[Y]]", merged)

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
            self.assertIn("### Shared Topic", text)
            self.assertIn("Compare the two approaches.", text)
            self.assertIn("#### 论文", text)
            self.assertIn("[[a|a]]", text)
            self.assertIn("#### 开放问题", text)
            self.assertIn("- Topic question", text)
            self.assertIn("#### 研究空白", text)
            self.assertIn("- Missing benchmark", text)
            # Nested open items carry no 来源 suffix (the topic is the parent).
            self.assertNotIn("— 来源：", text)
            self.assertNotIn("### 实体", text)
            agent_tree_path = root / "wiki" / "meta" / "agent-tree.md"
            self.assertFalse(agent_tree_path.exists())

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
                                "significance": "会改变跨组方法如何比较的结论",
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
                                "significance": "会改变该方向的选题判断",
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
                                "significance": "It would change which page the gap traces to.",
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
            (wiki / "sources" / "papers" / "rag" / "z.md").write_text(
                "# Paper Z\n", encoding="utf-8"
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
                "- [[wiki/sources/papers/rag/z.md|z]] - paper z\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            self.assertIsNotNone(tree)
            assert tree is not None
            # Topic t spans rag and llm-opt sources -> cross-domain section
            # with papers, questions, and gaps nested under the topic node.
            self.assertIn("## 跨领域", tree)
            self.assertIn("### T", tree)
            self.assertIn("topic t", tree)
            self.assertIn("#### 论文", tree)
            self.assertIn("[[x|x]] — paper x", tree)
            self.assertIn("[[y|y]] — paper y", tree)
            self.assertIn("#### 开放问题", tree)
            self.assertIn("- Q1", tree)
            self.assertIn("#### 研究空白", tree)
            self.assertIn("- gap1", tree)
            # Nested open items carry no 来源 suffix (the topic is the parent).
            self.assertNotIn("— 来源：", tree)
            # Unassigned paper z stays grouped in its own domain.
            self.assertIn("## rag", tree)
            self.assertIn("### 未归入主题的论文", tree)
            self.assertIn("[[z|z]] — paper z", tree)
            # llm-opt has no topics and no unassigned papers -> skipped.
            self.assertNotIn("## llm-opt", tree)
            self.assertLess(tree.index("## rag"), tree.index("## 跨领域"))

    def test_knowledge_tree_supports_progressive_topic_paper_and_gap_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "topics"):
                (wiki / sub).mkdir(parents=True)
            (wiki / "sources" / "papers" / "rag" / "x.md").write_text(
                "# Paper X\n", encoding="utf-8"
            )
            (wiki / "sources" / "papers" / "rag" / "z.md").write_text(
                "# Paper Z\n", encoding="utf-8"
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
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "- [[wiki/sources/papers/rag/z.md|z]] - paper z\n"
                "## 主题\n"
                "- [[wiki/topics/t.md|T]] - topic t\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            assert tree is not None
            # One shared tree exposes the topic signpost, its assigned paper,
            # open items, and the unassigned-paper fallback branch.
            self.assertIn("## rag", tree)
            self.assertIn("### T", tree)
            self.assertIn("topic t", tree)
            self.assertIn("[[x|x]] — paper x", tree)
            self.assertIn("#### 开放问题", tree)
            self.assertIn("- Q1", tree)
            self.assertIn("#### 研究空白", tree)
            self.assertIn("- gap1", tree)
            self.assertIn("### 未归入主题的论文", tree)
            self.assertIn("[[z|z]] — paper z", tree)

    def test_knowledge_tree_lists_paper_under_each_assigning_topic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for sub in ("sources/papers/rag", "topics"):
                (wiki / sub).mkdir(parents=True)
            (wiki / "sources" / "papers" / "rag" / "x.md").write_text(
                "# Paper X\n", encoding="utf-8"
            )
            for name in ("t1", "t2"):
                (wiki / "topics" / f"{name}.md").write_text(
                    "---\n"
                    "tags: [topic]\n"
                    'sources:\n  - "wiki/sources/papers/rag/x.md"\n'
                    "aliases:\n"
                    "status: stub\n"
                    "---\n\n"
                    f"# {name.capitalize()}\n\n",
                    encoding="utf-8",
                )
            (wiki / "index.md").write_text(
                "# Wiki 索引\n\n"
                "## 来源\n"
                "- [[wiki/sources/papers/rag/x.md|x]] - paper x\n"
                "## 主题\n"
                "- [[wiki/topics/t1.md|t1]] - topic one\n"
                "- [[wiki/topics/t2.md|t2]] - topic two\n",
                encoding="utf-8",
            )
            tree = PUBLISH.build_knowledge_tree(root)
            self.assertIsNotNone(tree)
            assert tree is not None
            # Multi-membership: the paper is listed once per assigning topic.
            self.assertEqual(tree.count("[[x|x]]"), 2)
            first = tree.index("[[x|x]]")
            self.assertLess(tree.index("### t1"), first)
            self.assertLess(tree.index("### t2"), tree.index("[[x|x]]", first + 1))
            # The paper is assigned by both topics -> no unassigned group.
            self.assertNotIn("未归入主题的论文", tree)

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
            agent_tree_path = root / "wiki" / "meta" / "agent-tree.md"
            original = tree_path.read_text(encoding="utf-8")
            legacy_agent = "# Legacy agent tree\n\nkeep this file untouched\n"
            agent_tree_path.write_text(legacy_agent, encoding="utf-8")
            second = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(tree_path.read_text(encoding="utf-8"), original)
            self.assertEqual(agent_tree_path.read_text(encoding="utf-8"), legacy_agent)
            report = json.loads((root / "publish-report.json").read_text(encoding="utf-8"))
            self.assertFalse(
                any(write.get("kind") == "agent-tree" for write in report["writes"])
            )


if __name__ == "__main__":
    unittest.main()
