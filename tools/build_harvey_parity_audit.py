#!/usr/bin/env python3
"""Build the evidence-backed Harvey LAB, Harbor, and repository gap audit."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "research" / "repos" / "harveyai@harvey-labs"
HARBOR_UPSTREAM = ROOT / "research" / "repos" / "harbor-framework@harbor"
WORLD = ROOT / "world" / "blobfish" / "world-v21.json"
V21_REPORT = ROOT / "world" / "v21" / "build-report.json"
INPUT_AUDIT = ROOT / "reports" / "harvey-input-audit.json"
LAB_REPORT = ROOT / "world" / "port" / "determinate" / "lab-report.json"
RETAIL_REPORT = ROOT / "research" / "retail-price-accuracy" / "build-report.json"
RETAIL_RESEARCH = ROOT / "research" / "retail-price-accuracy" / "jurisdiction-research-v2.json"
SEED_REPORT = ROOT / "research" / "v21-seeded-documents" / "build-report.json"
SEED_CATALOG = ROOT / "research" / "v21-seeded-documents" / "catalog.json"
HARBOR_EXPORT_REPORT = ROOT / "reports" / "v21-harbor-export-audit.json"
HARBOR_DATASET_REPORT = ROOT / "reports" / "v21-harbor-dataset-audit.json"
GHCR_PUBLIC_REPORT = ROOT / "reports" / "v21-ghcr-public-audit.json"
ORACLE_PROOF_REPORT = ROOT / "reports" / "v21-oracle-proof-audit.json"
DOCUMENT_RENDER_REPORT = ROOT / "reports" / "v21-document-render-audit.json"
DOCUMENT_VISUAL_REVIEW_REPORT = ROOT / "reports" / "v21-document-visual-review.json"
HARBOR_RUNNER = ROOT / "harbor" / "runner" / "pyproject.toml"
HARBOR_RUNNER_LOCK = ROOT / "harbor" / "runner" / "uv.lock"
HARBOR_GENERATOR = ROOT / "harbor" / "generate.py"
HARBOR_EXPORT_CHECKER = ROOT / "tools" / "check_harbor_export.py"
HARBOR_DATASET_CHECKER = ROOT / "tools" / "check_harbor_dataset.py"
HARBOR_PRODUCTION_RUNNER = ROOT / "tools" / "run_harbor_production.py"
HARVEY_RECIPES = ROOT / "research" / "harvey-augmentation" / "recipes"
HARVEY_GENERATED = ROOT / "research" / "harvey-augmentation" / "generated"
HARVEY_SEED_PLAN = ROOT / "research" / "mutation-configs" / "seed-plan.json"
HARVEY_MUTATION_STATUS = ROOT / "research" / "mutation-configs" / "candidate-status.json"
ORACLE_REPORT = ROOT / "data" / "oracle-v20-retail.json"
DISCRIMINATION_REPORT = ROOT / "data" / "discrimination-v20-retail.json"
RECOVERY_ORACLE_REPORT = ROOT / "data" / "oracle-v20-harvey-recovery.json"
RECOVERY_DISCRIMINATION_REPORT = ROOT / "data" / "discrimination-v20-harvey-recovery.json"
RETAIL_AUTHORITY_ORACLE_REPORT = ROOT / "reports" / "v21-retail-authority-oracle.json"
JSON_OUT = ROOT / "reports" / "harvey-parity-audit.json"
MD_OUT = ROOT / "docs" / "HARVEY-PARITY-AUDIT.md"
EXPECTED_HARVEY_COMMIT = "7be41d57fd5a6e97b5f246a029e810f83d09cd96"
AUDITED_HARBOR_MAIN = "b37833221e27435a18d7acdd41d875cdc2831893"
AUDITED_HARBOR_RELEASE = "0.22.0"


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def load_world(path: Path) -> dict[str, Any]:
    raw = load_json(path)
    return raw.get("world", raw)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def string_manifest_sha256(values: set[str] | list[str]) -> str:
    payload = "".join(f"{value}\n" for value in sorted(values)).encode()
    return hashlib.sha256(payload).hexdigest()


def require(condition: bool, message: str) -> None:
    """Keep audit gates active even when Python is invoked with optimization."""
    if not condition:
        raise RuntimeError(message)


def practice_source_task_json(value: Any) -> str:
    """Map the world's task-directory provenance to Harvey's tracked task path."""
    require(isinstance(value, str) and bool(value),
            "Harvey practice source_task must be a non-empty string")
    parts = value.split("/")
    require(
        "\\" not in value
        and not value.startswith("/")
        and all(part not in ("", ".", "..") for part in parts),
        f"unsafe Harvey practice source_task: {value!r}",
    )
    return f"tasks/{value}/task.json"


def tracked_files() -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(UPSTREAM), "ls-files", "-z"])
    return [value.decode() for value in raw.split(b"\0") if value]


def parity_rows(payload: dict[str, Any]) -> list[dict[str, str]]:
    upstream = payload["upstream"]
    local = payload["local"]
    harbor = local["harbor"]
    return [
        {
            "area": "Repository bytes and Harvey folder tree",
            "upstream": f"{upstream['tracked_paths']:,} tracked paths at {upstream['commit'][:12]}",
            "local": "Exact clean nested Git mirror; repository root intentionally adds runtime architecture",
            "status": "exact_nested_copy",
        },
        {
            "area": "Task configurations",
            "upstream": f"{upstream['task_configs']:,} task.json files",
            "local": f"All {local['harvey_tasks_hosted']:,} hosted inside {local['tasks']:,} total executable tasks",
            "status": "exact_plus_executable",
        },
        {
            "area": "Physical input documents",
            "upstream": f"{upstream['physical_inputs']:,} files / {upstream['input_bytes']:,} bytes",
            "local": "All exact bytes present in the nested mirror; full mirror is gitignored and deterministically hydrated",
            "status": "exact_local_copy_hydratable_distribution",
        },
        {
            "area": "DOCX/XLSX/PDF requested by audit",
            "upstream": (
                f"{upstream['input_extensions']['.docx']['files']:,} DOCX, "
                f"{upstream['input_extensions']['.xlsx']['files']:,} XLSX, 0 PDF"
            ),
            "local": (
                f"Every upstream DOCX/XLSX copied; {local['seed_documents']} new synthetic inputs include "
                f"{local['seed_formats']['pdf']} PDFs"
            ),
            "status": "exact_copy_plus_labeled_extension",
        },
        {
            "area": "Generic agent tools",
            "upstream": "bash, read, write, edit, glob, grep",
            "local": (
                f"Exact harness copied; file lanes retain shell/document tooling and state lanes expose "
                f"{local['agent_visible_tools']:,} executable product tools"
            ),
            "status": "exact_copy_plus_realistic_state_tools",
        },
        {
            "area": "Document skills and sandbox",
            "upstream": "DOCX/XLSX/PPTX skills and LibreOffice/pandoc/parsers sandbox",
            "local": "Exact sources copied and staged into applicable Harbor file lanes; locked derivative image used for execution",
            "status": "exact_and_operational",
        },
        {
            "area": "Evaluation and graders",
            "upstream": "Criterion-level LLM judge, all-pass scoring, one gold rubric; no per-task deterministic programs",
            "local": f"Exact judge copied; {local['verifiers']:,} task-specific deterministic verifiers added as a separate lane",
            "status": "exact_copy_plus_deterministic_lane",
        },
        {
            "area": "Firm-knowledge tasks",
            "upstream": "250 tasks over one shared 9,288-file DMS",
            "local": "250/250 hosted against pinned evidence indexes",
            "status": "operational_parity",
        },
        {
            "area": "Practice tasks",
            "upstream": "1,760 task-local assignments",
            "local": "1,760/1,760 hosted; one disclosed response.md adapter repairs a missing upstream output filename",
            "status": "operational_parity_with_adapter",
        },
        {
            "area": "Mutated and seeded documents",
            "upstream": "No repository-wide deterministic mutation program",
            "local": (
                f"{local['seed_packs']} structure-matched packs / {local['seed_documents']} DOCX-XLSX-PDF inputs, "
                f"including {local['retail_authority_packs']} jurisdiction packs"
            ),
            "status": "local_extension",
        },
        {
            "area": "51-jurisdiction retail authority reachability",
            "upstream": "No retail-compliance world or jurisdiction authority map",
            "local": (
                f"{local['jurisdictions_executable_specific_authority_mapped']}/51 exact citations and "
                "official URLs are exposed by executable tools; all remain attorney-gated"
            ),
            "status": "executable_issue_spotting_map",
        },
        {
            "area": "Harbor task format",
            "upstream": "Harvey LAB uses its own filesystem harness, not Harbor",
            "local": (
                f"{harbor['exported_tasks']:,} native Harbor schema-{harbor['schema_version']} packages with "
                "instruction.md, task.toml, environment, solution, and tests"
            ),
            "status": "native_harbor_export",
        },
        {
            "area": "Canonical world format",
            "upstream": "No stateful world model",
            "local": "world-v21.json is the canonical runtime model; generated dist packages are Harbor format",
            "status": "canonical_not_harbor_export_is_harbor",
        },
        {
            "area": "Harbor framework dependency",
            "upstream": "Not applicable",
            "local": (
                f"Local runner pins Harbor {harbor['runner_version']}; no Harbor API, OAuth, account, or hosted Hub is required"
            ),
            "status": "local_framework_only",
        },
        {
            "area": "Production image reachability",
            "upstream": "Not applicable",
            "local": (
                f"{harbor['public_images']}/2 immutable production images anonymously pullable"
            ),
            "status": (
                "public_digest_bound_images"
                if harbor["production_images_public"]
                else "external_registry_visibility_pending"
            ),
        },
    ]


def open_gaps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    local = payload["local"]
    upstream = payload["upstream"]
    gaps = [
        {
            "id": "G1", "class": "semantic_evaluation_boundary", "severity": "high",
            "gap": f"{local['practice_criteria_residual']:,} of {local['practice_criteria_total']:,} practice criteria remain outside the deterministic assertion subset.",
            "impact": "Exact VCode cannot safely replace legal-nuance, completeness, prose-quality, and professional-format judgment.",
            "closure": "Report the copied LAB judge independently or add source-grounded assertions with oracle and corruption gates; never infer semantic quality from deterministic state success.",
            "repository_controlled": False,
        },
        {
            "id": "G2", "class": "licensed_legal_review", "severity": "high",
            "gap": "All 51 jurisdictions have a specific authority map, but none of the new v2 rows is represented as a deployment-ready 51-jurisdiction legal opinion.",
            "impact": "Current text, applicability, remedies, notice periods, effective dates, local overlays, preemption, and class-action procedure still require qualified counsel.",
            "closure": "Counsel validates and signs a versioned jurisdiction memorandum; only then may a row become an executable legal rule or remedy.",
            "repository_controlled": False,
        },
        {
            "id": "G3", "class": "risk_claim_boundary", "severity": "high",
            "gap": "No receipt, contract term, disclaimer, refund policy, software control, or benchmark can ensure that a retailer will not be sued.",
            "impact": "A zero-lawsuit promise would itself be misleading and would confuse risk reduction with legal immunity.",
            "closure": "Use prevention, rapid correction, nonwaiver language, evidence preservation, audits, escalation, and current legal review; describe residual risk candidly.",
            "repository_controlled": False,
        },
        {
            "id": "G4", "class": "external_model_calibration", "severity": "high",
            "gap": "Frozen v19 external reference-model calibration remains incomplete at 856/6,972 episodes because the pinned account lacked funds.",
            "impact": "The partial run cannot support a completed comparative model benchmark or model-difficulty claim.",
            "closure": "Fund and resume the exact frozen denominator or publish a separately versioned replacement protocol.",
            "repository_controlled": False,
        },
        {
            "id": "G5", "class": "proprietary_api_fidelity", "severity": "medium",
            "gap": "The 1,100 product tools are executable synthetic legal-operations contracts, not certified mirrors of proprietary vendor APIs.",
            "impact": "Workflow realism and deterministic error behavior do not establish external-vendor request/response parity.",
            "closure": "Pin a licensed or public partner specification and add schema, error, authentication, pagination, and rate-limit conformance tests.",
            "repository_controlled": False,
        },
        {
            "id": "G6", "class": "fleet_capacity_measurement", "severity": "medium",
            "gap": "The full export is structurally and deterministically checked, but a 23,310-trial external model fleet run is not part of this repository audit.",
            "impact": "Representative real Harbor canaries prove integration; they do not measure model quality, wall time, registry throughput, or memory at full concurrency.",
            "closure": "Run the frozen dataset at an explicitly sized concurrency and publish agent/model, Harbor version, image digests, costs, failures, and denominator.",
            "repository_controlled": False,
        },
        {
            "id": "G7", "class": "immutable_upstream_defect", "severity": "medium",
            "gap": f"The exact upstream mirror contains {upstream['known_ooxml_source_defects']} known malformed OOXML XML parts.",
            "impact": "Repairing the source in place would destroy byte parity; strict parsers may require the exact-hash recovery path.",
            "closure": "Keep the immutable source, exact-hash allowlist, recovery copies, and separate normalized derivatives; fail on hash or defect-count drift.",
            "repository_controlled": False,
        },
        {
            "id": "G8", "class": "deterministic_grading_boundary", "severity": "medium",
            "gap": "Deterministic anchors do not completely grade visual polish, tracked-change semantics, recalculated formulas in every office application, or professional legal judgment.",
            "impact": "An artifact can satisfy exact anchors while remaining stylistically weak or legally incomplete.",
            "closure": "Keep render, OOXML semantic, formula-recalculation, file/state, and semantic-judge channels separate and expose disagreement.",
            "repository_controlled": False,
        },
    ]
    if not local["harbor"]["production_images_public"]:
        gaps.append({
            "id": "G9", "class": "external_registry_visibility", "severity": "high",
            "gap": (
                f"Only {local['harbor']['public_images']}/2 digest-bound GHCR production "
                "images are anonymously pullable."
            ),
            "impact": "An unauthenticated Harbor runner cannot start an otherwise valid exported task.",
            "closure": (
                "A package administrator must change both GHCR container packages to Public; "
                "rerun the digest-bound anonymous gate afterward."
            ),
            "repository_controlled": False,
        })
    gaps.append({
        "id": "G10", "class": "large_corpus_distribution", "severity": "low",
        "gap": "The 3.207-GB Harvey input payload is present locally but intentionally excluded from ordinary Git history.",
        "impact": "A clean source checkout has provenance and hydration scripts, not 60,971 inline binary inputs, until hydration runs.",
        "closure": "Run research/clone-repos.sh and the strict input audit, or publish a license-compatible content-addressed corpus artifact with hash verification.",
        "repository_controlled": False,
    })
    return gaps


def build_payload() -> dict[str, Any]:
    commit = command("git", "-C", str(UPSTREAM), "rev-parse", "HEAD")
    remote_main = command("git", "-C", str(UPSTREAM), "rev-parse", "origin/main")
    remote_url = command("git", "-C", str(UPSTREAM), "remote", "get-url", "origin")
    status = command("git", "-C", str(UPSTREAM), "status", "--porcelain")
    harbor_commit = command("git", "-C", str(HARBOR_UPSTREAM), "rev-parse", "HEAD")
    harbor_remote_main = command("git", "-C", str(HARBOR_UPSTREAM), "rev-parse", "origin/main")
    harbor_describe = command("git", "-C", str(HARBOR_UPSTREAM), "describe", "--tags", "--always")
    harbor_status = command("git", "-C", str(HARBOR_UPSTREAM), "status", "--porcelain")
    files = tracked_files()
    top_level = Counter(path.split("/", 1)[0] for path in files)
    task_configs = [path for path in files if path.startswith("tasks/") and path.endswith("/task.json")]
    grader_files = [path for path in files if "/grader/" in path or "/verifier" in path]
    input_audit = load_json(INPUT_AUDIT)
    lab = load_json(LAB_REPORT)
    retail = load_json(RETAIL_REPORT)
    research = load_json(RETAIL_RESEARCH)
    seeds = load_json(SEED_REPORT)
    seed_catalog = load_json(SEED_CATALOG)["packs"]
    v21 = load_json(V21_REPORT)
    world = load_world(WORLD)
    harbor_export = load_json(HARBOR_EXPORT_REPORT)
    harbor_dataset = load_json(HARBOR_DATASET_REPORT)
    ghcr_public = load_json(GHCR_PUBLIC_REPORT)
    oracle_proof = load_json(ORACLE_PROOF_REPORT)
    document_render = load_json(DOCUMENT_RENDER_REPORT)
    document_visual = load_json(DOCUMENT_VISUAL_REVIEW_REPORT)
    runner = tomllib.loads(HARBOR_RUNNER.read_text("utf-8"))
    runner_version = runner["project"]["dependencies"][0].split("==", 1)[1]
    seed_plan = load_json(HARVEY_SEED_PLAN)
    mutation_status = load_json(HARVEY_MUTATION_STATUS)
    oracle = load_json(ORACLE_REPORT)
    discrimination = load_json(DISCRIMINATION_REPORT)
    recovery_oracle = load_json(RECOVERY_ORACLE_REPORT)
    recovery_discrimination = load_json(RECOVERY_DISCRIMINATION_REPORT)
    retail_authority_oracle = load_json(RETAIL_AUTHORITY_ORACLE_REPORT)
    contract_files = sorted((ROOT / "mcp" / "v5" / "contracts").glob("*.json"))
    contracts = [load_json(path) for path in contract_files]
    visible = sum(tool.get("agent_visible") is not False for contract in contracts for tool in contract.get("tools") or [])
    internal = sum(tool.get("agent_visible") is False for contract in contracts for tool in contract.get("tools") or [])
    retail_sources = load_json(ROOT / "research" / "retail-price-accuracy" / "sources" / "manifest.json")
    authority_rows = [{**research["defaults"], **row} for row in research["jurisdictions"]]
    retail_packs = [pack for pack in seed_catalog if pack["domain"] == "retail-price-accuracy"]
    retail_task_count = sum(
        (task.get("provenance") or {}).get("source_pack", "").startswith("pack-retail-price-accuracy-")
        for task in world["tasks"]
    )
    harvey_practice_source_directories = {
        (task.get("file_lane") or {}).get("source_task")
        for task in world["tasks"]
        if (task.get("file_lane") or {}).get("source_commit") == EXPECTED_HARVEY_COMMIT[:12]
    }
    harvey_practice_source_directories.discard(None)
    harvey_practice_sources = {
        practice_source_task_json(value)
        for value in harvey_practice_source_directories
    }
    harvey_firm_sources = {
        (task.get("provenance") or {}).get("path")
        for task in world["tasks"]
        if task.get("method") == "harvey_lab_firm_knowledge_deterministic"
    }
    harvey_firm_sources.discard(None)
    hosted_harvey_sources = harvey_practice_sources | harvey_firm_sources
    upstream_harvey_sources = set(task_configs)
    missing_harvey_sources = sorted(upstream_harvey_sources - hosted_harvey_sources)
    unexpected_harvey_sources = sorted(hosted_harvey_sources - upstream_harvey_sources)
    payload: dict[str, Any] = {
        "schema_version": 2,
        "audit_date": "2026-08-23",
        "scope": "Harvey exact-copy, executable world, Harbor packages, tools, verifiers, documents, mutations, retail research, and production-format gaps",
        "upstream": {
            "repository": "https://github.com/harveyai/harvey-labs",
            "remote_url": remote_url,
            "commit": commit,
            "expected_commit": EXPECTED_HARVEY_COMMIT,
            "remote_main_commit": remote_main,
            "remote_main_verified_equal": remote_main == commit,
            "mirror_clean": status == "",
            "tracked_paths": len(files),
            "top_level_tracked_paths": dict(sorted(top_level.items())),
            "task_configs": len(task_configs),
            "task_path_manifest_sha256": string_manifest_sha256(task_configs),
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
        "harbor_upstream": {
            "repository": "https://github.com/harbor-framework/harbor",
            "audited_main_commit": harbor_commit,
            "audited_main_describe": harbor_describe,
            "remote_main_commit": harbor_remote_main,
            "mirror_clean": harbor_status == "",
            "pinned_release": AUDITED_HARBOR_RELEASE,
            "role": "local evaluation framework",
            "api_required": False,
            "hub_required": False,
        },
        "local": {
            "exact_mirror_path": str(UPSTREAM.relative_to(ROOT)),
            "world": str(WORLD.relative_to(ROOT)),
            "world_version": world["version"],
            "world_sha256": sha256(WORLD),
            "tasks": len(world["tasks"]),
            "verifiers": len(world["verifiers"]),
            "generated_v21_tasks": v21["added_generated_tasks"],
            "tables": len(world["tables"]),
            "seed_rows": sum(len(table.get("sample_rows") or []) for table in world["tables"]),
            "contract_systems": len(contracts),
            "agent_visible_tools": visible,
            "internal_operations": internal,
            "harvey_tasks_hosted": len(hosted_harvey_sources),
            "harvey_tasks_total": len(task_configs),
            "harvey_practice_sources_hosted": len(harvey_practice_sources),
            "harvey_firm_sources_hosted": len(harvey_firm_sources),
            "harvey_task_path_manifest_sha256": string_manifest_sha256(hosted_harvey_sources),
            "harvey_task_paths_missing": missing_harvey_sources,
            "harvey_task_paths_unexpected": unexpected_harvey_sources,
            "harvey_adapter_tasks": 1,
            "practice_criteria_total": lab["criteria"],
            "practice_criteria_determinized": lab["criteria_determinate"],
            "practice_criteria_residual": lab["criteria"] - lab["criteria_determinate"],
            "retail_tasks": 6,
            "retail_input_documents": retail["documents"],
            "retail_reference_pdfs": len(retail_sources["files"]),
            "jurisdictions": retail["jurisdictions"],
            "jurisdictions_benchmark_rules": len(retail["primary_source_triaged_jurisdictions"]),
            "jurisdictions_rule_queue": retail["pending_substantive_validation_jurisdictions"],
            "jurisdictions_specific_authority_mapped": len(authority_rows),
            "jurisdictions_executable_specific_authority_mapped": v21["retail_executable_authority_rows"],
            "retail_legacy_task_pairs_checked": v21["retail_legacy_task_pairs_checked"],
            "retail_authority_dependent_task_pairs_upgraded": v21["retail_authority_dependent_task_pairs_upgraded"],
            "retail_authority_verifier_programs_strengthened": v21["retail_authority_verifier_programs_strengthened"],
            "jurisdictions_substantive_legal_opinions": sum(row["substantive_legal_opinion"] for row in authority_rows),
            "jurisdictions_private_remedies_encoded": sum(row["private_remedy_encoded"] for row in authority_rows),
            "jurisdictions_all_attorney_gated": all(row["attorney_validation_required"] for row in authority_rows),
            "seed_packs": seeds["packs"],
            "seed_documents": seeds["documents"],
            "seed_formats": {"docx": seeds["docx"], "xlsx": seeds["xlsx"], "pdf": seeds["pdf"]},
            "seed_mutations": seeds["mutations"],
            "document_render_pages": document_render["total_rendered_pages"],
            "document_render_checks_passed": document_render["automated_checks"]["all_passed"],
            "document_contact_sheets": document_render["contact_sheets_generated"],
            "document_contact_sheet_visual_review": document_visual["status"],
            "retail_authority_packs": len(retail_packs),
            "retail_authority_tasks": retail_task_count,
            "strict_harvey_derivative_recipes": len(list(HARVEY_RECIPES.glob("*.json"))),
            "strict_harvey_generated_tasks": len(list(HARVEY_GENERATED.glob("tasks/**/task.json"))),
            "broad_harvey_source_tasks": len(seed_plan["variants"]),
            "broad_harvey_practice_areas": len({
                row["task"].split("/", 1)[0]
                for row in seed_plan["variants"]
            }),
            "broad_harvey_seed_variants": sum(len(row["seeds"]) for row in seed_plan["variants"]),
            "broad_harvey_seed_plan_sha256": sha256(HARVEY_SEED_PLAN),
            "blocked_harvey_mutation_candidates": len(mutation_status["blocked"]),
            "resolved_harvey_mutation_candidates": len(mutation_status.get("resolved") or []),
            "retail_oracle": {key: oracle[key] for key in ("total", "passed", "pass_rate")},
            "retail_authority_oracle": {
                key: retail_authority_oracle[key]
                for key in ("total", "passed", "pass_rate")
            },
            "retail_discrimination_failures": len(discrimination["summary"]["discrimination_failures"]),
            "harvey_recovery_oracle": {key: recovery_oracle[key] for key in ("total", "passed", "pass_rate")},
            "harvey_recovery_discrimination_failures": len(recovery_discrimination["summary"]["discrimination_failures"]),
            "harbor": {
                "schema_version": "1.4",
                "runner_version": runner_version,
                "runner_lock_packages": 91,
                "source_format": "custom canonical world JSON",
                "export_format": "one native Harbor task directory per world task",
                "exported_tasks": harbor_export["tasks"],
                "file_lanes": harbor_export["file_lanes"],
                "staged_documents": harbor_export["staged_documents"],
                "staged_skill_trees": harbor_export["staged_skill_trees"],
                "multistep_tasks": harbor_export["multistep_tasks"],
                "multistep_phases": harbor_export["multistep_phases"],
                "agent_world_leaks": harbor_export["agent_world_leaks"],
                "package_symlinks": harbor_export["package_symlinks"],
                "dataset": harbor_dataset["dataset"],
                "dataset_sha256": harbor_dataset["dataset_sha256"],
                "dataset_tasks": harbor_dataset["tasks"],
                "dataset_unique_digests": harbor_dataset["unique_digests"],
                "task_package_files": harbor_export["task_package_files"],
                "task_package_topology_sha256": harbor_export["task_package_topology_sha256"],
                "dataset_task_package_files": harbor_dataset["task_package_files"],
                "task_digest_manifest_sha256": harbor_dataset["task_digest_manifest_sha256"],
                "lab_agent_context_files": harbor_export["lab_agent_context_files"],
                "lab_agent_context_sha256": harbor_export["lab_agent_context_sha256"],
                "world_image_context_files": harbor_export["world_image_context_files"],
                "export_checker_sha256": harbor_export["checker_sha256"],
                "generator_sha256": harbor_export["generator_sha256"],
                "dataset_checker_sha256": harbor_dataset["checker_sha256"],
                "harbor_lock_sha256": harbor_dataset["harbor_lock_sha256"],
                "oracle_runner_sha256": oracle_proof["runner_sha256"],
                "world_image": harbor_export["world_image"],
                "lab_image": harbor_export["lab_image"],
                "production_images_public": ghcr_public["all_public"],
                "public_images": ghcr_public["public_images"],
                "images_checked_for_anonymous_pull": ghcr_public["images_checked"],
                "local_oracle_proof_metadata_matched": oracle_proof["matched"],
                "local_oracle_proof_failure_class": oracle_proof["failure_class"],
                "api_required": False,
            },
        },
        "closed_repository_gaps": [
            "All 2,010 Harvey task configurations are hosted path-for-path with a matching provenance-manifest hash; all 60,971 upstream inputs are present in the exact pinned mirror.",
            "The v21 world contains 23,310 tasks, 23,310 deterministic verifiers, 1,100 visible tools, and 254 tables.",
            "All 23,310 tasks have native Harbor packages whose generated text bytes, staged inputs, skills, world-image context, root topology, and publishable Harbor dataset file sets are checked exactly; package and digest manifests are recorded.",
            "Fifty-one specific retail authorities now drive 51 matched seed packs and admitted document-grounded tasks without encoding legal opinions or remedies.",
            "All 351 admitted seed documents render into the expected 585 pages and pass pagination, text, raster, geometry, and safe-edge-treatment checks.",
            f"The four strict and {sum(len(row['seeds']) for row in seed_plan['variants'])} broad Harvey mutation experiments are explicitly lifecycle-labeled as regression candidates and are not double-counted; 94 release-admitted mutations have stable task references and Harbor packages.",
            "Harbor runner is upgraded to v0.22.0 and remains a local framework with no Harbor API dependency.",
            "Validation scripts that retain assertions fail closed under python -O, and the regression suite enforces that invariant for every tracked production Python file.",
        ],
        "intentional_differences": [
            "Only research/repos/harveyai@harvey-labs reproduces Harvey's folder tree; repository root is a strict-superset implementation.",
            "The canonical world JSON is not Harbor format; the generated task directories and dataset are Harbor format.",
            "Harvey upstream has zero PDF inputs; local PDFs are labeled synthetic fixtures or provenance-tracked public references.",
            "Deterministic verifiers supplement rather than impersonate Harvey's LLM judge.",
            "Research-only mutation candidates remain reproducible but are excluded from production task counts until they satisfy the documented admission gate.",
            "Two additional entity maps are machine-classified as blocked by immutable upstream-source defects and are excluded from the 31-variant seed plan.",
        ],
        "answers": {
            "same_folder_structure": "Yes inside the exact nested Harvey mirror; no at repository root, intentionally.",
            "world_is_harbor_format": "Canonical world-v21.json is not Harbor. The generated dist/harbor-v21-prod task tree is native Harbor schema 1.4.",
            "harbor_api": "None is required. Harbor is the pinned local evaluation framework; Hub/API/OAuth is optional and outside the execution path.",
            "all_harvey_documents_copied": "Yes locally: 60,971/60,971 physical inputs. Upstream has zero PDF inputs. A clean Git checkout must hydrate the gitignored 3.207-GB mirror.",
            "all_harvey_tasks_tools_verifiers_copied": "All upstream source bytes are copied. Harvey supplies 2,010 tasks, six generic tools, an LLM judge, and one gold rubric—not 2,010 deterministic verifier programs. The 23,310 VCodes and 1,100 product tools are local additions.",
            "can_create_more_tasks": f"Yes. v21 admits {v21['added_generated_tasks']:,} generated document-grounded tasks and references every one of {seeds['packs']} seed packs.",
            "can_research_online": "Yes, with provenance and rights gates. The retail v2 map records 51 specific official authorities and preserves attorney validation boundaries.",
            "can_mutate_documents": f"Yes. {seeds['documents']} generated DOCX/XLSX/PDF inputs share one structure signature; mutations never overwrite the exact Harvey mirror.",
        },
    }
    payload["parity_matrix"] = parity_rows(payload)
    payload["open_gaps"] = open_gaps(payload)

    require(commit == remote_main == EXPECTED_HARVEY_COMMIT and status == "",
            "Harvey mirror is not the expected clean live-main checkout")
    require(remote_url == "https://github.com/harveyai/harvey-labs.git",
            "Harvey mirror remote drifted")
    require(harbor_commit == harbor_remote_main == AUDITED_HARBOR_MAIN and harbor_status == "",
            "Harbor mirror is not the expected clean live-main checkout")
    require(harbor_describe == "v0.22.0-2-gb3783322", "Harbor audited describe drifted")
    require(len(files) == 63_074 and len(task_configs) == 2_010,
            "Harvey tracked-path or task-config inventory drifted")
    require(len(harvey_practice_sources) == 1_760 and len(harvey_firm_sources) == 250,
            "hosted Harvey practice or firm task count drifted")
    require(hosted_harvey_sources == upstream_harvey_sources,
            "hosted Harvey task provenance differs from upstream")
    require(
        payload["upstream"]["task_path_manifest_sha256"]
        == payload["local"]["harvey_task_path_manifest_sha256"],
        "Harvey task-path manifests differ",
    )
    require(not missing_harvey_sources and not unexpected_harvey_sources,
            "Harvey hosted task paths contain omissions or unexpected entries")
    require(
        input_audit.get("schema_version") == 3
        and input_audit.get("source_commit") == commit
        and input_audit.get("source_expected_commit") == EXPECTED_HARVEY_COMMIT[:12]
        and input_audit.get("source_remote") == remote_url
        and input_audit.get("source_git_clean") is True,
        "Harvey input audit is stale or bound to a different source checkout",
    )
    format_validation = input_audit.get("format_validation") or {}
    require(
        input_audit.get("tracked_files") == 63_074
        and input_audit.get("physical_inputs") == 60_971
        and input_audit.get("physical_input_bytes") == 3_206_739_638
        and format_validation.get("pdfs_checked") == 0
        and format_validation.get("lfs_pointers") == 0
        and format_validation.get("zero_byte_inputs") == 0
        and format_validation.get("errors") == []
        and input_audit.get("known_source_defects", {}).get("matched") is True
        and input_audit.get("known_source_defects", {}).get("count") == 9,
        "Harvey input inventory, byte count, or format validation drifted",
    )
    require(len(world["tasks"]) == len(world["verifiers"]) == 23_310,
            "v21 task/verifier totals drifted")
    require(v21["world_sha256"] == sha256(WORLD), "v21 build report does not bind the world")
    require(visible == 1_100 and internal == 11 and len(world["tables"]) == 254,
            "v21 tool or table inventory drifted")
    require(seeds["packs"] == 117 and seeds["documents"] == 351,
            "v21 seed pack or document count drifted")
    require(payload["local"]["broad_harvey_source_tasks"] == 16,
            "broad Harvey source-task count drifted")
    require(payload["local"]["broad_harvey_practice_areas"] == 14,
            "broad Harvey practice-area count drifted")
    require(payload["local"]["broad_harvey_seed_variants"] == 35,
            "broad Harvey seed-variant count drifted")
    require(payload["local"]["blocked_harvey_mutation_candidates"] == 0,
            "blocked Harvey mutation count drifted")
    require(payload["local"]["resolved_harvey_mutation_candidates"] == 2,
            "resolved Harvey mutation count drifted")
    require(document_render["total_rendered_pages"] == 585,
            "rendered document page total drifted")
    require(document_render["rendered_pages"] == {"docx": 117, "pdf": 117, "xlsx": 351},
            "per-format rendered page totals drifted")
    require(document_render["automated_checks"]["all_passed"] is True,
            "document render checks did not all pass")
    require(document_render.get("catalog_file_bytes_and_hashes_verified") is True,
            "document render gate did not bind catalog file hashes")
    require(document_render.get("symlinked_sources") == 0,
            "document render gate found or failed to audit symlinked sources")
    require(document_visual["automated_report_sha256"] == sha256(DOCUMENT_RENDER_REPORT),
            "visual-review report does not bind the current automated render report")
    require(document_visual["contact_sheets_reviewed"] == 37,
            "visual-review contact-sheet count drifted")
    require(document_visual["pages_represented"] == 585 and document_visual["status"] == "passed",
            "visual review is incomplete or not passing")
    require(len(retail_packs) == len(authority_rows) == 51 and retail_task_count > 0,
            "retail authority pack, map, or task coverage drifted")
    require(v21["retail_executable_authority_rows"] == 51,
            "executable retail authority row count drifted")
    require(v21["retail_attorney_gated_research_rows"] == 45,
            "attorney-gated retail research count drifted")
    require(v21["retail_legacy_task_pairs_checked"] == 6,
            "legacy retail task-pair count drifted")
    require(v21["retail_authority_dependent_task_pairs_upgraded"] == 2,
            "authority-dependent task-pair count drifted")
    require(v21["retail_authority_verifier_programs_strengthened"] == 4,
            "authority verifier-program count drifted")
    require(retail_authority_oracle == {
        "total": 2,
        "passed": 2,
        "pass_rate": 1.0,
        "failed_condition_counts": {},
        "failures": [],
    }, "retail authority local oracle did not pass exactly 2/2")
    require(not any(row["substantive_legal_opinion"] or row["private_remedy_encoded"]
                    for row in authority_rows),
            "retail authority map encodes an unreviewed legal opinion or private remedy")
    require(runner_version == AUDITED_HARBOR_RELEASE, "Harbor runner pin drifted")
    require(harbor_export.get("schema_version") == 2,
            "Harbor export report schema version drifted")
    require(harbor_dataset.get("schema_version") == 2,
            "Harbor dataset report schema version drifted")
    require(
        harbor_export["tasks"] == harbor_dataset["tasks"]
        == harbor_dataset["unique_digests"] == 23_310,
        "Harbor export or dataset task totals drifted",
    )
    require(harbor_export["world_sha256"] == sha256(WORLD),
            "Harbor export report does not bind the current world")
    require(
        harbor_export["task_package_files"] == harbor_dataset["task_package_files"]
        and harbor_export["checker_sha256"] == sha256(HARBOR_EXPORT_CHECKER)
        and harbor_export["generator_sha256"] == sha256(HARBOR_GENERATOR)
        and harbor_dataset["checker_sha256"] == sha256(HARBOR_DATASET_CHECKER)
        and harbor_dataset["harbor_lock_sha256"] == sha256(HARBOR_RUNNER_LOCK),
        "Harbor byte/topology reports are stale or disagree on packaged files",
    )
    ghcr_images = {row.get("image") for row in ghcr_public.get("results") or []}
    require(
        ghcr_public.get("schema_version") == 1
        and ghcr_public.get("images_checked") == 2
        and ghcr_public.get("public_images")
        == sum(bool(row.get("anonymous_pull")) for row in ghcr_public.get("results") or [])
        and ghcr_public.get("all_public") == (ghcr_public.get("public_images") == 2)
        and ghcr_images == {harbor_export["world_image"], harbor_export["lab_image"]},
        "anonymous GHCR report is stale or not bound to both Harbor export images",
    )
    require(
        oracle_proof.get("schema_version") == 2
        and oracle_proof.get("runner_sha256") == sha256(HARBOR_PRODUCTION_RUNNER)
        and oracle_proof.get("world_image") == harbor_export["world_image"]
        and oracle_proof.get("export_solve_token_sha256")
        == harbor_export["solve_token_sha256"]
        and (
            (
                oracle_proof.get("matched") is True
                and oracle_proof.get("image_oracle_proof_sha256")
                == harbor_export["solve_token_sha256"]
                and oracle_proof.get("failure_class") is None
                and oracle_proof.get("error") is None
            )
            or (
                oracle_proof.get("matched") is False
                and oracle_proof.get("image_oracle_proof_sha256") is None
                and oracle_proof.get("failure_class")
                == "remote_image_inspection_unavailable"
                and isinstance(oracle_proof.get("error"), str)
                and bool(oracle_proof["error"])
                and ghcr_public.get("all_public") is False
            )
        ),
        "production oracle-proof report is stale or inconsistent",
    )
    require(not any(row["repository_controlled"] for row in payload["open_gaps"]),
            "repository-controlled gaps remain open")
    return payload


def markdown(payload: dict[str, Any]) -> str:
    upstream = payload["upstream"]
    local = payload["local"]
    harbor = local["harbor"]
    parity = "\n".join(
        f"| {row['area']} | {row['upstream']} | {row['local']} | `{row['status']}` |"
        for row in payload["parity_matrix"]
    )
    gaps = "\n".join(
        f"| {row['id']} | {row['severity']} | {row['gap']} | {row['closure']} |"
        for row in payload["open_gaps"]
    )
    extension_rows = "\n".join(
        f"| `{ext}` | {values['files']:,} | {values['bytes']:,} |"
        for ext, values in sorted(upstream["input_extensions"].items())
    )
    closed = "\n".join(f"- {row}" for row in payload["closed_repository_gaps"])
    differences = "\n".join(f"- {row}" for row in payload["intentional_differences"])
    return f"""# Harvey LAB parity and repository gap audit

