#!/usr/bin/env python3
"""Fail-closed scale, determinism, document, and adversarial checks for v21."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import ast
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from world.v21.catalog import iter_tools  # noqa: E402

WORLD_PATH = ROOT / "world" / "blobfish" / "world-v21.json"
REPORT_PATH = ROOT / "world" / "v21" / "build-report.json"
CONTRACTS_DIR = ROOT / "mcp" / "v5" / "contracts"
SEEDS_ROOT = ROOT / "research" / "v21-seeded-documents"
RETAIL_AUTHORITY_MAP = ROOT / "research" / "retail-price-accuracy" / "jurisdiction-research-v2.json"
LEGACY_RETAIL_PENDING_STATUS = "official_portal_identified_not_substantively_validated"
V21_RETAIL_PENDING_STATUS = "specific_authority_mapped_attorney_validation_required"
ADDED_TOOL_NAMES = {name for *_, name in iter_tools()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def legacy_vcode_config(vcode: str) -> dict[str, Any]:
    marker = "CONFIG = json.loads("
    config_line = next((line for line in vcode.splitlines() if line.startswith(marker)), None)
    assert config_line is not None and config_line.endswith(")")
    return json.loads(ast.literal_eval(config_line[len(marker):-1]))


def contracts() -> tuple[dict[str, dict], dict[str, dict], int, int]:
    tools: dict[str, dict] = {}
    tables: dict[str, dict] = {}
    visible = internal = 0
    for path in sorted(CONTRACTS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        contract = json.loads(path.read_text("utf-8"))
        for table in contract["tables"]:
            assert table["name"] not in tables, table["name"]
            tables[table["name"]] = table
        for tool in contract["tools"]:
            assert tool["name"] not in tools, tool["name"]
            tools[tool["name"]] = tool
            if tool.get("agent_visible") is False:
                internal += 1
            else:
                visible += 1
    return tools, tables, visible, internal


def simulate(task: dict[str, Any], table_rows: dict[str, list[dict]],
             tool_defs: dict[str, dict]) -> tuple[dict, dict, list[dict]]:
    allowed = task["tables_affected"]
    initial = {name: copy.deepcopy(table_rows[name]) for name in allowed}
    final = copy.deepcopy(initial)
    trace = []
    for tool_name, args in zip(task["walk"], task["reference_args"]):
        tool = tool_defs[tool_name]
        op = tool["op"]
        table = op["table"]
        kind = op["kind"]
        if tool_name not in ADDED_TOOL_NAMES:
            # Legacy coverage calls use vendor wire dialects. Their actual
            # state behavior is proven by the HTTP oracle; the pure VCode
            # test needs only the successful exact-argument trace because the
            # task's v21 create/update pair supplies the asserted state delta.
            observation = json.dumps({"legacy_contract_probe": tool_name,
                                      "results": final[table][:2]}, sort_keys=True)
        elif kind in {"list", "search"}:
            observation = json.dumps({"results": final[table], "total": len(final[table])}, sort_keys=True)
        elif kind == "get":
            row = next(row for row in final[table] if row["id"] == args["id"])
            observation = json.dumps(row, sort_keys=True)
        elif kind == "create":
            next_id = max((row["id"] for row in final[table]), default=0) + 1
            row = {"id": next_id, **args}
            for key, value in (op.get("defaults") or {}).items():
                row.setdefault(key, value)
            final[table].append(row)
            observation = json.dumps(row, sort_keys=True)
        elif kind == "update":
            row = next(row for row in final[table] if row["id"] == args["id"])
            for key, value in args.items():
                if key != "id":
                    row[key] = value
            observation = json.dumps(row, sort_keys=True)
        else:
            raise AssertionError(f"unexpected v21 op: {kind}")
        trace.append({"tool": tool_name, "requested_tool": tool_name,
                      "arguments": copy.deepcopy(args), "observation": observation, "ok": True})
    return initial, final, trace


def run_verifier(verifier: dict, initial: dict, final: dict, trace: list[dict]) -> dict:
    namespace: dict[str, Any] = {}
    exec(verifier["vcode"], namespace)
    verdict = namespace["verify"](copy.deepcopy(initial), copy.deepcopy(final), copy.deepcopy(trace))
    assert verdict["verifier_config_sha256"] == verifier["config_sha256"]
    return verdict


def check_documents(catalog: list[dict]) -> None:
    assert len(catalog) == 117
    signatures = set()
    counts = Counter()
    retail_packs = []
    for pack in catalog:
        assert pack["synthetic"] is True
        assert pack["attorney_validation_required"] is True
        assert pack["substantive_legal_opinion"] is False
        assert pack["private_remedy_encoded"] is False
        if pack["domain"] == "retail-price-accuracy":
            retail_packs.append(pack)
            assert pack["legal_research_status"] == "specific_authority_mapped_attorney_validation_required"
            assert pack["research_authority"]
            assert pack["research_authority_url"].startswith("https://")
        assert Path(ROOT / pack["documents_source"]).is_dir()
        manifest_path = ROOT / pack["manifest"]
        manifest = json.loads(manifest_path.read_text("utf-8"))
        signatures.add(json.dumps(manifest["structure_signature"], sort_keys=True))
        print_contract = manifest["structure_signature"]["xlsx"]["print_contract"]
        assert set(print_contract) == {"Evidence Register", "Computation", "Instructions"}
        assert all(config["orientation"] == "landscape" for config in print_contract.values())
        assert all(config["fit_to_width"] == config["fit_to_height"] == 1
                   for config in print_contract.values())
        documents = ROOT / pack["documents_source"]
        for record in manifest["files"]:
            path = documents / record["path"]
            assert path.is_file(), path
            assert path.stat().st_size == record["bytes"], path
            assert sha256(path) == record["sha256"], path
            counts[path.suffix.lower()] += 1
    assert len(signatures) == 1
    assert counts == Counter({".docx": 117, ".xlsx": 117, ".pdf": 117}), counts
    authority_map = json.loads(
        (ROOT / "research" / "retail-price-accuracy" / "jurisdiction-research-v2.json").read_text("utf-8")
    )
    authority_codes = {row["code"] for row in authority_map["jurisdictions"]}
    assert len(retail_packs) == len(authority_codes) == 51
    assert {pack["jurisdiction"] for pack in retail_packs} == authority_codes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0,
                        help="Check only N generated positive verifiers; 0 checks every generated verifier")
    arguments = parser.parse_args()
    world = json.loads(WORLD_PATH.read_text("utf-8"))
    report = json.loads(REPORT_PATH.read_text("utf-8"))
    tool_defs, contract_tables, visible, internal = contracts()
    catalog = json.loads((SEEDS_ROOT / "catalog.json").read_text("utf-8"))["packs"]
    check_documents(catalog)

    assert world["version"] == 21
    assert world["world_id"] == "legal-agent-simulation-world-v21"
    assert len(world["tasks"]) == len(world["verifiers"]) == 23_310
    assert visible == 1_100 and internal == 11
    assert len(world["tables"]) == len(contract_tables) == 254
    assert report["total_tasks"] == report["total_verifiers"] == 23_310
    assert report["visible_tools"] == report["visible_tools_exercised"] == 1_100
    assert report["seed_documents"] == 351 and report["seed_packs"] == 117
    assert report["retail_authority_packs"] == report["retail_authority_jurisdictions"] == 51
    assert report["retail_executable_authority_rows"] == 51
    assert report["retail_attorney_gated_research_rows"] == 45
    assert report["retail_legacy_task_pairs_checked"] == 6
    assert report["retail_authority_dependent_task_pairs_upgraded"] == 2
    assert report["retail_authority_verifier_programs_strengthened"] == 4

    tasks = {task["task_id"]: task for task in world["tasks"]}
    verifiers = {verifier["task_id"]: verifier for verifier in world["verifiers"]}
    assert len(tasks) == len(verifiers) == 23_310
    assert tasks.keys() == verifiers.keys()
    authority_payload = json.loads(RETAIL_AUTHORITY_MAP.read_text("utf-8"))
    authority_defaults = authority_payload["defaults"]
    authority_by_code = {
        row["code"]: {**authority_defaults, **row}
        for row in authority_payload["jurisdictions"]
    }
    rules_table = next(table for table in world["tables"] if table["name"] == "rc_jurisdiction_rules")
    executable_rules = rules_table["sample_rows"]
    assert len(executable_rules) == len(authority_by_code) == 51
    assert {row["jurisdiction_code"] for row in executable_rules} == set(authority_by_code)
    assert sum(row["research_status"] == "primary_source_triaged" for row in executable_rules) == 6
    assert sum(row["research_status"] == V21_RETAIL_PENDING_STATUS for row in executable_rules) == 45
    for row in executable_rules:
        authority = authority_by_code[row["jurisdiction_code"]]
        assert row["authority"] == authority["citation"]
        assert row["source_url"] == authority["authority_url"]
        assert row["attorney_validation_required"] == 1
        assert "Specific authority mapped" in row["verification_note"]
        assert LEGACY_RETAIL_PENDING_STATUS not in json.dumps(row, sort_keys=True)
    retail_task_ids = {task_id for task_id in tasks if task_id.startswith("task_v20_retail_")}
    assert len(retail_task_ids) == 6
    authority_dependent = 0
    strengthened_programs = 0
    authority_retrieval_assertion = {
        "anchors": ['"count": 51', '"total": 51'],
        "kind": "tool_observation_contains",
        "name": "all_51_authority_rows_retrieved",
        "tool": "retail_jurisdiction_rules_list",
    }
    for task_id in retail_task_ids:
        combined = json.dumps({"task": tasks[task_id], "verifier": verifiers[task_id]}, sort_keys=True)
        assert LEGACY_RETAIL_PENDING_STATUS not in combined
        is_authority_dependent = V21_RETAIL_PENDING_STATUS in combined
        authority_dependent += is_authority_dependent
        if is_authority_dependent:
            assert "official code portals pending" not in combined
            paired_calls = zip(tasks[task_id]["walk"], tasks[task_id]["reference_args"], strict=True)
            assert any(
                tool == "retail_jurisdiction_rules_list"
                and arguments.get("limit") == 100
                and arguments.get("offset", 0) == 0
                for tool, arguments in paired_calls
            )
            assert authority_retrieval_assertion in legacy_vcode_config(
                verifiers[task_id]["vcode"]
            )["assertions"]
        for vcode in [
            verifiers[task_id]["vcode"],
            *(verifiers[task_id].get("phase_vcodes") or {}).values(),
        ]:
            matching = [
                assertion
                for assertion in legacy_vcode_config(vcode)["assertions"]
                if assertion.get("name") == "all_51_authority_rows_retrieved"
            ]
            assert not matching or matching == [authority_retrieval_assertion]
            strengthened_programs += len(matching)
    assert authority_dependent == 2
    assert strengthened_programs == 4
    visible_names = {name for name, tool in tool_defs.items() if tool.get("agent_visible") is not False}
    walked = {name for task in tasks.values() for name in task.get("walk") or []}
    assert visible_names <= walked

    added_tool_names = ADDED_TOOL_NAMES
    generated = [task for task in world["tasks"] if task["task_id"].startswith("task_v21_")]
    assert len(generated) == report["added_generated_tasks"] == 20_963
    assert len({verifiers[task["task_id"]]["config_sha256"] for task in generated}) == len(generated)
    catalog_by_pack = {pack["pack_id"]: pack for pack in catalog}
    focused: dict[str, dict] = {}
    pack_counts = Counter()
    for task in generated:
        pack_counts[task["provenance"]["source_pack"]] += 1
        pack = catalog_by_pack[task["provenance"]["source_pack"]]
        file_lane = task["file_lane"]
        assert file_lane["inputs_only"] is True
        assert file_lane["deliverables"] == [] and file_lane["assertions"] == []
        assert file_lane["skills"] == []
        assert file_lane["documents_source"] == pack["documents_source"]
        assert task["provenance"]["research_authority"] == pack["research_authority"]
        assert task["provenance"]["research_authority_url"] == pack["research_authority_url"]
        assert task["provenance"]["legal_research_status"] == pack["legal_research_status"]
        assert task["provenance"]["private_remedy_encoded"] is False
        focus = task["provenance"]["focus_tool"]
        assert focus in task["walk"] and focus in added_tool_names
        focused.setdefault(focus, task)
        verifier = verifiers[task["task_id"]]
        assert verifier["deterministic"] is True
        assert "verifier_config_integrity" in verifier["vcode"]
        assert "no_row_deletions" in verifier["vcode"]
        assert "no_collateral_damage" in verifier["vcode"]
    assert set(pack_counts) == {pack["pack_id"] for pack in catalog}
    retail_task_counts = Counter(
        catalog_by_pack[task["provenance"]["source_pack"]]["jurisdiction"]
        for task in generated
        if catalog_by_pack[task["provenance"]["source_pack"]]["domain"] == "retail-price-accuracy"
    )
    authority_codes = {
        row["code"] for row in json.loads(
            (ROOT / "research" / "retail-price-accuracy" / "jurisdiction-research-v2.json").read_text("utf-8")
        )["jurisdictions"]
    }
    assert set(retail_task_counts) == authority_codes
    assert min(retail_task_counts.values()) > 0

    # Build an exact table-row map from the materialized world.  Positive
    # execution is checked for every generated verifier by default.
    table_rows = {table["name"]: table.get("sample_rows") or [] for table in world["tables"]}
    positives = generated if arguments.sample <= 0 else generated[:arguments.sample]
    focus_first: dict[str, tuple[dict, dict, dict, list]] = {}
    for task in positives:
        verifier = verifiers[task["task_id"]]
        initial, final, trace = simulate(task, table_rows, tool_defs)
        verdict = run_verifier(verifier, initial, final, trace)
        assert verdict["passed"], (task["task_id"], verdict["failed_conditions"])
        for name in task["walk"]:
            if name in added_tool_names:
                focus_first.setdefault(name, (task, verifier, initial, final, trace))
    if arguments.sample <= 0:
        assert set(focus_first) == added_tool_names

        # One four-mode adversarial rejection suite per added tool.
        for name, (task, verifier, initial, final, trace) in focus_first.items():
            missing = run_verifier(verifier, initial, final, trace[:-1])
            assert not missing["passed"], (name, "missing-call accepted")

            trapped = copy.deepcopy(final)
            created_table = task["effects"][0]["table"]
            created = max(trapped[created_table], key=lambda row: row["id"])
            created["summary"] = created.get("summary", "") + " AUTO-CLOSE WITHOUT REVIEW"
            rejected = run_verifier(verifier, initial, trapped, trace)
            assert not rejected["passed"], (name, "trap accepted")

            collateral_initial = copy.deepcopy(initial)
            collateral_final = copy.deepcopy(final)
            collateral_initial["unauthorized_table"] = [{"id": 1, "value": "before"}]
            collateral_final["unauthorized_table"] = [{"id": 1, "value": "after"}]
            collateral = run_verifier(verifier, collateral_initial, collateral_final, trace)
            assert not collateral["passed"], (name, "collateral mutation accepted")

            deleted = copy.deepcopy(final)
            primary_table = task["effects"][1]["table"]
            deleted[primary_table] = [row for row in deleted[primary_table] if row["id"] != 1]
            deletion = run_verifier(verifier, initial, deleted, trace)
            assert not deletion["passed"], (name, "row deletion accepted")

    print(json.dumps({
        "tasks": len(tasks), "verifiers": len(verifiers), "generated_checked": len(positives),
        "visible_tools": visible, "added_tools": len(added_tool_names),
        "adversarial_modes_per_added_tool": 4 if arguments.sample <= 0 else 0,
        "tables": len(world["tables"]), "seed_packs": len(catalog), "seed_documents": 351,
        "retail_authority_jurisdictions": len(retail_task_counts),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
