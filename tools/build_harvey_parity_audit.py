#!/usr/bin/env python3
"""Build the evidence-backed Harvey LAB parity and gap audit."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "research" / "repos" / "harveyai@harvey-labs"
WORLD = ROOT / "world" / "blobfish" / "world-v20.json"
INPUT_AUDIT = ROOT / "reports" / "harvey-input-audit.json"
LAB_REPORT = ROOT / "world" / "port" / "determinate" / "lab-report.json"
RETAIL_REPORT = ROOT / "research" / "retail-price-accuracy" / "build-report.json"
HARVEY_RECIPES = ROOT / "research" / "harvey-augmentation" / "recipes"
HARVEY_GENERATED = ROOT / "research" / "harvey-augmentation" / "generated"
HARVEY_SEED_PLAN = ROOT / "research" / "mutation-configs" / "seed-plan.json"
ORACLE_REPORT = ROOT / "data" / "oracle-v20-retail.json"
DISCRIMINATION_REPORT = ROOT / "data" / "discrimination-v20-retail.json"
RECOVERY_ORACLE_REPORT = ROOT / "data" / "oracle-v20-harvey-recovery.json"
RECOVERY_DISCRIMINATION_REPORT = ROOT / "data" / "discrimination-v20-harvey-recovery.json"
JSON_OUT = ROOT / "reports" / "harvey-parity-audit.json"
MD_OUT = ROOT / "docs" / "HARVEY-PARITY-AUDIT.md"
EXPECTED_COMMIT = "7be41d57fd5a6e97b5f246a029e810f83d09cd96"


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text("utf-8"))
    return raw.get("world", raw)


def tracked_files() -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(UPSTREAM), "ls-files", "-z"])
    return [value.decode() for value in raw.split(b"\0") if value]


def parity_rows() -> list[dict[str, str]]:
    return [
        {"area": "Repository bytes and folder tree", "upstream": "63,074 tracked paths", "local": "Exact nested Git mirror at the pinned commit", "status": "exact_copy"},
        {"area": "Task configurations", "upstream": "2,010 task.json files", "local": "All task configs remain byte-identical in the mirror; all 2,010 have an executable world-v20 adapter", "status": "exact_plus_executable"},
        {"area": "Input documents", "upstream": "60,971 physical inputs / 3.207 GB", "local": "Every physical input is present in the exact mirror; 51,683 task-local documents are indexed for executable retrieval", "status": "exact_copy_and_index"},
        {"area": "Office/PDF formats", "upstream": "DOCX/XLSX/PPTX/EML/TXT/JSON; zero PDFs", "local": "All upstream formats copied; synthetic retail extension adds 3 PDF receipts and 4 immutable primary-source PDFs", "status": "exact_plus_extension"},
        {"area": "Generic agent tools", "upstream": "bash, read, write, edit, glob, grep", "local": "Exact harness/tools.py is copied; Harbor file-lane agents retain a shell and document stack, while state work uses 110 visible product tools", "status": "exact_copy_different_operational_surface"},
        {"area": "Document skills", "upstream": "docx, xlsx, pptx skill trees", "local": "Exact skill trees are copied and staged into each file-lane Harbor task", "status": "exact_and_operational"},
        {"area": "Sandbox", "upstream": "LibreOffice/pandoc/parsers image", "local": "Exact sandbox source copied; used as the file-lane agent-image base", "status": "exact_and_operational"},
        {"area": "Evaluation", "upstream": "Criterion-by-criterion LLM judge; all-pass task scoring", "local": "Exact evaluation code copied; operational headline uses deterministic VCode and separate file/state lanes", "status": "exact_copy_alternative_default"},
        {"area": "Gold graders/verifiers", "upstream": "One grader/gold/rubric.json; no per-task deterministic verifier programs", "local": "The one gold file is copied; world v20 ships 2,331 deterministic verifier programs", "status": "exact_plus_extension"},
        {"area": "Firm knowledge", "upstream": "250 tasks over one shared 9,288-file DMS", "local": "All 250 hosted through the indexed shared corpus", "status": "operational_parity"},
        {"area": "Practice tasks", "upstream": "1,760 task-local assignments", "local": "All 1,760 hosted; one task receives the explicit response.md adapter because upstream omitted a filename", "status": "operational_parity_with_disclosed_adapter"},
        {"area": "Harbor format", "upstream": "Not Harbor; custom filesystem harness", "local": "Schema 1.4 task.toml, isolated agent/world containers, MCP, tests/test.sh, solution/solve.sh, and native multi-step [[steps]]", "status": "local_extension"},
        {"area": "Canonical world format", "upstream": "No world/ state model", "local": "Canonical world-v20.json is the runtime source format; harbor/generate.py exports it to Harbor", "status": "local_extension"},
    ]


def gaps() -> list[dict[str, Any]]:
    return [
        {
            "id": "G1",
            "severity": "high",
            "gap": "46,200 of 111,814 practice rubric criteria remain outside the deterministic assertion subset.",
            "impact": "VCode does not replace the upstream LLM judge for all prose quality, legal nuance, completeness, or formatting judgments.",
            "closure": "Run the copied LAB dual-judge lane as a separately reported semantic score, or add source-validated deterministic assertions with oracle and corruption gates.",
        },
        {
            "id": "G2",
            "severity": "high",
            "gap": "The 45 baseline-only state rows are not a completed 51-jurisdiction legal opinion.",
            "impact": "They identify official code portals and an operational floor but deliberately do not assert substantive law, remedies, local overlays, or effective dates.",
            "closure": "Qualified counsel must validate current primary text and applicability for each jurisdiction before deployment; encode each completed review with a version/effective-date pin.",
        },
        {
            "id": "G3",
            "severity": "high",
            "gap": "No receipt, contract term, disclaimer, or control can ensure that the retailer will not be sued.",
            "impact": "A zero-lawsuit guarantee would be misleading; controls reduce frequency, severity, and proof problems but cannot eliminate claims.",
            "closure": "Use accurate-charge prevention, rapid detection/refund, nonwaiver wording, evidence preservation, audits, escalation, and current legal review.",
        },
        {
            "id": "G4",
            "severity": "high",
            "gap": "Frozen v19 external reference-model calibration remains incomplete (856/6,972 episodes) because the pinned account lacked funds.",
            "impact": "Do not publish the partial model result as a completed comparative benchmark or infer model difficulty from deterministic oracle success.",
            "closure": "Fund and resume the exact frozen calibration denominator, or publish a separately versioned replacement protocol.",
        },
        {
            "id": "G5",
            "severity": "medium",
            "gap": "RetailGuard is a synthetic documentation-fixture API, not a conformance-tested mirror of a real retail platform.",
            "impact": "The workflows are executable and realistic, but request/response fidelity cannot be claimed for an external vendor.",
            "closure": "Choose a licensed/public retail API specification or partner sandbox, pin it, and add schema/error/pagination conformance tests.",
        },
        {
            "id": "G6",
            "severity": "medium",
            "gap": "The seven new/adapted tasks were structurally exported to Harbor, but a full 2,331-task Docker/Harbor fleet run was not repeated in this audit.",
            "impact": "Local runtime oracle and discrimination proofs cover all seven new/adapted tasks; container-registry availability and fleet-scale runtime remain separate operational checks.",
            "closure": "Build/publish the v20 world and LAB agent images, run the seven-task Harbor oracle canary, then fan out the full task tree with recorded Harbor version and image digests.",
        },
        {
            "id": "G7",
            "severity": "medium",
            "gap": "The exact upstream mirror contains nine known malformed OOXML XML parts.",
            "impact": "Normalizing them would destroy byte identity; some parsers require the exact-hash recovery path.",
            "closure": "Keep the immutable source, exact-hash allowlist, recovery copies, and separate normalized derivatives. Fail on any hash or defect-count drift.",
        },
        {
            "id": "G8",
            "severity": "medium",
            "gap": "Deterministic anchors do not fully grade visual polish, tracked-change semantics, formula correctness after every application, or professional legal judgment.",
            "impact": "An output can satisfy anchors while remaining stylistically weak or legally incomplete.",
            "closure": "Add OOXML semantic checks, formula recalculation, render comparisons, and the copied LAB judge as independent channels; never average away lane disagreement.",
        },
        {
            "id": "G9",
            "severity": "low",
            "gap": "The repository root intentionally does not reproduce Harvey's top-level layout.",
            "impact": "Only research/repos/harveyai@harvey-labs is an exact upstream tree; root world/mcp/harbor/research additions are local architecture.",
            "closure": "Use the nested mirror for byte/folder parity and the generated Harbor tree for runnable task parity; do not describe the repository root as an upstream clone.",
        },
        {
            "id": "G10",
            "severity": "low",
            "gap": "Upstream contains no PDF inputs, so there is nothing upstream to copy in that format.",
            "impact": "Claims that Harvey PDFs were copied would be false.",
            "closure": "Keep the zero-PDF audit fact. Add only clearly labeled synthetic or provenance-tracked public reference PDFs in separate extension lanes.",
        },
        {
            "id": "G11",
            "severity": "medium",
            "gap": "Four strict Harvey derivative tasks and 19 broad seeded variants are generator/harness assets, not separately admitted v20 state workflows.",
            "impact": "They are reproducible task/document expansions, but they do not yet receive a distinct world task ID, product-state verifier, oracle, discrimination result, and Harbor package.",
            "closure": "Index each derivative evidence set, compile its changed rubric facts, then require world admission, file/state lane agreement, oracle, corruption probes, and Harbor canary before counting it in the 2,331-task world total.",
        },
    ]


def build_payload() -> dict[str, Any]:
    commit = command("git", "-C", str(UPSTREAM), "rev-parse", "HEAD")
    status = command("git", "-C", str(UPSTREAM), "status", "--porcelain")
    files = tracked_files()
    top_level = Counter(path.split("/", 1)[0] for path in files)
    task_configs = [path for path in files if path.startswith("tasks/") and path.endswith("/task.json")]
    grader_files = [path for path in files if "/grader/" in path or "/verifier" in path]
    input_audit = json.loads(INPUT_AUDIT.read_text("utf-8"))
    lab = json.loads(LAB_REPORT.read_text("utf-8"))
    retail = json.loads(RETAIL_REPORT.read_text("utf-8"))
    seed_plan = json.loads(HARVEY_SEED_PLAN.read_text("utf-8"))
    world = load(WORLD)
    oracle = json.loads(ORACLE_REPORT.read_text("utf-8"))
    discrimination = json.loads(DISCRIMINATION_REPORT.read_text("utf-8"))
    recovery_oracle = json.loads(RECOVERY_ORACLE_REPORT.read_text("utf-8"))
    recovery_discrimination = json.loads(RECOVERY_DISCRIMINATION_REPORT.read_text("utf-8"))
    contract_files = sorted((ROOT / "mcp" / "v4" / "contracts").glob("*.json"))
    contracts = [json.loads(path.read_text("utf-8")) for path in contract_files]
    visible = sum(tool.get("agent_visible") is not False for contract in contracts for tool in contract.get("tools") or [])
    internal = sum(tool.get("agent_visible") is False for contract in contracts for tool in contract.get("tools") or [])
    retail_sources = json.loads((ROOT / "research" / "retail-price-accuracy" / "sources" / "manifest.json").read_text("utf-8"))
    payload = {
        "schema_version": 1,
        "audit_date": "2026-08-22",
        "scope": "Harvey LAB exact-copy, executable-port, Harbor, document, verifier, tool, mutation, and retail-research parity",
        "upstream": {
            "repository": "https://github.com/harveyai/harvey-labs",
            "commit": commit,
            "expected_commit": EXPECTED_COMMIT,
            "mirror_clean": status == "",
            "tracked_paths": len(files),
            "top_level_tracked_paths": dict(sorted(top_level.items())),
            "task_configs": len(task_configs),
            "practice_tasks": 1760,
            "firm_knowledge_tasks": 250,
            "physical_inputs": input_audit["physical_inputs"],
            "input_bytes": input_audit["physical_input_bytes"],
            "input_extensions": input_audit["extensions"],
            "pdf_inputs": input_audit["format_validation"]["pdfs_checked"],
            "generic_tools": ["bash", "read", "write", "edit", "glob", "grep"],
            "grader_or_verifier_paths": grader_files,
            "known_ooxml_source_defects": input_audit["known_source_defects"]["count"],
            "license": "MIT",
        },
        "local": {
            "exact_mirror_path": str(UPSTREAM.relative_to(ROOT)),
            "world": str(WORLD.relative_to(ROOT)),
            "world_version": world["version"],
            "tasks": len(world["tasks"]),
            "verifiers": len(world["verifiers"]),
            "tables": len(world["tables"]),
            "seed_rows": sum(len(table.get("sample_rows") or []) for table in world["tables"]),
            "contract_systems": len(contracts),
            "agent_visible_tools": visible,
            "internal_operations": internal,
            "harvey_tasks_hosted": 2010,
            "harvey_tasks_total": 2010,
            "harvey_adapter_tasks": 1,
            "practice_criteria_total": lab["criteria"],
            "practice_criteria_determinized": lab["criteria_determinate"],
            "practice_criteria_residual": lab["criteria"] - lab["criteria_determinate"],
            "retail_tasks": 6,
            "strict_harvey_derivative_recipes": len(list(HARVEY_RECIPES.glob("*.json"))),
            "strict_harvey_generated_tasks": len(list(HARVEY_GENERATED.glob("tasks/**/task.json"))),
            "broad_harvey_seed_families": len(seed_plan["variants"]),
            "broad_harvey_seed_variants": sum(len(row["seeds"]) for row in seed_plan["variants"]),
            "retail_input_documents": retail["documents"],
            "retail_reference_pdfs": len(retail_sources["files"]),
            "jurisdictions": retail["jurisdictions"],
            "jurisdictions_primary_source_triaged": len(retail["primary_source_triaged_jurisdictions"]),
            "jurisdictions_pending_substantive_validation": retail["pending_substantive_validation_jurisdictions"],
            "retail_oracle": {key: oracle[key] for key in ("total", "passed", "pass_rate")},
            "retail_discrimination_failures": len(discrimination["summary"]["discrimination_failures"]),
            "harvey_recovery_oracle": {key: recovery_oracle[key] for key in ("total", "passed", "pass_rate")},
            "harvey_recovery_discrimination_failures": len(recovery_discrimination["summary"]["discrimination_failures"]),
            "harbor": {
                "schema_version": "1.4",
                "source_format": "custom canonical world JSON",
                "export_format": "one Harbor task directory per world task",
                "validated_new_task_exports": 7,
                "native_multistep_retail_task_steps": 4,
            },
        },
        "parity_matrix": parity_rows(),
        "open_gaps": gaps(),
        "answers": {
            "same_folder_structure": "Yes inside the exact nested Harvey mirror; no at repository root, intentionally.",
            "world_is_harbor_format": "The canonical world JSON is not Harbor. harbor/generate.py exports schema-1.4 Harbor task directories; the selected v20 export was structurally validated.",
            "all_harvey_documents_copied": "Yes: 60,971/60,971 physical input files are in the clean pinned mirror. Upstream contains zero PDF inputs.",
            "all_harvey_tasks_hosted": "Yes in world v20: 2,010/2,010, with one disclosed response.md output-contract adapter and no upstream source edit.",
            "can_create_more_tasks": "Yes: six executable retail workflows and three matched document scenarios demonstrate the pattern.",
            "can_research_online": "Yes, with primary-source and rights gates; four official/public reference PDFs are pinned in the retail source manifest.",
            "can_mutate_documents": "Yes, in a separate synthetic derivative tree with identical structure, hashes, manifests, and visual PDF review; never overwrite the exact source mirror.",
        },
    }
    assert commit == EXPECTED_COMMIT and status == ""
    assert payload["upstream"]["task_configs"] == 2010
    assert payload["upstream"]["tracked_paths"] == 63074
    assert payload["upstream"]["physical_inputs"] == 60971
    assert visible == 110 and internal == 11
    return payload


def markdown(payload: dict[str, Any]) -> str:
    upstream = payload["upstream"]
    local = payload["local"]
    parity = "\n".join(
        f"| {row['area']} | {row['upstream']} | {row['local']} | `{row['status']}` |"
        for row in payload["parity_matrix"]
    )
    gap_rows = "\n".join(
        f"| {row['id']} | {row['severity']} | {row['gap']} | {row['closure']} |"
        for row in payload["open_gaps"]
    )
    return f"""# Harvey LAB parity and gap audit

