#!/usr/bin/env python3
"""Validate a processor paper-digest.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_KINDS = {"concept", "entity"}
ALLOWED_TIERS = {"L0", "L1", "L2"}
ALLOWED_GATES = {1, 2, 3, 4, 5}
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
MAX_DIGEST_BYTES = 8000


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


def audit_candidate(
    candidate: dict[str, Any],
    current_source_ref: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    label = f"candidate {candidate.get('id') or candidate.get('name') or '<unnamed>'}"

    kind = require_string(candidate, "kind", findings, label)
    tier = require_string(candidate, "tier", findings, label)
    definition = require_string(candidate, "definition", findings, label)
    require_string(candidate, "id", findings, label)
    require_string(candidate, "name", findings, label)

    if kind and kind not in ALLOWED_KINDS:
        findings.append(finding("error", "kind", f"{label} has invalid kind.", kind=kind))
    if tier and tier not in ALLOWED_TIERS:
        findings.append(finding("error", "tier", f"{label} has invalid tier.", tier=tier))

    source_refs = require_list(candidate, "source_refs", findings, label)
    valid_refs = [ref for ref in source_refs if isinstance(ref, str) and ref.strip()]
    if current_source_ref and current_source_ref not in valid_refs:
        findings.append(
            finding(
                "error",
                "current_source_missing",
                f"{label} must include the current source page.",
                source_ref=current_source_ref,
                source_refs=valid_refs,
            )
        )

    passed_gates = candidate.get("passed_gates", [])
    if not isinstance(passed_gates, list) or len(passed_gates) < 3:
        findings.append(
            finding(
                "error",
                "gates",
                f"{label} must pass at least three gates.",
                found=passed_gates,
            )
        )
    else:
        invalid_gates = sorted(set(passed_gates) - ALLOWED_GATES)
        if invalid_gates:
            findings.append(
                finding(
                    "error",
                    "gate_values",
                    f"{label} contains invalid gate numbers.",
                    invalid=invalid_gates,
                )
            )

    evidence = candidate.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        findings.append(finding("error", "evidence", f"{label} must have at least one evidence row."))
    else:
        for index, row in enumerate(evidence, start=1):
            if not isinstance(row, dict):
                findings.append(finding("error", "evidence_row", f"{label} evidence row {index} must be an object."))
                continue
            if not require_string(row, "pointer", findings, f"{label} evidence row {index}"):
                pass
            elif not audit_pointer(row["pointer"]):
                findings.append(
                    finding(
                        "error",
                        "evidence_pointer",
                        f"{label} evidence row {index} has an invalid pointer.",
                        pointer=row.get("pointer"),
                    )
                )
            require_string(row, "claim", findings, f"{label} evidence row {index}")

    relations = require_list(candidate, "relations", findings, label)
    for index, relation in enumerate(relations, start=1):
        if not isinstance(relation, dict):
            findings.append(finding("error", "relation_row", f"{label} relation {index} must be an object."))
            continue
        relation_type = relation.get("type")
        if relation_type not in ALLOWED_RELATION_TYPES:
            findings.append(
                finding("error", "relation_type", f"{label} relation {index} has invalid type.", type=relation_type)
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


def audit_topic_seed(topic: dict[str, Any], current_source_ref: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    label = f"topic seed {topic.get('id') or topic.get('name') or '<unnamed>'}"
    require_string(topic, "id", findings, label)
    require_string(topic, "name", findings, label)
    require_string(topic, "summary", findings, label)
    papers = require_list(topic, "papers", findings, label)
    if not any(isinstance(item, str) and item.strip() for item in papers):
        findings.append(finding("error", "topic_papers", f"{label} must list at least one source page."))
    elif current_source_ref and current_source_ref not in papers:
        findings.append(
            finding(
                "error",
                "current_source_missing",
                f"{label} must include the current source page.",
                source_ref=current_source_ref,
                papers=papers,
            )
        )
    return findings


def audit(digest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not isinstance(digest, dict):
        return {
            "schema_version": "1.0",
            "summary": {"status": "fail", "passes": 0, "warnings": 0, "errors": 1},
            "metrics": {},
            "findings": [finding("error", "top_level", "Paper digest must be a JSON object.")],
        }

    if digest.get("schema_version") != "1.0":
        findings.append(finding("error", "schema_version", "Unsupported paper digest schema version."))

    paper = digest.get("paper", {})
    current_source_ref = ""
    if not isinstance(paper, dict):
        findings.append(finding("error", "paper", "Paper digest must define paper."))
    else:
        for field in ("title", "source_sha256", "source_ref", "locator_mode", "paper_type"):
            if not isinstance(paper.get(field), str) or not paper[field].strip():
                findings.append(
                    finding("error", "paper_field", f"Paper digest paper must define {field}.", field=field)
                )
        current_source_ref = paper.get("source_ref", "").strip()

    analysis = digest.get("analysis", {})
    if not isinstance(analysis, dict):
        findings.append(finding("error", "analysis", "Paper digest must define analysis."))
    else:
        for field in ("one_sentence_summary", "problem", "method"):
            require_string(analysis, field, findings, "analysis")
        for field in ("datasets", "models", "metrics", "open_questions"):
            require_list(analysis, field, findings, "analysis")

        key_results = require_list(analysis, "key_results", findings, "analysis")
        for index, row in enumerate(key_results, start=1):
            if not isinstance(row, dict):
                findings.append(finding("error", "key_result_row", f"key_results row {index} must be an object."))
                continue
            require_string(row, "claim", findings, f"key_results row {index}")
            if not audit_pointer(row.get("pointer", "")):
                findings.append(
                    finding(
                        "error",
                        "key_result_pointer",
                        f"key_results row {index} must define a valid pointer.",
                        pointer=row.get("pointer"),
                    )
                )
            if row.get("confidence") not in ALLOWED_CONFIDENCE:
                findings.append(
                    finding(
                        "error",
                        "key_result_confidence",
                        f"key_results row {index} has invalid confidence.",
                        confidence=row.get("confidence"),
                    )
                )

        for key, text_field in (("limitations", "statement"), ("critical_observations", "observation")):
            rows = require_list(analysis, key, findings, "analysis")
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    findings.append(finding("error", f"{key}_row", f"{key} row {index} must be an object."))
                    continue
                require_string(row, text_field, findings, f"{key} row {index}")
                if not audit_pointer(row.get("pointer", "")):
                    findings.append(
                        finding(
                            "error",
                            f"{key}_pointer",
                            f"{key} row {index} must define a valid pointer.",
                            pointer=row.get("pointer"),
                        )
                    )

    candidates = require_list(digest, "candidates", findings, "paper digest")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            findings.append(finding("error", "candidate", "Each candidate must be an object."))
            continue
        findings.extend(audit_candidate(candidate, current_source_ref))

    topic_seeds = require_list(digest, "topic_seeds", findings, "paper digest")
    for topic in topic_seeds:
        if not isinstance(topic, dict):
            findings.append(finding("error", "topic_seed", "Each topic seed must be an object."))
            continue
        findings.extend(audit_topic_seed(topic, current_source_ref))

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
            "candidates": len(candidates),
            "topic_seeds": len(topic_seeds),
        },
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a paper-digest.json.")
    parser.add_argument("--digest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    digest_path = args.digest.expanduser().resolve()
    if not digest_path.is_file():
        print("ERROR: --digest must point to an existing file.", file=sys.stderr)
        return 2
    try:
        raw = digest_path.read_text(encoding="utf-8")
        digest = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = audit(digest)
    if len(raw.encode("utf-8")) > MAX_DIGEST_BYTES:
        report["findings"].append(
            finding(
                "warning",
                "digest_size",
                f"Paper digest exceeds the recommended {MAX_DIGEST_BYTES} bytes.",
                bytes=len(raw.encode("utf-8")),
            )
        )
        report["summary"]["warnings"] += 1
        report["summary"]["status"] = "pass_with_warnings" if report["summary"]["errors"] == 0 else "fail"

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
        print(f"Wrote digest audit report: {output}")

    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
