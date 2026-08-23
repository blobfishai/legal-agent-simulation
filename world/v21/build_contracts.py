#!/usr/bin/env python3
"""Build v5 product contracts with exactly 1,100 visible executable tools.

V5 is a mechanical copy of v4 plus 22 CounselOps documentation-fixture
systems.  Every added operation uses a generic SQLite-backed runtime kind and
is therefore executable, not a schema-only placeholder.
"""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import json
import shutil
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from world.v21.catalog import (
    DOMAIN_RESOURCES,
    JURISDICTIONS,
    OPERATIONS,
    OWNERS,
    RISK_LEVELS,
    resource_label,
    table_name,
    tool_name,
)

SOURCE = ROOT / "mcp" / "v4"
DEFAULT_OUTPUT = ROOT / "mcp" / "v5"
FIXED_TIME = "2026-08-22T12:00:00Z"

COLUMNS = [
    {"name": "id", "type": "INTEGER", "pk": True},
    {"name": "external_key", "type": "TEXT"},
    {"name": "matter_ref", "type": "TEXT"},
    {"name": "jurisdiction", "type": "TEXT"},
    {"name": "status", "type": "TEXT"},
    {"name": "title", "type": "TEXT"},
    {"name": "summary", "type": "TEXT"},
    {"name": "owner", "type": "TEXT"},
    {"name": "due_date", "type": "TEXT"},
    {"name": "risk_level", "type": "TEXT"},
    {"name": "amount", "type": "REAL"},
    {"name": "version", "type": "INTEGER"},
    {"name": "source_pack", "type": "TEXT"},
    {"name": "updated_at", "type": "TEXT"},
]


def seed_rows(domain: dict, resource: str) -> list[dict[str, Any]]:
    rows = []
    label = resource_label(resource)
    for index in range(1, 9):
        pack_variant = ((index - 1) % 3) + 1
        external_key = f"{domain['prefix'].upper()}-{resource.upper()}-{index:03d}"
        source_pack = f"pack-{domain['key']}-{pack_variant:02d}"
        rows.append({
            "id": index,
            "external_key": external_key,
            "matter_ref": f"MAT-{domain['prefix'].upper()}-{index:04d}",
            "jurisdiction": JURISDICTIONS[index - 1],
            "status": "open" if index == 1 else ("review" if index % 2 else "pending"),
            "title": f"{domain['label']} - {label} Record {index:03d}",
            "summary": (
                f"{source_pack} | ANCHOR-{external_key} | synthetic {label.lower()} "
                "fact pattern; attorney validation required before external use."
            ),
            "owner": OWNERS[index - 1],
            "due_date": f"2026-{9 + ((index - 1) // 4):02d}-{5 + index:02d}",
            "risk_level": RISK_LEVELS[(index - 1) % len(RISK_LEVELS)],
            "amount": float(12500 + index * 1375),
            "version": index,
            "source_pack": source_pack,
            "updated_at": FIXED_TIME,
        })
    return rows


def params(*, write: bool = False) -> dict[str, str]:
    base = {
        "external_key": "string", "matter_ref": "string", "jurisdiction": "string",
        "status": "string", "title": "string", "summary": "string", "owner": "string",
        "due_date": "string", "risk_level": "string", "amount": "number",
        "version": "integer", "source_pack": "string", "updated_at": "string",
    }
    if write:
        return base
    return {"status": "string", "jurisdiction": "string", "risk_level": "string",
            "owner": "string", "limit": "integer", "offset": "integer"}


