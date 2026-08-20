#!/usr/bin/env python3
"""Regression tests for deterministic workflow status reporting."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "workflow_status.py"


def make_paper(batch: Path, name: str, *, card: bool = True, digest: bool = True) -> None:
    paper_dir = batch / name
    paper_dir.mkdir(parents=True)
    (paper_dir / "source_bundle.json").write_text("{}", encoding="utf-8")
    if card:
        (paper_dir / "paper-card.md").write_text("# Card", encoding="utf-8")
    if digest:
        (paper_dir / "paper-digest.json").write_text("{}", encoding="utf-8")


class WorkflowStatusTests(unittest.TestCase):
    def test_all_papers_complete_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "work" / "batch"
            make_paper(batch, "a")
            make_paper(batch, "b")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--work-dir", str(batch)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("2/2 complete", result.stdout)

    def test_missing_digest_is_reported_and_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "work" / "batch"
            make_paper(batch, "a", digest=False)
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--work-dir", str(batch)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("INCOMPLETE", result.stdout)
            self.assertIn("paper-digest.json", result.stdout)

    def test_empty_card_counts_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory) / "work" / "batch"
            make_paper(batch, "a")
            (batch / "a" / "paper-card.md").write_text("", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--work-dir", str(batch)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("paper-card.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
