#!/usr/bin/env python3
"""Regression tests for the paper digest audit."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_paper_digest.py"
SPEC = importlib.util.spec_from_file_location("audit_paper_digest", SCRIPT_PATH)
assert SPEC and SPEC.loader
DIGEST_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIGEST_AUDIT)


def valid_digest() -> dict:
    return {
        "schema_version": "3.0",
        "paper": {
            "title": "Test Paper",
            "source_sha256": "a" * 64,
            "source_ref": "wiki/sources/current.md",
            "locator_mode": "page-grounded",
            "paper_type": "methods",
        },
        "analysis": {
            "one_sentence_summary": "The paper proposes a test method.",
            "problem": "An unresolved test problem.",
            "method": "A method with a mechanism.",
            "key_results": [
                {
                    "claim": "Accuracy improves.",
                    "pointer": "[Paper: PDF p. 6, Table 1]",
                    "confidence": "high",
                }
            ],
            "limitations": [
                {
                    "statement": "Only one dataset.",
                    "pointer": "[Paper: PDF p. 10]",
                }
            ],
            "critical_observations": [
                {
                    "observation": "No error bars.",
                    "pointer": "[Paper: PDF p. 7]",
                }
            ],
            "unexplained_results": [
                {
                    "statement": "Performance improves, but the mechanism is not tested.",
                    "pointer": "[Paper: PDF p. 8]",
                }
            ],
            "open_questions": ["Would the method transfer?"],
        },
        "topic_seeds": [
            {
                "id": "topic-1",
                "name": "Test Topic",
                "papers": ["wiki/sources/current.md"],
                "summary": "A possible comparison topic.",
            }
        ],
    }


class PaperDigestAuditTests(unittest.TestCase):
    def test_valid_digest_passes(self) -> None:
        report = DIGEST_AUDIT.audit(valid_digest())
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["status"], "pass")

    def test_candidates_field_is_rejected(self) -> None:
        digest = valid_digest()
        digest["candidates"] = [
            {
                "id": "candidate-1",
                "name": "Test Candidate",
                "kind": "concept",
                "tier": "L1",
            }
        ]
        report = DIGEST_AUDIT.audit(digest)
        self.assertTrue(any(item["code"] == "candidates_removed" for item in report["findings"]))

    def test_topic_seed_must_include_current_source(self) -> None:
        digest = valid_digest()
        digest["topic_seeds"][0]["papers"] = ["wiki/sources/other.md"]
        report = DIGEST_AUDIT.audit(digest)
        self.assertTrue(any(item["code"] == "current_source_missing" for item in report["findings"]))

    def test_unexplained_results_are_required_and_traceable(self) -> None:
        digest = valid_digest()
        digest["analysis"].pop("unexplained_results")
        report = DIGEST_AUDIT.audit(digest)
        self.assertTrue(
            any(
                item["code"] == "missing_list"
                and item.get("details", {}).get("field") == "unexplained_results"
                for item in report["findings"]
            )
        )

        digest = valid_digest()
        digest["analysis"]["unexplained_results"][0]["pointer"] = "p. 8"
        report = DIGEST_AUDIT.audit(digest)
        self.assertTrue(
            any(item["code"] == "unexplained_results_pointer" for item in report["findings"])
        )

    def test_topic_seed_rejects_embedded_gap_candidates(self) -> None:
        digest = valid_digest()
        digest["topic_seeds"][0]["research_gaps"] = ["A generic gap."]
        report = DIGEST_AUDIT.audit(digest)
        self.assertTrue(
            any(item["code"] == "topic_seed_candidate_content" for item in report["findings"])
        )

    def test_manifest_identity_mismatch_is_rejected(self) -> None:
        expected = {
            "source_sha256": "b" * 64,
            "source_ref": "wiki/sources/papers/correct.md",
            "work_dir": "work/batch/paper",
            "source_path": "raw/papers/correct.pdf",
        }
        report = DIGEST_AUDIT.audit(valid_digest(), expected)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("manifest_source_sha256_mismatch", codes)
        self.assertIn("manifest_source_ref_mismatch", codes)
        self.assertEqual(report["summary"]["status"], "fail")

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest_path = root / "paper-digest.json"
            report_path = root / "paper-digest-report.json"
            digest_path.write_text(json.dumps(valid_digest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--digest",
                    str(digest_path),
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