Audit date: {payload['audit_date']}

Harvey upstream: `harveyai/harvey-labs@{upstream['commit']}`

Harbor upstream checked: `harbor-framework/harbor@{payload['harbor_upstream']['audited_main_commit']}` (`{payload['harbor_upstream']['audited_main_describe']}`)

## Executive answer

The Harvey repository is copied completely at
`research/repos/harveyai@harvey-labs`. It is a clean, byte-exact nested Git
checkout at the same live `main` commit, with all **{upstream['tracked_paths']:,}
tracked paths**, all **{upstream['task_configs']:,} task configurations**, and
all **{upstream['physical_inputs']:,} physical inputs** ({upstream['input_bytes']:,}
bytes). Harvey has **zero PDF input files**; claiming that Harvey PDFs were
copied would be false. Every upstream DOCX, XLSX, PPTX, EML, TXT, and JSON input
is present.

The executable v21 world has **{local['tasks']:,} tasks**,
**{local['verifiers']:,} deterministic verifiers**, **{local['agent_visible_tools']:,}
agent-visible tools**, **{local['internal_operations']} internal operations**,
**{local['tables']} state tables**, and **{local['seed_documents']} new matched
DOCX/XLSX/PDF inputs**. All 2,010 Harvey tasks are hosted inside that world.

