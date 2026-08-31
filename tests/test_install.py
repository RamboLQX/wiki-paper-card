#!/usr/bin/env python3
"""Regression tests for install.sh host layouts.

The skills reference sibling directories (adapters/, vendor/, scripts/) via
'../../' from inside the skill directory. Hosts resolve those references
against the skill base directory, so a vault install must place
those siblings next to the host skills or every session fails with
"cannot read .../adapters/dsh/dsh-mode.md: not found". The install must also
write a WIKI_PAPER_CARD_ROOT pointer file into each host directory so sessions
resolve <REPO_ROOT> deterministically instead of inferring it from the skill
symlink. These tests pin the install layout and its self-check.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).parents[1]
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
SKILL_NAMES = ("wiki-paper-card", "wiki-shared", "wiki-gap-mining")
RESOURCE_NAMES = ("adapters", "vendor", "scripts")
# Representative shared '../../' references from the skill directory.
SHARED_LEXICAL_REFS = (
    "../../vendor/nature-paper-card/SKILL.md",
    "../../scripts/build_processor_pack.py",
)
HOST_ADAPTER_REF = {
    ".claude": "../../adapters/claude-code/agents/wiki-processor.md",
    ".dsh": "../../adapters/dsh/dsh-mode.md",
    ".agents": "../../adapters/codex/codex-mode.md",
}


def run_install(vault: Path, host: str = "dsh") -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(INSTALL_SH), "--host", host, str(vault)],
        capture_output=True,
        text=True,
    )


def run_default_install(vault: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(INSTALL_SH), str(vault)],
        capture_output=True,
        text=True,
    )


def assert_skill_links(test: unittest.TestCase, vault: Path, host_dir: str) -> None:
    for name in SKILL_NAMES:
        link = vault / host_dir / "skills" / name
        test.assertTrue(link.is_symlink(), f"{link} should be a symlink")
        test.assertEqual(
            os.path.realpath(link),
            os.path.realpath(REPO_ROOT / "skills" / name),
            f"{link} should point into the repo skills/",
        )


def assert_resource_links(test: unittest.TestCase, vault: Path, host_dir: str) -> None:
    for name in RESOURCE_NAMES:
        link = vault / host_dir / name
        test.assertTrue(link.is_symlink(), f"{link} should be a symlink")
        test.assertEqual(
            os.path.realpath(link),
            os.path.realpath(REPO_ROOT / name),
            f"{link} should point into the repo {name}/",
        )


def assert_lexical_refs_resolve(test: unittest.TestCase, vault: Path, host_dir: str) -> None:
    skill_dir = vault / host_dir / "skills" / "wiki-paper-card"
    refs = (*SHARED_LEXICAL_REFS, HOST_ADAPTER_REF[host_dir])
    for ref in refs:
        target = Path(os.path.normpath(str(skill_dir / ref)))
        test.assertTrue(target.is_file(), f"../../ ref {ref} should resolve to {target}")


def assert_repo_root_pointer(test: unittest.TestCase, vault: Path, host_dir: str) -> None:
    """The install must write a deterministic <REPO_ROOT> pointer file whose
    target exposes the pinned upstream router, so sessions never have to infer
    the repository root from the skill symlink."""
    pointer = vault / host_dir / "WIKI_PAPER_CARD_ROOT"
    test.assertTrue(pointer.is_file(), f"{pointer} should be a pointer file")
    content = pointer.read_text(encoding="utf-8").strip()
    test.assertEqual(os.path.realpath(content), os.path.realpath(REPO_ROOT),
                     f"{pointer} should contain the repository root")
    pinned = Path(content) / "vendor" / "nature-paper-card" / "SKILL.md"
    test.assertTrue(pinned.is_file(), f"pointer target should expose the pinned router: {pinned}")


def make_vault(directory: str) -> Path:
    vault = Path(directory) / "vault"
    vault.mkdir()
    return vault


class InstallLayoutTests(unittest.TestCase):
    def test_dsh_install_creates_skills_and_resource_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            assert_skill_links(self, vault, ".dsh")
            assert_resource_links(self, vault, ".dsh")
            assert_lexical_refs_resolve(self, vault, ".dsh")
            assert_repo_root_pointer(self, vault, ".dsh")
            self.assertIn("可解析", result.stdout)

    def test_install_writes_repo_root_pointer_for_claude(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="claude")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            assert_skill_links(self, vault, ".claude")
            assert_resource_links(self, vault, ".claude")
            assert_lexical_refs_resolve(self, vault, ".claude")
            assert_repo_root_pointer(self, vault, ".claude")

    def test_codex_install_creates_layout_and_agents_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="codex")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            assert_skill_links(self, vault, ".agents")
            assert_resource_links(self, vault, ".agents")
            assert_lexical_refs_resolve(self, vault, ".agents")
            assert_repo_root_pointer(self, vault, ".agents")
            self.assertEqual(
                (vault / "AGENTS.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "template" / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertFalse((vault / "CLAUDE.md").exists())
            self.assertFalse((vault / ".claude").exists())
            self.assertFalse((vault / ".dsh").exists())

    def test_both_keeps_legacy_claude_and_dsh_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="both")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((vault / ".claude").is_dir())
            self.assertTrue((vault / ".dsh").is_dir())
            self.assertTrue((vault / "CLAUDE.md").is_file())
            self.assertFalse((vault / ".agents").exists())
            self.assertFalse((vault / "AGENTS.md").exists())

    def test_default_install_keeps_legacy_both_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_default_install(vault)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Install complete for host: both", result.stdout)
            self.assertTrue((vault / ".claude").is_dir())
            self.assertTrue((vault / ".dsh").is_dir())
            self.assertFalse((vault / ".agents").exists())

    def test_all_install_creates_three_hosts_with_identical_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="all")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            for host_dir in (".claude", ".dsh", ".agents"):
                assert_skill_links(self, vault, host_dir)
                assert_resource_links(self, vault, host_dir)
                assert_repo_root_pointer(self, vault, host_dir)
            self.assertEqual(
                (vault / "CLAUDE.md").read_text(encoding="utf-8"),
                (vault / "AGENTS.md").read_text(encoding="utf-8"),
            )

    def test_codex_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            first = run_install(vault, host="codex")
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            second = run_install(vault, host="codex")
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            self.assertIn("unchanged", second.stdout)
            assert_resource_links(self, vault, ".agents")
            assert_repo_root_pointer(self, vault, ".agents")

    def test_all_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            first = run_install(vault, host="all")
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            second = run_install(vault, host="all")
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            self.assertIn("unchanged", second.stdout)
            self.assertNotIn("WARNING", second.stderr)

    def test_existing_agents_entry_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            custom = "# Existing Vault Rules\n"
            (vault / "AGENTS.md").write_text(custom, encoding="utf-8")
            result = run_install(vault, host="codex")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual((vault / "AGENTS.md").read_text(encoding="utf-8"), custom)
            self.assertIn("merge missing sections manually", result.stdout)

    def test_all_warns_when_entry_files_differ(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            (vault / "CLAUDE.md").write_text("# Existing Claude Rules\n", encoding="utf-8")
            result = run_install(vault, host="all")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("DSH may load both", result.stderr)
            self.assertEqual(
                (vault / "CLAUDE.md").read_text(encoding="utf-8"),
                "# Existing Claude Rules\n",
            )

    def test_conflicting_resource_path_fails_with_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            (vault / ".agents" / "adapters").mkdir(parents=True)
            result = run_install(vault, host="codex")
            self.assertEqual(result.returncode, 1)
            self.assertIn("CONFLICT", result.stderr)
            self.assertIn("adapters", result.stderr)
            # The conflict must not be silently replaced.
            self.assertTrue((vault / ".agents" / "adapters").is_dir())
            self.assertFalse((vault / ".agents" / "adapters").is_symlink())

    def test_invalid_host_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="unknown")
            self.assertEqual(result.returncode, 2)
            self.assertIn("codex", result.stderr)
            self.assertIn("all", result.stderr)

    def test_completion_report_lists_only_selected_host_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="codex")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn(".agents/WIKI_PAPER_CARD_ROOT", result.stdout)
            self.assertNotIn(".dsh/WIKI_PAPER_CARD_ROOT", result.stdout)
            self.assertNotIn(".claude/WIKI_PAPER_CARD_ROOT", result.stdout)


if __name__ == "__main__":
    unittest.main()