Audit date: {payload['audit_date']}  
Upstream: `harveyai/harvey-labs@{upstream['commit']}`

## Executive answer

The exact Harvey repository is copied at
`research/repos/harveyai@harvey-labs`: it is a clean nested Git checkout at the
pinned commit with all **{upstream['tracked_paths']:,} tracked paths**, all
**{upstream['task_configs']:,} task configurations**, and all
**{upstream['physical_inputs']:,} physical input files**
({upstream['input_bytes']:,} bytes). The upstream corpus contains **zero PDF
inputs**; the audit therefore does not make the false claim that Harvey PDFs
were copied.

World v20 operationally hosts **2,010/2,010 Harvey tasks**. The only prior miss
had 15 intact inputs and 74 criteria but no output filename; v20 adds the
disclosed `response.md` adapter without editing the upstream task. World v20
then adds six executable retail-compliance tasks, producing **{local['tasks']:,}
tasks and {local['verifiers']:,} deterministic verifiers** over
{local['agent_visible_tools']} visible tools, {local['internal_operations']}
internal operations, {local['contract_systems']} systems, and
{local['tables']} state tables.

The folder-format answer has two parts:

- **Exact folder parity:** yes, inside the nested Harvey mirror.
- **Repository-root parity:** no, intentionally; this project adds
  `world/`, `mcp/`, `harbor/`, research, and verifier architecture.
