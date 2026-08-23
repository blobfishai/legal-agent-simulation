#!/usr/bin/env python3
"""Static integrity gate for world v20 and its retail evidence pack."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harbor import generate as harbor_generate  # noqa: E402
from world.local.v2runtime import V2Runtime  # noqa: E402


CANONICAL_WORLD_PATH = ROOT / "world" / "blobfish" / "world-v20.json"
DRAFT_WORLD_PATH = ROOT / "world" / "blobfish" / "world-v20-draft.json"
CANONICAL_REPORT_PATH = ROOT / "world" / "v20" / "build-report.json"
REALWORLD_REPORT_PATH = ROOT / "world" / "v20" / "realworld-build-report.json"
CONTRACTS = ROOT / "mcp" / "v4" / "contracts"
RETAIL_ROOT = ROOT / "research" / "retail-price-accuracy"
RETAIL_TASK_IDS = {
    "task_v20_retail_incident_audit",
    "task_v20_retail_refund_exposure",
    "task_v20_retail_51_jurisdiction_triage",
    "task_v20_retail_receipt_redline",
    "task_v20_retail_control_remediation",
    "task_v20_retail_national_closeout",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    canonical_raw = json.loads(CANONICAL_WORLD_PATH.read_text("utf-8"))
    canonical = canonical_raw.get("world", canonical_raw)
    canonical_report = json.loads(CANONICAL_REPORT_PATH.read_text("utf-8"))
    assert len(canonical["tasks"]) == len(canonical["verifiers"]) == 2331
    assert canonical_report["total_tasks"] == canonical_report["total_verifiers"] == 2331
    assert hashlib.sha256(CANONICAL_WORLD_PATH.read_bytes()).hexdigest() == canonical_report["world_sha256"]

    raw = json.loads(DRAFT_WORLD_PATH.read_text("utf-8"))
    world = raw.get("world", raw)
    report = json.loads(REALWORLD_REPORT_PATH.read_text("utf-8"))
    assert world["version"] == 20
    assert world["world_id"] == "legal-agent-simulation-world-v20-draft"
    assert len(world["tasks"]) == len(world["verifiers"]) == 2347
    assert len({task["task_id"] for task in world["tasks"]}) == 2347
    assert {verifier["task_id"] for verifier in world["verifiers"]} == {
        task["task_id"] for task in world["tasks"]
    }
    assert report["total_tasks"] == 2347
    assert report["harvey_lab_tasks_hosted"] == report["harvey_lab_source_tasks"] == 2010

    tasks = {task["task_id"]: task for task in world["tasks"]}
    verifiers = {verifier["task_id"]: verifier for verifier in world["verifiers"]}
    assert RETAIL_TASK_IDS <= tasks.keys()
    assert RETAIL_TASK_IDS <= verifiers.keys()
    recovered = [
        task for task in world["tasks"]
        if (task.get("provenance") or {}).get("adapter_output_contract") == "response.md"
    ]
    assert len(recovered) == 1
    assert recovered[0]["task_id"] == "labp_b50165c2a9cd39db"
    assert recovered[0]["file_lane"]["deliverables"] == ["response.md"]
    recovered_source = ROOT / recovered[0]["file_lane"]["documents_source"]
    assert len([path for path in recovered_source.iterdir() if path.is_file()]) == 15
    assert world["lab_practice_recovery"]["source_task_unchanged"] is True

    practice_sources = {
        (task.get("file_lane") or {}).get("source_task")
        for task in world["tasks"]
        if (task.get("file_lane") or {}).get("source_commit") == "7be41d57fd5a"
    }
    practice_sources.discard(None)
    firm_sources = {
        (task.get("provenance") or {}).get("path")
        for task in world["tasks"]
        if task.get("method") == "harvey_lab_firm_knowledge_deterministic"
    }
    firm_sources.discard(None)
    assert len(practice_sources) == 1760
    assert len(firm_sources) == 250

    runtime = V2Runtime(str(CONTRACTS))
    assert len(runtime.tools) == 121
    assert len(runtime.mcp_tools()) == 110
    assert len([name for name in runtime.tools if name.startswith("retail_")]) == 19
    assert len(runtime.tables) == 56
    retail_contract = json.loads((CONTRACTS / "retail-compliance.json").read_text("utf-8"))
    retail_table_names = {table["name"] for table in retail_contract["tables"]}
    assert len(retail_table_names) == 9
    world_tables = {table["name"]: table for table in world["tables"]}
    assert retail_table_names <= world_tables.keys()
    seeds = json.loads((RETAIL_ROOT / "seed-data.json").read_text("utf-8"))["tables"]
    for source in retail_contract["tables"]:
        name = source["name"]
        assert world_tables[name]["columns"] == source["columns"]
        assert world_tables[name]["sample_rows"] == seeds[name]
        ids = [row["id"] for row in seeds[name]]
        assert len(ids) == len(set(ids))
    rules = seeds["rc_jurisdiction_rules"]
    assert len(rules) == 51
    assert len({row["jurisdiction_code"] for row in rules}) == 51
    assert sum(row["research_status"] == "primary_source_triaged" for row in rules) == 6
    assert sum(row["research_status"] == "official_portal_identified_not_substantively_validated" for row in rules) == 45
    assert all(row["attorney_validation_required"] == 1 for row in rules)

    visible_tools = set(runtime.tools)
    exercised_retail_tools: set[str] = set()
    for task_id in RETAIL_TASK_IDS:
        task = tasks[task_id]
        assert set(task["required_tools"]) <= visible_tools
        exercised_retail_tools.update(
            name for name in task["required_tools"] if name.startswith("retail_")
        )
        assert task["file_lane"]["grading"] == "determinate"
        source = ROOT / task["file_lane"]["documents_source"]
        assert source.is_dir()
        assert sorted(path.name for path in source.iterdir() if path.is_file()) == [
            "checkout-event-log.xlsx",
            "customer-price-accuracy-policy.docx",
            "incident-report.docx",
            "jurisdiction-source-register.xlsx",
            "sample-receipts.pdf",
        ]
        assert verifiers[task_id]["vcode"].startswith('"""Generated deterministic verifier')
    assert exercised_retail_tools == {
        name for name in runtime.tools if name.startswith("retail_")
    }
    assert len(tasks["task_v20_retail_national_closeout"]["multi_step"]["phases"]) == 4
    assert set(verifiers["task_v20_retail_national_closeout"]["phase_vcodes"]) == {
        "01-evidence-and-preservation",
        "02-legal-triage",
        "03-refunds-policy-and-wording",
        "04-controls-and-closeout",
    }

    manifests = [
        RETAIL_ROOT / "scenarios" / "ca-price-weight-duplicate-scan-v1" / "manifest.json",
        RETAIL_ROOT / "mutations" / "mi-price-weight-duplicate-scan-v1" / "manifest.json",
        RETAIL_ROOT / "mutations" / "dc-price-weight-duplicate-scan-v1" / "manifest.json",
    ]
    parsed = [json.loads(path.read_text("utf-8")) for path in manifests]
    assert all(row["structure_signature"] == parsed[0]["structure_signature"] for row in parsed)
    assert parsed[0]["structure_signature"]["pdf_pages"] == {"sample-receipts.pdf": 2}
    for manifest_path, manifest in zip(manifests, parsed):
        documents = manifest_path.parent / "documents"
        for record in manifest["files"]:
            path = documents / record["path"]
            assert path.stat().st_size == record["bytes"]
            assert sha256(path) == record["sha256"]

    source_manifest = json.loads((RETAIL_ROOT / "sources" / "manifest.json").read_text("utf-8"))
    for record in source_manifest["files"]:
        path = RETAIL_ROOT / "sources" / record["path"]
        assert path.is_file() and path.read_bytes().startswith(b"%PDF")
        assert sha256(path) == record["sha256"]

    assert harbor_generate.contracts_for_world(str(CANONICAL_WORLD_PATH)) == str(CONTRACTS)
    assert harbor_generate.contracts_for_world(str(DRAFT_WORLD_PATH)) == str(CONTRACTS)
    assert harbor_generate.contract_tool_count(str(CONTRACTS)) == 110
    assert hashlib.sha256(DRAFT_WORLD_PATH.read_bytes()).hexdigest() == report["world_sha256"]
    print(
        "v20 retail gate: 2331 canonical + 16 real-world = 2347 merged draft; "
        "Harvey 2010/2010; "
        "110 tools (19 RetailGuard); 51 jurisdictions; 15 matched input documents"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
