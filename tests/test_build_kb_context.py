#!/usr/bin/env python3
"""Regression tests for compact KB context generation."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_kb_context.py"
SPEC = importlib.util.spec_from_file_location("build_kb_context", SCRIPT_PATH)
assert SPEC and SPEC.loader
KB_CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KB_CONTEXT)


class BuildKbContextTests(unittest.TestCase):
    def test_build_context_selects_related_source_and_open_questions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for name in ("sources", "concepts", "entities", "topics"):
                (wiki / name).mkdir(parents=True)
            (wiki / "index.md").write_text(
                "# Index\n\n"
                "- [[wiki/sources/a.md|A]] — knowledge conflict mechanism\n"
                "- [[wiki/concepts/conflict.md|Knowledge Conflict]] — cross-paper hub\n",
                encoding="utf-8",
            )
            (wiki / "concepts" / "conflict.md").write_text(
                "# Knowledge Conflict\n\n"
                "A conflict between parametric and contextual knowledge.\n\n"
                "## 开放问题\n\n"
                "How do head-level and neuron-level interventions overlap?\n",
                encoding="utf-8",
            )
            context = KB_CONTEXT.build_context(
                root,
                "knowledge conflict mechanism",
                max_pages=3,
                max_chars=1600,
            )
            self.assertIn("A", context)
            self.assertIn("[[a|A]]", context)
            self.assertIn("开放问题", context)
            self.assertIn("overlap", context)
            self.assertLessEqual(len(context), 1600)

    def test_empty_wiki_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = KB_CONTEXT.build_context(Path(directory), "paper", 3, 1600)
            self.assertIn("为空", context)


if __name__ == "__main__":
    unittest.main()
