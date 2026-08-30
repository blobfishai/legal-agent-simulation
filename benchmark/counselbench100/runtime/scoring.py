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


def _anchor_variants(value: Any) -> set[str]:
    """Return conservative textual variants for one source-derived fact."""

    normalized = normalize(str(value))
    variants = {normalized}
    # Employees normally omit cents when an amount is a whole dollar value.
    variants.add(re.sub(r"(\$[0-9,]+)\.00\b", r"\1", normalized))
    # Native records sometimes call out a unit while a concise work product
    # uses the same exact number without repeating the noun.
    variants.add(re.sub(r"\s+records?\b", "", normalized))
    # A matter-scoped native identifier is commonly cited by its terminal
    # record number (for example ``R983`` rather than ``CB-MA-2401-R983``).
    # Keep this deliberately narrow so a generic number cannot satisfy a
    # source-anchor check.
    terminal_record = re.search(r"-([re]\d{2,})$", normalized)
    if terminal_record:
        variants.add(terminal_record.group(1))
    return {variant for variant in variants if variant}


def _contains_anchor(text: str, value: Any) -> bool:
    normalized = normalize(text)
    return any(variant in normalized for variant in _anchor_variants(value))


def _section_headings(text: str) -> list[re.Match[str]]:
    """Find headings that carry a business disposition for following rows."""

    return list(
        re.finditer(
            r"(?mi)^[ \t]*(?:"
            r"#{1,6}[ \t]+[^\n]+|"
            r"(?:SIGNING|CLOSING CONDITIONS?|PRICED EXCEPTIONS?|"
            r"SUPPORTED ACTIONS?|EVIDENCE HOLDS?|OPEN ACTIONS?)\b[^\n]*|"
            r"[A-Z][A-Z0-9 &/:'’()_.-]{3,}"
            r")[ \t]*$",
            text,
        )
    )


def _natural_row_segments(text: str) -> tuple[list[str], dict[str, str]]:
    """Extract human-authored rows without prescribing markdown or JSON."""

    marker = re.compile(
        r"(?mi)^[ \t]*(?:(?:[#>*•-]+|\d+[.)])\s*)*"
        r"(CBP-\d{3}-\d{2})\b"
    )
    matches = list(marker.finditer(text))
    headings = _section_headings(text)
    rows: list[str] = []
    by_key: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        next_row = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        next_heading = next(
            (heading.start() for heading in headings if heading.start() > match.start()),
            len(text),
        )
        end = min(next_row, next_heading)
        prior_heading = next(
            (heading for heading in reversed(headings) if heading.start() < match.start()),
            None,
        )
        heading_text = prior_heading.group(0).strip() if prior_heading else ""
        body = text[match.start():end].strip()
        segment = f"{heading_text}\n{body}".strip()
        key = match.group(1)
        rows.append(key)
        by_key.setdefault(key, []).append(segment)
    return rows, {key: "\n".join(values) for key, values in by_key.items()}


def _topic_matches(text: str, topic: Any) -> bool:
    """Recognize a legal/business topic without prescribing one exact label."""

    normalized_text = re.sub(r"[-_/]+", " ", normalize(text))
    normalized_topic = re.sub(r"[-_/]+", " ", normalize(str(topic)))
    if normalized_topic and normalized_topic in normalized_text:
        return True
    generic = {
        "and", "for", "from", "issue", "matter", "review", "status", "the",
        "under", "with", "exposure", "requirement", "requirements",
    }
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", normalized_topic)
        if len(word) >= 3 and word not in generic
    ]
    overlap = sum(re.search(rf"\b{re.escape(word)}\b", normalized_text) is not None for word in words)
    if words and overlap >= min(2, len(words)):
        return True
    acronym = "".join(word[0] for word in words)
    return len(acronym) >= 2 and re.search(
        rf"\b{re.escape(acronym)}\b", normalized_text
    ) is not None


def _missing_control_matches(
    segment: str,
    row: dict[str, Any],
    fact_matches: int,
) -> bool:
    """Check that a hold identifies its actual failed control."""

    for field in ("hold_reason", "required_next_evidence"):
        if row.get(field) and _contains_anchor(segment, row[field]):
            return True
    normalized = normalize(segment)
    failure_mode = row.get("failure_mode")
    if failure_mode == "identity_ambiguous":
        return (
            _contains_anchor(segment, row.get("entity_id"))
            and _contains_anchor(segment, row.get("alternate_id"))
            and any(word in normalized for word in ("ambiguous", "collision", "crosswalk", "identity"))
        )
    if failure_mode == "trigger_not_met":
        return fact_matches >= 2 and any(
            phrase in normalized
            for phrase in ("below", "does not meet", "has not met", "not met", "no trigger")
        )
    if failure_mode == "authority_pending":
        owner_or_capacity = (
            _contains_anchor(segment, row.get("control_owner"))
            or _contains_anchor(segment, row.get("remaining_capacity"))
        )
        return owner_or_capacity and any(
            phrase in normalized
            for phrase in ("inactive", "no capacity", "pending", "not approved", "approval required", "zero capacity")
        )
    if failure_mode == "revision_stale":
        return (
            _contains_anchor(segment, row.get("referenced_revision"))
            and _contains_anchor(segment, row.get("current_revision"))
            and any(word in normalized for word in ("stale", "superseded", "current", "effective revision"))
        )
    return False