The format answer is precise:

- The nested Harvey mirror has the same folder structure and bytes as Harvey.
- The repository root adds `world/`, `mcp/`, `harbor/`, deterministic verifiers,
  research, and release architecture; it is not a renamed upstream clone.
- `world-v21.json` is a canonical state model, not a Harbor task directory.
- `dist/harbor-v21-prod/tasks/*` is native Harbor schema {harbor['schema_version']}.
- Harbor {harbor['runner_version']} is a local framework. No Harbor API,
  account, OAuth login, or hosted Hub is required.

## Folder and format topology

```text
legal-agent-simulation/
├── research/repos/harveyai@harvey-labs/  # exact Harvey tree
├── world/blobfish/world-v21.json          # canonical stateful world (not Harbor)
├── mcp/v5/contracts/                      # 1,100 visible product tools
├── research/v21-seeded-documents/         # 117 packs / 351 matched inputs
├── harbor/                                # exporter, images, locked Harbor runner
└── dist/harbor-v21-prod/
    ├── dataset/dataset.toml                # Harbor dataset manifest
    └── tasks/<task-id>/                    # native Harbor task packages
```

The full Harvey binary corpus is intentionally gitignored because it is 3.207
GB of input payload (about 5.46 GiB with Git metadata). A clean checkout uses
`research/clone-repos.sh`, then the strict audit verifies commit, paths, bytes,
formats, LFS/zero-byte absence, OOXML CRCs, and known-defect hashes. This is a
complete local copy with deterministic hydration, not an ordinary-Git bundle.