def build_tools(domain: dict, resource: str) -> list[dict[str, Any]]:
    table = table_name(domain, resource)
    label = resource_label(resource)
    product = f"CounselOps {domain['label']}"
    common = (
        f"Synthetic documentation-fixture operation for {domain['label'].lower()} "
        f"{label.lower()} records; modeled on ordinary legal-operations workflow semantics."
    )
    required = [
        "external_key", "matter_ref", "jurisdiction", "status", "title", "summary",
        "owner", "due_date", "risk_level", "amount", "version", "source_pack",
    ]
    create_args = {
        "external_key": f"CONF-{domain['prefix'].upper()}-{resource.upper()}-001",
        "matter_ref": f"MAT-{domain['prefix'].upper()}-0001", "jurisdiction": "CA",
        "status": "draft", "title": f"Conformance {label}",
        "summary": "Synthetic conformance record; attorney validation required.",
        "owner": "legal-operations", "due_date": "2026-09-30", "risk_level": "medium",
        "amount": 1000.0, "version": 1, "source_pack": f"pack-{domain['key']}-01",
    }
    return [
        {
            "name": tool_name(domain, resource, "list"),
            "mirrors": f"{product} synthetic {label} collection",
            "description": f"List {label.lower()} with deterministic filters and pagination. {common}",
            "op": {"kind": "list", "table": table,
                   "filters": ["status", "jurisdiction", "risk_level", "owner"],
                   "default_order": "id"},
            "params": params(), "conformance_args": {"status": "open", "limit": 20},
        },
        {
            "name": tool_name(domain, resource, "get"),
            "mirrors": f"{product} synthetic {label} detail",
            "description": f"Get one complete {label.lower()} record by integer id. {common}",
            "op": {"kind": "get", "table": table},
            "params": {"id": "integer"}, "conformance_args": {"id": 1},
        },
        {
            "name": tool_name(domain, resource, "search"),
            "mirrors": f"{product} synthetic {label} search",
            "description": f"Search {label.lower()} keys, titles, summaries, matters, and source packs. {common}",
            "op": {"kind": "search", "table": table,
                   "fields": ["external_key", "matter_ref", "title", "summary", "source_pack"],
                   "preview": ["summary"]},
            "params": {"query": "string", "limit": "integer", "offset": "integer"},
            "conformance_args": {"query": f"pack-{domain['key']}-01", "limit": 20},
        },
        {
            "name": tool_name(domain, resource, "create"),
            "mirrors": f"{product} synthetic {label} filing workflow",
            "description": f"Create a fully attributed {label.lower()} record. {common}",
            "op": {"kind": "create", "table": table, "required": required,
                   "defaults": {"updated_at": FIXED_TIME}},
            "params": params(write=True), "conformance_args": create_args,
        },
        {
            "name": tool_name(domain, resource, "update"),
            "mirrors": f"{product} synthetic {label} change-control workflow",
            "description": f"Update an existing {label.lower()} record with explicit change fields. {common}",
            "op": {"kind": "update", "table": table,
                   "allowed": [column["name"] for column in COLUMNS if column["name"] != "id"]},
            "params": {"id": "integer", **params(write=True)},
            "conformance_args": {"id": 1, "status": "review", "version": 2,
                                 "updated_at": FIXED_TIME},
        },
    ]


def build_contract(domain: dict) -> dict[str, Any]:
    tables = []
    tools = []
    for resource in domain["resources"]:
        tables.append({
            "name": table_name(domain, resource),
            "columns": COLUMNS,
            "seed": {"rows": seed_rows(domain, resource)},
        })
        tools.extend(build_tools(domain, resource))
    assert len(tables) == 9 and len(tools) == 45
    return {
        "$schema": "lawfirm-qwen.mcp-contract.v5",
        "system": f"counselops-{domain['key']}-v21",
        "product": f"CounselOps {domain['label']} (SIMULATED)",
        "provenance": (
            "Synthetic documentation fixture modeled on common legal-operations resource and "
            "change-control patterns; no commercial API conformance or legal conclusion is claimed."
        ),
        "tables": tables,
        "tools": tools,
    }


def count_contracts(contracts_dir: Path) -> dict[str, int]:
    totals = {"contracts": 0, "tables": 0, "tools": 0, "visible_tools": 0, "internal_tools": 0}
    for path in sorted((contracts_dir / "contracts").glob("*.json")):
        if path.name.startswith("_"):
            continue
        contract = json.loads(path.read_text("utf-8"))
        totals["contracts"] += 1
        totals["tables"] += len(contract["tables"])
        totals["tools"] += len(contract["tools"])
        totals["visible_tools"] += sum(tool.get("agent_visible") is not False for tool in contract["tools"])
        totals["internal_tools"] += sum(tool.get("agent_visible") is False for tool in contract["tools"])
    return totals


def build(output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(SOURCE, output)
    systems = json.loads((SOURCE / "systems.json").read_text("utf-8"))
    systems["note"] = (
        "V5 preserves v4 exactly and adds 22 executable CounselOps documentation-fixture "
        "systems. Added surfaces make no commercial-vendor conformance claim."
    )
    for domain in DOMAIN_RESOURCES:
        contract = build_contract(domain)
        filename = f"counselops-{domain['key']}.json"
        (output / "contracts" / filename).write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", "utf-8"
        )
        systems["systems"][f"counselops-{domain['key']}"] = {
            "product": contract["product"],
            "description": (
                f"Nine {domain['label'].lower()} resource registries with list, get, search, "
                "create, and update operations. Synthetic documentation fixture."
            ),
            "tools": [tool["name"] for tool in contract["tools"]],
        }
    (output / "systems.json").write_text(json.dumps(systems, indent=2, sort_keys=True) + "\n", "utf-8")
    totals = count_contracts(output)
    if totals != {"contracts": 32, "tables": 254, "tools": 1111,
                  "visible_tools": 1100, "internal_tools": 11}:
        raise SystemExit(f"unexpected v5 totals: {totals}")
    report = {
        "schema_version": 1,
        "source": str(SOURCE.relative_to(ROOT)),
        "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
        "added_systems": 22,
        "added_tables": 198,
        "added_visible_tools": 990,
        **totals,
    }
    (output / "build-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
