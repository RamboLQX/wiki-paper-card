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
ALLOWED_SCHEMA_VERSIONS = {"2.0", "3.0"}
ITEM_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HISTORY_TERMS = ("本批", "本次新增", "追加证据")


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


def audit_topic_action_v2(
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
            else:
                significance = item.get("significance", "")
                if not isinstance(significance, str) or not significance.strip():
                    findings.append(
                        finding(
                            "error",
                            "research_gap_significance",
                            f"{gap_label} is open but lacks significance; state "
                            "which judgment or choice the gap would change (see "
                            "skills/wiki-shared/references/writing-guide.md).",
                        )
                    )
                evidence_boundary = item.get("evidence_boundary", "")
                if not isinstance(evidence_boundary, str) or not evidence_boundary.strip():
                    findings.append(
                        finding(
                            "warning",
                            "research_gap_evidence_boundary",
                            f"{gap_label} lacks evidence_boundary and will render "
                            "as a tentative direction with the [待验证] tag.",
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


def audit_v3_item_id(
    item: dict[str, Any],
    label: str,
    seen_ids: set[str],
    findings: list[dict[str, Any]],
) -> str:
    item_id = require_string(item, "id", findings, label)
    if item_id and not ITEM_ID_RE.fullmatch(item_id):
        findings.append(
            finding(
                "error",
                "item_id_format",
                f"{label} id must be a lowercase kebab-case identifier.",
                id=item_id,
            )
        )
    if item_id in seen_ids:
        findings.append(
            finding(
                "error",
                "duplicate_item_id",
                f"{label} duplicates item id {item_id}.",
                id=item_id,
            )
        )
    elif item_id:
        seen_ids.add(item_id)
    return item_id


def audit_v3_paragraph(
    paragraph: Any,
    label: str,
    finding_ids: set[str],
    contradiction_ids: set[str],
    findings: list[dict[str, Any]],
) -> None:
    if not isinstance(paragraph, dict):
        findings.append(
            finding("error", "narrative_paragraph", f"{label} must be an object.")
        )
        return
    text = require_string(paragraph, "text", findings, label)
    if text and re.search(r"(?m)^\s*[-*+]\s+", text):
        findings.append(
            finding(
                "error",
                "narrative_bullet",
                f"{label} must be prose, not a Markdown bullet list.",
            )
        )
    for term in HISTORY_TERMS:
        if term in text:
            findings.append(
                finding(
                    "error",
                    "narrative_history",
                    f"{label} contains processing-history language.",
                    term=term,
                )
            )
    refs = require_nonempty_string_list(
        paragraph,
        "finding_refs",
        findings,
        label,
        "narrative_finding_refs",
    )
    if len(refs) != len(set(refs)):
        findings.append(
            finding(
                "error",
                "duplicate_narrative_ref",
                f"{label} repeats a finding reference.",
            )
        )
    unknown = sorted(set(refs) - finding_ids)
    if unknown:
        findings.append(
            finding(
                "error",
                "unknown_finding_ref",
                f"{label} references unknown finding ids.",
                ids=unknown,
            )
        )
    contradiction_refs = paragraph.get("contradiction_refs", [])
    if not isinstance(contradiction_refs, list) or not all(
        isinstance(ref, str) and ref.strip() for ref in contradiction_refs
    ):
        findings.append(
            finding(
                "error",
                "narrative_contradiction_refs",
                f"{label} contradiction_refs must be a list of non-empty strings.",
            )
        )
    else:
        unknown_contradictions = sorted(set(contradiction_refs) - contradiction_ids)
        if unknown_contradictions:
            findings.append(
                finding(
                    "error",
                    "unknown_contradiction_ref",
                    f"{label} references unknown contradiction ids.",
                    ids=unknown_contradictions,
                )
            )


def audit_v3_narrative(
    narrative: Any,
    finding_ids: set[str],
    contradiction_ids: set[str],
    findings: list[dict[str, Any]],
    label: str,
    source_count: int,
) -> None:
    if not isinstance(narrative, dict):
        findings.append(
            finding("error", "narrative_shape", f"{label} narrative must be an object.")
        )
        return
    overview = narrative.get("overview")
    if not isinstance(overview, dict):
        findings.append(
            finding("error", "narrative_overview", f"{label} narrative.overview must be an object.")
        )
    else:
        paragraphs = overview.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            findings.append(
                finding(
                    "error",
                    "narrative_overview",
                    f"{label} narrative.overview.paragraphs must be a non-empty list.",
                )
            )
        else:
            if not 2 <= len(paragraphs) <= 3:
                findings.append(
                    finding(
                        "error",
                        "narrative_overview_depth",
                        f"{label} overview must contain two or three complete paragraphs.",
                        paragraphs=len(paragraphs),
                    )
                )
            for index, paragraph in enumerate(paragraphs, start=1):
                audit_v3_paragraph(
                    paragraph,
                    f"{label} overview paragraph {index}",
                    finding_ids,
                    contradiction_ids,
                    findings,
                )

    for field, require_nonempty in (("synthesis_blocks", True), ("controversy_blocks", False)):
        blocks = narrative.get(field)
        if not isinstance(blocks, list) or (require_nonempty and not blocks):
            qualifier = "a non-empty list" if require_nonempty else "a list"
            findings.append(
                finding(
                    "error",
                    "narrative_blocks",
                    f"{label} narrative.{field} must be {qualifier}.",
                )
            )
            continue
        if field == "synthesis_blocks":
            minimum = 3 if source_count >= 4 else 1
            if not minimum <= len(blocks) <= 5:
                findings.append(
                    finding(
                        "error",
                        "narrative_synthesis_depth",
                        f"{label} synthesis depth does not match the current evidence base.",
                        sources=source_count,
                        minimum_blocks=minimum,
                        maximum_blocks=5,
                        found_blocks=len(blocks),
                    )
                )
        seen_block_ids: set[str] = set()
        for block_index, block in enumerate(blocks, start=1):
            block_label = f"{label} {field} block {block_index}"
            if not isinstance(block, dict):
                findings.append(
                    finding("error", "narrative_block", f"{block_label} must be an object.")
                )
                continue
            block_id = require_string(block, "id", findings, block_label)
            if block_id in seen_block_ids:
                findings.append(
                    finding(
                        "error",
                        "duplicate_narrative_block_id",
                        f"{block_label} duplicates block id {block_id}.",
                    )
                )
            elif block_id:
                seen_block_ids.add(block_id)
            require_string(block, "heading", findings, block_label)
            paragraphs = block.get("paragraphs")
            if not isinstance(paragraphs, list) or not paragraphs:
                findings.append(
                    finding(
                        "error",
                        "narrative_block_paragraphs",
                        f"{block_label} paragraphs must be a non-empty list.",
                    )
                )
                continue
            if len(paragraphs) < 2:
                findings.append(
                    finding(
                        "error",
                        "narrative_block_depth",
                        f"{block_label} must separate the main relationship from its boundary and implication.",
                        paragraphs=len(paragraphs),
                    )
                )
            for paragraph_index, paragraph in enumerate(paragraphs, start=1):
                audit_v3_paragraph(
                    paragraph,
                    f"{block_label} paragraph {paragraph_index}",
                    finding_ids,
                    contradiction_ids,
                    findings,
                )


def audit_topic_action_v3(
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
    if action_type not in ALLOWED_TOPIC_ACTIONS:
        findings.append(
            finding("error", "topic_action", f"{label} has invalid action.", action=action_type)
        )
    if name and name in target_names:
        findings.append(
            finding("error", "duplicate_target", f"{label} duplicates target page {name}.", name=name)
        )
    elif name:
        target_names.add(name)
    if purpose == "refresh" and action_type != "update_topic":
        findings.append(
            finding(
                "error",
                "refresh_action",
                f"{label} refresh plans may only update an existing Topic.",
                action=action_type,
            )
        )

    papers = set(
        require_nonempty_string_list(
            action, "papers", findings, label, "topic_papers"
        )
    )
    if action_type == "create_topic" and len(papers) < 2:
        findings.append(
            finding(
                "error",
                "topic_papers",
                "create_topic requires at least two source page references.",
                papers=sorted(papers),
            )
        )
    if purpose == "ingest" and papers and not (papers & batch_refs):
        findings.append(
            finding(
                "error",
                "missing_batch_topic_paper",
                f"{label} must reference at least one current-batch source page.",
            )
        )
    if action_type == "update_topic":
        require_string(action, "existing_page", findings, label)
        base_hash = require_string(action, "base_topic_sha256", findings, label)
        if base_hash and not SHA256_RE.fullmatch(base_hash):
            findings.append(
                finding(
                    "error",
                    "base_topic_sha256",
                    f"{label} base_topic_sha256 must be 64 lowercase hexadecimal characters.",
                )
            )
    elif "base_topic_sha256" in action:
        findings.append(
            finding(
                "error",
                "base_topic_sha256",
                f"{label} create_topic must not define base_topic_sha256.",
            )
        )

    if "summary" in action:
        findings.append(
            finding(
                "error",
                "legacy_summary",
                f"{label} schema 3.0 uses index_summary instead of summary.",
            )
        )

    mining_forbidden = (
        "narrative",
        "comparisons",
        "key_findings",
        "contradictions",
        "page_status",
    )
    if purpose == "mining":
        for field in mining_forbidden:
            if field in action:
                findings.append(
                    finding(
                        "error",
                        "mining_field_forbidden",
                        f"{label} mining action must not define {field}.",
                        field=field,
                    )
                )
        if action_type == "update_topic" and "index_summary" in action:
            findings.append(
                finding(
                    "error",
                    "mining_field_forbidden",
                    f"{label} mining update must not define index_summary.",
                    field="index_summary",
                )
            )
        if "category" in action:
            findings.append(
                finding(
                    "error",
                    "mining_field_forbidden",
                    f"{label} mining action must not change category.",
                    field="category",
                )
            )
        if action_type == "create_topic":
            require_string(action, "index_summary", findings, label)
    else:
        require_string(action, "index_summary", findings, label)

    if purpose == "refresh":
        for field in (
            "open_questions",
            "research_gaps",
            "remove_open_question_ids",
            "remove_research_gap_ids",
            "annotate_research_gaps",
            "category",
            "page_status",
        ):
            if field in action:
                findings.append(
                    finding(
                        "error",
                        "refresh_field_forbidden",
                        f"{label} refresh action must not define {field}.",
                        field=field,
                    )
                )

    page_status = action.get("page_status")
    if page_status is not None and page_status not in {"stub", "draft", "evergreen"}:
        findings.append(
            finding(
                "error",
                "page_status",
                f"{label} page_status must be stub, draft, or evergreen.",
                status=page_status,
            )
        )

    finding_ids: set[str] = set()
    contradiction_ids: set[str] = set()
    if purpose in {"ingest", "refresh"}:
        comparisons = require_list(action, "comparisons", findings, label)
        comparison_refs: set[str] = set()
        for index, item in enumerate(comparisons, start=1):
            item_label = f"{label} comparison {index}"
            if not isinstance(item, dict):
                findings.append(
                    finding("error", "comparison_shape", f"{item_label} must be an object.")
                )
                continue
            if "dimension" in item:
                continue
            source_ref = require_string(item, "source_ref", findings, item_label)
            if source_ref in comparison_refs:
                findings.append(
                    finding(
                        "error",
                        "duplicate_comparison_source",
                        f"{item_label} duplicates flat comparison source_ref {source_ref}.",
                        source_ref=source_ref,
                    )
                )
            elif source_ref:
                comparison_refs.add(source_ref)
            if source_ref and source_ref not in papers:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{item_label} references a source not listed in topic papers.",
                        source_refs=[source_ref],
                    )
                )
        key_findings = require_list(action, "key_findings", findings, label)
        for index, item in enumerate(key_findings, start=1):
            item_label = f"{label} key_finding {index}"
            if not isinstance(item, dict):
                findings.append(
                    finding("error", "key_finding_shape", f"{item_label} must be an object.")
                )
                continue
            item_id = audit_v3_item_id(item, item_label, finding_ids, findings)
            require_string(item, "claim", findings, item_label)
            kind = require_string(item, "kind", findings, item_label)
            if kind and kind not in {"consensus", "single", "conflict"}:
                findings.append(
                    finding("error", "key_finding_kind", f"{item_label} has unknown kind.", kind=kind)
                )
            refs = require_nonempty_string_list(
                item, "source_refs", findings, item_label, "key_finding_source_refs"
            )
            unknown_refs = sorted(set(refs) - papers)
            if unknown_refs:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{item_label} references sources not listed in topic papers.",
                        source_refs=unknown_refs,
                    )
                )
            if kind == "consensus" and len(set(refs)) < 2:
                findings.append(
                    finding(
                        "error",
                        "consensus_sources",
                        f"{item_label} consensus requires at least two independent source_refs.",
                        id=item_id,
                    )
                )
            pointers = require_list(item, "pointers", findings, item_label)
            if not pointers:
                findings.append(
                    finding("error", "key_finding_pointers", f"{item_label} requires at least one pointer.")
                )
            for pointer_index, pointer in enumerate(pointers, start=1):
                pointer_label = f"{item_label} pointer {pointer_index}"
                if not isinstance(pointer, dict):
                    findings.append(
                        finding("error", "key_finding_pointer", f"{pointer_label} must be an object.")
                    )
                    continue
                source_ref = require_string(pointer, "source_ref", findings, pointer_label)
                require_string(pointer, "pointer", findings, pointer_label)
                if source_ref and source_ref not in refs:
                    findings.append(
                        finding(
                            "error",
                            "pointer_source_ref",
                            f"{pointer_label} source_ref is not listed in the finding source_refs.",
                            source_ref=source_ref,
                        )
                    )

        contradictions = require_list(action, "contradictions", findings, label)
        for index, item in enumerate(contradictions, start=1):
            item_label = f"{label} contradiction {index}"
            if not isinstance(item, dict):
                findings.append(
                    finding("error", "contradiction_shape", f"{item_label} must be an object.")
                )
                continue
            audit_v3_item_id(item, item_label, contradiction_ids, findings)
            for field in (
                "position_a",
                "position_a_source_ref",
                "position_a_pointer",
                "position_b",
                "position_b_source_ref",
                "position_b_pointer",
                "resolving_evidence",
            ):
                require_string(item, field, findings, item_label)
            contradiction_refs = {
                str(item.get("position_a_source_ref", "")).strip(),
                str(item.get("position_b_source_ref", "")).strip(),
            } - {""}
            unknown_refs = sorted(contradiction_refs - papers)
            if unknown_refs:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{item_label} references sources not listed in topic papers.",
                        source_refs=unknown_refs,
                    )
                )

        audit_v3_narrative(
            action.get("narrative"),
            finding_ids,
            contradiction_ids,
            findings,
            label,
            len(papers),
        )

    seen_item_ids: set[str] = set()
    open_questions = (
        []
        if purpose == "refresh"
        else require_list(action, "open_questions", findings, label)
    )
    for index, item in enumerate(open_questions, start=1):
        item_label = f"{label} open_question {index}"
        if not isinstance(item, dict):
            findings.append(
                finding(
                    "error",
                    "open_question_shape",
                    f"{item_label} must be an object in schema 3.0.",
                )
            )
            continue
        audit_v3_item_id(item, item_label, seen_item_ids, findings)
        require_string(item, "question", findings, item_label)
        origin = require_string(item, "origin", findings, item_label)
        if origin and origin not in {"ingest", "mining"}:
            findings.append(
                finding("error", "item_origin", f"{item_label} has invalid origin.", origin=origin)
            )
        question_refs = require_nonempty_string_list(
            item, "source_refs", findings, item_label, "open_question_source_refs"
        )
        unknown_refs = sorted(set(question_refs) - papers)
        if unknown_refs:
            findings.append(
                finding(
                    "error",
                    "item_source_outside_topic",
                    f"{item_label} references sources not listed in topic papers.",
                    source_refs=unknown_refs,
                )
            )
        status = item.get("status", "open")
        if status not in {"open", "answered"}:
            findings.append(
                finding("error", "open_question_status", f"{item_label} has unknown status.", status=status)
            )
        elif status == "answered":
            answer_refs = require_nonempty_string_list(
                item, "answered_by", findings, item_label, "open_question_answer_source"
            )
            unknown_refs = sorted(set(answer_refs) - papers)
            if unknown_refs:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{item_label} answered_by references sources not listed in topic papers.",
                        source_refs=unknown_refs,
                    )
                )
            require_string(item, "answered_pointer", findings, item_label)

    research_gaps = (
        []
        if purpose == "refresh"
        else require_list(action, "research_gaps", findings, label)
    )
    for index, item in enumerate(research_gaps, start=1):
        item_label = f"{label} research_gap {index}"
        if not isinstance(item, dict):
            findings.append(
                finding(
                    "error",
                    "research_gap_shape",
                    f"{item_label} must be an object in schema 3.0.",
                )
            )
            continue
        audit_v3_item_id(item, item_label, seen_item_ids, findings)
        gap_heading = require_string(item, "gap", findings, item_label)
        origin = require_string(item, "origin", findings, item_label)
        if origin and origin not in {"ingest", "mining"}:
            findings.append(
                finding("error", "item_origin", f"{item_label} has invalid origin.", origin=origin)
            )
        gap_refs = require_nonempty_string_list(
            item, "source_refs", findings, item_label, "research_gap_source_refs"
        )
        unknown_refs = sorted(set(gap_refs) - papers)
        if unknown_refs:
            findings.append(
                finding(
                    "error",
                    "item_source_outside_topic",
                    f"{item_label} references sources not listed in topic papers.",
                    source_refs=unknown_refs,
                )
            )
        require_string(item, "direction", findings, item_label)
        require_string(item, "continuity", findings, item_label)
        status = item.get("status", "open")
        if status == "open" and re.search(r"[\u3400-\u9fff]", gap_heading):
            readability_issues: list[str] = []
            if gap_heading.startswith(("缺少", "需要", "尚缺", "亟需")):
                readability_issues.append("weak_opening")
            if gap_heading.count("、") >= 2:
                readability_issues.append("dense_enumeration")
            if len(re.sub(r"\s+", "", gap_heading)) > 42:
                readability_issues.append("long_heading")
            if readability_issues:
                findings.append(
                    finding(
                        "warning",
                        "research_gap_heading_readability",
                        f"{item_label} gap should name a research object and one blocked judgment; move variables and study-design details to reader_narrative.",
                        issues=readability_issues,
                    )
                )
        reader_narrative = item.get("reader_narrative")
        if reader_narrative is None:
            if status == "open":
                findings.append(
                    finding(
                        "warning",
                        "research_gap_reader_narrative",
                        f"{item_label} omits reader_narrative; the publisher will use the legacy labelled fallback.",
                    )
                )
        elif not isinstance(reader_narrative, list):
            findings.append(
                finding(
                    "error",
                    "research_gap_reader_narrative",
                    f"{item_label} reader_narrative must be a list of one or two non-empty paragraphs.",
                )
            )
        else:
            if not 1 <= len(reader_narrative) <= 2:
                findings.append(
                    finding(
                        "error",
                        "research_gap_reader_narrative",
                        f"{item_label} reader_narrative must contain one or two paragraphs.",
                    )
                )
            for paragraph in reader_narrative:
                if not isinstance(paragraph, str) or not paragraph.strip():
                    findings.append(
                        finding(
                            "error",
                            "research_gap_reader_narrative",
                            f"{item_label} reader_narrative paragraphs must be non-empty strings.",
                        )
                    )
                    continue
                if re.search(r"(?m)^\s*[-*+]\s+", paragraph):
                    findings.append(
                        finding(
                            "error",
                            "research_gap_reader_narrative",
                            f"{item_label} reader_narrative must be prose, not a Markdown bullet list.",
                        )
                    )
                for term in HISTORY_TERMS:
                    if term in paragraph:
                        findings.append(
                            finding(
                                "error",
                                "research_gap_reader_narrative",
                                f"{item_label} reader_narrative contains processing-history language.",
                                term=term,
                            )
                        )
        progress_updates = item.get("progress_updates", [])
        if not isinstance(progress_updates, list):
            findings.append(
                finding(
                    "error",
                    "research_gap_progress_updates",
                    f"{item_label} progress_updates must be a list.",
                )
            )
            progress_updates = []
        seen_progress_ids: set[str] = set()
        for progress_index, progress in enumerate(progress_updates, start=1):
            progress_label = f"{item_label} progress_update {progress_index}"
            if not isinstance(progress, dict):
                findings.append(
                    finding(
                        "error",
                        "research_gap_progress_shape",
                        f"{progress_label} must be an object.",
                    )
                )
                continue
            progress_id = require_string(progress, "id", findings, progress_label)
            if progress_id:
                if not ITEM_ID_RE.fullmatch(progress_id):
                    findings.append(
                        finding(
                            "error",
                            "progress_id",
                            f"{progress_label} has an invalid stable progress id.",
                            id=progress_id,
                        )
                    )
                elif progress_id in seen_progress_ids:
                    findings.append(
                        finding(
                            "error",
                            "duplicate_progress_id",
                            f"{item_label} reuses progress id {progress_id}.",
                            id=progress_id,
                        )
                    )
                else:
                    seen_progress_ids.add(progress_id)
            progress_refs = require_nonempty_string_list(
                progress,
                "source_refs",
                findings,
                progress_label,
                "research_gap_progress_source_refs",
            )
            unknown_progress_refs = sorted(set(progress_refs) - papers)
            if unknown_progress_refs:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{progress_label} references sources not listed in topic papers.",
                        source_refs=unknown_progress_refs,
                    )
                )
            for progress_field in (
                "method",
                "result",
                "pointer",
                "remaining_boundary",
            ):
                require_string(progress, progress_field, findings, progress_label)
        if status not in {"open", "answered"}:
            findings.append(
                finding("error", "research_gap_status", f"{item_label} has unknown status.", status=status)
            )
        elif status == "answered":
            answer_refs = require_nonempty_string_list(
                item, "answered_by", findings, item_label, "research_gap_answer_source"
            )
            unknown_refs = sorted(set(answer_refs) - papers)
            if unknown_refs:
                findings.append(
                    finding(
                        "error",
                        "item_source_outside_topic",
                        f"{item_label} answered_by references sources not listed in topic papers.",
                        source_refs=unknown_refs,
                    )
                )
            require_string(item, "answered_pointer", findings, item_label)
            for resolution_field in (
                "resolution_method",
                "resolution_summary",
                "resolution_scope",
            ):
                require_string(item, resolution_field, findings, item_label)
        else:
            require_string(item, "significance", findings, item_label)
        for field in (
            "evidence_boundary",
            "experiment",
            "success_criterion",
            "risk",
            "priority",
        ):
            if field in item and (not isinstance(item[field], str) or not item[field].strip()):
                findings.append(
                    finding(
                        "warning",
                        f"research_gap_{field}",
                        f"{item_label} {field} is present but empty; omit it or provide text.",
                    )
                )
        priority = item.get("priority", "")
        if purpose == "ingest" and priority:
            findings.append(
                finding(
                    "warning",
                    "ingest_research_gap_priority",
                    f"{item_label} should omit priority during ingest because user and resource context is unavailable.",
                )
            )
        if priority and priority not in {"高", "中", "低"}:
            findings.append(
                finding(
                    "error",
                    "research_gap_priority",
                    f"{item_label} priority must be one of 高/中/低.",
                    priority=priority,
                )
            )

    for field, code in (
        ("remove_open_question_ids", "remove_open_question_ids"),
        ("remove_research_gap_ids", "remove_research_gap_ids"),
    ):
        if field in action:
            values = string_list(action.get(field))
            if not isinstance(action.get(field), list) or len(values) != len(action[field]):
                findings.append(
                    finding("error", code, f"{label} {field} must be a list of non-empty strings.")
                )
            invalid_ids = sorted(value for value in values if not ITEM_ID_RE.fullmatch(value))
            if invalid_ids:
                findings.append(
                    finding(
                        "error",
                        "item_id",
                        f"{label} {field} contains invalid stable item ids.",
                        ids=invalid_ids,
                    )
                )
            overlap = sorted(set(values) & seen_item_ids)
            if overlap:
                findings.append(
                    finding(
                        "error",
                        "item_remove_update_conflict",
                        f"{label} cannot remove and update the same item id.",
                        ids=overlap,
                    )
                )

    if "remove_open_questions" in action or "remove_research_gaps" in action:
        findings.append(
            finding(
                "error",
                "legacy_text_mutation",
                f"{label} schema 3.0 must mutate open items by id, not text fragments.",
            )
        )
    annotations = action.get("annotate_research_gaps")
    if annotations is not None:
        if not isinstance(annotations, list):
            findings.append(
                finding("error", "annotate_research_gaps", f"{label} annotate_research_gaps must be a list.")
            )
        else:
            for index, annotation in enumerate(annotations, start=1):
                if not isinstance(annotation, dict):
                    findings.append(
                        finding(
                            "error",
                            "annotate_research_gap_shape",
                            f"{label} annotation {index} must be an object with id and note.",
                        )
                    )
                    continue
                annotation_id = require_string(
                    annotation, "id", findings, f"{label} annotation {index}"
                )
                if annotation_id and not ITEM_ID_RE.fullmatch(annotation_id):
                    findings.append(
                        finding(
                            "error",
                            "item_id",
                            f"{label} annotation {index} has an invalid stable item id.",
                            id=annotation_id,
                        )
                    )
                require_string(annotation, "note", findings, f"{label} annotation {index}")

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
    schema_version = plan.get("schema_version")
    if schema_version not in ALLOWED_SCHEMA_VERSIONS:
        findings.append(finding("error", "schema_version", "Unsupported link plan schema version."))
        schema_version = "2.0"

    purpose = plan.get("purpose", "ingest")
    if purpose not in {"ingest", "mining", "refresh"}:
        findings.append(
            finding(
                "error",
                "purpose",
                "Link plan purpose must be 'ingest', 'mining', or 'refresh'.",
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
    if purpose == "refresh" and schema_version != "3.0":
        findings.append(
            finding(
                "error",
                "refresh_schema",
                "Refresh plans require schema_version 3.0.",
            )
        )
    if schema_version == "3.0" and purpose in {"mining", "refresh"}:
        if batch_refs:
            findings.append(
                finding(
                    "error",
                    f"{purpose}_batch",
                    f"Schema 3.0 {purpose} plans must keep batch.source_pages empty.",
                )
            )
        label = batch.get("label", "") if isinstance(batch, dict) else ""
        if not isinstance(label, str) or not label.strip():
            findings.append(
                finding(
                    "error",
                    f"{purpose}_batch_label",
                    f"Schema 3.0 {purpose} plans must define a non-empty batch.label.",
                )
            )

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
        if schema_version == "3.0":
            findings.extend(
                audit_topic_action_v3(action, batch_refs, target_names, purpose)
            )
        else:
            findings.extend(
                audit_topic_action_v2(action, batch_refs, target_names, purpose)
            )

    return {
        "schema_version": schema_version,
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
