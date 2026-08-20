#!/usr/bin/env python3
"""Validate a batch link-plan.json before wiki writes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_KINDS = {"concept", "entity"}
ALLOWED_HUB_ACTIONS = {"create_hub", "update_hub"}
ALLOWED_TOPIC_ACTIONS = {"create_topic", "update_topic"}
ALLOWED_RELATION_TYPES = {
    "defines",
    "uses",
    "extends",
    "implements",
    "derived_from",
    "supports",
    "contradicts",
    "same_as",
    "is_instance_of",
    "applied_to",
}
ALLOWED_PROVENANCE = {"Paper", "External", "Analysis", "Hypothesis", "User"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def finding(level: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"level": level, "code": code, "message": message}
    if details:
        item["details"] = details
    return item


def require_string(
    item: dict[str, Any],
    field: str,
    findings: list[dict[str, Any]],
    item_label: str,
) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        findings.append(
            finding(
                "error",
                "missing_string",
                f"{item_label} must define {field}.",
                item=item.get("id") or item.get("name"),
                field=field,
            )
        )
        return ""
    return value.strip()


def require_list(
    item: dict[str, Any],
    field: str,
    findings: list[dict[str, Any]],
    item_label: str,
) -> list[Any]:
    value = item.get(field)
    if not isinstance(value, list):
        findings.append(
            finding(
                "error",
                "missing_list",
                f"{item_label} must define {field} as a list.",
                item=item.get("id") or item.get("name"),
                field=field,
            )
        )
        return []
    return value


def audit_pointer(pointer: str) -> bool:
    return isinstance(pointer, str) and pointer.startswith(("[Paper:", "[External:"))


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def audit_relations(relations: Any, label: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not isinstance(relations, list):
        return [finding("error", "relations", f"{label} relations must be a list.")]
    for index, relation in enumerate(relations, start=1):
        if not isinstance(relation, dict):
            findings.append(finding("error", "relation_row", f"{label} relation {index} must be an object."))
            continue
        if relation.get("type") not in ALLOWED_RELATION_TYPES:
            findings.append(
                finding("error", "relation_type", f"{label} relation {index} has invalid type.", type=relation.get("type"))
            )
        require_string(relation, "target", findings, f"{label} relation {index}")
        if not audit_pointer(relation.get("pointer", "")):
            findings.append(
                finding(
                    "error",
                    "relation_pointer",
                    f"{label} relation {index} must define a valid pointer.",
                    pointer=relation.get("pointer"),
                )
            )
        if relation.get("provenance") not in ALLOWED_PROVENANCE:
            findings.append(
                finding(
                    "error",
                    "relation_provenance",
                    f"{label} relation {index} has invalid provenance.",
                    provenance=relation.get("provenance"),
                )
            )
        if relation.get("confidence") not in ALLOWED_CONFIDENCE:
            findings.append(
                finding(
                    "error",
                    "relation_confidence",
                    f"{label} relation {index} has invalid confidence.",
                    confidence=relation.get("confidence"),
                )
            )
    return findings


def audit_hub_action(action: dict[str, Any], batch_refs: set[str], target_names: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    label = f"hub action {action.get('id') or action.get('name') or '<unnamed>'}"
    action_type = require_string(action, "action", findings, label)
    kind = require_string(action, "kind", findings, label)
    tier = require_string(action, "tier", findings, label)
    require_string(action, "id", findings, label)
    name = require_string(action, "name", findings, label)
    require_string(action, "definition", findings, label)

    if action_type not in ALLOWED_HUB_ACTIONS:
        findings.append(finding("error", "hub_action", f"{label} has invalid action.", action=action_type))
    if kind not in ALLOWED_KINDS:
        findings.append(finding("error", "hub_kind", f"{label} has invalid kind.", kind=kind))
    if tier != "L2":
        findings.append(finding("error", "hub_tier", f"{label} must use L2.", tier=tier))
    if name and name in target_names:
        findings.append(finding("error", "duplicate_target", f"{label} duplicates target page {name}.", name=name))
    elif name:
        target_names.add(name)

    source_refs = set(string_list(action.get("source_refs")))
    unknown_refs = sorted(source_refs - batch_refs)
    if unknown_refs:
        findings.append(
            finding(
                "error",
                "unknown_source_refs",
                f"{label} references sources outside the current batch.",
                source_refs=unknown_refs,
            )
        )
    if action_type == "create_hub":
        if len(source_refs) < 2 and action.get("connect_existing") is not True:
            findings.append(
                finding(
                    "error",
                    "cross_source",
                    "create_hub requires two distinct source pages or connect_existing.",
                    source_refs=sorted(source_refs),
                )
            )
    elif action_type == "update_hub":
        if action.get("connect_existing") is not True and not string_list([action.get("existing_page")]):
            findings.append(
                finding(
                    "error",
                    "existing_page",
                    "update_hub requires connect_existing or existing_page.",
                )
            )

    evidence = action.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        findings.append(finding("error", "evidence", f"{label} must have at least one evidence row."))
    else:
        for index, row in enumerate(evidence, start=1):
            if not isinstance(row, dict):
                findings.append(finding("error", "evidence_row", f"{label} evidence row {index} must be an object."))
                continue
            source_ref = require_string(row, "source_ref", findings, f"{label} evidence row {index}")
            if source_ref and source_ref not in batch_refs:
                findings.append(
                    finding(
                        "error",
                        "evidence_source",
                        f"{label} evidence row {index} must reference a batch source page.",
                        source_ref=source_ref,
                    )
                )
            if not audit_pointer(row.get("pointer", "")):
                findings.append(
                    finding(
                        "error",
                        "evidence_pointer",
                        f"{label} evidence row {index} must define a valid pointer.",
                        pointer=row.get("pointer"),
                    )
                )
            require_string(row, "claim", findings, f"{label} evidence row {index}")

    findings.extend(audit_relations(action.get("relations", []), label))
    return findings


def audit_topic_action(action: dict[str, Any], batch_refs: set[str], target_names: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    label = f"topic action {action.get('id') or action.get('name') or '<unnamed>'}"
    action_type = require_string(action, "action", findings, label)
    require_string(action, "id", findings, label)
    name = require_string(action, "name", findings, label)
    require_string(action, "summary", findings, label)

    if action_type not in ALLOWED_TOPIC_ACTIONS:
        findings.append(finding("error", "topic_action", f"{label} has invalid action.", action=action_type))
    if name and name in target_names:
        findings.append(finding("error", "duplicate_target", f"{label} duplicates target page {name}.", name=name))
    elif name:
        target_names.add(name)

    papers = set(string_list(action.get("papers")))
    unknown_refs = sorted(papers - batch_refs)
    if unknown_refs:
        findings.append(
            finding(
                "error",
                "unknown_topic_papers",
                f"{label} references papers outside the current batch.",
                papers=unknown_refs,
            )
        )
    if action_type == "create_topic" and len(papers) < 2:
        findings.append(
            finding(
                "error",
                "topic_papers",
                "create_topic requires at least two distinct batch source pages.",
                papers=sorted(papers),
            )
        )
    if action_type == "update_topic" and not string_list([action.get("existing_page")]):
        findings.append(finding("error", "existing_page", "update_topic requires existing_page."))

    comparisons = action.get("comparisons", [])
    if not isinstance(comparisons, list):
        findings.append(finding("error", "comparisons", f"{label} comparisons must be a list."))
    else:
        for index, row in enumerate(comparisons, start=1):
            if not isinstance(row, dict):
                findings.append(finding("error", "comparison_row", f"{label} comparison {index} must be an object."))
                continue
            if "dimension" in row:
                continue
            paper = (row.get("paper") or row.get("source_ref") or "").strip()
            method = row.get("method", "")
            if not paper and not method:
                findings.append(finding("error", "comparison_identity", f"{label} comparison {index} has no paper identity or method."))
            if "granularity" in row and "intervention_granularity" not in row:
                findings.append(finding("warning", "comparison_legacy_key", f"{label} comparison {index} uses legacy 'granularity'; use 'intervention_granularity'.", field="granularity"))
            if not row.get("intervention_granularity") and not row.get("granularity"):
                findings.append(finding("warning", "comparison_granularity", f"{label} comparison {index} lacks intervention granularity.", paper=paper))

    contradictions = action.get("contradictions", [])
    if isinstance(contradictions, list):
        for index, item in enumerate(contradictions, start=1):
            if not isinstance(item, dict):
                continue
            pos_a = item.get("position_a") or item.get("a")
            pos_b = item.get("position_b") or item.get("b")
            if "resolve" in item and "resolving_evidence" not in item:
                findings.append(finding("warning", "contradiction_legacy_key", f"{label} contradiction {index} uses legacy 'resolve'; use 'resolving_evidence'.", field="resolve"))
            if pos_a and pos_b and not (item.get("resolving_evidence") or item.get("resolve")):
                findings.append(finding("warning", "contradiction_resolution", f"{label} contradiction {index} has two positions but no resolving evidence."))

    key_findings = action.get("key_findings", [])
    if isinstance(key_findings, list):
        for index, item in enumerate(key_findings, start=1):
            if not isinstance(item, dict):
                continue
            if not str(item.get("claim", "")).strip():
                findings.append(finding("warning", "key_finding_claim", f"{label} key_finding {index} lacks a claim."))
            kind = item.get("kind")
            if kind and kind not in {"consensus", "single", "conflict"}:
                findings.append(finding("warning", "key_finding_kind", f"{label} key_finding {index} has unknown kind.", kind=kind))

    research_gaps = action.get("research_gaps", [])
    if isinstance(research_gaps, list):
        for index, item in enumerate(research_gaps, start=1):
            if isinstance(item, str):
                continue
            if not isinstance(item, dict) or not str(item.get("gap", "")).strip():
                findings.append(finding("error", "research_gap_shape", f"{label} research_gap {index} must be a string or an object with a non-empty gap."))

    return findings


def audit(plan: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not isinstance(plan, dict):
        return {
            "schema_version": "1.0",
            "summary": {"status": "fail", "passes": 0, "warnings": 0, "errors": 1},
            "metrics": {},
            "findings": [finding("error", "top_level", "Link plan must be a JSON object.")],
        }
    if plan.get("schema_version") != "1.0":
        findings.append(finding("error", "schema_version", "Unsupported link plan schema version."))

    batch = plan.get("batch", {})
    source_pages = require_list(batch, "source_pages", findings, "batch") if isinstance(batch, dict) else []
    batch_refs: set[str] = set()
    for index, page in enumerate(source_pages, start=1):
        if not isinstance(page, dict):
            findings.append(finding("error", "source_page", f"batch source page {index} must be an object."))
            continue
        source_ref = require_string(page, "source_ref", findings, f"batch source page {index}")
        if source_ref:
            batch_refs.add(source_ref)
        require_string(page, "work_dir", findings, f"batch source page {index}")
        require_string(page, "title", findings, f"batch source page {index}")
    if not batch_refs:
        findings.append(finding("error", "batch", "Link plan must define at least one batch source page."))

    target_names: set[str] = set()
    hub_actions = require_list(plan, "hub_actions", findings, "link plan")
    for action in hub_actions:
        if not isinstance(action, dict):
            findings.append(finding("error", "hub_action", "Each hub action must be an object."))
            continue
        findings.extend(audit_hub_action(action, batch_refs, target_names))

    topic_actions = require_list(plan, "topic_actions", findings, "link plan")
    for action in topic_actions:
        if not isinstance(action, dict):
            findings.append(finding("error", "topic_action", "Each topic action must be an object."))
            continue
        findings.extend(audit_topic_action(action, batch_refs, target_names))

    return {
        "schema_version": "1.0",
        "summary": {
            "status": "fail"
            if any(item["level"] == "error" for item in findings)
            else ("pass_with_warnings" if any(item["level"] == "warning" for item in findings) else "pass"),
            "passes": sum(item["level"] == "pass" for item in findings),
            "warnings": sum(item["level"] == "warning" for item in findings),
            "errors": sum(item["level"] == "error" for item in findings),
        },
        "metrics": {
            "source_pages": len(batch_refs),
            "hub_actions": len(hub_actions),
            "topic_actions": len(topic_actions),
        },
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a link-plan.json.")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_path = args.plan.expanduser().resolve()
    if not plan_path.is_file():
        print("ERROR: --plan must point to an existing file.", file=sys.stderr)
        return 2
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = audit(plan)
    print(
        f"Audit status: {report['summary']['status']} "
        f"(passes={report['summary']['passes']}, "
        f"warnings={report['summary']['warnings']}, "
        f"errors={report['summary']['errors']})"
    )
    for item in report["findings"]:
        print(f"{item['level'].upper():7} {item['code']}: {item['message']}")
        if item.get("details"):
            print(f"        {json.dumps(item['details'], ensure_ascii=False)}")

    if args.report:
        output = args.report.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote link plan audit report: {output}")

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
