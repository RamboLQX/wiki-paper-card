#!/usr/bin/env python3
"""Regression tests for the upstream Paper Card terminology audit."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = (
    Path(__file__).parents[1]
    / "vendor"
    / "nature-paper-card"
    / "scripts"
    / "audit_paper_card.py"
)
SPEC = importlib.util.spec_from_file_location("audit_paper_card", SCRIPT_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


VALID_LEDGER = (
    "### 术语规范表\n\n"
    "| 规范术语 | 首次定义或中文释义 | 原文变体 | 使用决策 | 来源 |\n"
    "|---|---|---|---|---|\n"
    "| Test method | A test method | test-method | 统一使用 Test method | {pointer} |"
)


def card(locator_mode: str, ledger: str) -> str:
    pointer = (
        "[Paper: Abstract]"
        if locator_mode == "source-limited"
        else "[Paper: Section Methods]"
    )
    sections = []
    for number in range(1, 17):
        body = f"Placeholder {pointer}"
        if number == 1:
            body += "\n\n" + ledger.format(pointer=pointer)
        sections.append(f"## {number:02d}. Section {number}\n\n{body}\n")
    return (
        "# Test Paper\n\n"
        "> Source coverage: Full paper\n"
        "> Extraction confidence: High\n"
        f"> Locator mode: {locator_mode}\n"
        "> Primary analytical lens: methods\n"
        "> Secondary analytical lens: None\n"
        "> Context verification: Paper-only\n"
        "> Card completeness: Complete relative to supplied source\n\n"
        + "\n".join(sections)
    )


def terminology_finding(report: dict) -> dict:
    return next(
        item for item in report["findings"]
        if item["code"] == "terminology_ledger"
    )


class TerminologyLedgerAuditTests(unittest.TestCase):
    def test_valid_five_column_ledger_passes(self) -> None:
        report = AUDIT.audit(card("structure-grounded", VALID_LEDGER), None, "structure-grounded")
        self.assertEqual(terminology_finding(report)["level"], "pass")
        self.assertEqual(report["metrics"]["terminology_row_count"], 1)

    def test_missing_ledger_fails(self) -> None:
        report = AUDIT.audit(card("structure-grounded", ""), None, "structure-grounded")
        self.assertEqual(terminology_finding(report)["level"], "error")

    def test_row_without_source_pointer_fails(self) -> None:
        ledger = VALID_LEDGER.replace("{pointer}", "Section Methods")
        report = AUDIT.audit(card("structure-grounded", ledger), None, "structure-grounded")
        self.assertEqual(terminology_finding(report)["level"], "error")

    def test_source_limited_explicit_not_assessable_passes(self) -> None:
        ledger = "### 术语规范表\n\n无法根据现有材料建立可靠术语表。"
        report = AUDIT.audit(card("source-limited", ledger), None, "source-limited")
        self.assertEqual(terminology_finding(report)["level"], "pass")
        self.assertEqual(report["metrics"]["terminology_row_count"], 0)


if __name__ == "__main__":
    unittest.main()
