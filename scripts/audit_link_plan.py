#!/usr/bin/env python3
"""Validate a batch link-plan.json before wiki writes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_TOPIC_ACTIONS = {"create_topic", "update_topic"}


def normalize_page_name(value: str) -> str:
    """Lowercase and strip punctuation/space for identity comparison."""
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(value).lower())


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


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def require_nonempty_string_list(
    item: dict[str, Any],
    field: str,
    findings: list[dict[str, Any]],
    item_label: str,
    code: str,
) -> list[str]:
    value = item.get(field)
    values = string_list(value)
    if not isinstance(value, list) or not values or len(values) != len(value):
        findings.append(
            finding(
                "error",
                code,
                f"{item_label} must define {field} as a non-empty list of strings.",
                field=field,
            )
        )
        return []
    return values


def audit_topic_action(
    action: dict[str, Any],
    batch_refs: set[str],
    target_names: set[str],
    purpose: str,
) -> list[dict[str, Any]]:
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
    if purpose == "ingest" and unknown_refs:
        findings.append(
            finding(
                "error",
                "unknown_topic_papers",
                f"{label} references papers outside the current batch.",
                papers=unknown_refs,
            )
        )
    if action_type == "create_topic" and len(papers) < 2:
        if purpose == "mining":
            message = "create_topic requires at least two source page references."
        else:
            message = "create_topic requires at least two distinct batch source pages."
        findings.append(
            finding(
                "error",
                "topic_papers",
                message,
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
    if not isinstance(research_gaps, list):
        findings.append(finding("error", "research_gaps", f"{label} research_gaps must be a list."))
    else:
        for index, item in enumerate(research_gaps, start=1):
            if isinstance(item, str):
                findings.append(
                    finding(
                        "error",
                        "research_gap_legacy_string",
                        f"{label} research_gap {index} uses the legacy string format; "
                        "new plans must use an object with non-empty gap, source_refs, "
                        "direction, and continuity (see skills/wiki-paper-card/references/link-plan-schema.md).",
                    )
                )
                continue
            if not isinstance(item, dict) or not str(item.get("gap", "")).strip():
                findings.append(
                    finding(
                        "error",
                        "research_gap_shape",
                        f"{label} research_gap {index} must be an object with a non-empty gap "
                        "(plus source_refs, direction, and continuity).",
                    )
                )
                continue
            gap_label = f"{label} research_gap {index}"
            require_nonempty_string_list(
                item,
                "source_refs",
                findings,
                gap_label,
                "research_gap_source_refs",
            )
            if not isinstance(item.get("direction"), str) or not item["direction"].strip():
                findings.append(
                    finding(
                        "error",
                        "research_gap_direction",
                        f"{gap_label} must define direction.",
                    )
                )
            if not isinstance(item.get("continuity"), str) or not item["continuity"].strip():
                findings.append(
                    finding(
                        "error",
                        "research_gap_continuity",
                        f"{gap_label} must define continuity.",
                    )
                )
            for field_name in (
                "significance",
                "evidence_boundary",
                "experiment",
                "success_criterion",
                "risk",
                "priority",
            ):
                if field_name in item and (
                    not isinstance(item.get(field_name), str)
                    or not item[field_name].strip()
                ):
                    findings.append(
                        finding(
                            "warning",
                            f"research_gap_{field_name}",
                            f"{gap_label} {field_name} is present but empty; "
                            "omit it or provide a non-empty value.",
                        )
                    )
            priority = item.get("priority", "")
            if priority and priority not in {"高", "中", "低"}:
                findings.append(
                    finding(
                        "error",
                        "research_gap_priority",
                        f"{gap_label} priority must be one of 高/中/低.",
                        priority=priority,
                    )
                )
            status = item.get("status", "open")
            if status not in {"open", "answered"}:
                findings.append(finding("error", "research_gap_status", f"{label} research_gap {index} has unknown status.", status=status))
            elif status == "answered":
                require_nonempty_string_list(
                    item,
                    "answered_by",
                    findings,
                    gap_label,
                    "research_gap_answer_source",
                )
                if not isinstance(item.get("answered_pointer"), str) or not item["answered_pointer"].strip():
                    findings.append(
                        finding(
                            "error",
                            "research_gap_answer_pointer",
                            f"{gap_label} is answered but lacks answered_pointer.",
                        )
                    )

    open_questions = action.get("open_questions", [])
    if isinstance(open_questions, list):
        for index, item in enumerate(open_questions, start=1):
            if isinstance(item, str):
                continue
            if not isinstance(item, dict) or not str(item.get("question", "")).strip():
                findings.append(finding("error", "open_question_shape", f"{label} open_question {index} must be a string or an object with a non-empty question."))
                continue
            status = item.get("status", "open")
            if status not in {"open", "answered"}:
                findings.append(finding("error", "open_question_status", f"{label} open_question {index} has unknown status.", status=status))
            elif status == "answered":
                question_label = f"{label} open_question {index}"
                require_nonempty_string_list(
                    item,
                    "answered_by",
                    findings,
                    question_label,
                    "open_question_answer_source",
                )
                if not isinstance(item.get("answered_pointer"), str) or not item["answered_pointer"].strip():
                    findings.append(
                        finding(
                            "error",
                            "open_question_answer_pointer",
                            f"{question_label} is answered but lacks answered_pointer.",
                        )
                    )

    remove_open_questions = action.get("remove_open_questions")
    if remove_open_questions is not None and (
        not isinstance(remove_open_questions, list)
        or not all(isinstance(item, str) and item.strip() for item in remove_open_questions)
    ):
        findings.append(
            finding(
                "error",
                "remove_open_questions",
                f"{label} remove_open_questions must be a list of non-empty strings.",
            )
        )

    remove_research_gaps = action.get("remove_research_gaps")
    if remove_research_gaps is not None and (
        not isinstance(remove_research_gaps, list)
        or not all(isinstance(item, str) and item.strip() for item in remove_research_gaps)
    ):
        findings.append(
            finding(
                "error",
                "remove_research_gaps",
                f"{label} remove_research_gaps must be a list of non-empty strings.",
            )
        )

    annotate_research_gaps = action.get("annotate_research_gaps")
    if annotate_research_gaps is not None:
        if not isinstance(annotate_research_gaps, list):
            findings.append(
                finding(
                    "error",
                    "annotate_research_gaps",
                    f"{label} annotate_research_gaps must be a list.",
                )
            )
        else:
            for index, annotation in enumerate(annotate_research_gaps, start=1):
                if not isinstance(annotation, dict) or not str(annotation.get("match", "")).strip() or not str(annotation.get("note", "")).strip():
                    findings.append(
                        finding(
                            "error",
                            "annotate_research_gap_shape",
                            f"{label} annotate_research_gap {index} must be an object "
                            "with non-empty match and note.",
                        )
                    )

    category = action.get("category")
    if category is not None and (
        not isinstance(category, str) or not category.strip()
    ):
        findings.append(
            finding(
                "warning",
                "topic_category",
                f"{label} category is present but empty; omit it or provide "
                "a non-empty value (single category string).",
            )
        )

    return findings


def audit(plan: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not isinstance(plan, dict):
        return {
            "schema_version": "2.0",
            "summary": {"status": "fail", "passes": 0, "warnings": 0, "errors": 1},
            "metrics": {},
            "findings": [finding("error", "top_level", "Link plan must be a JSON object.")],
        }
    if plan.get("schema_version") != "2.0":
        findings.append(finding("error", "schema_version", "Unsupported link plan schema version."))

    purpose = plan.get("purpose", "ingest")
    if purpose not in {"ingest", "mining"}:
        findings.append(
            finding(
                "error",
                "purpose",
                "Link plan purpose must be 'ingest' or 'mining'.",
                purpose=purpose,
            )
        )
        purpose = "ingest"

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
    if purpose == "ingest" and not batch_refs:
        findings.append(finding("error", "batch", "Link plan must define at least one batch source page."))

    if plan.get("hub_actions"):
        findings.append(
            finding(
                "error",
                "hub_actions_removed",
                "Link plan must not carry hub_actions: the hub layer was removed.",
                count=len(plan.get("hub_actions")),
            )
        )

    target_names: set[str] = set()
    topic_actions = require_list(plan, "topic_actions", findings, "link plan")
    for action in topic_actions:
        if not isinstance(action, dict):
            findings.append(finding("error", "topic_action", "Each topic action must be an object."))
            continue
        findings.extend(audit_topic_action(action, batch_refs, target_names, purpose))

    return {
        "schema_version": "2.0",
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