- **Harbor:** Harvey LAB itself is not Harbor. The canonical world JSON is not
  Harbor either. `harbor/generate.py` exports real Harbor schema 1.4 task
  directories with isolated agent/world containers, MCP, `tests/test.sh`,
  `solution/solve.sh`, mounted inputs, artifacts, and native multi-step tasks.

## Measured inventory

| Measure | Harvey LAB | Local v20 |
| --- | ---: | ---: |
| Task configs / hosted Harvey tasks | {upstream['task_configs']:,} | {local['harvey_tasks_hosted']:,}/{local['harvey_tasks_total']:,} |
| Total executable tasks | — | {local['tasks']:,} |
| Physical upstream inputs | {upstream['physical_inputs']:,} | {upstream['physical_inputs']:,} exact-mirror copies |
| Input bytes | {upstream['input_bytes']:,} | same exact bytes |
| Generic / visible product tools | 6 | {local['agent_visible_tools']} + {local['internal_operations']} internal |
| Per-task deterministic verifiers | 0 | {local['verifiers']:,} |
| Practice criteria determinized | — | {local['practice_criteria_determinized']:,}/{local['practice_criteria_total']:,} |
| Retail scenarios / inputs | — | 3 / {local['retail_input_documents']} |
| Strict Harvey derivative tasks | — | {local['strict_harvey_generated_tasks']} from {local['strict_harvey_derivative_recipes']} recipes |
| Broad seeded Harvey variants | — | {local['broad_harvey_seed_variants']} across {local['broad_harvey_seed_families']} task families |
| 50 states + D.C. rows | — | {local['jurisdictions']} |
| Primary-source-triaged / research queue | — | {local['jurisdictions_primary_source_triaged']} / {local['jurisdictions_pending_substantive_validation']} |
| Retail oracle | — | {local['retail_oracle']['passed']}/{local['retail_oracle']['total']} |
| Retail bad-path leaks | — | {local['retail_discrimination_failures']} across no-op/text-only/blind-write/wrong-value |
| Recovered Harvey task oracle / bad-path leaks | — | {local['harvey_recovery_oracle']['passed']}/{local['harvey_recovery_oracle']['total']} / {local['harvey_recovery_discrimination_failures']} |

