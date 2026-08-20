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
                "aliases": [],
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
                "open_questions": [],
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

    def test_create_hub_requires_two_sources(self) -> None:
        plan = valid_link_plan()
        plan["hub_actions"][0]["source_refs"] = ["wiki/sources/a.md"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "cross_source" for item in report["findings"]))

    def test_connect_existing_satisfies_cross_source_rule(self) -> None:
        plan = valid_link_plan()
        plan["hub_actions"][0]["source_refs"] = ["wiki/sources/a.md"]
        plan["hub_actions"][0]["connect_existing"] = True
        report = LINK_AUDIT.audit(plan)
        self.assertEqual(report["summary"]["errors"], 0)

    def test_non_l2_hub_action_fails(self) -> None:
        plan = valid_link_plan()
        plan["hub_actions"][0]["tier"] = "L1"
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "hub_tier" for item in report["findings"]))

    def test_create_topic_requires_two_papers(self) -> None:
        plan = valid_link_plan()
        plan["topic_actions"][0]["papers"] = ["wiki/sources/a.md"]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "topic_papers" for item in report["findings"]))

    def test_unknown_source_fails(self) -> None:
        plan = valid_link_plan()
        plan["hub_actions"][0]["source_refs"] = [
            "wiki/sources/a.md",
            "wiki/sources/outside.md",
        ]
        report = LINK_AUDIT.audit(plan)
        self.assertTrue(any(item["code"] == "unknown_source_refs" for item in report["findings"]))

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


if __name__ == "__main__":
    unittest.main()
