#!/usr/bin/env python3
"""Regression tests for the batch link plan audit."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_link_plan.py"
SPEC = importlib.util.spec_from_file_location("audit_link_plan", SCRIPT_PATH)
assert SPEC and SPEC.loader
LINK_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LINK_AUDIT)


def valid_link_plan() -> dict:
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
                "key_findings": [
                    {
                        "claim": "Both papers agree on the concept.",
                        "kind": "consensus",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "pointer": "[Paper: PDF p. 3, Fig. 1]",
                    }
                ],
                "contradictions": [],
                "open_questions": [],
                "research_gaps": [],
                "existing_page": None,
            }
        ],
    }


def valid_v3_link_plan() -> dict:
    plan = valid_link_plan()
    plan["schema_version"] = "3.0"
    plan["workflow_mode"] = "wiki-full"
    action = plan["topic_actions"][0]
    action.pop("summary")
    action["index_summary"] = "Two papers establish a shared topic with a remaining boundary."
    action["page_status"] = "draft"
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
                    "text": "The topic compares a shared result and its evidence boundary.",
                    "finding_refs": ["kf-shared-result"],
                },
                {
                    "id": "overview-state",
                    "text": "Current evidence supports the result in two settings, while cross-setting comparability remains unresolved.",
                    "finding_refs": ["kf-shared-result"],
                }
            ]
        },
        "synthesis_blocks": [
            {
                "id": "synthesis-shared-result",
                "heading": "The shared result is supported across both papers",
                "paragraphs": [
                    {
                        "text": "The two papers support the result under different settings.",
                        "finding_refs": ["kf-shared-result"],
                    },
                    {
                        "text": "Because the studies do not share one benchmark, the evidence supports a bounded comparison rather than universal transfer.",
                        "finding_refs": ["kf-shared-result"],
                    }
                ],
            }
        ],
        "controversy_blocks": [],
    }
    action["open_questions"] = [
        {
            "id": "oq-boundary",
            "origin": "ingest",
            "question": "Does the result hold outside the measured settings?",
            "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            "status": "open",
        }
    ]
    action["research_gaps"] = [
        {
            "id": "rg-unified-test",
            "origin": "ingest",
            "gap": "Current evidence cannot support a fair method comparison.",
            "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
            "direction": "Run both methods on one benchmark.",
            "continuity": "A later paper can perform the comparison.",
            "significance": "It would change which method is preferred.",
            "reader_narrative": [
                "The papers cannot yet support a method choice because their results come from different benchmarks.",
                "A matched comparison would show whether the reported ranking reflects the methods or the evaluation setting.",
            ],
            "status": "open",
        }
    ]
    return plan


def valid_v3_refresh_plan() -> dict:
    plan = valid_v3_link_plan()
    plan["purpose"] = "refresh"
    plan.pop("workflow_mode")
    plan["batch"] = {"source_pages": [], "label": "topic refresh 2026-09"}
    action = plan["topic_actions"][0]
    action["action"] = "update_topic"
    action["existing_page"] = "wiki/topics/Shared Topic.md"
    action["base_topic_sha256"] = "a" * 64
    for field in ("open_questions", "research_gaps", "page_status", "category"):
        action.pop(field, None)
    return plan


class LinkPlanAuditTests(unittest.TestCase):
    def test_manifest_requires_exact_batch_membership_and_paths(self) -> None:
        plan = valid_link_plan()
        plan["batch"]["source_pages"][0]["source_ref"] = "wiki/sources/wrong-a.md"
        plan["batch"]["source_pages"].pop()
        manifest = {
            "schema_version": "1.0",
            "work_root": "work",
            "paper_count": 2,
            "papers": [
                {
                    "source_path": "raw/a.pdf",
                    "source_sha256": "a" * 64,
                    "source_ref": "wiki/sources/a.md",
                    "work_dir": "work/a",
                },
                {
                    "source_path": "raw/b.pdf",
                    "source_sha256": "b" * 64,
                    "source_ref": "wiki/sources/b.md",
                    "work_dir": "work/b",
                },
            ],
        }
        report = LINK_AUDIT.audit(plan, manifest)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("manifest_source_ref_mismatch", codes)
        self.assertIn("manifest_batch_missing", codes)
        self.assertEqual(report["summary"]["status"], "fail")

    def test_valid_schema_v3_plan_passes(self) -> None:
        report = LINK_AUDIT.audit(valid_v3_link_plan())
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])
        self.assertEqual(report["schema_version"], "3.0")
        self.assertEqual(report["workflow_mode"], "wiki-full")

    def test_schema_v3_ingest_requires_valid_workflow_mode(self) -> None:
        plan = valid_v3_link_plan()
        plan.pop("workflow_mode")
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "workflow_mode" for item in report["findings"]))

        plan["workflow_mode"] = "card-only"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "workflow_mode" for item in report["findings"]))

    def test_schema_v3_non_ingest_rejects_workflow_mode(self) -> None:
        plan = valid_v3_refresh_plan()
        plan["workflow_mode"] = "wiki-topic"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "workflow_mode_forbidden" for item in report["findings"])
        )

    def test_wiki_topic_accepts_empty_research_gaps(self) -> None:
        plan = valid_v3_link_plan()
        plan["workflow_mode"] = "wiki-topic"
        plan["topic_actions"][0]["research_gaps"] = []
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_wiki_topic_rejects_research_gap_content_and_mutations(self) -> None:
        plan = valid_v3_link_plan()
        plan["workflow_mode"] = "wiki-topic"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "workflow_mode_research_gaps" for item in report["findings"])
        )

        for field, value in (
            ("remove_research_gap_ids", ["rg-unified-test"]),
            ("remove_research_gaps", ["unified test"]),
            ("annotate_research_gaps", [{"id": "rg-unified-test", "note": "note"}]),
        ):
            with self.subTest(field=field):
                plan = valid_v3_link_plan()
                plan["workflow_mode"] = "wiki-topic"
                action = plan["topic_actions"][0]
                action["research_gaps"] = []
                action[field] = value
                report = LINK_AUDIT.audit(plan)
                self.assertTrue(
                    any(
                        item["code"] == "workflow_mode_gap_mutation"
                        and item.get("details", {}).get("field") == field
                        for item in report["findings"]
                    ),
                    report["findings"],
                )

    def test_schema_v3_refresh_plan_passes_without_batch_sources(self) -> None:
        report = LINK_AUDIT.audit(valid_v3_refresh_plan())
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_schema_v3_refresh_rejects_open_item_mutation_and_create(self) -> None:
        plan = valid_v3_refresh_plan()
        action = plan["topic_actions"][0]
        action["action"] = "create_topic"
        action["open_questions"] = []
        report = LINK_AUDIT.audit(plan)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("refresh_action", codes)
        self.assertIn("refresh_field_forbidden", codes)

    def test_schema_v3_refresh_batches_multiple_distinct_topics(self) -> None:
        plan = valid_v3_refresh_plan()
        second = json.loads(json.dumps(plan["topic_actions"][0]))
        second.update(
            {
                "id": "topic-2-refresh",
                "name": "Second Topic",
                "existing_page": "wiki/topics/Second Topic.md",
            }
        )
        plan["topic_actions"].append(second)
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_schema_v3_update_requires_base_topic_hash(self) -> None:
        plan = valid_v3_link_plan()
        action = plan["topic_actions"][0]
        action["action"] = "update_topic"
        action["existing_page"] = "wiki/topics/Shared Topic.md"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "missing_string"
                and item.get("details", {}).get("field") == "base_topic_sha256"
                for item in report["findings"]
            )
        )
        action["base_topic_sha256"] = "a" * 64
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_schema_v3_mining_update_rejects_narrative_fields(self) -> None:
        plan = valid_v3_link_plan()
        plan["purpose"] = "mining"
        plan.pop("workflow_mode")
        plan["batch"] = {"source_pages": [], "label": "gap mining 2026-08"}
        action = plan["topic_actions"][0]
        action["action"] = "update_topic"
        action["existing_page"] = "wiki/topics/Shared Topic.md"
        action["base_topic_sha256"] = "a" * 64
        action.pop("index_summary")
        action.pop("page_status")
        report = LINK_AUDIT.audit(plan)
        forbidden = {
            item.get("details", {}).get("field")
            for item in report["findings"]
            if item["code"] == "mining_field_forbidden"
        }
        self.assertEqual(
            forbidden,
            {"narrative", "comparisons", "key_findings", "contradictions"},
        )

    def test_schema_v3_mining_groups_multiple_candidates_in_one_topic_action(self) -> None:
        plan = valid_v3_link_plan()
        plan["purpose"] = "mining"
        plan.pop("workflow_mode")
        plan["batch"] = {"source_pages": [], "label": "gap mining 2026-09"}
        action = plan["topic_actions"][0]
        action.update(
            {
                "action": "update_topic",
                "existing_page": "wiki/topics/Shared Topic.md",
                "base_topic_sha256": "a" * 64,
                "research_gaps": [
                    action["research_gaps"][0],
                    {
                        "id": "rg-transfer-test",
                        "origin": "mining",
                        "gap": "A transfer test is missing.",
                        "source_refs": ["wiki/sources/a.md"],
                        "direction": "Test one shifted setting.",
                        "continuity": "A later paper can run the shifted test.",
                        "significance": "It would delimit the result's scope.",
                        "status": "open",
                    },
                ],
            }
        )
        for field in ("index_summary", "page_status", "narrative", "comparisons", "key_findings", "contradictions"):
            action.pop(field, None)
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_schema_v3_flat_comparison_requires_source_ref(self) -> None:
        plan = valid_v3_link_plan()
        plan["topic_actions"][0]["comparisons"] = [
            {"paper": "Paper A", "method": "Method A"}
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "missing_string"
                and item.get("details", {}).get("field") == "source_ref"
                for item in report["findings"]
            )
        )

    def test_schema_v3_flat_comparison_rejects_duplicate_source_ref(self) -> None:
        plan = valid_v3_link_plan()
        row = {
            "source_ref": "wiki/sources/a.md",
            "paper": "Paper A",
            "method": "Method A",
        }
        plan["topic_actions"][0]["comparisons"] = [row, dict(row)]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "duplicate_comparison_source"
                for item in report["findings"]
            )
        )

    def test_schema_v3_open_items_require_unique_ids_and_origin(self) -> None:
        plan = valid_v3_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"][0]["id"] = "oq-boundary"
        action["research_gaps"][0]["origin"] = "unknown"
        report = LINK_AUDIT.audit(plan)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("duplicate_item_id", codes)
        self.assertIn("item_origin", codes)

    def test_schema_v3_research_gap_progress_requires_traceable_fields(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        gap["progress_updates"] = [
            {
                "id": "progress-shared-benchmark",
                "source_refs": ["wiki/sources/b.md"],
                "method": "Run both methods on one shared benchmark.",
                "result": "The shared benchmark removes one comparison confound.",
                "pointer": "[Paper: PDF p. 8, Table 3]",
                "remaining_boundary": "Cross-domain transfer remains untested.",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

        gap["progress_updates"][0].pop("method")
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "missing_string"
                and item.get("details", {}).get("field") == "method"
                for item in report["findings"]
            )
        )

    def test_schema_v3_research_gap_reader_narrative_is_bounded(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        gap["reader_narrative"] = ["one", "two", "three"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_reader_narrative" and item["level"] == "error" for item in report["findings"])
        )

        gap.pop("reader_narrative")
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_reader_narrative" and item["level"] == "warning" for item in report["findings"])
        )

    def test_schema_v3_research_gap_reader_narrative_must_be_prose(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        gap["reader_narrative"] = ["- Evidence is missing."]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_reader_narrative" and item["level"] == "error" for item in report["findings"])
        )

    def test_schema_v3_research_gap_heading_readability_warns_without_blocking(self) -> None:
        cases = {
            "缺少能够比较不同方法效果的共同评估框架": "weak_opening",
            "现有研究分别考察材料类型、采样频率、测量环境，尚不能确定这些因素的独立作用": "dense_enumeration",
            "现有证据尚不能确定不同数据来源下模型性能差异是否来自训练策略本身而不是样本组成和评价流程的系统变化": "long_heading",
        }
        for heading, expected_issue in cases.items():
            with self.subTest(heading=heading):
                plan = valid_v3_link_plan()
                plan["topic_actions"][0]["research_gaps"][0]["gap"] = heading
                report = LINK_AUDIT.audit(plan)
                warnings = [
                    item
                    for item in report["findings"]
                    if item["code"] == "research_gap_heading_readability"
                ]
                self.assertEqual(report["summary"]["errors"], 0, report["findings"])
                self.assertEqual(len(warnings), 1, report["findings"])
                self.assertIn(expected_issue, warnings[0]["details"]["issues"])

    def test_schema_v3_subject_predicate_gap_heading_passes_readability_check(self) -> None:
        plan = valid_v3_link_plan()
        plan["topic_actions"][0]["research_gaps"][0]["gap"] = (
            "现有证据无法判断不同方法的效果差异"
        )
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])
        self.assertFalse(
            any(
                item["code"] == "research_gap_heading_readability"
                for item in report["findings"]
            )
        )

    def test_schema_v3_ingest_priority_is_only_a_warning_for_compatibility(self) -> None:
        plan = valid_v3_link_plan()
        plan["topic_actions"][0]["research_gaps"][0]["priority"] = "高"
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])
        self.assertTrue(
            any(item["code"] == "ingest_research_gap_priority" for item in report["findings"])
        )

    def test_schema_v3_research_gap_progress_ids_and_sources_are_checked(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        progress = {
            "id": "progress-shared-benchmark",
            "source_refs": ["wiki/sources/outside.md"],
            "method": "Run one shared benchmark.",
            "result": "One confound is removed.",
            "pointer": "[Paper: PDF p. 8]",
            "remaining_boundary": "Transfer remains open.",
        }
        gap["progress_updates"] = [progress, dict(progress)]
        report = LINK_AUDIT.audit(plan)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("duplicate_progress_id", codes)
        self.assertIn("item_source_outside_topic", codes)

    def test_schema_v3_answered_gap_requires_resolution_record(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        gap["status"] = "answered"
        gap.pop("significance")
        gap["answered_by"] = ["wiki/sources/b.md"]
        gap["answered_pointer"] = "[Paper: PDF p. 8, Table 3]"
        report = LINK_AUDIT.audit(plan)
        missing = {
            item.get("details", {}).get("field")
            for item in report["findings"]
            if item["code"] == "missing_string"
        }
        self.assertTrue(
            {"resolution_method", "resolution_summary", "resolution_scope"}
            <= missing
        )

        gap["resolution_method"] = "Run a controlled comparison."
        gap["resolution_summary"] = "The comparison closes the recorded gap."
        gap["resolution_scope"] = "Three public datasets under matched settings."
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0, report["findings"])

    def test_schema_v3_narrative_refs_must_resolve_and_be_prose(self) -> None:
        plan = valid_v3_link_plan()
        paragraph = plan["topic_actions"][0]["narrative"]["overview"]["paragraphs"][0]
        paragraph["text"] = "- Added in this batch"
        paragraph["finding_refs"] = ["missing-finding"]
        report = LINK_AUDIT.audit(plan)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("narrative_bullet", codes)
        self.assertIn("unknown_finding_ref", codes)

    def test_schema_v3_narrative_requires_reader_facing_depth(self) -> None:
        plan = valid_v3_link_plan()
        narrative = plan["topic_actions"][0]["narrative"]
        narrative["overview"]["paragraphs"] = narrative["overview"]["paragraphs"][:1]
        narrative["synthesis_blocks"][0]["paragraphs"] = narrative["synthesis_blocks"][0]["paragraphs"][:1]
        report = LINK_AUDIT.audit(plan)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("narrative_overview_depth", codes)
        self.assertIn("narrative_block_depth", codes)

    def test_schema_v3_mature_topic_requires_three_synthesis_blocks(self) -> None:
        plan = valid_v3_link_plan()
        action = plan["topic_actions"][0]
        action["papers"].extend(["wiki/sources/c.md", "wiki/sources/d.md"])
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "narrative_synthesis_depth"
                for item in report["findings"]
            )
        )

    def test_schema_v3_uses_id_mutations_not_text_fragments(self) -> None:
        plan = valid_v3_link_plan()
        action = plan["topic_actions"][0]
        action["remove_research_gaps"] = ["unified test"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "legacy_text_mutation" for item in report["findings"])
        )

    def test_schema_v3_mutation_ids_use_stable_id_format(self) -> None:
        plan = valid_v3_link_plan()
        action = plan["topic_actions"][0]
        action["remove_open_question_ids"] = ["Question 1"]
        action["annotate_research_gaps"] = [
            {"id": "Gap 1", "note": "Related evidence exists."}
        ]
        report = LINK_AUDIT.audit(plan)
        invalid_ids = [
            item for item in report["findings"] if item["code"] == "item_id"
        ]
        self.assertEqual(len(invalid_ids), 2)

    def test_schema_v3_answer_sources_must_belong_to_topic(self) -> None:
        plan = valid_v3_link_plan()
        gap = plan["topic_actions"][0]["research_gaps"][0]
        gap["status"] = "answered"
        gap.pop("significance")
        gap["answered_by"] = ["wiki/sources/outside.md"]
        gap["answered_pointer"] = "[Paper: PDF p. 8]"
        gap["resolution_method"] = "Run a controlled comparison."
        gap["resolution_summary"] = "The comparison closes the recorded gap."
        gap["resolution_scope"] = "Matched settings only."
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(
                item["code"] == "item_source_outside_topic"
                and item.get("details", {}).get("source_refs")
                == ["wiki/sources/outside.md"]
                for item in report["findings"]
            )
        )

    def test_valid_plan_passes(self) -> None:
        report = LINK_AUDIT.audit(valid_link_plan())
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_hub_actions_are_rejected(self) -> None:
        plan = valid_link_plan()
        plan["hub_actions"] = [
            {
                "action": "create_hub",
                "id": "hub-1",
                "name": "Shared Concept",
                "kind": "concept",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "hub_actions_removed" for item in report["findings"])
        )

    def test_create_topic_requires_two_papers(self) -> None:
        plan = valid_link_plan()
        plan["topic_actions"][0]["papers"] = ["wiki/sources/a.md"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "topic_papers" for item in report["findings"]))

    def test_unknown_source_fails(self) -> None:
        plan = valid_link_plan()
        plan["topic_actions"][0]["papers"] = [
            "wiki/sources/a.md",
            "wiki/sources/outside.md",
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "unknown_topic_papers" for item in report["findings"]))

    def test_topic_without_key_findings_passes_cleanly(self) -> None:
        plan = valid_link_plan()
        plan["topic_actions"][0].pop("key_findings", None)
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["warnings"], 0)

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "link-plan.json"
            report_path = root / "link-plan-report.json"
            plan_path.write_text(json.dumps(valid_link_plan()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--plan",
                    str(plan_path),
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

    def test_open_question_objects_pass_and_status_is_checked(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["open_questions"] = [
            {"question": "Q1", "status": "open"},
            {
                "question": "Q2",
                "status": "answered",
                "answered_by": ["wiki/sources/a.md"],
                "answered_pointer": "[Paper: PDF p. 2]",
            },
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        action["open_questions"].append({"question": "Q3", "status": "answered"})
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "open_question_answer_source" for item in report["findings"])
        )
        action["open_questions"] = [
            {
                "question": "Q3",
                "status": "answered",
                "answered_by": ["wiki/sources/a.md"],
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "open_question_answer_pointer" for item in report["findings"])
        )
        action["open_questions"] = [{"question": "Q4", "status": "draft"}]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "open_question_status" for item in report["findings"])
        )
        action["open_questions"] = [{"status": "open"}]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "open_question_shape" for item in report["findings"])
        )

    def test_research_gap_status_and_answer_source(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "Run a unified benchmark.",
                "continuity": "A future paper can test it.",
                "significance": "It would change which benchmark the field trusts.",
                "status": "open",
            },
            {
                "gap": "G2",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "Compare both settings.",
                "continuity": "The next paper can close the gap.",
                "status": "answered",
                "answered_by": ["wiki/sources/b.md"],
                "answered_pointer": "[Paper: PDF p. 4]",
            },
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        action["research_gaps"].append(
            {
                "gap": "G3",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "Test G3.",
                "continuity": "Future work can answer G3.",
                "status": "answered",
            }
        )
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_answer_source" for item in report["findings"])
        )
        action["research_gaps"] = [
            {
                "gap": "G3",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "Test G3.",
                "continuity": "Future work can answer G3.",
                "status": "answered",
                "answered_by": ["wiki/sources/b.md"],
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_answer_pointer" for item in report["findings"])
        )
        action["research_gaps"] = [
            {
                "gap": "G4",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "Test G4.",
                "continuity": "Future work can answer G4.",
                "status": "unknown",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_status" for item in report["findings"])
        )

    def test_research_gap_requires_traceable_object_fields(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = ["Legacy gap"]
        report = LINK_AUDIT.audit(plan)
        legacy = [item for item in report["findings"] if item["code"] == "research_gap_legacy_string"]
        self.assertEqual(len(legacy), 1)
        self.assertIn("source_refs", legacy[0]["message"])
        self.assertIn("direction", legacy[0]["message"])

        complete = {
            "gap": "A traceable gap.",
            "source_refs": ["wiki/sources/a.md"],
            "direction": "Run a targeted experiment.",
            "continuity": "A future paper can answer it.",
            "significance": "It would change which methods are considered reliable.",
            "status": "open",
        }
        for field, code in (
            ("source_refs", "research_gap_source_refs"),
            ("direction", "research_gap_direction"),
            ("continuity", "research_gap_continuity"),
        ):
            with self.subTest(field=field):
                item = dict(complete)
                item.pop(field)
                action["research_gaps"] = [item]
                report = LINK_AUDIT.audit(plan)
                self.assertTrue(
                    any(finding["code"] == code for finding in report["findings"])
                )

    def test_research_gap_full_v2_fields_pass_clean(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
                "significance": "Why it matters.",
                "evidence_boundary": "Existing methods stop here.",
                "experiment": "Run benchmark X with metric Y.",
                "success_criterion": "Improvement over baseline.",
                "risk": "Paper B hints this may fail.",
                "priority": "高",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["warnings"], 0)

    def test_research_gap_open_requires_significance(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertTrue(
            any(item["code"] == "research_gap_significance" for item in report["findings"])
        )
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
                "significance": "",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_significance" for item in report["findings"])
        )

    def test_research_gap_answered_is_exempt_from_significance(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
                "status": "answered",
                "answered_by": ["wiki/sources/b.md"],
                "answered_pointer": "[Paper: PDF p. 4]",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertFalse(
            any(item["code"] == "research_gap_significance" for item in report["findings"])
        )

    def test_research_gap_empty_optional_v2_fields_warn_not_block(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
                "significance": "Why it matters.",
                "experiment": "",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertTrue(
            any(item["code"] == "research_gap_experiment" for item in report["findings"])
        )

    def test_research_gap_priority_must_be_label(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["research_gaps"] = [
            {
                "gap": "G1",
                "source_refs": ["wiki/sources/a.md"],
                "direction": "d",
                "continuity": "c",
                "significance": "Why it matters.",
                "priority": "P1",
            }
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "research_gap_priority" for item in report["findings"])
        )

    def test_topic_category_field_is_optional_and_warns_when_empty(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["category"] = "评估框架"
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["warnings"], 0)
        action["category"] = ""
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertTrue(
            any(item["code"] == "topic_category" for item in report["findings"])
        )

    def test_remove_and_annotate_fields_validation(self) -> None:
        plan = valid_link_plan()
        action = plan["topic_actions"][0]
        action["remove_open_questions"] = ["Q1"]
        action["remove_research_gaps"] = ["gap fragment"]
        action["annotate_research_gaps"] = [{"match": "gap", "note": "note"}]
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)
        action["remove_open_questions"] = [1]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "remove_open_questions" for item in report["findings"])
        )
        action["remove_open_questions"] = ["Q1"]
        action["remove_research_gaps"] = [""]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "remove_research_gaps" for item in report["findings"])
        )
        action["remove_research_gaps"] = ["gap fragment"]
        action["annotate_research_gaps"] = [{"match": ""}]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "annotate_research_gap_shape" for item in report["findings"])
        )

    def mining_plan(self) -> dict:
        return {
            "schema_version": "2.0",
            "purpose": "mining",
            "batch": {"source_pages": [], "label": "gap mining"},
            "topic_actions": [
                {
                    "action": "create_topic",
                    "id": "mining-1",
                    "name": "Cross Group Direction",
                    "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                    "summary": "Cross-group candidate direction.",
                    "comparisons": [],
                    "key_findings": [],
                    "contradictions": [],
                    "open_questions": [],
                    "research_gaps": [],
                    "existing_page": None,
                }
            ],
        }

    def test_mining_plan_without_batch_pages_passes(self) -> None:
        report = LINK_AUDIT.audit(self.mining_plan())
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_ingest_plan_without_batch_pages_fails(self) -> None:
        plan = self.mining_plan()
        plan.pop("purpose")
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "batch" for item in report["findings"]))

    def test_mining_plan_allows_references_outside_batch(self) -> None:
        plan = self.mining_plan()
        plan["topic_actions"][0]["papers"] = [
            "wiki/sources/other-a.md",
            "wiki/sources/other-b.md",
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertFalse(
            any(item["code"] == "unknown_topic_papers" for item in report["findings"])
        )
        self.assertEqual(report["summary"]["errors"], 0)

    def test_mining_create_topic_requires_two_references(self) -> None:
        plan = self.mining_plan()
        plan["topic_actions"][0]["papers"] = ["wiki/sources/a.md"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "topic_papers" for item in report["findings"]))

    def test_unknown_purpose_fails(self) -> None:
        plan = self.mining_plan()
        plan["purpose"] = "scan"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "purpose" for item in report["findings"]))

    def test_schema_v2_refresh_is_rejected(self) -> None:
        plan = self.mining_plan()
        plan["purpose"] = "refresh"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(
            any(item["code"] == "refresh_schema" for item in report["findings"])
        )
