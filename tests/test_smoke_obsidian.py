#!/usr/bin/env python3
"""Regression tests for the post-publish Obsidian smoke check (soft gate)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "smoke_obsidian.py"
SPEC = importlib.util.spec_from_file_location("smoke_obsidian", SCRIPT_PATH)
assert SPEC and SPEC.loader
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


def publish_report(root: Path, status: str = "pass") -> Path:
    report_path = root / "publish-report.json"
    report_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "summary": {"status": status},
                "writes": [
                    {
                        "kind": "source",
                        "path": "wiki/sources/papers/a.md",
                        "action": "create",
                    },
                    {"kind": "topic", "path": "wiki/topics/C.md", "action": "create"},
                ],
                "errors": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report_path


class FakeCheck(SMOKE.SmokeCheck):
    """SmokeCheck with the subprocess runner replaced by canned responses."""

    def __init__(self, responses: dict[str, tuple[int, str]]) -> None:
        super().__init__(cli="fake-cli")
        self.responses = responses
        self.calls: list[str] = []

    def run(self, arguments: list[str]) -> tuple[int, str, str]:
        key = arguments[0] if arguments else ""
        self.calls.append(key)
        if key == "eval":
            # identify the JS payload by a marker inside it
            code = arguments[1]
            if "openFile" in code:
                return 0, "=> ok", ""
            if "getMostRecentLeaf().detach" in code:
                return 0, "=> ok", ""
            code, stdout = self.responses["check"]
            return code, stdout, ""
        return 0, "", ""


def cli_env() -> dict[str, str]:
    env = dict(os.environ)
    env["WIKI_PAPER_CARD_SMOKE_DISABLE"] = "1"
    return env


class SmokeObsidianTests(unittest.TestCase):
    def test_read_publish_report_collects_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pages, status = SMOKE.read_publish_report(publish_report(Path(directory)))
        self.assertEqual(pages, ["wiki/sources/papers/a.md", "wiki/topics/C.md"])
        self.assertEqual(status, "pass")

    def test_check_page_passes_when_decorations_render(self) -> None:
        check = FakeCheck(
            {"check": (0, "=> " + json.dumps({"headers": 3, "rawLinks": 0, "rawBold": 0}))}
        )
        result = check.check_page("wiki/topics/C.md")
        self.assertEqual(result["status"], "pass")
        self.assertIn("eval", check.calls)

    def test_check_page_fails_on_raw_wikilinks_and_bold(self) -> None:
        check = FakeCheck(
            {"check": (0, "=> " + json.dumps({"headers": 0, "rawLinks": 5, "rawBold": 2}))}
        )
        result = check.check_page("wiki/topics/C.md")
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["problems"])

    def test_missing_cli_skips_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = publish_report(Path(directory))
            with mock.patch.object(SMOKE, "find_cli", return_value=None):
                result = SMOKE.run_check(report, strict=False, timeout=10.0, vault=None)
        self.assertEqual(result["summary"]["status"], "skipped")
        self.assertIn("reason", result["summary"])

    def test_cli_strict_mode_exits_nonzero_when_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = publish_report(Path(directory))
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--report",
                str(report),
                "--strict",
            ]
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, env=cli_env()
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("skipped", result.stdout)

    def test_cli_soft_mode_exits_zero_when_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = publish_report(Path(directory))
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--report",
                str(report),
            ]
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, env=cli_env()
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
