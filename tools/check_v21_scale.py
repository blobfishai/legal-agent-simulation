#!/usr/bin/env python3
"""Fail-closed scale, determinism, document, and adversarial checks for v21."""
from __future__ import annotations

import argparse
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
ADDED_TOOL_NAMES = {name for *_, name in iter_tools()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    assert len(catalog) == 66
    signatures = set()
    counts = Counter()
    for pack in catalog:
        assert pack["synthetic"] is True
        assert pack["attorney_validation_required"] is True
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
    assert counts == Counter({".docx": 66, ".xlsx": 66, ".pdf": 66}), counts


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
    assert report["seed_documents"] == 198 and report["seed_packs"] == 66

    tasks = {task["task_id"]: task for task in world["tasks"]}
    verifiers = {verifier["task_id"]: verifier for verifier in world["verifiers"]}
    assert len(tasks) == len(verifiers) == 23_310
    assert tasks.keys() == verifiers.keys()
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
        focus = task["provenance"]["focus_tool"]
        assert focus in task["walk"] and focus in added_tool_names
        focused.setdefault(focus, task)
        verifier = verifiers[task["task_id"]]
        assert verifier["deterministic"] is True
        assert "verifier_config_integrity" in verifier["vcode"]
        assert "no_row_deletions" in verifier["vcode"]
        assert "no_collateral_damage" in verifier["vcode"]
    assert set(pack_counts) == {pack["pack_id"] for pack in catalog}

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
        "tables": len(world["tables"]), "seed_packs": len(catalog), "seed_documents": 198,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
