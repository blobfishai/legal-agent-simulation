"""Deterministic branch-, state-, and answer-level CounselBench scoring."""

from __future__ import annotations

import re
from typing import Any


def normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def mean(values: dict[str, bool]) -> float:
    if not values:
        return 1.0
    return sum(bool(value) for value in values.values()) / len(values)


def _rows_by_key(value: Any, field: str) -> tuple[list[Any], dict[str, dict[str, Any]]]:
    rows = value if isinstance(value, list) else []
    indexed = {
        str(row.get(field)): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get(field), str)
    }
    return rows, indexed


def score_decision(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    expected = spec["expected_decision"]
    actual = value if isinstance(value, dict) else {}
    criteria: dict[str, bool] = {
        "decision_is_object": isinstance(value, dict),
    }
    for field in ("schema_version", "task_id", "matter_number", "prepared_for", "as_of"):
        criteria[f"top_level.{field}"] = actual.get(field) == expected[field]

    actual_choice = actual.get("decision") if isinstance(actual.get("decision"), dict) else {}
    expected_choice = expected["decision"]
    for field in (
        "question", "selected_option_id", "recommendation", "alternatives_considered"
    ):
        criteria[f"choice.{field}"] = actual_choice.get(field) == expected_choice[field]
    criteria["choice.rationale"] = normalize(
        actual_choice.get("rationale")
    ) == normalize(expected_choice["rationale"])

    actual_options, options_by_id = _rows_by_key(
        actual_choice.get("alternatives_evaluated"), "id"
    )
    expected_options = {
        option["id"]: option for option in expected_choice["alternatives_evaluated"]
    }
    criteria["choice.alternatives_evaluated.exact_count"] = (
        len(actual_options) == len(expected_options)
    )
    criteria["choice.alternatives_evaluated.exact_population"] = (
        set(options_by_id) == set(expected_options)
    )
    for option_id, expected_option in expected_options.items():
        actual_option = options_by_id.get(option_id)
        for field, expected_value in expected_option.items():
            criteria[f"choice.alternatives_evaluated.{option_id}.{field}"] = (
                isinstance(actual_option, dict)
                and actual_option.get(field) == expected_value
            )

    for group in ("control_comparison", "authority_application"):
        actual_group = actual_choice.get(group)
        expected_group = expected_choice[group]
        criteria[f"choice.{group}.is_object"] = isinstance(actual_group, dict)
        for field, expected_value in expected_group.items():
            criteria[f"choice.{group}.{field}"] = (
                isinstance(actual_group, dict)
                and actual_group.get(field) == expected_value
            )

    actual_actions, actions_by_key = _rows_by_key(actual.get("actions"), "portfolio_key")
    actual_holds, holds_by_key = _rows_by_key(actual.get("holds"), "portfolio_key")
    criteria["actions.exact_count"] = len(actual_actions) == len(expected["actions"])
    criteria["holds.exact_count"] = len(actual_holds) == len(expected["holds"])
    expected_action_keys = {row["portfolio_key"] for row in expected["actions"]}
    expected_hold_keys = {row["portfolio_key"] for row in expected["holds"]}
    criteria["actions.exact_population"] = set(actions_by_key) == expected_action_keys
    criteria["holds.exact_population"] = set(holds_by_key) == expected_hold_keys
    criteria["populations.disjoint"] = not (set(actions_by_key) & set(holds_by_key))

    details: list[dict[str, Any]] = []
    for expected_row in expected["actions"]:
        key = expected_row["portfolio_key"]
        actual_row = actions_by_key.get(key)
        present = isinstance(actual_row, dict)
        checks: dict[str, bool] = {"present": present}
        criteria[f"{key}.action.present"] = present
        for field in (
            "id", "portfolio_key", "issue", "severity", "identity_id", "owner",
            "due_date", "source_paths",
        ):
            passed = present and actual_row.get(field) == expected_row[field]
            checks[field] = bool(passed)
            criteria[f"{key}.action.{field}"] = bool(passed)
        determination = normalize(actual_row.get("determination") if present else "")
        expected_determination = normalize(expected_row["determination"])
        checks["determination"] = determination == expected_determination
        criteria[f"{key}.action.determination"] = checks["determination"]
        action = normalize(actual_row.get("recommended_action") if present else "")
        expected_action = normalize(expected_row["recommended_action"])
        checks["recommended_action"] = action == expected_action
        criteria[f"{key}.action.recommended_action"] = checks["recommended_action"]
        details.append({"portfolio_key": key, "branch": "action", "checks": checks})

    for expected_row in expected["holds"]:
        key = expected_row["portfolio_key"]
        actual_row = holds_by_key.get(key)
        present = isinstance(actual_row, dict)
        checks = {"present": present}
        criteria[f"{key}.hold.present"] = present
        for field in (
            "id", "portfolio_key", "issue", "reason", "required_next_evidence", "source_paths"
        ):
            passed = present and actual_row.get(field) == expected_row[field]
            checks[field] = bool(passed)
            criteria[f"{key}.hold.{field}"] = bool(passed)
        details.append({"portfolio_key": key, "branch": "evidence_hold", "checks": checks})

    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
    }