def _semantic_row_criteria(
    text: str,
    spec: dict[str, Any],
    *,
    strict_population: bool,
) -> tuple[dict[str, bool], list[dict[str, Any]]]:
    """Grade distinct business rows independent of their serialization."""

    row_markers, segments = _natural_row_segments(text)
    expected_rows = spec.get("semantic_state_contract") or []
    expected_keys = {row["portfolio_key"] for row in expected_rows}
    actual_keys = set(segments)
    criteria: dict[str, bool] = {
        "rows.population": actual_keys == expected_keys,
        "rows.no_duplicates": (
            len(row_markers) == len(set(row_markers))
            if strict_population
            else True
        ),
        "rows.exact_count": (
            len(row_markers) == len(expected_rows)
            if strict_population
            else expected_keys <= actual_keys
        ),
    }
    details: list[dict[str, Any]] = []
    for row in expected_rows:
        key = row["portfolio_key"]
        segment = segments.get(key, "")
        normalized = normalize(segment)
        present = bool(segment)
        action_markers = (
            "closing condition",
            "open action",
            "supported action",
            "action:",
            "priced exception",
            "signing",
            "cure",
            "proceed",
            "authorized",
        )
        hold_markers = ("evidence hold", "on hold", "remains open", "blocked", "unresolved")
        fact_matches = sum(
            _contains_anchor(segment, anchor) for anchor in row["fact_anchors"]
        )
        source_matches = sum(
            any(
                source.get(field) and _contains_anchor(segment, source[field])
                for field in (
                    "resource_id",
                    "evidence_id",
                    "source_path",
                    "document_record_id",
                )
            )
            for source in row["source_records"]
        )
        source_matches += sum(
            _contains_anchor(segment, record_id)
            for record_id in row.get("business_record_ids", [])
        )
        missing_control = _missing_control_matches(
            segment,
            row,
            fact_matches,
        )
        branch = (
            any(marker in normalized for marker in action_markers)
            if row["disposition"] == "action"
            else any(marker in normalized for marker in hold_markers)
            or missing_control
        )
        checks = {
            "present": present,
            "branch": present and branch,
            "topic": present and _topic_matches(segment, row["topic"]),
            "facts": present
            and (
                fact_matches >= 2
                or (row["disposition"] != "action" and missing_control)
            ),
            "source_anchor": present and source_matches >= 1,
        }
        if row["disposition"] == "action":
            checks.update(
                {
                    "identity": present and _contains_anchor(segment, row["entity_id"]),
                    "owner": present and _contains_anchor(segment, row["owner"]),
                    "due_date": present and _contains_anchor(segment, row["due_date"]),
                }
            )
        else:
            checks["missing_control"] = present and missing_control
        for name, passed in checks.items():
            criteria[f"{key}.{name}"] = bool(passed)
        details.append(
            {
                "portfolio_key": key,
                "expected_disposition": row["disposition"],
                "fact_anchors_matched": fact_matches,
                "source_anchors_matched": source_matches,
                "checks": checks,
            }
        )
    return criteria, details


