#!/usr/bin/env python3
"""Build world v21 with measured 10x task, verifier, and tool scale."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from world.v21.catalog import (  # noqa: E402
    DOMAIN_RESOURCES,
    OPERATIONS,
    RISK_LEVELS,
    iter_resources,
    iter_tools,
    resource_label,
    table_name,
    tool_name,
)
from world.v21.verifiers import compile_vcode, config_hash  # noqa: E402
from world.v19.verifiers import compile_vcode as compile_legacy_vcode  # noqa: E402

DEFAULT_BASE = ROOT / "world" / "blobfish" / "world-v20.json"
DEFAULT_V19 = ROOT / "world" / "blobfish" / "world-v19.json"
DEFAULT_REALWORLD = ROOT / "world" / "blobfish" / "world-v20-draft.json"
DEFAULT_CONTRACTS = ROOT / "mcp" / "v5" / "contracts"
DEFAULT_SEEDS = ROOT / "research" / "v21-seeded-documents" / "catalog.json"
RETAIL_AUTHORITY_MAP = (
    ROOT / "research" / "retail-price-accuracy" / "jurisdiction-research-v2.json"
)
DEFAULT_OUTPUT = ROOT / "world" / "blobfish" / "world-v21.json"
DEFAULT_REPORT = ROOT / "world" / "v21" / "build-report.json"

TARGET_TASKS = 23_310
TARGET_VISIBLE_TOOLS = 1_100
FIXED_TIME = "2026-08-22T12:00:00Z"
TRAP_PHRASE = "AUTO-CLOSE WITHOUT REVIEW"
LEGACY_RETAIL_PENDING_STATUS = "official_portal_identified_not_substantively_validated"
V21_RETAIL_PENDING_STATUS = "specific_authority_mapped_attorney_validation_required"

CAPABILITIES = (
    "record_intake_and_triage", "deadline_and_escalation_control",
    "evidence_preservation", "issue_matrix_filing", "notice_workflow",
    "approval_routing", "remediation_tracking", "reserve_calculation",
    "cross_record_reconciliation", "quality_control", "audit_closeout",
    "cross_jurisdiction_coordination",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"required build input is missing: {path}")
    data = json.loads(path.read_text("utf-8"))
    return data.get("world", data)


def replace_strings(value: Any, replacements: tuple[tuple[str, str], ...]) -> Any:
    """Recursively migrate frozen task prose and embedded verifier configs."""
    if isinstance(value, str):
        for before, after in replacements:
            value = value.replace(before, after)
        return value
    if isinstance(value, list):
        return [replace_strings(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: replace_strings(item, replacements) for key, item in value.items()}
    return value


def strengthen_legacy_authority_vcode(vcode: str) -> tuple[str, bool]:
    """Require a complete unfiltered 51-row authority-list observation."""
    marker = "CONFIG = json.loads("
    config_line = next((line for line in vcode.splitlines() if line.startswith(marker)), None)
    if config_line is None or not config_line.endswith(")"):
        raise SystemExit("legacy retail verifier config is not decodable")
    encoded = ast.literal_eval(config_line[len(marker):-1])
    config = json.loads(encoded)
    tool = "retail_jurisdiction_rules_list"
    if tool not in config["required_path"]:
        return vcode, False
    assertion_name = "all_51_authority_rows_retrieved"
    if any(row.get("name") == assertion_name for row in config["assertions"]):
        return vcode, False
    config["assertions"].append({
        "kind": "tool_observation_contains",
        "name": assertion_name,
        "tool": tool,
        # Oracle traces preserve the beginning of each tool result. The list
        # envelope emits count/total before rows, so these anchors remain
        # robust even when the 51-row response exceeds the trace text cap.
        # Exact citation/URL identity is independently fail-closed below and
        # in tools/check_v21_scale.py.
        "anchors": ['"count": 51', '"total": 51'],
    })
    return compile_legacy_vcode(
        config["task_id"],
        config["required_path"],
        config["assertions"],
        allowed_tables=config["allowed_tables"],
        min_success_calls=config["min_success_calls"],
    ), True


def upgrade_retail_authority_lane(world: dict[str, Any]) -> dict[str, int]:
    """Project the 51-row issue-spotting map into executable v21 state.

    The v20 snapshot stays frozen. v21 replaces the 45 generic portal queues
    with exact citations and official authority URLs, while deliberately not
    inventing remedies, deadlines, applicability conclusions, or local-law
    overlays. The six previously triaged benchmark rows retain their v20
    operational fields but receive the same exact v2 citation provenance.
    """
    payload = load_json(RETAIL_AUTHORITY_MAP)
    defaults = payload.get("defaults") or {}
    mapped_rows = [{**defaults, **row} for row in payload.get("jurisdictions") or []]
    mapped = {row.get("code"): row for row in mapped_rows}
    if payload.get("schema_version") != 2 or len(mapped_rows) != len(mapped) or len(mapped) != 51:
        raise SystemExit("retail authority v2 map must contain 50 states plus DC")
    if defaults.get("mapping_status") != V21_RETAIL_PENDING_STATUS:
        raise SystemExit("retail authority v2 mapping status drifted")
    for row in mapped_rows:
        if (
            not row.get("citation")
            or not str(row.get("authority_url") or "").startswith("https://")
            or row.get("substantive_legal_opinion")
            or row.get("private_remedy_encoded")
            or row.get("current_text_and_local_overlays_validated")
            or not row.get("attorney_validation_required")
        ):
            raise SystemExit(f"unsafe or incomplete retail authority mapping: {row.get('code')}")

    tables = {table["name"]: table for table in world["tables"]}
    rules_table = tables.get("rc_jurisdiction_rules")
    if rules_table is None:
        raise SystemExit("v21 is missing executable rc_jurisdiction_rules")
    rules = rules_table.get("sample_rows") or []
    rule_codes = {row.get("jurisdiction_code") for row in rules}
    if len(rules) != len(rule_codes) or rule_codes != set(mapped):
        raise SystemExit("executable retail rules must cover exactly the authority v2 map")

    primary = pending = 0
    for rule in rules:
        authority = mapped[rule["jurisdiction_code"]]
        if authority["name"] != rule["jurisdiction_name"]:
            raise SystemExit(f"retail jurisdiction name mismatch: {rule['jurisdiction_code']}")
        rule["authority"] = authority["citation"]
        rule["source_url"] = authority["authority_url"]
        rule["last_verified"] = payload["as_of"]
        rule["attorney_validation_required"] = 1
        rule["verification_note"] = (
            f"Specific authority mapped from {authority['source_kind']} for issue spotting: "
            f"{authority['authority_focus']} Current text, scope, applicability, remedies, "
            "effective date, preemption, and local overlays remain attorney work."
        )
        if rule["research_status"] == "primary_source_triaged":
            primary += 1
            continue
        rule["rule_tier"] = "specific_authority_research_queue"
        rule["research_status"] = V21_RETAIL_PENDING_STATUS
        rule["price_standard"] = authority["operational_baseline"]
        rule["consumer_remedy"] = (
            "Promptly correct every verified overcharge and preserve statutory rights; "
            "do not assume a bonus, free-item remedy, waiver, notice deadline, private "
            "right, or class procedure before current attorney validation."
        )
        rule["notice_window_days"] = None
        rule["payment_window_days"] = None
        pending += 1
    if primary != 6 or pending != 45:
        raise SystemExit(f"unexpected retail authority tiers: primary={primary} pending={pending}")

    replacements = (
        (LEGACY_RETAIL_PENDING_STATUS, V21_RETAIL_PENDING_STATUS),
        (
            "45 official code portals pending substantive review",
            "45 specific authorities mapped for issue spotting and pending substantive review",
        ),
        (
            "never turn an official-code portal into a legal conclusion",
            "never turn an issue-spotting citation into a legal conclusion",
        ),
        ("45 official_portal", "45 specific_authority_mapped"),
        ("45 rows remain", "45 mapped rows remain"),
    )
    task_ids = {
        task["task_id"] for task in world["tasks"]
        if task["task_id"].startswith("task_v20_retail_")
    }
    verifier_ids = {
        verifier["task_id"] for verifier in world["verifiers"]
        if verifier["task_id"].startswith("task_v20_retail_")
    }
    if len(task_ids) != 6 or verifier_ids != task_ids:
        raise SystemExit("expected six paired legacy retail tasks for the v21 authority migration")
    verifiers_by_id = {verifier["task_id"]: verifier for verifier in world["verifiers"]}
    authority_dependent_task_ids = {
        task["task_id"]
        for task in world["tasks"]
        if task["task_id"] in task_ids
        and LEGACY_RETAIL_PENDING_STATUS in json.dumps(
            {"task": task, "verifier": verifiers_by_id[task["task_id"]]}, sort_keys=True
        )
    }
    if len(authority_dependent_task_ids) != 2:
        raise SystemExit("expected two retail task pairs to contain the legacy portal status")
    world["tasks"] = [
        replace_strings(task, replacements) if task["task_id"] in task_ids else task
        for task in world["tasks"]
    ]
    world["verifiers"] = [
        replace_strings(verifier, replacements) if verifier["task_id"] in verifier_ids else verifier
        for verifier in world["verifiers"]
    ]
    strengthened_programs = 0
    for verifier in world["verifiers"]:
        if verifier["task_id"] not in authority_dependent_task_ids:
            continue
        verifier["vcode"], changed = strengthen_legacy_authority_vcode(verifier["vcode"])
        if changed:
            strengthened_programs += 1
            if "all_51_authority_rows_retrieved" not in verifier["assertions"]:
                verifier["assertions"].append("all_51_authority_rows_retrieved")
        for phase, phase_vcode in (verifier.get("phase_vcodes") or {}).items():
            upgraded, changed = strengthen_legacy_authority_vcode(phase_vcode)
            verifier["phase_vcodes"][phase] = upgraded
            strengthened_programs += int(changed)
    if strengthened_programs != 4:
        raise SystemExit(
            f"expected four authority-dependent verifier programs, got {strengthened_programs}"
        )
    return {
        "jurisdictions": len(rules),
        "specific_authorities": len(mapped),
        "primary_source_triaged": primary,
        "attorney_gated_research": pending,
        "legacy_task_pairs_checked": len(task_ids),
        "authority_dependent_task_pairs_upgraded": len(authority_dependent_task_ids),
        "authority_verifier_programs_strengthened": strengthened_programs,
    }


def primary_key(table: dict[str, Any]) -> str:
    return next((column["name"] for column in table["columns"] if column.get("pk")), "id")


def merge_realworld_lane(world: dict[str, Any], v19: dict[str, Any],
                         draft: dict[str, Any]) -> dict[str, int]:
    base_task_ids = {task["task_id"] for task in v19["tasks"]}
    existing_tasks = {task["task_id"]: task for task in world["tasks"]}
    candidates = [task for task in draft["tasks"] if task["task_id"] not in base_task_ids]
    draft_verifiers = {verifier["task_id"]: verifier for verifier in draft["verifiers"]}
    existing_verifiers = {verifier["task_id"]: verifier for verifier in world["verifiers"]}
    added_tasks = []
    for task in candidates:
        if task["task_id"] not in draft_verifiers:
            raise SystemExit(f"real-world verifier missing: {task['task_id']}")
        if task["task_id"] in existing_tasks:
            if existing_tasks[task["task_id"]] != task:
                raise SystemExit(f"real-world task collision: {task['task_id']}")
            if existing_verifiers.get(task["task_id"]) != draft_verifiers[task["task_id"]]:
                raise SystemExit(f"real-world verifier collision: {task['task_id']}")
            continue
        copied = copy.deepcopy(task)
        added_tasks.append(copied)
        world["tasks"].append(copied)
        world["verifiers"].append(copy.deepcopy(draft_verifiers[task["task_id"]]))

    world_tables = {table["name"]: table for table in world["tables"]}
    v19_tables = {table["name"]: table for table in v19["tables"]}
    added_rows = 0
    for draft_table in draft["tables"]:
        name = draft_table["name"]
        if name not in v19_tables:
            if name in world_tables:
                if world_tables[name] != draft_table:
                    raise SystemExit(f"real-world table collision: {name}")
                continue
            world["tables"].append(copy.deepcopy(draft_table))
            world_tables[name] = world["tables"][-1]
            added_rows += len(draft_table.get("sample_rows") or [])
            continue
        key = primary_key(draft_table)
        base_by_id = {str(row.get(key)): row for row in v19_tables[name].get("sample_rows") or []}
        target = world_tables[name]
        target_by_id = {str(row.get(key)): row for row in target.get("sample_rows") or []}
        for row in draft_table.get("sample_rows") or []:
            row_key = str(row.get(key))
            if row_key in base_by_id:
                if row != base_by_id[row_key]:
                    raise SystemExit(f"real-world lane mutates frozen v19 row: {name}:{row_key}")
                continue
            if row_key in target_by_id and target_by_id[row_key] != row:
                raise SystemExit(f"real-world row collision: {name}:{row_key}")
            if row_key not in target_by_id:
                target.setdefault("sample_rows", []).append(copy.deepcopy(row))
                target_by_id[row_key] = row
                added_rows += 1
    return {"tasks": len(added_tasks), "verifiers": len(added_tasks), "rows": added_rows}


def load_contract_bundle(contracts_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict], dict[str, dict]]:
    contracts = []
    tables: dict[str, dict] = {}
    tools: dict[str, dict] = {}
    for path in sorted(contracts_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        contract = json.loads(path.read_text("utf-8"))
        contracts.append(contract)
        for table in contract["tables"]:
            if table["name"] in tables:
                raise SystemExit(f"duplicate contract table: {table['name']}")
            tables[table["name"]] = table
        for tool in contract["tools"]:
            if tool["name"] in tools:
                raise SystemExit(f"duplicate contract tool: {tool['name']}")
            tools[tool["name"]] = tool
    return contracts, tables, tools


def embed_contract_tables(world: dict[str, Any], contract_tables: dict[str, dict]) -> int:
    existing = {table["name"] for table in world["tables"]}
    added = 0
    for name, table in contract_tables.items():
        if name in existing:
            continue
        seed = table.get("seed") or {}
        if seed.get("rows") is None:
            raise SystemExit(f"v21 added table must use explicit deterministic seed rows: {name}")
        world["tables"].append({
            "name": name,
            "columns": copy.deepcopy(table["columns"]),
            "sample_rows": copy.deepcopy(seed["rows"]),
        })
        added += 1
    return added


def legacy_reference_args(tool: dict[str, Any]) -> dict[str, Any]:
    """Return a safe deterministic wire-shaped probe for a legacy v4 tool."""
    if tool.get("conformance_args") is not None:
        return copy.deepcopy(tool["conformance_args"])
    op = tool["op"]
    kind = op["kind"]
    params = tool.get("params") or {}
    if kind == "get":
        return {"id": 1}
    if kind == "search":
        if "query" in params:
            return {"query": "a", "limit": 20}
        if "q" in params:
            return {"q": "a", "pageSize": 20}
        if "body" in params:
            return {"body": {"libraryId": "LEGAL", "anywhere": "a"}}
        return {"query": "a"}
    if kind == "create" and tool["name"] == "holds_create":
        return {"workspace_id": 1, "custodian": "Legacy Coverage Custodian",
                "issued_at": "2026-08-22"}
    return {}


def exact_create_args(pack: dict[str, Any], domain: dict, resource: str,
                      sequence: int) -> dict[str, Any]:
    token = hashlib.sha256(f"v21:create:{sequence}:{pack['pack_id']}".encode()).hexdigest()[:12]
    return {
        "external_key": f"V21-{sequence:05d}",
        "matter_ref": pack["matter_ref"],
        "jurisdiction": pack["jurisdiction"],
        "status": "filed",
        "title": f"{resource_label(resource)} deterministic work product {sequence:05d}",
        "summary": (
            f"DETERMINISTIC-{token} | {pack['anchor']} | quantity {pack['item_count']} | "
            f"rate {pack['unit_rate']:.2f} | exposure {pack['total_amount']:.2f} | "
            "attorney validation required"
        ),
        "owner": f"{domain['prefix']}-review-counsel",
        "due_date": pack["due_date"],
        "risk_level": pack["risk_level"],
        "amount": pack["total_amount"],
        "version": 1 + (sequence % 7),
        "source_pack": pack["pack_id"],
        "updated_at": FIXED_TIME,
    }


def exact_update_args(pack: dict[str, Any], domain: dict, sequence: int) -> dict[str, Any]:
    token = hashlib.sha256(f"v21:update:{sequence}:{pack['pack_id']}".encode()).hexdigest()[:12]
    return {
        "id": 1,
        "status": pack["expected_status"],
        "summary": (
            f"REMEDIATION-{token} | source {pack['anchor']} | response due {pack['due_date']} | "
            f"pinned exposure {pack['total_amount']:.2f} | no external legal conclusion"
        ),
        "owner": f"{domain['prefix']}-lead-counsel",
        "due_date": pack["due_date"],
        "risk_level": pack["risk_level"],
        "amount": pack["total_amount"],
        "version": 10 + (sequence % 17),
        "source_pack": pack["pack_id"],
        "updated_at": FIXED_TIME,
    }


def build_generated_task(sequence: int, focus: tuple[dict, str, str, str],
                         resources: list[tuple[dict, str]], packs: list[dict[str, Any]],
                         table_rows: dict[str, list[dict]],
                         legacy_call: tuple[str, dict[str, Any], str, str] | None = None
                         ) -> tuple[dict, dict]:
    domain, resource, focus_operation, focus_tool = focus
    resource_index = resources.index((domain, resource))
    related_domain, related_resource = resources[(resource_index + 1) % len(resources)]
    if related_domain["key"] != domain["key"]:
        related_domain, related_resource = domain, domain["resources"][0]
    action_resource = domain["resources"][(domain["resources"].index(resource) + 2) % 9]
    pack = packs[(sequence - 1) % len(packs)]
    primary_table = table_name(domain, resource)
    related_table = table_name(related_domain, related_resource)
    action_table = primary_table if focus_operation == "create" else table_name(domain, action_resource)
    primary_row = table_rows[primary_table][0]
    related_row = table_rows[related_table][0]

    if focus_operation == "list":
        first_args = {"status": "open", "limit": 25}
    elif focus_operation == "search":
        first_args = {"query": primary_row["external_key"], "limit": 20}
    else:
        first_args = {"id": 1}
    first_tool = focus_tool if focus_operation in {"list", "get", "search"} else tool_name(domain, resource, "get")
    related_tool = tool_name(related_domain, related_resource, "get")
    related_args = {"id": 1}
    create_resource = resource if focus_operation == "create" else action_resource
    create_tool = tool_name(domain, create_resource, "create")
    create_args = exact_create_args(pack, domain, create_resource, sequence)
    update_tool = tool_name(domain, resource, "update")
    update_args = exact_update_args(pack, domain, sequence)
    walk = [first_tool, related_tool, create_tool, update_tool]
    reference_args = [first_args, related_args, create_args, update_args]
    task_id = f"task_v21_{domain['prefix']}_{resource}_{sequence:05d}"
    allowed_table_set = {primary_table, related_table, action_table}
    legacy_tool = legacy_table = legacy_kind = None
    if legacy_call is not None:
        legacy_tool, legacy_args, legacy_table, legacy_kind = legacy_call
        walk.insert(0, legacy_tool)
        reference_args.insert(0, legacy_args)
        allowed_table_set.add(legacy_table)
    allowed_tables = sorted(allowed_table_set)

    assertions: list[dict[str, Any]] = [
        {"kind": "tool_observation_contains", "name": "primary_record_read",
         "tool": first_tool, "anchors": [f"ANCHOR-{primary_row['external_key']}"]},
        {"kind": "tool_observation_contains", "name": "related_record_read",
         "tool": related_tool, "anchors": [f"ANCHOR-{related_row['external_key']}"]},
    ]
    for index, (tool, args) in enumerate(zip(walk, reference_args), 1):
        assertions.append({"kind": "trace_argument_equals", "name": f"exact_call_{index}",
                           "tool": tool, "matches": args})
    assertions.extend([
        {"kind": "new_row", "name": "exact_work_product_created", "table": action_table,
         "count": 1, "matches": create_args},
        {"kind": "new_row_count", "name": "single_work_product_created",
         "table": action_table, "count": 1},
        {"kind": "changed_row", "name": "source_record_remediated", "table": primary_table,
         "id": 1, "before": {"status": "open", "source_pack": primary_row["source_pack"]},
         "matches": update_args},
        {"kind": "changed_row_count", "name": "single_source_record_changed",
         "table": primary_table, "count": 1},
        {"kind": "state_forbidden_text", "name": "fabrication_trap_absent",
         "tables": allowed_tables, "text": TRAP_PHRASE},
        {"kind": "tool_min_calls", "name": "focus_tool_exercised",
         "tool": focus_tool, "minimum": 1},
    ])
    if legacy_tool is not None:
        assertions.append({"kind": "tool_min_calls", "name": "legacy_tool_exercised",
                           "tool": legacy_tool, "minimum": 1})
    vcode = compile_vcode(task_id, walk, assertions, allowed_tables=allowed_tables,
                          min_success_calls=len(walk), forbid_deletes=True)
    digest = config_hash(task_id, walk, assertions, allowed_tables=allowed_tables,
                         min_success_calls=len(walk), forbid_deletes=True)
    prompt = (
        f"Complete a {domain['label']} control-remediation workflow for {pack['matter_ref']} using "
        f"the mounted files `matter-brief.docx`, `evidence-register.xlsx`, and `source-extract.pdf` "
        f"from {pack['pack_id']}. Reconcile the evidence anchor {pack['anchor']}, quantity "
        f"{pack['item_count']}, unit rate ${pack['unit_rate']:.2f}, pinned exposure "
        f"${pack['total_amount']:.2f}, and response date {pack['due_date']}. First exercise "
        f"`{focus_tool}` against {resource_label(resource).lower()} record "
        f"{primary_row['external_key']}; then inspect related {resource_label(related_resource).lower()} "
        f"record {related_row['external_key']}. File one {resource_label(create_resource).lower()} "
        f"record with external_key `{create_args['external_key']}` and the exact attributed facts in "
        f"the inputs. Finally update source record id 1 to status `{update_args['status']}`, owner "
        f"`{update_args['owner']}`, risk `{update_args['risk_level']}`, and version "
        f"{update_args['version']}. Preserve the synthetic/attorney-validation limitation, make no "
        f"collateral edits, delete no records, and do not repeat the rejected trap phrase from the inputs."
    )
    if pack.get("legal_research_status") != "not_applicable":
        prompt += (
            f" The inputs map `{pack['research_authority']}` for issue spotting. Preserve that citation "
            "and its source URL, but do not state that its current text, applicability, remedies, local "
            "overlays, or effective date have been validated; route those conclusions to qualified counsel."
        )
    if legacy_tool is not None:
        prompt += (
            f" As a compatibility check, also exercise inherited tool `{legacy_tool}` using its "
            "pinned contract-shaped request and preserve its result in the execution trace."
        )
    effects = [{"table": action_table, "op": "insert"},
               {"table": primary_table, "op": "update"}]
    if legacy_tool is not None and legacy_kind in {"create", "update"}:
        effects.append({"table": legacy_table, "op": legacy_kind})
    task = {
        "task_id": task_id,
        "outcome_class": "eligible_action",
        "prompt": prompt,
        "goal": f"Reconcile, file, and remediate a {domain['label'].lower()} record",
        "required_tools": sorted(set(walk)),
        "walk": walk,
        "reference_args": reference_args,
        "method": "v21_counselops_document_grounded_matrix",
        "complexity": "high" if sequence % 4 == 0 else "medium",
        "steps": [
            "Read and reconcile all three mounted input documents",
            "Locate the exact primary and related system-of-record entries",
            "Create the pinned work-product record",
            "Update the source record without collateral mutations",
        ],
        "tables_affected": allowed_tables,
        "effects": effects,
        "provenance": {
            "family": domain["key"], "source_pack": pack["pack_id"],
            "focus_tool": focus_tool,
            "legacy_coverage_tool": legacy_tool,
            "synthetic": True, "legal_advice": False,
            "research_authority": pack.get("research_authority"),
            "research_authority_url": pack.get("research_authority_url"),
            "legal_research_status": pack.get("legal_research_status"),
            "private_remedy_encoded": pack.get("private_remedy_encoded", False),
            "generator": "world/v21/build.py",
        },
        "capability": CAPABILITIES[(sequence - 1) % len(CAPABILITIES)],
        "capability_name": CAPABILITIES[(sequence - 1) % len(CAPABILITIES)],
        "difficulty_tier": "deterministic_matrix",
        "acceptance_label": "admitted_v21_determinate_workflow",
        "file_lane": {
            "source_task": f"synthetic-v21/{pack['pack_id']}/{task_id}",
            "source_commit": "local-v21",
            "documents_source": pack["documents_source"],
            "inputs_only": True,
            "deliverables": [],
            # Input-only evidence needs no authoring manual. An explicit empty
            # list also keeps this lane independent of the ignored Harvey
            # source clone on clean checkouts.
            "skills": [],
            "grading": "determinate-state-and-trace",
            "assertions": [],
        },
    }
    verifier = {
        "task_id": task_id,
        "assertions": [assertion["name"] for assertion in assertions],
        "vcode": vcode,
        "config_sha256": digest,
        "generated_by": "world/v21/build.py",
        "deterministic": True,
    }
    return task, verifier


def write_world(world: dict[str, Any], output: Path) -> str:
    payload = json.dumps(world, ensure_ascii=False, separators=(",", ":")) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(payload, "utf-8")
    temporary.replace(output)
    return hashlib.sha256(payload.encode()).hexdigest()


def build(base_path: Path, v19_path: Path, realworld_path: Path, contracts_dir: Path,
          seeds_path: Path, output: Path, report_path: Path) -> dict[str, Any]:
    if not base_path.exists() and base_path.resolve() == DEFAULT_BASE.resolve():
        subprocess.run([sys.executable, str(ROOT / "world" / "v20" / "build_retail.py"),
                        "--out", str(base_path)], cwd=ROOT, check=True)
    world = copy.deepcopy(load_json(base_path))
    v19 = load_json(v19_path)
    if not realworld_path.exists():
        subprocess.run([sys.executable, str(ROOT / "world" / "v20" / "build.py"),
                        "--base", str(base_path), "--out", str(realworld_path)], cwd=ROOT, check=True)
    realworld = load_json(realworld_path)
    merge_report = merge_realworld_lane(world, v19, realworld)
    retail_authority_upgrade = upgrade_retail_authority_lane(world)
    contracts, contract_tables, contract_tools = load_contract_bundle(contracts_dir)
    visible_tools = {name for name, tool in contract_tools.items() if tool.get("agent_visible") is not False}
    internal_tools = set(contract_tools) - visible_tools
    if len(visible_tools) != TARGET_VISIBLE_TOOLS:
        raise SystemExit(f"expected {TARGET_VISIBLE_TOOLS} visible tools, found {len(visible_tools)}")
    added_tables = embed_contract_tables(world, contract_tables)
    packs = json.loads(seeds_path.read_text("utf-8"))["packs"]
    if len(packs) != 117 or sum(len(pack["files"]) for pack in packs) != 351:
        raise SystemExit("v21 seed catalog must contain 117 packs / 351 documents")
    retail_packs = [pack for pack in packs if pack["domain"] == "retail-price-accuracy"]
    if len(retail_packs) != 51 or len({pack["jurisdiction"] for pack in retail_packs}) != 51:
        raise SystemExit("v21 seed catalog must contain one retail authority pack per state plus DC")
    if any(pack.get("substantive_legal_opinion") or pack.get("private_remedy_encoded")
           for pack in retail_packs):
        raise SystemExit("v21 retail authority packs may not encode legal opinions or private remedies")

    resources = list(iter_resources())
    focus_tools = list(iter_tools())
    added_tool_names = {item[3] for item in focus_tools}
    preexisting_walk_tools = {tool for task in world["tasks"] for tool in task.get("walk") or []}
    legacy_missing = sorted(visible_tools - added_tool_names - preexisting_walk_tools)
    legacy_calls = [
        (name, legacy_reference_args(contract_tools[name]), contract_tools[name]["op"]["table"],
         contract_tools[name]["op"]["kind"])
        for name in legacy_missing
    ]
    table_rows = {
        name: copy.deepcopy((table.get("seed") or {}).get("rows") or [])
        for name, table in contract_tables.items()
    }
    generated_count = TARGET_TASKS - len(world["tasks"])
    if generated_count < len(focus_tools):
        raise SystemExit("target task count is too small to exercise every v21 tool")
    generated_tasks = []
    generated_verifiers = []
    focus_counts: Counter[str] = Counter()
    pack_counts: Counter[str] = Counter()
    legacy_coverage_counts: Counter[str] = Counter()
    for index in range(generated_count):
        focus = focus_tools[index % len(focus_tools)]
        sequence = index + 1
        legacy_call = legacy_calls[index] if index < len(legacy_calls) else None
        task, verifier = build_generated_task(
            sequence, focus, resources, packs, table_rows, legacy_call=legacy_call
        )
        generated_tasks.append(task)
        generated_verifiers.append(verifier)
        focus_counts[focus[3]] += 1
        pack_counts[task["provenance"]["source_pack"]] += 1
        if legacy_call is not None:
            legacy_coverage_counts[legacy_call[0]] += 1
    world["tasks"].extend(generated_tasks)
    world["verifiers"].extend(generated_verifiers)

    task_ids = [task["task_id"] for task in world["tasks"]]
    verifier_ids = [verifier["task_id"] for verifier in world["verifiers"]]
    if len(task_ids) != TARGET_TASKS or len(task_ids) != len(set(task_ids)):
        raise SystemExit(f"task cardinality/uniqueness failure: {len(task_ids)}")
    if len(verifier_ids) != TARGET_TASKS or set(verifier_ids) != set(task_ids):
        raise SystemExit("verifier coverage failure")
    all_walk_tools = {tool for task in world["tasks"] for tool in task.get("walk") or []}
    missing_exercised = sorted(visible_tools - all_walk_tools)
    if missing_exercised:
        raise SystemExit(f"visible tools not exercised by admitted tasks: {missing_exercised}")
    if set(focus_counts) != {tool[3] for tool in focus_tools}:
        raise SystemExit("not every added v21 tool received a focus task")
    if set(legacy_coverage_counts) != set(legacy_missing):
        raise SystemExit("not every previously unexercised v4 tool received a coverage task")
    if set(pack_counts) != {pack["pack_id"] for pack in packs}:
        raise SystemExit("not every v21 seed pack is referenced by an admitted task")
    generated_hashes = [verifier["config_sha256"] for verifier in generated_verifiers]
    if len(generated_hashes) != len(set(generated_hashes)):
        raise SystemExit("generated verifier configs are not unique")

    world["version"] = 21
    world["world_id"] = "legal-agent-simulation-world-v21"
    world["lineage"] = {
        "base": str(base_path.relative_to(ROOT)),
        "merged_overlay": str(realworld_path.relative_to(ROOT)),
        "compiler": "world/v21/build.py",
        "contracts": "mcp/v5/contracts",
        "seed_documents": "research/v21-seeded-documents/catalog.json",
        "target": "10x canonical v20 task/verifier count and 10x v4 visible-tool count",
    }
    world["v21_expansion"] = {
        "canonical_v20_tasks": 2331,
        "realworld_lane_tasks": merge_report["tasks"],
        "generated_tasks": generated_count,
        "total_tasks": TARGET_TASKS,
        "visible_tools": len(visible_tools),
        "internal_tools": len(internal_tools),
        "added_systems": 22,
        "added_tables": added_tables,
        "seed_packs": len(packs),
        "seed_documents": sum(len(pack["files"]) for pack in packs),
        "retail_authority_packs": len(retail_packs),
        "retail_authority_jurisdictions": len({pack["jurisdiction"] for pack in retail_packs}),
        "retail_executable_authority_rows": retail_authority_upgrade["specific_authorities"],
        "retail_attorney_gated_research_rows": retail_authority_upgrade["attorney_gated_research"],
        "retail_legacy_task_pairs_checked": retail_authority_upgrade["legacy_task_pairs_checked"],
        "retail_authority_dependent_task_pairs_upgraded": retail_authority_upgrade["authority_dependent_task_pairs_upgraded"],
        "retail_authority_verifier_programs_strengthened": retail_authority_upgrade["authority_verifier_programs_strengthened"],
        "generated_verifier_configs_unique": len(set(generated_hashes)),
        "all_visible_tools_exercised": True,
        "legacy_tools_newly_exercised": len(legacy_missing),
        "all_seed_packs_referenced": True,
    }
    digest = write_world(world, output)
    report = {
        "schema_version": 2,
        "base": str(base_path.relative_to(ROOT)),
        "base_tasks": 2331,
        "merged_realworld": merge_report,
        "added_generated_tasks": generated_count,
        "total_tasks": len(world["tasks"]),
        "total_verifiers": len(world["verifiers"]),
        "generated_unique_verifier_configs": len(set(generated_hashes)),
        "contracts": len(contracts),
        "tables": len(world["tables"]),
        "added_tables": added_tables,
        "visible_tools": len(visible_tools),
        "internal_tools": len(internal_tools),
        "visible_tools_exercised": len(visible_tools & all_walk_tools),
        "added_tools_with_focus_tasks": len(focus_counts),
        "legacy_tools_newly_exercised": len(legacy_coverage_counts),
        "seed_packs": len(packs),
        "seed_documents": sum(len(pack["files"]) for pack in packs),
        "retail_authority_packs": len(retail_packs),
        "retail_authority_jurisdictions": len({pack["jurisdiction"] for pack in retail_packs}),
        "retail_executable_authority_rows": retail_authority_upgrade["specific_authorities"],
        "retail_attorney_gated_research_rows": retail_authority_upgrade["attorney_gated_research"],
        "retail_legacy_task_pairs_checked": retail_authority_upgrade["legacy_task_pairs_checked"],
        "retail_authority_dependent_task_pairs_upgraded": retail_authority_upgrade["authority_dependent_task_pairs_upgraded"],
        "retail_authority_verifier_programs_strengthened": retail_authority_upgrade["authority_verifier_programs_strengthened"],
        "seed_pack_reference_min": min(pack_counts.values()),
        "seed_pack_reference_max": max(pack_counts.values()),
        "world_sha256": digest,
        "world_bytes": output.stat().st_size,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--v19", type=Path, default=DEFAULT_V19)
    parser.add_argument("--realworld", type=Path, default=DEFAULT_REALWORLD)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    arguments = parser.parse_args()
    report = build(arguments.base, arguments.v19, arguments.realworld, arguments.contracts,
                   arguments.seeds, arguments.out, arguments.report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
