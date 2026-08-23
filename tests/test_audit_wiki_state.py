#!/usr/bin/env python3
"""Regression tests for the wiki state structural audit."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "audit_wiki_state.py"
SPEC = importlib.util.spec_from_file_location("audit_wiki_state", SCRIPT_PATH)
assert SPEC and SPEC.loader
WIKI_STATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WIKI_STATE)


def prepare_wiki(root: Path) -> Path:
    wiki = root / "wiki"
    for directory in ("entities", "topics", "sources/papers/x", "meta"):
        (wiki / directory).mkdir(parents=True, exist_ok=True)
    return wiki


class AuditWikiStateTests(unittest.TestCase):
    def test_clean_wiki_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = prepare_wiki(Path(directory))
            (wiki / "entities" / "Entity.md").write_text(
                "---\n"
                "tags: [entity]\n"
                'created: "2026-01-01"\n'
                "aliases:\n"
                '  - "Alias Name"\n'
                "---\n\n"
                "# Concept\n\n"
                "A definition.\n\n"
                "## 证据\n\n"
                "| 来源 | 断言 | 证据 | confidence |\n"
                "|---|---|---|---|\n"
                "| Paper A | claim | [Paper: PDF p. 1] | - |\n",
                encoding="utf-8",
            )
            (wiki / "sources/papers/x/a.md").write_text(
                "# Paper A\n\n"
                "## 关联页面\n\n"
                "- [[Entity|Entity]] - 实体\n"
                "- [[Alias Name|Alias Name]] - 实体\n",
                encoding="utf-8",
            )
            (wiki / "log.md").write_text("# 操作日志\n", encoding="utf-8")
            report = WIKI_STATE.audit(Path(directory))
            self.assertEqual(report["summary"]["status"], "pass", report["findings"])
            self.assertEqual(report["summary"]["errors"], 0)

    def test_detects_orphan_table_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = prepare_wiki(Path(directory))
            (wiki / "entities" / "C.md").write_text(
                "# C\n\n"
                "## 证据\n\n"
                "| 来源 | 断言 | 证据 | confidence |\n"
                "|---|---|---|---|\n"
                "| A | claim | [Paper: PDF p. 1] | - |\n"
                "\n"
                "| B | orphan | [Paper: PDF p. 2] | - |\n",
                encoding="utf-8",
            )
            report = WIKI_STATE.audit(Path(directory))
            self.assertTrue(
                any(item["code"] == "orphan_table_row" for item in report["findings"])
            )
            self.assertTrue(report["summary"]["errors"] > 0)

    def test_detects_raw_html_and_unresolved_backlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = prepare_wiki(Path(directory))
            (wiki / "sources/papers/x/a.md").write_text(
                "# Paper A\n\n"
                "对比 <image> token。\n\n"
                "## 关联页面\n\n"
                "- [[Missing Page|Missing Page]] - 主题\n",
                encoding="utf-8",
            )
            report = WIKI_STATE.audit(Path(directory))
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("raw_html_tag", codes)
            self.assertIn("unresolved_backlink", codes)

    def test_detects_duplicate_log_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = prepare_wiki(Path(directory))
            (wiki / "log.md").write_text(
                "# 操作日志\n\n"
                "- 更新：wiki/entities/C.md\n"
                "- 更新：wiki/entities/C.md\n",
                encoding="utf-8",
            )
            report = WIKI_STATE.audit(Path(directory))
            self.assertTrue(
                any(
                    item["code"] == "duplicate_log_entry"
                    for item in report["findings"]
                )
            )

    def test_cli_exits_nonzero_on_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = prepare_wiki(root)
            (wiki / "entities" / "C.md").write_text(
                "# C\n\n对比 <image> token。\n", encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--wiki-root",
                    str(root),
                    "--report",
                    str(root / "wiki-state-report.json"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            report = json.loads(
                (root / "wiki-state-report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["summary"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
