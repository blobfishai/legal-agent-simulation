"""Deterministic criterion-level scoring for CounselBench-100.

The grader deliberately avoids semantic or model-based judging. Every criterion
is recoverable from the task prompt, seeded record-control metadata, the MCP
trace, and the final two deliverables.
"""

from __future__ import annotations

import re
from typing import Any


FACT_PATTERNS = (
    re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?%", re.IGNORECASE),
    re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE),
    re.compile(r"\bCB-[A-Z0-9-]+\b", re.IGNORECASE),
)


def normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def controlled_fact_tokens(value: Any) -> set[str]:
    text = value if isinstance(value, str) else ""
    return {
        match.group(0).casefold()
        for pattern in FACT_PATTERNS
        for match in pattern.finditer(text)
    }


def mean(values: dict[str, bool]) -> float:
    if not values:
        return 1.0
    return sum(bool(value) for value in values.values()) / len(values)


def score_findings(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    expected = spec["expected_findings"]
    expected_rows = spec["scoring_findings"]
    actual = value if isinstance(value, dict) else {}
    rows = actual.get("findings") if isinstance(actual.get("findings"), list) else []
    row_ids = [row.get("id") for row in rows if isinstance(row, dict)]
    rows_by_id = {
        str(row.get("id")): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }

    criteria: dict[str, bool] = {
        "findings_is_object": isinstance(value, dict),
        "findings_exact_count": len(rows) == len(expected_rows),
        "finding_ids_unique": len(row_ids) == len(set(row_ids)) == len(expected_rows),
    }
    for key in ("schema_version", "task_id", "matter_number", "prepared_for", "as_of"):
        criteria[f"top_level_{key}"] = actual.get(key) == expected.get(key)

    details: list[dict[str, Any]] = []
    exact_fields = (
        "id", "issue", "severity", "primary_source", "corroborating_source",
    )
    for expected_row in expected_rows:
        finding_id = expected_row["id"]
        actual_row = rows_by_id.get(finding_id)
        present = isinstance(actual_row, dict)
        checks: dict[str, bool] = {"present": present}
        criteria[f"{finding_id}.present"] = present
        for field in exact_fields:
            passed = present and actual_row.get(field) == expected_row[field]
            checks[field] = bool(passed)
            criteria[f"{finding_id}.{field}"] = bool(passed)

        determination = actual_row.get("determination") if present else ""
        normalized_determination = normalize(determination)
        missing_fact_anchors = [
            anchor
            for anchor in expected_row["fact_anchors"]
            if normalize(anchor) not in normalized_determination
        ]
        facts_grounded = not missing_fact_anchors
        observed_tokens = controlled_fact_tokens(determination)
        allowed_tokens = controlled_fact_tokens(expected_row["allowed_fact_text"])
        unsupported_tokens = sorted(observed_tokens - allowed_tokens)
        facts_source_bounded = not unsupported_tokens
        checks["fact_anchors"] = facts_grounded
        checks["facts_source_bounded"] = facts_source_bounded
        criteria[f"{finding_id}.fact_anchors"] = facts_grounded
        criteria[f"{finding_id}.facts_source_bounded"] = facts_source_bounded

        action = actual_row.get("recommended_action") if present else ""
        normalized_action = normalize(action)
        missing_action_anchors = [
            anchor
            for anchor in expected_row["action_anchors"]
            if normalize(anchor) not in normalized_action
        ]
        action_grounded = not missing_action_anchors
        checks["action_anchors"] = action_grounded
        criteria[f"{finding_id}.action_anchors"] = action_grounded
        details.append(
            {
                "id": finding_id,
                "checks": checks,
                "missing_fact_anchors": missing_fact_anchors,
                "unsupported_fact_tokens": unsupported_tokens,
                "missing_action_anchors": missing_action_anchors,
            }
        )

    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
    }


def score_memo(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    memo = value if isinstance(value, str) else ""
    normalized = normalize(memo)
    criteria: dict[str, bool] = {}
    for section in spec["memo_sections"]:
        criteria[f"section.{section}"] = normalize(section) in normalized

    details: list[dict[str, Any]] = []
    for finding in spec["scoring_findings"]:
        anchors = [
            finding["id"],
            finding["issue"],
            finding["severity"],
            finding["primary_source"],
            finding["corroborating_source"],
            *finding["fact_anchors"],
            *finding["action_anchors"],
        ]
        missing = [anchor for anchor in anchors if normalize(anchor) not in normalized]
        criterion = f"finding.{finding['id']}"
        criteria[criterion] = not missing
        details.append({"id": finding["id"], "missing_anchors": missing})

    forbidden_present = [
        claim for claim in spec["forbidden_claims"] if normalize(claim) in normalized
    ]
    criteria["forbidden_claims_absent"] = not forbidden_present
    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
        "forbidden_claims_present": forbidden_present,
    }


def aggregate_scores(
    procedure: dict[str, bool],
    findings: dict[str, Any],
    memo: dict[str, Any],
) -> dict[str, Any]:
    category_scores = {
        "procedure": round(mean(procedure), 6),
        "findings": findings["score"],
        "memo": memo["score"],
    }
    uncapped = (
        category_scores["procedure"] * 0.25
        + category_scores["findings"] * 0.55
        + category_scores["memo"] * 0.20
    )
    reward = uncapped
    cap_reason = None
    if not procedure.get("exact_deliverable_set") or not procedure.get(
        "deliverables_written_through_mcp"
    ):
        reward = min(reward, 0.20)
        cap_reason = "deliverables_missing_or_not_written_through_mcp"
    elif not all(procedure.values()):
        reward = min(reward, 0.49)
        cap_reason = "required_review_procedure_incomplete"
    passed = all(procedure.values()) and findings["passed"] and memo["passed"]
    return {
        "passed": passed,
        "reward": round(reward, 6),
        "uncapped_reward": round(uncapped, 6),
        "cap_reason": cap_reason,
        "category_scores": category_scores,
        "weights": {"procedure": 0.25, "findings": 0.55, "memo": 0.20},
    }
