#!/usr/bin/env python3
"""Regression tests for install.sh host layout.

The skills reference sibling directories (adapters/, vendor/, scripts/) via
'../../' from inside the skill directory. DSH resolves those references
lexically against the skill base directory, so a vault install must place
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
# Representative '../../' references from the skill directory; must all exist
# in the installed layout (lexical resolution, as DSH performs it).
LEXICAL_REFS = (
    "../../adapters/dsh/dsh-mode.md",
    "../../vendor/nature-paper-card/SKILL.md",
    "../../scripts/build_processor_pack.py",
)


def run_install(vault: Path, host: str = "dsh") -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(INSTALL_SH), "--host", host, str(vault)],
        capture_output=True,
        text=True,
    )


def assert_skill_links(test: unittest.TestCase, vault: Path) -> None:
    for name in SKILL_NAMES:
        link = vault / ".dsh" / "skills" / name
        test.assertTrue(link.is_symlink(), f"{link} should be a symlink")
        test.assertEqual(
            os.path.realpath(link),
            os.path.realpath(REPO_ROOT / "skills" / name),
            f"{link} should point into the repo skills/",
        )


def assert_resource_links(test: unittest.TestCase, vault: Path) -> None:
    for name in RESOURCE_NAMES:
        link = vault / ".dsh" / name
        test.assertTrue(link.is_symlink(), f"{link} should be a symlink")
        test.assertEqual(
            os.path.realpath(link),
            os.path.realpath(REPO_ROOT / name),
            f"{link} should point into the repo {name}/",
        )


def assert_lexical_refs_resolve(test: unittest.TestCase, vault: Path) -> None:
    skill_dir = vault / ".dsh" / "skills" / "wiki-paper-card"
    for ref in LEXICAL_REFS:
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
            assert_skill_links(self, vault)
            assert_resource_links(self, vault)
            assert_lexical_refs_resolve(self, vault)
            assert_repo_root_pointer(self, vault, ".dsh")
            self.assertIn("可解析", result.stdout)

    def test_install_writes_repo_root_pointer_for_claude(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            result = run_install(vault, host="claude")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            assert_repo_root_pointer(self, vault, ".claude")

    def test_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            first = run_install(vault)
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            second = run_install(vault)
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            self.assertIn("unchanged", second.stdout)
            assert_resource_links(self, vault)
            assert_repo_root_pointer(self, vault, ".dsh")

    def test_conflicting_resource_path_fails_with_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = make_vault(directory)
            (vault / ".dsh" / "adapters").mkdir(parents=True)
            result = run_install(vault)
            self.assertEqual(result.returncode, 1)
            self.assertIn("CONFLICT", result.stderr)
            self.assertIn("adapters", result.stderr)
            # The conflict must not be silently replaced.
            self.assertTrue((vault / ".dsh" / "adapters").is_dir())
            self.assertFalse((vault / ".dsh" / "adapters").is_symlink())


if __name__ == "__main__":
    unittest.main()