def _score_natural_decision(value: str, spec: dict[str, Any]) -> dict[str, Any]:
    expected = spec["expected_decision"]
    choice = expected["decision"]
    normalized = normalize(value)
    criteria: dict[str, bool] = {
        "decision_is_human_readable": bool(normalized),
        "top_level.matter_number": _contains_anchor(value, expected["matter_number"]),
        "top_level.prepared_for": _contains_anchor(value, expected["prepared_for"]),
        "top_level.as_of": _contains_anchor(value, expected["as_of"]),
        "choice.selected_option_id": _contains_anchor(value, choice["selected_option_id"]),
        "choice.action_count": _contains_anchor(value, len(expected["actions"])),
        "choice.hold_count": _contains_anchor(value, len(expected["holds"])),
    }
    for option in choice["alternatives_evaluated"]:
        prefix = f"choice.option.{option['id']}"
        criteria[f"{prefix}.present"] = _contains_anchor(value, option["id"])
        criteria[f"{prefix}.cost"] = _contains_anchor(
            value, f"${option['incrementalCost']:,}"
        )
        criteria[f"{prefix}.outcome_date"] = _contains_anchor(
            value, option["outcomeDate"]
        )
        criteria[f"{prefix}.authority"] = _contains_anchor(
            value, option["authorityStatus"]
        )
    for group in ("control_comparison", "authority_application"):
        for field, expected_value in choice[group].items():
            if isinstance(expected_value, bool):
                criteria[f"choice.{group}.{field}"] = (
                    "approval required" in normalized
                    if expected_value
                    else _contains_anchor(
                        value,
                        choice["authority_application"][
                            "selectedAuthorityStatus"
                        ],
                    )
                )
                continue
            values = expected_value if isinstance(expected_value, list) else [expected_value]
            criteria[f"choice.{group}.{field}"] = all(
                _contains_anchor(value, item) for item in values
            )
    row_criteria, details = _semantic_row_criteria(
        value, spec, strict_population=False
    )
    criteria.update(row_criteria)
    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
        "details": details,
        "serialization": "human-readable",
    }


def score_decision(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, str):
        return _score_natural_decision(value, spec)
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
    if isinstance(value, str):
        expected = spec["expected_register"]
        criteria: dict[str, bool] = {
            "register_is_human_readable": bool(normalize(value)),
            "top_level.matter_number": _contains_anchor(
                value, expected["matter_number"]
            ),
            "top_level.selected_option": _contains_anchor(
                value, spec["expected_decision"]["decision"]["selected_option_id"]
            ),
        }
        row_criteria, details = _semantic_row_criteria(
            value, spec, strict_population=True
        )
        criteria.update(row_criteria)
        return {
            "criteria": criteria,
            "score": round(mean(criteria), 6),
            "passed": all(criteria.values()),
            "details": details,
            "serialization": "human-readable",
        }
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
    if isinstance(value, str) and not value.lstrip().startswith("{"):
        choice = expected["decision"]
        criteria: dict[str, bool] = {
            "human_readable": bool(normalized),
            "summary.matter_number": _contains_anchor(
                memo, expected["matter_number"]
            ),
            "summary.selected_option": _contains_anchor(
                memo, choice["selected_option_id"]
            ),
            "summary.action_count": _contains_anchor(
                memo, len(expected["actions"])
            ),
            "summary.hold_count": _contains_anchor(
                memo, len(expected["holds"])
            ),
        }
        row_criteria, details = _semantic_row_criteria(
            memo, spec, strict_population=False
        )
        criteria.update(row_criteria)
        for option in choice["alternatives_evaluated"]:
            criteria[f"alternative.{option['id']}"] = _contains_anchor(
                memo, option["id"]
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
            "serialization": "human-readable",
        }
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


def score_notification(value: Any, spec: dict[str, Any]) -> dict[str, Any]:
    """Grade the concise team handoff by business content, not exact prose."""

    text = value if isinstance(value, str) else ""
    expected = spec["expected_decision"]
    choice = expected["decision"]
    control = choice["control_comparison"]
    authority = choice["authority_application"]
    criteria: dict[str, bool] = {
        "human_readable": bool(normalize(text)),
        "matter_number": _contains_anchor(text, expected["matter_number"]),
        "selected_option": _contains_anchor(text, choice["selected_option_id"]),
        "action_count": _contains_anchor(text, len(expected["actions"])),
        "hold_count": _contains_anchor(text, len(expected["holds"])),
        "selected_outcome_date": _contains_anchor(
            text, control["selectedOutcomeDate"]
        ),
        "business_need_date": _contains_anchor(text, control["businessNeedDate"]),
        "timing_status": _contains_anchor(text, control["timingStatus"]),
        "authority_status": _contains_anchor(
            text, authority["selectedAuthorityStatus"]
        ),
        "created_note_reference": _contains_anchor(
            text, spec["state_contract"]["note_id"]
        ),
        "register_reference": "register" in normalize(text),
    }
    for hold in expected["holds"]:
        criteria[f"hold.{hold['portfolio_key']}"] = _contains_anchor(
            text, hold["portfolio_key"]
        ) or _contains_anchor(text, hold["required_next_evidence"])
    forbidden = [
        claim for claim in spec["forbidden_claims"] if normalize(claim) in normalize(text)
    ]
    criteria["forbidden_claims_absent"] = not forbidden
    return {
        "criteria": criteria,
        "score": round(mean(criteria), 6),
        "passed": all(criteria.values()),
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
