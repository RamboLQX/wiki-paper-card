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


class LinkPlanAuditTests(unittest.TestCase):
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