Upstream input format counts:

| Extension | Files | Bytes |
| --- | ---: | ---: |
{chr(10).join(f"| `{ext}` | {values['files']:,} | {values['bytes']:,} |" for ext, values in sorted(upstream['input_extensions'].items()))}

## Exact copy versus executable implementation

| Area | Harvey LAB | This repository | Status |
| --- | --- | --- | --- |
{parity}

## Retail case correction and task design

The prompt's Walmart example conflates multiple matters. `Rector v. Walmart`
alleges shelf/register mismatches in D.C.; `Kahn v. Walmart` concerns alleged
scanner-price discrepancies; the $45 million `Kukorinis` settlement concerned
weighted goods and bagged citrus in the Middle District of Florida—not a
California self-checkout double-charge settlement. California separately
reported checkout-price and price/weight enforcement resolutions.

The new environment therefore models the legal work without encoding the
conflation as fact:

1. evidence preservation and incident audit;
2. transaction-level exposure and jurisdiction-gated refunds;
3. a candid 50-state-plus-D.C. research matrix;
4. receipt and policy redlines with statutory-rights savings language;
5. duplicate-scan, price-sync, and weight-control implementation plus retest;
6. a four-checkpoint national closeout matter.

The three scenario packs (CA, MI, D.C.) have the same five filenames, DOCX
heading topology, XLSX sheet/column topology, and two-page receipt layout.
Facts and answers change, not the file-reading structure. All receipt pages
were rendered and visually inspected. Four immutable primary-source PDFs have
URL, retrieval date, and SHA-256 records in `sources/manifest.json`.

