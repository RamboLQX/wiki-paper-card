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
            for name in ("sources", "entities", "topics"):
                (wiki / name).mkdir(parents=True)
            (wiki / "index.md").write_text(
                "# Index\n\n"
                "- [[wiki/sources/a.md|A]] — knowledge conflict mechanism\n"
                "- [[wiki/entities/conflict.md|Knowledge Conflict]] — entity stub\n",
                encoding="utf-8",
            )
            (wiki / "entities" / "conflict.md").write_text(
                "# Knowledge Conflict\n\n"
                "> 本页由 publish_wiki.py 确定性生成。\n",
                encoding="utf-8",
            )
            (wiki / "sources" / "a.md").write_text(
                "# A\n\n"
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

    def test_alias_bridges_english_query_to_chinese_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for name in ("sources", "entities", "topics"):
                (wiki / name).mkdir(parents=True)
            (wiki / "index.md").write_text(
                "# Index\n\n"
                "## 实体\n"
                "- [[wiki/entities/knowledge-conflict.md|知识冲突]] — 参数化知识与上下文知识相悖\n"
                "- [[wiki/entities/other.md|其他实体]] — 与查询无关的实体\n",
                encoding="utf-8",
            )
            (wiki / "entities" / "knowledge-conflict.md").write_text(
                "---\n"
                "tags: [entity]\n"
                'aliases:\n  - "parametric knowledge"\n  - "contextual knowledge"\n'
                "status: stub\n"
                "---\n\n"
                "# 知识冲突\n\n"
                "> 本页由 publish_wiki.py 确定性生成。\n",
                encoding="utf-8",
            )
            (wiki / "entities" / "other.md").write_text(
                "# 其他实体\n\n无关内容。\n", encoding="utf-8"
            )
            context = KB_CONTEXT.build_context(
                root, "parametric knowledge", max_pages=1, max_chars=1600
            )
            self.assertIn("[[knowledge-conflict|知识冲突]]", context)
            self.assertNotIn("[[other|其他实体]]", context)

    def test_zero_overlap_marks_index_order_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wiki = root / "wiki"
            for name in ("sources", "entities", "topics"):
                (wiki / name).mkdir(parents=True)
            (wiki / "index.md").write_text(
                "# Index\n\n"
                "## 来源\n"
                "- [[wiki/sources/a.md|A]] — 完全无关的中文描述\n",
                encoding="utf-8",
            )
            (wiki / "sources" / "a.md").write_text(
                "# A\n\n无关内容。\n", encoding="utf-8"
            )
            context = KB_CONTEXT.build_context(
                root, "unrelated english terms", max_pages=3, max_chars=1600
            )
            self.assertIn("无关键词重合", context)
            self.assertIn("[[a|A]]", context)


if __name__ == "__main__":
    unittest.main()
