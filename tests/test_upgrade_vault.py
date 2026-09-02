#!/usr/bin/env python3
"""Regression tests for explicit Vault inspection and Topic migration."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).parents[1]
UPGRADE_SCRIPT = REPO_ROOT / "scripts" / "upgrade_vault.py"


def run_upgrade(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(UPGRADE_SCRIPT), *arguments],
        capture_output=True,
        text=True,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tree_snapshot(root: Path, directory: str) -> dict[str, bytes]:
    target = root / directory
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }


def old_topic_text() -> str:
    return (
        "---\n"
        "tags: [topic]\n"
        'created: "2026-01-01"\n'
        'updated: "2026-01-01"\n'
        "sources:\n"
        '  - "wiki/sources/a.md"\n'
        '  - "wiki/sources/b.md"\n'
        'status: "draft"\n'
        "---\n\n"
        "# Shared Topic\n\n"
        "## 概述\n\n旧版概述。\n\n"
        "## 关键发现\n\n- 旧版发现。\n\n"
        "## 论文与方法对照\n\n"
        "| 论文 | 方法 |\n|---|---|\n| A | old |\n\n"
        "## 开放问题\n\n- 旧版问题。\n\n"
        "## 研究空白与候选方向\n\n- 旧版空白。\n\n"
        "## 自定义研究记录\n\n保留这段人工内容。\n"
    )


def migration_plan(topic_text: str) -> dict:
    return {
        "schema_version": "3.0",
        "purpose": "migration",
        "batch": {"source_pages": [], "label": "legacy Topic migration"},
        "topic_actions": [
            {
                "action": "update_topic",
                "id": "topic-migration-shared",
                "name": "Shared Topic",
                "papers": ["wiki/sources/a.md", "wiki/sources/b.md"],
                "existing_page": "wiki/topics/Shared Topic.md",
                "base_topic_sha256": sha256_text(topic_text),
                "index_summary": "Two papers establish a shared result with one open boundary.",
                "page_status": "draft",
                "comparisons": [
                    {
                        "source_ref": "wiki/sources/a.md",
                        "paper": "Paper A",
                        "method": "Method A",
                        "intervention_granularity": "sample",
                        "main_result": "Shared result",
                        "boundary": "One benchmark",
                        "pointer": "[Paper: PDF p. 3]",
                    }
                ],
                "key_findings": [
                    {
                        "id": "kf-shared-result",
                        "claim": "Both papers support the shared result.",
                        "kind": "consensus",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "pointers": [
                            {
                                "source_ref": "wiki/sources/a.md",
                                "pointer": "[Paper: PDF p. 3]",
                            },
                            {
                                "source_ref": "wiki/sources/b.md",
                                "pointer": "[Paper: PDF p. 4]",
                            },
                        ],
                    }
                ],
                "contradictions": [],
                "narrative": {
                    "overview": {
                        "paragraphs": [
                            {
                                "id": "overview-scope",
                                "text": "This topic studies whether the shared result transfers across settings.",
                                "finding_refs": ["kf-shared-result"],
                            },
                            {
                                "id": "overview-state",
                                "text": "Current evidence supports the result in two settings, while comparability remains unresolved.",
                                "finding_refs": ["kf-shared-result"],
                            },
                        ]
                    },
                    "synthesis_blocks": [
                        {
                            "id": "synthesis-shared-result",
                            "heading": "The result is supported across two settings",
                            "paragraphs": [
                                {
                                    "text": "The papers support the result under different settings.",
                                    "finding_refs": ["kf-shared-result"],
                                },
                                {
                                    "text": "The evidence supports a bounded comparison rather than universal transfer.",
                                    "finding_refs": ["kf-shared-result"],
                                },
                            ],
                        }
                    ],
                    "controversy_blocks": [],
                },
                "open_questions": [
                    {
                        "id": "oq-transfer",
                        "origin": "ingest",
                        "question": "Does the result transfer to a shared benchmark?",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "status": "open",
                    }
                ],
                "research_gaps": [
                    {
                        "id": "rg-unified-benchmark",
                        "origin": "ingest",
                        "gap": "Current evidence cannot support a fair method comparison.",
                        "source_refs": ["wiki/sources/a.md", "wiki/sources/b.md"],
                        "direction": "Run both methods on one benchmark.",
                        "continuity": "A later paper can perform the comparison.",
                        "significance": "It would change which method is preferred.",
                        "reader_narrative": [
                            "The papers cannot yet support a method choice because their results use different benchmarks.",
                            "A matched comparison would distinguish method effects from evaluation-setting effects.",
                        ],
                        "status": "open",
                    }
                ],
            }
        ],
    }


def prepare_legacy_vault(root: Path) -> tuple[Path, str]:
    for directory in ("raw", "wiki/topics", "wiki/sources", "work/upgrade-run"):
        (root / directory).mkdir(parents=True)
    (root / "raw" / "paper.pdf").write_bytes(b"source bytes")
    (root / "wiki" / "sources" / "a.md").write_text("# Paper A\n", encoding="utf-8")
    (root / "wiki" / "sources" / "b.md").write_text("# Paper B\n", encoding="utf-8")
    topic_text = old_topic_text()
    topic_path = root / "wiki" / "topics" / "Shared Topic.md"
    topic_path.write_text(topic_text, encoding="utf-8")
    plan_path = root / "work" / "upgrade-run" / "migration-plan.json"
    plan_path.write_text(
        json.dumps(migration_plan(topic_text), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return plan_path, topic_text


class UpgradeVaultTests(unittest.TestCase):
    def test_inspect_classifies_topics_without_changing_raw_or_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("raw", "wiki/topics", "wiki/meta/topic-state"):
                (root / path).mkdir(parents=True)
            (root / "raw" / "paper.pdf").write_bytes(b"source bytes")
            (root / "wiki" / "topics" / "Plain.md").write_text(
                "# Plain\n\n## 概述\n\nOld.\n", encoding="utf-8"
            )
            markers = "\n".join(
                f"%% wiki-paper-card:managed-start {key} %%\nText\n"
                f"%% wiki-paper-card:managed-end {key} %%"
                for key in ("overview", "synthesis", "controversies")
            )
            (root / "wiki" / "topics" / "Marker.md").write_text(
                f"# Marker\n\n{markers}\n", encoding="utf-8"
            )
            (root / "wiki" / "topics" / "Current.md").write_text(
                "# Current\n", encoding="utf-8"
            )
            (root / "wiki" / "meta" / "topic-state" / "Current.json").write_text(
                json.dumps({"schema_version": "1.0", "topic_path": "wiki/topics/Current.md"}),
                encoding="utf-8",
            )
            (root / "wiki" / "topics" / "Invalid.md").write_text(
                "# Invalid\n", encoding="utf-8"
            )
            (root / "wiki" / "meta" / "topic-state" / "Invalid.json").write_text(
                "{}", encoding="utf-8"
            )
            (root / "wiki" / "topics" / "Broken State.md").write_text(
                "# Broken State\n", encoding="utf-8"
            )
            (root / "wiki" / "meta" / "topic-state" / "Broken State.json").symlink_to(
                root / "missing-state.json"
            )
            (root / "wiki" / "meta" / "topic-state" / "Orphan.json").write_text(
                "{}", encoding="utf-8"
            )
            before = {**tree_snapshot(root, "raw"), **tree_snapshot(root, "wiki")}
            report_path = root / "work" / "upgrade" / "inspection.json"
            result = run_upgrade(
                "inspect",
                "--wiki-root",
                str(root),
                "--report",
                str(report_path),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["summary"]["current"], 1)
            self.assertEqual(report["summary"]["legacy-marker"], 1)
            self.assertEqual(report["summary"]["legacy-plain"], 1)
            self.assertEqual(report["summary"]["invalid-state"], 2)
            self.assertEqual(report["summary"]["orphan_states"], 1)
            after = {**tree_snapshot(root, "raw"), **tree_snapshot(root, "wiki")}
            self.assertEqual(after, before)

    def test_inspect_rejects_report_inside_wiki_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "wiki" / "topics").mkdir(parents=True)
            (root / "work").mkdir()
            topic_path = root / "wiki" / "topics" / "Legacy.md"
            topic_path.write_text("# Legacy\n", encoding="utf-8")
            before = tree_snapshot(root, "wiki")
            report_path = root / "wiki" / "inspection.json"
            result = run_upgrade(
                "inspect",
                "--wiki-root",
                str(root),
                "--report",
                str(report_path),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("under <wiki-root>/work", result.stderr)
            self.assertFalse(report_path.exists())
            self.assertEqual(tree_snapshot(root, "wiki"), before)

    def test_apply_stages_migration_and_rollback_restores_exact_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path, original_topic = prepare_legacy_vault(root)
            wiki_before = tree_snapshot(root, "wiki")
            raw_before = tree_snapshot(root, "raw")
            run_dir = root / "work" / "upgrade-run"
            applied = run_upgrade(
                "apply",
                "--wiki-root",
                str(root),
                "--plan",
                str(plan_path),
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            migrated = topic_path.read_text(encoding="utf-8")
            self.assertNotEqual(migrated, original_topic)
            self.assertIn("## 自定义研究记录\n\n保留这段人工内容。", migrated)
            self.assertNotIn("## 关键发现", migrated)
            self.assertTrue(
                (root / "wiki" / "meta" / "topic-state" / "Shared Topic.json").is_file()
            )
            self.assertEqual(tree_snapshot(root, "raw"), raw_before)
            manifest = json.loads(
                (run_dir / "backup-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["status"], "applied")
            self.assertFalse((run_dir / "staging-vault").exists())

            replay = run_upgrade(
                "apply",
                "--wiki-root",
                str(root),
                "--plan",
                str(plan_path),
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertIn("already applied", replay.stdout)

            rolled_back = run_upgrade(
                "rollback",
                "--wiki-root",
                str(root),
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
            self.assertEqual(tree_snapshot(root, "wiki"), wiki_before)
            self.assertEqual(tree_snapshot(root, "raw"), raw_before)

    def test_rollback_refuses_to_overwrite_post_migration_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path, _ = prepare_legacy_vault(root)
            run_dir = root / "work" / "upgrade-run"
            applied = run_upgrade(
                "apply",
                "--wiki-root",
                str(root),
                "--plan",
                str(plan_path),
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            edited = topic_path.read_text(encoding="utf-8") + "\nUser edit.\n"
            topic_path.write_text(edited, encoding="utf-8")
            rolled_back = run_upgrade(
                "rollback",
                "--wiki-root",
                str(root),
                "--run-dir",
                str(run_dir),
            )
            self.assertEqual(rolled_back.returncode, 1)
            self.assertIn("changed after migration", rolled_back.stderr)
            self.assertEqual(topic_path.read_text(encoding="utf-8"), edited)

    def test_stale_migration_plan_never_changes_real_wiki(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path, _ = prepare_legacy_vault(root)
            topic_path = root / "wiki" / "topics" / "Shared Topic.md"
            topic_path.write_text(
                topic_path.read_text(encoding="utf-8") + "\nChanged before apply.\n",
                encoding="utf-8",
            )
            wiki_before = tree_snapshot(root, "wiki")
            result = run_upgrade(
                "apply",
                "--wiki-root",
                str(root),
                "--plan",
                str(plan_path),
                "--run-dir",
                str(root / "work" / "upgrade-run"),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("stale_topic_plan", result.stderr)
            self.assertEqual(tree_snapshot(root, "wiki"), wiki_before)


if __name__ == "__main__":
    unittest.main()
