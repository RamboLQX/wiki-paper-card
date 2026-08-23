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