## All currently identified gaps

These are not hidden behind the word “parity.”

| ID | Severity | Gap | Required closure |
| --- | --- | --- | --- |
{gap_rows}

## What “copy all tools and verifiers” means here

Every upstream tool, judge, scoring, sandbox, skill, test, and utility source
file is present in the exact mirror. Harvey has six generic filesystem tools
and LLM-judge scoring; it does **not** provide 2,010 deterministic verifier
programs to copy. The local product tools and VCodes are additions. Describing
them as verbatim Harvey tools or verifiers would be inaccurate.

## Reproduction and gates

```bash
python3 tools/audit_harvey_inputs.py --check
python3 world/port/lab_determinize.py --check
python3 tools/build_retail_price_accuracy_pack.py
python3 tools/build_retail_price_accuracy_pack.py --check
python3 world/v20/build.py
python3 tools/check_v20_retail.py
python3 tools/check_harbor_file_lane.py
python3 tools/build_harvey_parity_audit.py --check
```

The machine-readable companion is `reports/harvey-parity-audit.json`.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = markdown(payload)
    if args.check:
        for path, expected in ((JSON_OUT, json_text), (MD_OUT, md_text)):
            if not path.is_file() or path.read_text("utf-8") != expected:
                print(f"stale audit artifact: {path.relative_to(ROOT)}", file=sys.stderr)
                return 2
        print("Harvey parity audit artifacts are current")
        return 0
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json_text, "utf-8")
    MD_OUT.write_text(md_text, "utf-8")
    print(json.dumps({
        "upstream_tasks": payload["upstream"]["task_configs"],
        "hosted_tasks": payload["local"]["harvey_tasks_hosted"],
        "physical_inputs": payload["upstream"]["physical_inputs"],
        "open_gaps": len(payload["open_gaps"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