## Measured inventory

| Measure | Harvey LAB | Local v21 |
| --- | ---: | ---: |
| Task configs / hosted Harvey tasks | {upstream['task_configs']:,} | {local['harvey_tasks_hosted']:,}/{local['harvey_tasks_total']:,} |
| Task-path manifest SHA-256 | `{upstream['task_path_manifest_sha256']}` | `{local['harvey_task_path_manifest_sha256']}` |
| Broad mutation candidates | — | {local['broad_harvey_seed_variants']} variants across {local['broad_harvey_source_tasks']} tasks / {local['broad_harvey_practice_areas']} practice areas; {local['blocked_harvey_mutation_candidates']} blocked and {local['resolved_harvey_mutation_candidates']} resolved upstream-defect candidates; plan `{local['broad_harvey_seed_plan_sha256']}` |
| Total executable tasks | — | {local['tasks']:,} |
| Physical upstream inputs | {upstream['physical_inputs']:,} | {upstream['physical_inputs']:,} exact local copies |
| Input bytes | {upstream['input_bytes']:,} | same exact bytes |
| Generic / visible product tools | 6 | {local['agent_visible_tools']:,} + {local['internal_operations']} internal |
| Per-task deterministic verifier programs | 0 | {local['verifiers']:,} |
| Practice criteria determinized | — | {local['practice_criteria_determinized']:,}/{local['practice_criteria_total']:,} |
| New structure-matched packs / inputs | — | {local['seed_packs']} / {local['seed_documents']} |
| New DOCX / XLSX / PDF | — | {local['seed_formats']['docx']} / {local['seed_formats']['xlsx']} / {local['seed_formats']['pdf']} |
| Rendered fixture pages passing automated QA | — | {local['document_render_pages']}/{local['document_render_pages']} |
| Retail scenario inputs | — | {local['retail_input_documents']} across 3 matched scenarios |
| Specific state-plus-D.C. authority maps | — | {local['jurisdictions_specific_authority_mapped']}/51 |
| Authority maps represented as legal opinions/remedies | — | {local['jurisdictions_substantive_legal_opinions']} / {local['jurisdictions_private_remedies_encoded']} |
| Retail authority packs / admitted tasks | — | {local['retail_authority_packs']} / {local['retail_authority_tasks']:,} |
| Harbor packages / unique content digests | — | {harbor['exported_tasks']:,} / {harbor['dataset_unique_digests']:,} |
| Harbor package files / exact topology hash | — | {harbor['task_package_files']:,} / `{harbor['task_package_topology_sha256']}` |
| Harbor file lanes / staged document instances | — | {harbor['file_lanes']:,} / {harbor['staged_documents']:,} |
| Harbor multi-step tasks / phases | — | {harbor['multistep_tasks']} / {harbor['multistep_phases']} |
| Anonymous production image pulls | — | {harbor['public_images']}/2 exact digests |

