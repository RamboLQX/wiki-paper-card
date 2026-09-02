#!/usr/bin/env python3
"""Regression tests for deterministic digest finalization."""

from __future__ import annotations

import copy
import unittest

from scripts import finalize_paper_digest


class FinalizePaperDigestTests(unittest.TestCase):
    def test_changes_only_identity_fields(self) -> None:
        digest = {
            "schema_version": "3.0",
            "paper": {
                "title": "Semantic title",
                "source_sha256": "wrong",
                "source_ref": "wiki/sources/wrong.md",
                "locator_mode": "page-grounded",
                "paper_type": "methods",
            },
            "analysis": {"method": "Semantic method"},
            "topic_seeds": [
                {
                    "id": "topic-one",
                    "name": "Semantic topic",
                    "papers": ["wiki/sources/wrong.md"],
                    "summary": "Semantic summary",
                }
            ],
        }
        before = copy.deepcopy(digest)
        expected = {
            "source_sha256": "a" * 64,
            "source_ref": "wiki/sources/papers/correct.md",
            "work_dir": "work/batch/paper",
            "source_path": "raw/papers/correct.pdf",
        }

        finalized, changes = finalize_paper_digest.finalize_digest(digest, expected)

        self.assertEqual(finalized["paper"]["title"], before["paper"]["title"])
        self.assertEqual(finalized["paper"]["locator_mode"], before["paper"]["locator_mode"])
        self.assertEqual(finalized["paper"]["paper_type"], before["paper"]["paper_type"])
        self.assertEqual(finalized["analysis"], before["analysis"])
        self.assertEqual(finalized["topic_seeds"][0]["name"], before["topic_seeds"][0]["name"])
        self.assertEqual(finalized["topic_seeds"][0]["summary"], before["topic_seeds"][0]["summary"])
        self.assertEqual(finalized["paper"]["source_sha256"], "a" * 64)
        self.assertEqual(finalized["paper"]["source_ref"], expected["source_ref"])
        self.assertEqual(finalized["topic_seeds"][0]["papers"], [expected["source_ref"]])
        self.assertEqual(
            {change["field"] for change in changes},
            {"paper.source_sha256", "paper.source_ref", "topic_seeds[0].papers"},
        )

    def test_rejects_missing_semantic_structure(self) -> None:
        expected = {
            "source_sha256": "a" * 64,
            "source_ref": "wiki/sources/paper.md",
            "work_dir": "work/batch/paper",
            "source_path": "raw/paper.pdf",
        }
        with self.assertRaisesRegex(finalize_paper_digest.ManifestError, "define paper"):
            finalize_paper_digest.finalize_digest({"topic_seeds": []}, expected)


if __name__ == "__main__":
    unittest.main()
