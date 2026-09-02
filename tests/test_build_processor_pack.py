#!/usr/bin/env python3
"""Regression tests for processor context pack generation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_processor_pack.py"
SPEC = importlib.util.spec_from_file_location("build_processor_pack", SCRIPT_PATH)
assert SPEC and SPEC.loader
PACK_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACK_MODULE)

FIXTURE_FILES = {
    "skills/wiki-paper-card/references/processor-brief.md": "# processor brief fixture\n",
    "skills/wiki-paper-card/references/paper-digest-schema.md": "# digest schema fixture\n",
    "skills/wiki-shared/references/knowledge-model.md": "# knowledge model fixture\n",
    "skills/wiki-shared/references/writing-guide.md": "# writing guide fixture\n",
    "vendor/nature-paper-card/SKILL.md": "# upstream router fixture\n",
    "vendor/nature-paper-card/manifest.yaml": (
        "name: fixture\n"
        "always_load:\n"
        "  - ../nature-shared/core/terminology-ledger.md\n"
        "  - static/core/principles.md\n"
        "  - static/core/workflow.md\n"
        "  - static/core/output-contract.md\n"
        "axes:\n"
        "  paper_type:\n"
        "    values:\n"
        "      methods:   static/fragments/paper_type/methods.md\n"
        "      discovery: static/fragments/paper_type/discovery.md\n"
        "      resource:  static/fragments/paper_type/resource.md\n"
        "      clinical:  static/fragments/paper_type/clinical.md\n"
        "      materials: static/fragments/paper_type/materials.md\n"
        "      review:    static/fragments/paper_type/review.md\n"
        "    default: methods\n"
        "references:\n"
        "  on_demand:\n"
        "    - condition: provenance labels\n"
        "      path: references/evidence-and-provenance.md\n"
        "    - condition: card structure\n"
        "      path: references/card-schema.md\n"
        "    - condition: research ideas\n"
        "      path: references/research-idea-gates.md\n"
    ),
    "vendor/nature-paper-card/static/core/principles.md": "# principles fixture\n",
    "vendor/nature-paper-card/static/core/workflow.md": "# workflow fixture\n",
    "vendor/nature-paper-card/static/core/output-contract.md": "# output contract fixture\n",
    "vendor/nature-shared/core/terminology-ledger.md": "# terminology fixture\n",
    "vendor/nature-paper-card/references/evidence-and-provenance.md": "# provenance fixture\n",
    "vendor/nature-paper-card/references/card-schema.md": "# card schema fixture\n",
    "vendor/nature-paper-card/references/research-idea-gates.md": "# idea gates fixture\n",
}
for lens in ("methods", "discovery", "resource", "clinical", "materials", "review"):
    FIXTURE_FILES[f"vendor/nature-paper-card/static/fragments/paper_type/{lens}.md"] = (
        f"# {lens} lens fixture\n"
    )


def build_fixture(directory: Path) -> Path:
    root = directory / "fixture-repo"
    for rel, content in FIXTURE_FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


class ManifestParsingTests(unittest.TestCase):
    def test_fallback_parser_matches_yaml_parser_on_real_manifest(self) -> None:
        text = (ROOT / "vendor" / "nature-paper-card" / "manifest.yaml").read_text(
            encoding="utf-8"
        )
        from_yaml = PACK_MODULE.parse_manifest_yaml(text)
        from_fallback = PACK_MODULE.parse_manifest_fallback(text)
        self.assertEqual(from_yaml["always_load"], from_fallback["always_load"])
        self.assertEqual(
            from_yaml["axes"]["paper_type"]["values"],
            from_fallback["axes"]["paper_type"]["values"],
        )
        yaml_paths = [
            item.get("path") if isinstance(item, dict) else item
            for item in from_yaml["references"]["on_demand"]
        ]
        self.assertEqual(yaml_paths, from_fallback["references"]["on_demand"])


class TopicDiscoveryContractTests(unittest.TestCase):
    def test_paper_card_reader_contract_covers_summary_and_internal_marker(self) -> None:
        processor = (
            ROOT / "skills/wiki-paper-card/references/processor-brief.md"
        ).read_text(encoding="utf-8")
        writing_guide = (
            ROOT / "skills/wiki-shared/references/writing-guide.md"
        ).read_text(encoding="utf-8")
        digest = (
            ROOT / "skills/wiki-paper-card/references/paper-digest-schema.md"
        ).read_text(encoding="utf-8")
        combined = " ".join((processor + writing_guide + digest).split())
        self.assertIn("problem or motivation", combined)
        self.assertIn("core approach", combined)
        self.assertIn("evidence-bounded result or contribution", combined)
        self.assertIn("Never render that marker in the Paper Card", combined)

    def test_gap_contract_uses_only_four_inputs_and_no_count_target(self) -> None:
        processor = (
            ROOT / "skills/wiki-paper-card/references/processor-brief.md"
        ).read_text(encoding="utf-8")
        digest = (
            ROOT / "skills/wiki-paper-card/references/paper-digest-schema.md"
        ).read_text(encoding="utf-8")
        linker = (
            ROOT / "skills/wiki-paper-card/references/linker-brief.md"
        ).read_text(encoding="utf-8")
        self.assertIn("exactly four inputs and no others", processor)
        for signal in (
            "analysis.limitations",
            "analysis.critical_observations",
            "analysis.unexplained_results",
            "Topic seeds",
        ):
            self.assertIn(signal, processor)
        self.assertIn("must not be copied into a Topic seed", digest)
        self.assertIn("There is no target gap count", linker)
        self.assertNotIn("Record only the 2-3 gaps", linker)

    def test_processor_contract_supports_overlapping_comparison_views(self) -> None:
        processor = (
            ROOT / "skills/wiki-paper-card/references/processor-brief.md"
        ).read_text(encoding="utf-8")
        digest = (
            ROOT / "skills/wiki-paper-card/references/paper-digest-schema.md"
        ).read_text(encoding="utf-8")
        combined = processor + "\n" + digest
        normalized = " ".join(combined.split())
        self.assertIn("paper-supported candidate comparison view", normalized)
        self.assertIn("overlap in paper membership", normalized)
        self.assertIn("discovery prompts, not required categories", normalized)
        self.assertNotIn("non-overlapping seeds", normalized)

    def test_linker_contract_reviews_disjoint_partitions_without_forcing_overlap(
        self,
    ) -> None:
        linker = (
            ROOT / "skills/wiki-paper-card/references/linker-brief.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Build candidate comparison views across the batch", linker)
        self.assertIn("paper-to-action membership map", linker)
        self.assertIn("disjoint partition of the batch", linker)
        self.assertIn("Do not manufacture overlap", linker)
        self.assertIn("do not create a whole-batch Topic unless", linker)

    def test_topic_discovery_rules_remain_domain_neutral(self) -> None:
        contract_paths = (
            "skills/wiki-paper-card/references/processor-brief.md",
            "skills/wiki-paper-card/references/paper-digest-schema.md",
            "skills/wiki-paper-card/references/linker-brief.md",
            "skills/wiki-shared/references/knowledge-model.md",
        )
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8") for path in contract_paths
        )
        self.assertNotIn("knowledge conflict", combined.lower())
        self.assertNotIn("知识冲突", combined)


class BuildPackTests(unittest.TestCase):
    def test_build_pack_merges_all_expected_sources(self) -> None:
        pack, records = PACK_MODULE.build_pack(ROOT)
        roles = [record["role"] for record in records]
        for expected in (
            "processor-brief",
            "upstream-router",
            "upstream-manifest",
            "knowledge-model",
            "writing-guide",
            "digest-schema",
            "lens:methods",
            "lens:review",
            "reference:references/card-schema.md",
        ):
            self.assertIn(expected, roles)
        self.assertGreaterEqual(len(records), 18)
        for section in (
            "## processor-brief",
            "## upstream-router",
            "## writing-guide",
            "## lens:methods",
        ):
            self.assertIn(section, pack)
        self.assertIn("Nature Paper Card - Router", pack)  # upstream router content

    def test_build_pack_is_deterministic(self) -> None:
        first, _ = PACK_MODULE.build_pack(ROOT)
        second, _ = PACK_MODULE.build_pack(ROOT)
        self.assertEqual(first, second)

    def test_manifest_records_match_source_hashes(self) -> None:
        _, records = PACK_MODULE.build_pack(ROOT)
        for record in records:
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(
                record["sha256"], PACK_MODULE.sha256_file(path), record["role"]
            )

    def test_missing_source_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = build_fixture(Path(directory))
            (root / "vendor/nature-paper-card/SKILL.md").unlink()
            with self.assertRaises(ValueError):
                PACK_MODULE.build_pack(root)


class VerifyCliTests(unittest.TestCase):
    def test_verify_passes_then_fails_after_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = build_fixture(base)
            pack_path = base / "processor-pack.md"
            manifest_path = base / "processor-pack.manifest.json"
            command = [
                sys.executable,
                str(SCRIPT_PATH),
                "--repo-root",
                str(root),
                "--output",
                str(pack_path),
                "--manifest",
                str(manifest_path),
            ]
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            verify = command + ["--verify"]
            result = subprocess.run(verify, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("VERIFY OK", result.stdout)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "1.0")
            self.assertEqual(manifest["pack_sha256"], PACK_MODULE.sha256_file(pack_path))

            (root / "skills/wiki-paper-card/references/processor-brief.md").write_text(
                "# changed\n", encoding="utf-8"
            )
            result = subprocess.run(verify, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("VERIFY FAIL", result.stderr)


if __name__ == "__main__":
    unittest.main()