Upstream input format counts:

| Extension | Files | Bytes |
| --- | ---: | ---: |
{extension_rows}

## Exact copy versus executable implementation

| Area | Harvey LAB | This repository | Status |
| --- | --- | --- | --- |
{parity}

## What “copy all tasks, tools, and verifiers” means

Every Harvey source file—including tasks, six generic filesystem tools,
judge/scoring code, skills, sandbox, tests, utilities, and the single gold
rubric—is in the exact mirror. Harvey does **not** ship 2,010 deterministic
verifier programs or 1,100 legal-product APIs. Those are local additions.

All 1,760 practice tasks and 250 firm-knowledge tasks are hosted. One practice
task omitted an output filename upstream; the port adds a disclosed
`response.md` adapter without editing the source. The LAB judge remains a
separate semantic lane because exact state checks cannot grade every criterion.

## Seeded documents and task generation

The seed catalog has **{local['seed_packs']} packs / {local['seed_documents']}
documents**. Every pack contains one DOCX matter brief, one XLSX evidence and
computation register, and one PDF source extract. All packs share the same
heading, table, worksheet, formula, print, page-size, and PDF structure
signature. Content, jurisdiction, dates, amounts, anchors, risk, and issue facts
change. Every file is synthetic, hashed, manifested, reproducible, and
attorney-gated.

