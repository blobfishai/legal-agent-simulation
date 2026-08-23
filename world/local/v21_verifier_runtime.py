"""Shared deterministic execution engine for compact world-v21 VCode configs."""
from __future__ import annotations

import hashlib
import json


def _rows(state, table):
    return state.get(table, []) if isinstance(state, dict) else []


def _index(state, table):
    return {str(row.get("id")): row for row in _rows(state, table)}


def _new(initial_state, final_state, table):
    before = _index(initial_state, table)
    return [row for key, row in _index(final_state, table).items() if key not in before]


def _deleted(initial_state, final_state, table):
    after = _index(final_state, table)
    return [row for key, row in _index(initial_state, table).items() if key not in after]


def _changed(initial_state, final_state, table):
    before = _index(initial_state, table)
    after = _index(final_state, table)
    return [(before[key], after[key]) for key in before.keys() & after.keys()
            if before[key] != after[key]]


def _matches(row, expected):
    for key, value in expected.items():
        actual = row.get(key)
        if isinstance(value, dict) and "startswith" in value:
            if not str(actual or "").startswith(str(value["startswith"])):
                return False
        elif isinstance(value, dict) and "contains" in value:
            if str(value["contains"]).casefold() not in str(actual or "").casefold():
                return False
        elif actual != value:
            return False
    return True


def _contains_text(value, needle):
    if isinstance(value, dict):
        return any(_contains_text(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return needle.casefold() in str(value or "").casefold()


def verify_config(config_json, config_sha256, initial_state, final_state, trace):
    """Run one immutable verifier config against state snapshots and a trace."""
    config = json.loads(config_json)
    checks = []

    def check(name, passed, details):
        checks.append({"name": name, "passed": bool(passed), "details": details})

    actual_digest = hashlib.sha256(config_json.encode()).hexdigest()
    check("verifier_config_integrity", actual_digest == config_sha256,
          f"expected={config_sha256} actual={actual_digest}")

    successful = [step for step in trace
                  if step.get("ok") and step.get("tool") != "_final_answer"]
    tools = [step.get("tool") for step in successful]
    cursor = 0
    for tool in tools:
        if cursor < len(config["required_path"]) and tool == config["required_path"][cursor]:
            cursor += 1
    check("required_path", cursor == len(config["required_path"]),
          f"matched={cursor}/{len(config['required_path'])} observed={tools}")
    if config["min_success_calls"]:
        check("minimum_successful_calls", len(successful) >= config["min_success_calls"],
              f"successful={len(successful)} minimum={config['min_success_calls']}")

    for index, assertion in enumerate(config["assertions"]):
        kind = assertion["kind"]
        name = assertion.get("name") or f"assertion_{index + 1}"
        if kind == "new_row":
            rows = [row for row in _new(initial_state, final_state, assertion["table"])
                    if _matches(row, assertion.get("matches") or {})]
            count = assertion.get("count", 1)
            check(name, len(rows) == count,
                  f"table={assertion['table']} matching={len(rows)} expected={count}")
        elif kind == "absent_new_row":
            rows = [row for row in _new(initial_state, final_state, assertion["table"])
                    if _matches(row, assertion.get("matches") or {})]
            check(name, not rows,
                  f"table={assertion['table']} forbidden_matching={len(rows)}")
        elif kind == "new_row_count":
            rows = _new(initial_state, final_state, assertion["table"])
            count = assertion["count"]
            check(name, len(rows) == count,
                  f"table={assertion['table']} new={len(rows)} expected={count}")
        elif kind == "changed_row":
            row_id = str(assertion["id"])
            before = _index(initial_state, assertion["table"]).get(row_id)
            after = _index(final_state, assertion["table"]).get(row_id)
            final_match = bool(after and _matches(after, assertion.get("matches") or {}))
            before_match = bool(before and _matches(before, assertion.get("before") or {}))
            check(name, bool(before and after and before != after and before_match and final_match),
                  f"table={assertion['table']} id={row_id} before={before} after={after}")
        elif kind == "changed_row_count":
            rows = _changed(initial_state, final_state, assertion["table"])
            count = assertion["count"]
            check(name, len(rows) == count,
                  f"table={assertion['table']} changed={len(rows)} expected={count}")
        elif kind == "tool_observation_contains":
            observations = "\n".join(str(step.get("observation") or "") for step in successful
                                      if step.get("tool") == assertion["tool"])
            anchors = assertion.get("anchors") or []
            missing = [anchor for anchor in anchors
                       if str(anchor).casefold() not in observations.casefold()]
            check(name, not missing, f"tool={assertion['tool']} missing={missing}")
        elif kind == "trace_argument_equals":
            candidates = [step.get("arguments") or {} for step in successful
                          if step.get("tool") == assertion["tool"]]
            expected = assertion.get("matches") or {}
            matched = any(_matches(candidate, expected) for candidate in candidates)
            check(name, matched,
                  f"tool={assertion['tool']} expected={expected} candidates={candidates}")
        elif kind == "tool_min_calls":
            observed = sum(1 for tool in tools if tool == assertion["tool"])
            minimum = assertion["minimum"]
            check(name, observed >= minimum,
                  f"tool={assertion['tool']} calls={observed} minimum={minimum}")
        elif kind == "state_forbidden_text":
            tables = assertion.get("tables") or list(final_state)
            needle = str(assertion["text"])
            hits = []
            for table in tables:
                before = _index(initial_state, table)
                for key, row in _index(final_state, table).items():
                    if (key not in before or before[key] != row) and _contains_text(row, needle):
                        hits.append(f"{table}:{key}")
            check(name, not hits, f"text={needle!r} hits={hits}")
        else:
            check(name, False, f"unsupported assertion kind={kind}")

    if config["forbid_deletes"]:
        scoped = config["allowed_tables"] or sorted(set(initial_state) | set(final_state))
        deleted = {table: len(_deleted(initial_state, final_state, table)) for table in scoped}
        deleted = {table: count for table, count in deleted.items() if count}
        check("no_row_deletions", not deleted, f"deleted={deleted}")

    if config["allowed_tables"] is not None:
        allowed = set(config["allowed_tables"]) | {"audit_logs"}
        changed = [table for table in set(initial_state) | set(final_state)
                   if table not in allowed
                   and _rows(initial_state, table) != _rows(final_state, table)]
        check("no_collateral_damage", not changed, f"changed={sorted(changed)}")

    failed = [item["name"] for item in checks if not item["passed"]]
    return {
        "task_id": config["task_id"],
        "passed": not failed,
        "reward": 0.0 if failed else 1.0,
        "failed_conditions": failed,
        "assertions": checks,
        "verifier_config_sha256": config_sha256,
        "explanation": ("All deterministic checks passed" if not failed
                        else "Failed: " + ", ".join(failed)),
    }


__all__ = ["verify_config"]
