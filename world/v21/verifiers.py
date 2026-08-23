"""Self-contained deterministic verifier compiler for v21 workflows."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def config_hash(
    task_id: str,
    required_path: list[str],
    assertions: list[dict[str, Any]],
    *,
    allowed_tables: list[str] | None,
    min_success_calls: int,
    forbid_deletes: bool,
) -> str:
    config = {
        "task_id": task_id,
        "required_path": required_path,
        "assertions": assertions,
        "allowed_tables": allowed_tables,
        "min_success_calls": min_success_calls,
        "forbid_deletes": forbid_deletes,
    }
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def compile_vcode(
    task_id: str,
    required_path: list[str],
    assertions: list[dict[str, Any]],
    *,
    allowed_tables: list[str] | None = None,
    min_success_calls: int = 0,
    forbid_deletes: bool = True,
) -> str:
    config = {
        "task_id": task_id,
        "required_path": required_path,
        "assertions": assertions,
        "allowed_tables": allowed_tables,
        "min_success_calls": min_success_calls,
        "forbid_deletes": forbid_deletes,
    }
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    # Keep each verifier's unique, integrity-bound configuration in the world,
    # but execute it through one shipped engine. Embedding the same ~10 KB
    # interpreter 20,963 times made world-v21 exceed a 2 GB container at load.
    return f'''"""Generated compact deterministic v21 verifier for {task_id}."""
try:
    from v21_verifier_runtime import verify_config as _verify_config
except ModuleNotFoundError:
    from world.local.v21_verifier_runtime import verify_config as _verify_config

CONFIG_JSON = {encoded!r}
CONFIG_SHA256 = {digest!r}
_required_workflow_path = {required_path!r}
CHECK_CONTRACT = ("verifier_config_integrity", "no_row_deletions", "no_collateral_damage")

def verify(initial_state, final_state, trace):
    return _verify_config(CONFIG_JSON, CONFIG_SHA256, initial_state, final_state, trace)
'''

    # Expanded implementation retained below as executable specification for
    # older generated artifacts; new v21 builds return the compact form above.
    return f'''"""Generated deterministic v21 verifier for {task_id}."""
import hashlib
import json

CONFIG_JSON = {encoded!r}
CONFIG = json.loads(CONFIG_JSON)
CONFIG_SHA256 = {digest!r}

def _rows(state, table):
    return state.get(table, []) if isinstance(state, dict) else []

def _index(state, table):
    return {{str(row.get("id")): row for row in _rows(state, table)}}

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

def verify(initial_state, final_state, trace):
    checks = []
    def check(name, passed, details):
        checks.append({{"name": name, "passed": bool(passed), "details": details}})

    actual_digest = hashlib.sha256(CONFIG_JSON.encode()).hexdigest()
    check("verifier_config_integrity", actual_digest == CONFIG_SHA256,
          f"expected={{CONFIG_SHA256}} actual={{actual_digest}}")

    successful = [step for step in trace
                  if step.get("ok") and step.get("tool") != "_final_answer"]
    tools = [step.get("tool") for step in successful]
    cursor = 0
    for tool in tools:
        if cursor < len(CONFIG["required_path"]) and tool == CONFIG["required_path"][cursor]:
            cursor += 1
    check("required_path", cursor == len(CONFIG["required_path"]),
          f"matched={{cursor}}/{{len(CONFIG['required_path'])}} observed={{tools}}")
    if CONFIG["min_success_calls"]:
        check("minimum_successful_calls", len(successful) >= CONFIG["min_success_calls"],
              f"successful={{len(successful)}} minimum={{CONFIG['min_success_calls']}}")

    for index, assertion in enumerate(CONFIG["assertions"]):
        kind = assertion["kind"]
        name = assertion.get("name") or f"assertion_{{index + 1}}"
        if kind == "new_row":
            rows = [row for row in _new(initial_state, final_state, assertion["table"])
                    if _matches(row, assertion.get("matches") or {{}})]
            count = assertion.get("count", 1)
            check(name, len(rows) == count,
                  f"table={{assertion['table']}} matching={{len(rows)}} expected={{count}}")
        elif kind == "absent_new_row":
            rows = [row for row in _new(initial_state, final_state, assertion["table"])
                    if _matches(row, assertion.get("matches") or {{}})]
            check(name, not rows,
                  f"table={{assertion['table']}} forbidden_matching={{len(rows)}}")
        elif kind == "new_row_count":
            rows = _new(initial_state, final_state, assertion["table"])
            count = assertion["count"]
            check(name, len(rows) == count,
                  f"table={{assertion['table']}} new={{len(rows)}} expected={{count}}")
        elif kind == "changed_row":
            row_id = str(assertion["id"])
            before = _index(initial_state, assertion["table"]).get(row_id)
            after = _index(final_state, assertion["table"]).get(row_id)
            final_match = bool(after and _matches(after, assertion.get("matches") or {{}}))
            before_match = bool(before and _matches(before, assertion.get("before") or {{}}))
            check(name, bool(before and after and before != after and before_match and final_match),
                  f"table={{assertion['table']}} id={{row_id}} before={{before}} after={{after}}")
        elif kind == "changed_row_count":
            rows = _changed(initial_state, final_state, assertion["table"])
            count = assertion["count"]
            check(name, len(rows) == count,
                  f"table={{assertion['table']}} changed={{len(rows)}} expected={{count}}")
        elif kind == "tool_observation_contains":
            observations = "\\n".join(str(step.get("observation") or "") for step in successful
                                      if step.get("tool") == assertion["tool"])
            anchors = assertion.get("anchors") or []
            missing = [anchor for anchor in anchors
                       if str(anchor).casefold() not in observations.casefold()]
            check(name, not missing, f"tool={{assertion['tool']}} missing={{missing}}")
        elif kind == "trace_argument_equals":
            candidates = [step.get("arguments") or {{}} for step in successful
                          if step.get("tool") == assertion["tool"]]
            expected = assertion.get("matches") or {{}}
            matched = any(_matches(candidate, expected) for candidate in candidates)
            check(name, matched,
                  f"tool={{assertion['tool']}} expected={{expected}} candidates={{candidates}}")
        elif kind == "tool_min_calls":
            observed = sum(1 for tool in tools if tool == assertion["tool"])
            minimum = assertion["minimum"]
            check(name, observed >= minimum,
                  f"tool={{assertion['tool']}} calls={{observed}} minimum={{minimum}}")
        elif kind == "state_forbidden_text":
            tables = assertion.get("tables") or list(final_state)
            needle = str(assertion["text"])
            hits = []
            for table in tables:
                before = _index(initial_state, table)
                for key, row in _index(final_state, table).items():
                    if (key not in before or before[key] != row) and _contains_text(row, needle):
                        hits.append(f"{{table}}:{{key}}")
            check(name, not hits, f"text={{needle!r}} hits={{hits}}")
        else:
            check(name, False, f"unsupported assertion kind={{kind}}")

    if CONFIG["forbid_deletes"]:
        scoped = CONFIG["allowed_tables"] or sorted(set(initial_state) | set(final_state))
        deleted = {{table: len(_deleted(initial_state, final_state, table)) for table in scoped}}
        deleted = {{table: count for table, count in deleted.items() if count}}
        check("no_row_deletions", not deleted, f"deleted={{deleted}}")

    if CONFIG["allowed_tables"] is not None:
        allowed = set(CONFIG["allowed_tables"]) | {{"audit_logs"}}
        changed = [table for table in set(initial_state) | set(final_state)
                   if table not in allowed
                   and _rows(initial_state, table) != _rows(final_state, table)]
        check("no_collateral_damage", not changed, f"changed={{sorted(changed)}}")

    failed = [item["name"] for item in checks if not item["passed"]]
    return {{
        "task_id": CONFIG["task_id"],
        "passed": not failed,
        "reward": 0.0 if failed else 1.0,
        "failed_conditions": failed,
        "assertions": checks,
        "verifier_config_sha256": CONFIG_SHA256,
        "explanation": "All deterministic checks passed" if not failed
                       else "Failed: " + ", ".join(failed),
    }}
'''


__all__ = ["compile_vcode", "config_hash"]