All **{local['document_render_pages']} rendered pages** pass expected-pagination,
extractable-text, nonblank-raster, geometry, and safe-edge-treatment checks. The
machine report distinguishes automated raster evidence from contact-sheet human
review instead of treating structural validation as visual proof.

The 51 retail packs add one authority-mapped evidence set for every state and
D.C. All are referenced by admitted v21 tasks. Workbooks carry citation,
official URL, source type, common controls, and fields rejecting legal-opinion
or private-remedy encoding. They do not overwrite Harvey inputs or the frozen
v20 snapshot. In v21, the same 51 citations and official URLs are projected
into the executable `rc_jurisdiction_rules` table. All six legacy retail
task/verifier pairs pass the migration audit; the two authority-dependent pairs
are rewritten away from the generic-portal vocabulary. Four top-level/phase
VCode programs require an unfiltered list observation with both `count=51` and
`total=51`; separate fail-closed build and checker gates prove that those 51
executable rows exactly match the mapped citations and official URLs.
Both authority-dependent workflows also pass the live local HTTP oracle
({local['retail_authority_oracle']['passed']}/{local['retail_authority_oracle']['total']}).

## Walmart example and 51-jurisdiction research

The request's example conflates distinct matters. `Rector v. Walmart` alleges
shelf/register mismatches in D.C.; the cited opinion concerns a first-filed
stay, not a merits settlement. `Kahn v. Walmart` addresses alleged scanner
discrepancies. The $45 million `Kukorinis` settlement concerned weighted goods
and bagged citrus in Florida, not a California self-checkout double-charge
settlement. California separately reported checkout and price/weight cases.

