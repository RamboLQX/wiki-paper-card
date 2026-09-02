#!/usr/bin/env python3
"""Inspect, apply, and roll back explicit legacy Topic migrations.

The script never creates semantic migration content. An Agent writes a complete
schema 3.0 ``purpose: migration`` plan; this wrapper classifies the Vault,
tests that plan in a staged copy, limits the write set, backs up changed files,
and commits only after deterministic audits pass.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SCRIPT = ROOT / "scripts" / "publish_wiki.py"
LINK_AUDIT_SCRIPT = ROOT / "scripts" / "audit_link_plan.py"
WIKI_AUDIT_SCRIPT = ROOT / "scripts" / "audit_wiki_state.py"
DERIVED_PATHS = {
    Path("wiki/index.md"),
    Path("wiki/log.md"),
    Path("wiki/meta/knowledge-tree.md"),
    Path("wiki/meta/research.md"),
}


def load_publish_module() -> Any:
    spec = importlib.util.spec_from_file_location("publish_wiki", PUBLISH_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError("Unable to load publish_wiki.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PUBLISH = load_publish_module()


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def project_version() -> str:
    version_path = ROOT / "VERSION"
    return version_path.read_text(encoding="utf-8").strip()


def validate_wiki_root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if not root.is_dir():
        raise ValueError("--wiki-root must point to an existing directory")
    if not (root / "wiki").is_dir():
        raise ValueError("--wiki-root must contain wiki/")
    return root


def classify_topic(wiki_root: Path, topic_path: Path) -> dict[str, Any]:
    relative = topic_path.relative_to(wiki_root)
    state_path = PUBLISH.topic_state_path(wiki_root, topic_path)
    base = {
        "path": relative.as_posix(),
        "state_path": state_path.relative_to(wiki_root).as_posix(),
    }
    if topic_path.is_symlink():
        return {**base, "classification": "manual-review", "reason": "topic_is_symlink"}
    try:
        text = topic_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {**base, "classification": "manual-review", "reason": str(exc)}
    if state_path.is_symlink():
        return {**base, "classification": "invalid-state", "reason": "state_is_symlink"}
    if state_path.exists():
        try:
            PUBLISH.load_topic_state(state_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return {**base, "classification": "invalid-state", "reason": str(exc)}
        return {**base, "classification": "current", "reason": "valid_topic_state"}
    _, _, body = PUBLISH.parse_frontmatter(text)
    if PUBLISH.has_managed_blocks(body):
        return {
            **base,
            "classification": "legacy-marker",
            "reason": "complete_legacy_v3_markers",
        }
    return {
        **base,
        "classification": "legacy-plain",
        "reason": "no_topic_state_or_complete_markers",
    }


def inspect_hosts(wiki_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for host, directory, entry in (
        ("claude", ".claude", "CLAUDE.md"),
        ("dsh", ".dsh", "CLAUDE.md"),
        ("codex", ".agents", "AGENTS.md"),
    ):
        host_root = wiki_root / directory
        if not host_root.exists():
            continue
        pointer_path = host_root / "WIKI_PAPER_CARD_ROOT"
        pointer = ""
        if pointer_path.is_file():
            try:
                pointer = pointer_path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeDecodeError):
                pointer = ""
        skill_path = host_root / "skills" / "wiki-paper-card"
        expected_skill = ROOT / "skills" / "wiki-paper-card"
        skill_current = False
        try:
            skill_current = skill_path.resolve() == expected_skill.resolve()
        except OSError:
            pass
        template = ROOT / "template" / entry
        entry_path = wiki_root / entry
        entry_status = "missing"
        if entry_path.is_file():
            try:
                entry_status = (
                    "current"
                    if template.is_file() and entry_path.read_bytes() == template.read_bytes()
                    else "different"
                )
            except OSError:
                entry_status = "unreadable"
        rows.append(
            {
                "host": host,
                "directory": directory,
                "pointer": pointer,
                "pointer_current": bool(pointer) and Path(pointer).expanduser().resolve() == ROOT,
                "skill_current": skill_current,
                "entry": entry,
                "entry_status": entry_status,
            }
        )
    return rows


def inspect_vault(wiki_root: Path) -> dict[str, Any]:
    topic_root = wiki_root / "wiki" / "topics"
    topics = (
        [classify_topic(wiki_root, path) for path in sorted(topic_root.rglob("*.md"))]
        if topic_root.is_dir()
        else []
    )
    counts = {
        name: sum(item["classification"] == name for item in topics)
        for name in (
            "current",
            "legacy-marker",
            "legacy-plain",
            "invalid-state",
            "manual-review",
        )
    }
    state_root = wiki_root / "wiki" / "meta" / "topic-state"
    orphan_states: list[str] = []
    if state_root.is_dir():
        for state_path in sorted(state_root.rglob("*.json")):
            relative = state_path.relative_to(state_root).with_suffix(".md")
            if not (topic_root / relative).is_file():
                orphan_states.append(state_path.relative_to(wiki_root).as_posix())
    runtime_marker = wiki_root / ".wiki-paper-card" / "runtime-version"
    installed_version = None
    if runtime_marker.is_file():
        try:
            installed_version = runtime_marker.read_text(encoding="utf-8").strip() or None
        except (OSError, UnicodeDecodeError):
            installed_version = None
    return {
        "schema_version": "1.0",
        "generated_at": now_utc(),
        "wiki_root": str(wiki_root),
        "repository_version": project_version(),
        "runtime_version": installed_version,
        "summary": {"topics": len(topics), **counts, "orphan_states": len(orphan_states)},
        "topics": topics,
        "orphan_topic_states": orphan_states,
        "hosts": inspect_hosts(wiki_root),
    }


def load_migration_plan(path: Path) -> dict[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read migration plan: {exc}") from exc
    if not isinstance(plan, dict):
        raise ValueError("Migration plan must be a JSON object")
    if plan.get("schema_version") != "3.0" or plan.get("purpose") != "migration":
        raise ValueError("Apply accepts only schema 3.0 purpose=migration plans")
    actions = plan.get("topic_actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("Migration plan must contain at least one topic action")
    return plan


def safe_run_dir(wiki_root: Path, value: Path) -> Path:
    run_dir = value.expanduser().resolve()
    work_root = (wiki_root / "work").resolve()
    if run_dir == work_root or work_root not in run_dir.parents:
        raise ValueError("--run-dir must be a subdirectory of <wiki-root>/work")
    return run_dir


def safe_work_output(wiki_root: Path, value: Path) -> Path:
    output = value.expanduser().resolve()
    work_root = (wiki_root / "work").resolve()
    if output == work_root or work_root not in output.parents:
        raise ValueError("--report must be a file under <wiki-root>/work")
    return output


def migration_allowlist(wiki_root: Path, plan: dict[str, Any]) -> set[Path]:
    allowed = set(DERIVED_PATHS)
    for action in plan["topic_actions"]:
        if not isinstance(action, dict) or action.get("action") != "update_topic":
            raise ValueError("Migration actions may only update existing Topics")
        value = action.get("existing_page")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Every migration action must define existing_page")
        topic_path = PUBLISH.safe_relative_path(wiki_root, value.strip())
        relative = topic_path.relative_to(wiki_root)
        if Path("wiki/topics") not in [relative, *relative.parents]:
            raise ValueError(f"Migration target is outside wiki/topics: {relative}")
        allowed.add(relative)
        allowed.add(PUBLISH.topic_state_path(wiki_root, topic_path).relative_to(wiki_root))
    return allowed


def ensure_wiki_has_no_symlinks(wiki_root: Path) -> None:
    for path in (wiki_root / "wiki").rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Migration does not operate on symlinks inside wiki/: {path}")


def run_command(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(arguments, capture_output=True, text=True)


def file_map(root: Path) -> dict[Path, Path]:
    wiki = root / "wiki"
    return {
        path.relative_to(root): path
        for path in wiki.rglob("*")
        if path.is_file()
    }


def changed_paths(before_root: Path, after_root: Path) -> list[Path]:
    before = file_map(before_root)
    after = file_map(after_root)
    changed: list[Path] = []
    for relative in sorted(set(before) | set(after)):
        before_bytes = before[relative].read_bytes() if relative in before else None
        after_bytes = after[relative].read_bytes() if relative in after else None
        if before_bytes != after_bytes:
            changed.append(relative)
    return changed


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, target)


def record_before(wiki_root: Path, backup_root: Path, relative: Path) -> dict[str, Any]:
    source = wiki_root / relative
    record: dict[str, Any] = {
        "path": relative.as_posix(),
        "existed_before": source.is_file(),
        "before_sha256": sha256_file(source) if source.is_file() else None,
        "backup_path": None,
        "after_sha256": None,
    }
    if source.exists() and not source.is_file():
        raise ValueError(f"Migration target is not a regular file: {relative}")
    if source.is_file():
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)
        record["backup_path"] = backup.relative_to(backup_root.parent).as_posix()
    return record


def matches_version(wiki_root: Path, record: dict[str, Any], field: str) -> bool:
    path = wiki_root / record["path"]
    expected = record.get(field)
    if expected is None:
        return not path.exists()
    return path.is_file() and sha256_file(path) == expected


def restore_records(wiki_root: Path, run_dir: Path, records: list[dict[str, Any]]) -> None:
    for record in records:
        target = wiki_root / record["path"]
        if record["existed_before"]:
            backup_value = record.get("backup_path")
            if not isinstance(backup_value, str):
                raise ValueError(f"Backup is missing for {record['path']}")
            atomic_copy(run_dir / backup_value, target)
        elif target.is_file():
            target.unlink()


def apply_migration(wiki_root: Path, plan_path: Path, run_dir: Path) -> int:
    plan = load_migration_plan(plan_path)
    plan_sha256 = sha256_file(plan_path)
    allowed = migration_allowlist(wiki_root, plan)
    ensure_wiki_has_no_symlinks(wiki_root)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "backup-manifest.json"
    stage_root = run_dir / "staging-vault"
    if manifest_path.exists():
        try:
            previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Unable to read existing backup manifest: {exc}") from exc
        previous_files = previous_manifest.get("files", [])
        if (
            previous_manifest.get("status") == "applied"
            and previous_manifest.get("plan_sha256") == plan_sha256
            and isinstance(previous_files, list)
            and previous_files
            and all(
                isinstance(record, dict)
                and isinstance(record.get("path"), str)
                and matches_version(wiki_root, record, "after_sha256")
                for record in previous_files
            )
        ):
            print("Migration already applied; no files changed")
            return 0
        raise ValueError("--run-dir already contains different or incomplete migration state")
    if stage_root.exists():
        raise ValueError("--run-dir contains stale staging state; use a new run directory")

    plan_report = run_dir / "migration-plan-report.json"
    audit = run_command(
        [sys.executable, str(LINK_AUDIT_SCRIPT), "--plan", str(plan_path), "--report", str(plan_report)]
    )
    if audit.returncode:
        sys.stderr.write(audit.stdout + audit.stderr)
        return 1

    stage_root.mkdir(parents=True)
    shutil.copytree(wiki_root / "wiki", stage_root / "wiki")
    staged_publish_report = run_dir / "staged-publish-report.json"
    publish = run_command(
        [
            sys.executable,
            str(PUBLISH_SCRIPT),
            "--plan",
            str(plan_path),
            "--wiki-root",
            str(stage_root),
            "--report",
            str(staged_publish_report),
        ]
    )
    if publish.returncode:
        sys.stderr.write(publish.stdout + publish.stderr)
        shutil.rmtree(stage_root)
        return 1

    staged_audit_report = run_dir / "staged-wiki-audit-report.json"
    staged_audit = run_command(
        [
            sys.executable,
            str(WIKI_AUDIT_SCRIPT),
            "--wiki-root",
            str(stage_root),
            "--report",
            str(staged_audit_report),
        ]
    )
    if staged_audit.returncode:
        sys.stderr.write(staged_audit.stdout + staged_audit.stderr)
        shutil.rmtree(stage_root)
        return 1

    changed = changed_paths(wiki_root, stage_root)
    unexpected = sorted(set(changed) - allowed)
    if unexpected:
        shutil.rmtree(stage_root)
        raise ValueError(
            "Staged publisher changed paths outside the migration write set: "
            + ", ".join(path.as_posix() for path in unexpected)
        )
    if not changed:
        shutil.rmtree(stage_root)
        write_json(
            run_dir / "migration-result.json",
            {
                "schema_version": "1.0",
                "status": "no-op",
                "plan_sha256": plan_sha256,
                "verified_at": now_utc(),
            },
        )
        print("Migration is already reflected in the Vault; no files changed")
        return 0

    backup_root = run_dir / "backup"
    records = [record_before(wiki_root, backup_root, relative) for relative in changed]
    manifest = {
        "schema_version": "1.0",
        "status": "prepared",
        "created_at": now_utc(),
        "wiki_root": str(wiki_root),
        "plan_path": str(plan_path),
        "plan_sha256": plan_sha256,
        "files": records,
    }
    write_json(manifest_path, manifest)
    if not all(matches_version(wiki_root, record, "before_sha256") for record in records):
        shutil.rmtree(stage_root)
        raise ValueError("Vault changed after staging; no migration files were committed")

    committed: list[dict[str, Any]] = []
    try:
        for record in records:
            source = stage_root / record["path"]
            if not source.is_file():
                raise ValueError(f"Staged migration unexpectedly deleted {record['path']}")
            atomic_copy(source, wiki_root / record["path"])
            committed.append(record)
        for record in records:
            record["after_sha256"] = sha256_file(wiki_root / record["path"])
        manifest["status"] = "applied"
        manifest["applied_at"] = now_utc()
        write_json(manifest_path, manifest)

        final_audit_report = run_dir / "wiki-audit-report.json"
        final_audit = run_command(
            [
                sys.executable,
                str(WIKI_AUDIT_SCRIPT),
                "--wiki-root",
                str(wiki_root),
                "--report",
                str(final_audit_report),
            ]
        )
        if final_audit.returncode:
            raise RuntimeError(final_audit.stdout + final_audit.stderr)
    except Exception:
        restore_records(wiki_root, run_dir, committed)
        manifest["status"] = "failed-restored"
        manifest["restored_at"] = now_utc()
        write_json(manifest_path, manifest)
        shutil.rmtree(stage_root)
        raise

    shutil.rmtree(stage_root)
    print(f"Migration applied: {len(records)} file(s) changed; backup={manifest_path}")
    return 0


def rollback_migration(wiki_root: Path, run_dir: Path) -> int:
    manifest_path = run_dir / "backup-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read backup manifest: {exc}") from exc
    if manifest.get("status") != "applied":
        raise ValueError("Rollback requires an applied migration manifest")
    if Path(str(manifest.get("wiki_root", ""))).expanduser().resolve() != wiki_root:
        raise ValueError("Backup manifest belongs to a different Vault")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Backup manifest has no files")
    if any(
        not isinstance(record, dict) or not isinstance(record.get("path"), str)
        for record in records
    ):
        raise ValueError("Backup manifest contains an invalid file record")
    changed_after = [
        record["path"]
        for record in records
        if not matches_version(wiki_root, record, "after_sha256")
    ]
    if changed_after:
        raise ValueError(
            "Rollback refused because files changed after migration: "
            + ", ".join(changed_after)
        )
    restore_records(wiki_root, run_dir, records)
    manifest["status"] = "rolled-back"
    manifest["rolled_back_at"] = now_utc()
    write_json(manifest_path, manifest)
    rollback_report = run_dir / "rollback-wiki-audit-report.json"
    run_command(
        [
            sys.executable,
            str(WIKI_AUDIT_SCRIPT),
            "--wiki-root",
            str(wiki_root),
            "--report",
            str(rollback_report),
        ]
    )
    print(f"Migration rolled back: {len(records)} file(s) restored")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and safely apply explicit wiki-paper-card Topic migrations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Classify runtime and Topic state without modifying Wiki content.")
    inspect_parser.add_argument("--wiki-root", type=Path, required=True)
    inspect_parser.add_argument("--report", type=Path)

    apply_parser = subparsers.add_parser("apply", help="Stage, audit, back up, and apply a purpose=migration plan.")
    apply_parser.add_argument("--wiki-root", type=Path, required=True)
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--run-dir", type=Path, required=True)

    rollback_parser = subparsers.add_parser("rollback", help="Restore an applied migration when no migrated file has changed since.")
    rollback_parser.add_argument("--wiki-root", type=Path, required=True)
    rollback_parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        wiki_root = validate_wiki_root(args.wiki_root)
        if args.command == "inspect":
            report_path = safe_work_output(wiki_root, args.report) if args.report else None
            report = inspect_vault(wiki_root)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if report_path:
                write_json(report_path, report)
            return 0
        run_dir = safe_run_dir(wiki_root, args.run_dir)
        if args.command == "apply":
            plan_path = args.plan.expanduser().resolve()
            if not plan_path.is_file():
                raise ValueError("--plan must point to an existing file")
            return apply_migration(wiki_root, plan_path, run_dir)
        return rollback_migration(wiki_root, run_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