def score_register(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    expected = spec["expected_register"]
    actual = value if isinstance(value, dict) else {}
    criteria: dict[str, bool] = {
        "register_is_object": isinstance(value, dict),
    }
    for field in ("schema_version", "task_id", "matter_number"):
        criteria[f"top_level.{field}"] = actual.get(field) == expected[field]
    actual_rows, rows_by_key = _rows_by_key(actual.get("rows"), "portfolio_key")
    expected_by_key = {row["portfolio_key"]: row for row in expected["rows"]}
    criteria["rows.exact_count"] = len(actual_rows) == len(expected["rows"])
    criteria["rows.exact_population"] = set(rows_by_key) == set(expected_by_key)
    details: list[dict[str, Any]] = []
    for key, expected_row in expected_by_key.items():
        actual_row = rows_by_key.get(key)
        present = isinstance(actual_row, dict)
        exact = present and actual_row == expected_row
        criteria[f"{key}.present"] = present
        criteria[f"{key}.exact_state"] = bool(exact)
        details.append(
            {
                "portfolio_key": key,
                "present": present,
                "exact_state": bool(exact),
                "expected_disposition": expected_row["disposition"],
            }
        )
    criteria["register.exact_state"] = actual == expected
    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
    }


def score_advice(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    memo = value if isinstance(value, str) else ""
    normalized = normalize(memo)
    expected = spec["expected_decision"]
    criteria: dict[str, bool] = {}
    for section in (
        "Recommendation", "Control comparison", "Authority application",
        "Why this is the supported option", "Supported actions", "Evidence holds",
        "Alternatives considered", "Assumptions and limits",
    ):
        criteria[f"section.{section}"] = normalize(section) in normalized
    choice = expected["decision"]
    for anchor_name, anchor in (
        ("recommendation", choice["recommendation"]),
        ("selected_option", choice["selected_option_id"]),
        ("action_count", str(len(expected["actions"]))),
        ("hold_count", str(len(expected["holds"]))),
    ):
        criteria[f"summary.{anchor_name}"] = normalize(anchor) in normalized
    details: list[dict[str, Any]] = []
    for row in expected["actions"]:
        anchors = [
            row["portfolio_key"], row["issue"], row["severity"], row["identity_id"],
            row["owner"], row["due_date"], row["determination"],
            row["recommended_action"], *row["source_paths"],
        ]
        missing = [anchor for anchor in anchors if normalize(anchor) not in normalized]
        criteria[f"action.{row['portfolio_key']}"] = not missing
        details.append({"portfolio_key": row["portfolio_key"], "missing_anchors": missing})
    for row in expected["holds"]:
        anchors = [
            row["portfolio_key"], row["issue"], row["reason"],
            row["required_next_evidence"], *row["source_paths"],
        ]
        missing = [anchor for anchor in anchors if normalize(anchor) not in normalized]
        criteria[f"hold.{row['portfolio_key']}"] = not missing
        details.append({"portfolio_key": row["portfolio_key"], "missing_anchors": missing})
    for option_id in choice["alternatives_considered"]:
        criteria[f"alternative.{option_id}"] = normalize(option_id) in normalized
    for option in choice["alternatives_evaluated"]:
        anchors = (
            option["id"],
            option["outcome"],
            f"${option['incrementalCost']:,}",
            option["authorityStatus"],
        )
        criteria[f"alternative_contract.{option['id']}"] = all(
            normalize(anchor) in normalized for anchor in anchors
        )
    control = choice["control_comparison"]
    for field, value in control.items():
        criteria[f"control_comparison.{field}"] = normalize(str(value)) in normalized
    authority = choice["authority_application"]
    for field in (
        "authorityRecord", "selectedOptionId", "selectedAuthorityStatus",
    ):
        criteria[f"authority_application.{field}"] = (
            normalize(str(authority[field])) in normalized
        )
    for field in ("approvalRequiredOptionIds", "unsupportedOptionIds"):
        criteria[f"authority_application.{field}"] = all(
            normalize(str(option_id)) in normalized for option_id in authority[field]
        )
    forbidden = [
        claim for claim in spec["forbidden_claims"] if normalize(claim) in normalized
    ]
    criteria["forbidden_claims_absent"] = not forbidden
    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
        "forbidden_claims_present": forbidden,
    }


def aggregate_scores(
    procedure: dict[str, bool],
    decision: dict[str, Any],
    register: dict[str, Any],
    advice: dict[str, Any],
) -> dict[str, Any]:
    weights = {"investigation": 0.25, "decision": 0.35, "state": 0.25, "advice": 0.15}
    category_scores = {
        "investigation": round(mean(procedure), 6),
        "decision": decision["score"],
        "state": register["score"],
        "advice": advice["score"],
    }
    uncapped = sum(category_scores[key] * weight for key, weight in weights.items())
    reward = uncapped
    cap_reason = None
    if not procedure.get("exact_deliverable_set") or not procedure.get("write_scope_contained"):
        reward = min(reward, 0.20)
        cap_reason = "state_write_missing_or_out_of_scope"
    elif not procedure.get("all_outputs_verified_by_readback"):
        reward = min(reward, 0.35)
        cap_reason = "state_not_verified_by_readback"
    elif not procedure.get("all_required_evidence_precedes_first_write"):
        reward = min(reward, 0.49)
        cap_reason = "required_investigation_incomplete_or_late"
    elif not all(procedure.values()):
        reward = min(reward, 0.59)
        cap_reason = "procedure_incomplete"
    passed = (
        all(procedure.values())
        and decision["passed"]
        and register["passed"]
        and advice["passed"]
    )
    return {
        "passed": passed,
        "reward": round(reward, 6),
        "uncapped_reward": round(uncapped, 6),
        "cap_reason": cap_reason,
        "category_scores": category_scores,
        "weights": weights,
    }