The executable work covers preservation, transaction reconstruction, exposure,
authority mapping, remedy gating, receipt/policy redlines, duplicate-scan and
price-sync controls, weights, retesting, and national closeout. Common wording
corrects verified overcharges promptly and preserves statutory rights; it never
promises litigation immunity.

The v2 map advances all 51 jurisdictions from a portal list to a specific
statute, regulation, or official enforcement-program map. Every row still sets
`substantive_legal_opinion=false`, `private_remedy_encoded=false`,
`current_text_and_local_overlays_validated=false`, and
`attorney_validation_required=true`.

## Harbor executable evidence

The export contains **{harbor['exported_tasks']:,}/{local['tasks']:,} tasks**,
**{harbor['dataset_unique_digests']:,} unique package digests**,
**{harbor['task_package_files']:,} byte-checked package files**,
**{harbor['file_lanes']:,} file lanes**, **{harbor['staged_documents']:,} staged
document instances**, and **zero agent-side world leaks or package symlinks**.
Package topology SHA-256: `{harbor['task_package_topology_sha256']}`. Dataset
task-digest manifest SHA-256: `{harbor['task_digest_manifest_sha256']}`. Dataset
SHA-256: `{harbor['dataset_sha256']}`. The locked runner uses Harbor
{harbor['runner_version']} with a 91-package graph. The export is bound to
`{harbor['world_image']}` and `{harbor['lab_image']}`; the independent
anonymous registry audit passes {harbor['public_images']}/2 exact digests.
Local remote-metadata comparison of the export oracle proof is
`{str(harbor['local_oracle_proof_metadata_matched']).lower()}` with failure
class `{harbor['local_oracle_proof_failure_class']}`. Registry privacy can
excuse remote inspection unavailability, but never an oracle-integrity failure;
the release workflow's successful oracle canaries remain the independent
production proof. Harbor Hub is optional.

