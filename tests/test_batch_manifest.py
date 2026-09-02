#!/usr/bin/env python3
"""Regression tests for deterministic batch manifests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import batch_manifest


def write_bundle(work_dir: Path, source: Path) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    (work_dir / "source_bundle.json").write_text(
        json.dumps(
            {
                "source_path": str(source.resolve()),
                "source_sha256": digest,
                "validation": {"status": "valid"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class BatchManifestTests(unittest.TestCase):
    def test_builds_canonical_unicode_paths_from_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw" / "papers" / "知识冲突" / "论文一.pdf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"paper-one")
            work_dir = root / "work" / "批次" / "paper-one"
            write_bundle(work_dir, source)

            manifest = batch_manifest.build_manifest(root, root / "work" / "批次")

            self.assertEqual(manifest["paper_count"], 1)
            self.assertEqual(
                manifest["papers"][0],
                {
                    "source_path": "raw/papers/知识冲突/论文一.pdf",
                    "source_sha256": hashlib.sha256(b"paper-one").hexdigest(),
                    "source_ref": "wiki/sources/papers/知识冲突/论文一.md",
                    "work_dir": "work/批次/paper-one",
                },
            )

    def test_rejects_source_outside_raw(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "outside.pdf"
            source.write_bytes(b"outside")
            work_dir = root / "work" / "batch" / "outside"
            write_bundle(work_dir, source)

            with self.assertRaisesRegex(batch_manifest.ManifestError, "source_path must stay under"):
                batch_manifest.build_manifest(root, root / "work" / "batch")

    def test_rejects_source_changed_after_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw" / "paper.pdf"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"prepared")
            work_dir = root / "work" / "batch" / "paper"
            write_bundle(work_dir, source)
            source.write_bytes(b"changed")

            with self.assertRaisesRegex(batch_manifest.ManifestError, "changed after preparation"):
                batch_manifest.build_manifest(root, root / "work" / "batch")

    def test_rejects_two_sources_with_same_target(self) -> None:
        digest_a = hashlib.sha256(b"a").hexdigest()
        digest_b = hashlib.sha256(b"b").hexdigest()
        manifest = {
            "schema_version": "1.0",
            "work_root": "work/batch",
            "papers": [
                {
                    "source_path": "raw/paper.pdf",
                    "source_sha256": digest_a,
                    "source_ref": "wiki/sources/paper.md",
                    "work_dir": "work/batch/a",
                },
                {
                    "source_path": "raw/paper.json",
                    "source_sha256": digest_b,
                    "source_ref": "wiki/sources/paper.md",
                    "work_dir": "work/batch/b",
                },
            ],
        }
        with self.assertRaisesRegex(batch_manifest.ManifestError, "duplicate source_ref"):
            batch_manifest.validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