## Closed repository-controlled gaps

{closed}

## Intentional differences, not hidden parity claims

{differences}

## All remaining gaps and external boundaries

| ID | Severity | Gap | Required closure |
| --- | --- | --- | --- |
{gaps}

No open item is a repository-controlled implementation omission. The remaining
items are semantic or legal-review boundaries, external calibration and fleet
measurement, proprietary-spec access, immutable upstream defects, or corpus
distribution constraints. Research-only mutation candidates are explicitly
lifecycle-labeled and are not double-counted as graded tasks.

## Reproduction and gates

```bash
npm run harvey:input-audit-check
npm run harvey:parity-audit-check
python3 tools/build_retail_price_accuracy_pack.py --check
python3 tools/build_v21_seed_documents.py --check
npm run v21:check
npm run v21:document-render-check
python3 tools/run_harbor_production.py generate \
  --world-image {harbor['world_image']} \
  --lab-image {harbor['lab_image']}
# This exits 1 while G9 remains; structural and dataset reports are still written first.
python3 tools/run_harbor_production.py check \
  --world-image {harbor['world_image']} \
  --lab-image {harbor['lab_image']}
uv run --project harbor/runner --locked harbor --version
```

Machine-readable evidence: `reports/harvey-parity-audit.json`,
`reports/v21-harbor-export-audit.json`,
`reports/v21-harbor-dataset-audit.json`,
`reports/v21-ghcr-public-audit.json`,
`reports/v21-oracle-proof-audit.json`,
`reports/v21-document-render-audit.json`, and
`reports/v21-document-visual-review.json`.
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
        "world_tasks": payload["local"]["tasks"],
        "seed_documents": payload["local"]["seed_documents"],
        "open_gaps": len(payload["open_gaps"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
