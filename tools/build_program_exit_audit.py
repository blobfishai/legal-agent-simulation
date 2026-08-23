#!/usr/bin/env python3
"""Build the fail-closed M0-M8 LAB-Superset program exit audit.

The public superset claim used to infer readiness from four top-level signals.
That was necessary but not sufficient: a stale conformance report, a broken M3
state machine, or an incomplete ecosystem adapter could be missed.  This file
collects every milestone's binary acceptance facts into one deterministic
artifact.  It does not execute the expensive checks; CI executes the commands
listed for each milestone and then proves this derived artifact is unchanged.
"""

from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "program-exit-v19.json"
DOC = ROOT / "docs" / "PROGRAM-STATUS.md"


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text())


def world(relative: str) -> dict[str, Any]:
    raw = load(relative)
    return raw.get("world", raw)


def fixture_count() -> int:
    base = ROOT / "tools" / "fixtures" / "verdicts"
    paths = [*base.glob("*.json"), *base.glob("*.json.gz")]
    return len({path.name.removesuffix(".gz").removesuffix(".json") for path in paths})


def badbank_count() -> int:
    namespace = runpy.run_path(str(ROOT / "tools" / "badbank" / "defects.py"))
    tasks, verifiers, expectations = namespace["build"]()
    assert len(tasks) == len(verifiers) == len(expectations)
    return len(tasks)


def check(
    check_id: str,
    passed: bool,
    measure: str,
    *proof: str,
    blocker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": check_id,
        "passed": bool(passed),
        "measure": measure,
        "proof": list(proof),
    }
    if blocker is not None and not passed:
        row["blocker"] = blocker
    return row


def milestone(
    milestone_id: str,
    name: str,
    checks: list[dict[str, Any]],
    commands: list[str],
) -> dict[str, Any]:
    failed = [row for row in checks if not row["passed"]]
    external = bool(failed) and all(row.get("blocker", {}).get("kind") for row in failed)
    return {
        "id": milestone_id,
        "name": name,
        "status": "passed" if not failed else ("blocked_external" if external else "failed"),
        "passed": not failed,
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "checks": checks,
        "verification_commands": commands,
    }


def build() -> dict[str, Any]:
    v16 = world("world/blobfish/world-v16.json")
    v17 = world("world/blobfish/world-v17.json")
    v18 = world("world/blobfish/world-v18.json")
    v19 = world("world/blobfish/world-v19.json")
    v17_report = load("world/v17/build-report.json")
    v18_report = load("world/v18/build-report.json")
    v19_report = load("world/v19/build-report.json")

    oracle16 = load("data/oracle-v16.json")
    oracle17 = load("data/oracle-v17.json")
    oracle18_m3 = load("data/oracle-v18-m3.json")
    oracle18 = load("data/oracle-v18.json")
    oracle19 = load("data/oracle-v19-m6.json")
    disc16 = load("data/discrimination-v16-classified.json")
    disc17 = load("data/discrimination-v17.json")["summary"]
    disc18_m3 = load("data/discrimination-v18-m3.json")["summary"]
    disc18 = load("data/discrimination-v18.json")["summary"]
    disc19 = load("data/discrimination-v19-m6.json")["summary"]
    boundary = load("data/migration/v16-boundary-shift.json")

    migration = v16["surface_migration"]
    conformance = load("data/conformance.json")["summary"]
    wire = load("data/conformance-wire.json")["summary"]
    behavior = load("data/conformance-behavior.json")["summary"]
    courtlistener = load("data/conformance-courtlistener.json")["summary"]

    ingest = load("world/ingest/lab-ingest-report.json")
    compiler = v17_report["lab_compiler"]
    grounding = v17_report["existing_graph_grounding"]
    file_lane = load("data/harbor-v17-file-lane-smoke.json")

    replay = load("data/capstone-replay-v19.json")
    precorrection = load("data/precorrection-v19.json")
    harbor_multistep = load("data/harbor-v19-multistep-smoke.json")

    canary = load("data/leaderboard/canary-proof-v19.json")
    protocol = load(
        "data/leaderboard/protocol-proof/deepseek-chat/"
        "v19-all-tools-fixed50-context-v4/manifest.json"
    )
    checkpoint = load("data/leaderboard/calibration-checkpoint-v19.json")
    sweep_health = load(
        "data/leaderboard/results/deepseek-chat@v19-triage.sweep-health.json"
    )
    triage = load("data/triage/world-v19.json")
    suspect_audit = load("data/triage/world-v19-suspect-audit.json")
    leaderboard = load("data/leaderboard/results/deepseek-chat@v19-triage.v2.json")

    skill_census = load("data/ecosystem/skill-census.json")
    skill_candidates = load("data/ecosystem/skill-task-candidates.json")
    schema_diff = load("data/ecosystem/mcp-schema-diff.json")
    byo = load("data/ecosystem/byo-mcp-proof.json")

    ci = (ROOT / ".github" / "workflows" / "world-ci.yml").read_text()
    badbank = badbank_count()
    fixtures = fixture_count()
    total19 = len(v19["tasks"])
    diligence_tasks = [
        task for task in v17["tasks"]
        if str((task.get("provenance") or {}).get("source_task") or "").startswith("diligence/")
    ]
    diligence_sources = {
        task["provenance"]["source_task"] for task in diligence_tasks
    }
    diligence_metrics = {"precision", "recall", "f_beta", "over_included"}

    classified16_clean = all(
        int(disc16["counts"].get(name, 0)) == 0
        for name in ("BROKEN-KEY", "BROKEN-GUARD", "HARNESS-ERROR")
    ) and not disc16.get("globalErrors") and not disc16.get("assertionManifestDrift")
    disc17_clean = not disc17["discrimination_failures"] and not disc17["harness_errors"]
    disc18_m3_clean = (
        not disc18_m3["discrimination_failures"] and not disc18_m3["harness_errors"]
    )
    disc18_clean = not disc18["discrimination_failures"] and not disc18["harness_errors"]
    disc19_clean = not disc19["discrimination_failures"] and not disc19["harness_errors"]

    milestones = [
        milestone(
            "M0",
            "Safety nets",
            [
                check(
                    "golden_verdict_fixtures",
                    fixtures == total19,
                    f"{fixtures}/{total19} current-world task fixture bundles",
                    "tools/fixtures/verdicts",
                    "tools/check_fixtures.py",
                ),
                check(
                    "gate_the_gates",
                    badbank == 6,
                    f"{badbank}/6 known-bad tasks represented",
                    "tools/badbank/defects.py",
                    "tools/check_gates.py",
                ),
                check(
                    "ci_trust_chain",
                    all(token in ci for token in (
                        "tools/check_fixtures.py", "tools/check_gates.py",
                        "tools/check_superset_matrix.py",
                    )),
                    "CI contains fixtures, badbank, and public-claim gates",
                    ".github/workflows/world-ci.yml",
                ),
            ],
            [
                "python3 tools/check_fixtures.py --base http://127.0.0.1:8988",
                "python3 tools/check_gates.py --world world/blobfish/world-v16.json --port 8975",
            ],
        ),
        milestone(
            "M1",
            "Product-surface migration",
            [
                check(
                    "gen1_retired_after_migration",
                    migration["legacy_tools_removed"] == 99
                    and migration["tasks_migrated"] + migration["tasks_native_product"] == 291,
                    (
                        f"{migration['legacy_tools_removed']} Gen-1 tools retired after "
                        f"{migration['tasks_migrated']} migrated + "
                        f"{migration['tasks_native_product']} native tasks"
                    ),
                    "world/blobfish/world-v16.json",
                    "world/migrate/id-manifest.json",
                ),
                check(
                    "v16_oracle",
                    oracle16["passed"] == oracle16["total"] == 291,
                    f"{oracle16['passed']}/{oracle16['total']} reference walks pass",
                    "data/oracle-v16.json",
                ),
                check(
                    "v16_discrimination",
                    classified16_clean,
                    (
                        "0 broken keys, 0 broken guards, 0 harness errors; "
                        f"{disc16['counts']['no-answer-key']} content gaps explicitly classified"
                    ),
                    "data/discrimination-v16-classified.json",
                    "docs/DISCRIMINATION-v16.md",
                ),
                check(
                    "v16_boundary_remeasurement",
                    boundary["comparison"]["task_count"] == 21
                    and boundary["summary"]["stable"] + boundary["summary"]["changed"] == 21
                    and all(row.get("observed_evidence") for row in boundary["rows"]),
                    (
                        f"21/21 boundary tasks remeasured; {boundary['summary']['changed']} "
                        "observed class changes explained"
                    ),
                    "data/migration/v16-boundary-shift.json",
                    "docs/V16-BOUNDARY-SHIFT.md",
                ),
            ],
            [
                "python3 world/migrate/gen1_to_v16.py --check",
                "python3 tools/check_product_surface.py",
                "node sim/compare-v16-boundary.mjs",
            ],
        ),
        milestone(
            "M2",
            "Vendor contract fidelity",
            [
                check(
                    "conformance_registry",
                    conformance["registry_covered"] == conformance["registry_total"] == 91
                    and conformance["harness_failures"] == 0
                    and conformance["simulator_extension_gaps"] == 0,
                    (
                        "91/91 task-used product-contract tools registered; "
                        "0 harness/extension gaps"
                    ),
                    "data/conformance.json",
                    "docs/CONFORMANCE.md",
                ),
                check(
                    "task_used_surface_closure",
                    oracle18["passed"] == oracle18["total"] == len(v18["tasks"])
                    and oracle19["passed"] == oracle19["total"]
                    and oracle18["total"] + oracle19["total"] == total19,
                    (
                        f"all {total19} admitted task walks close over the 91 agent-visible "
                        "tools; no unused endpoints were added to chase the planning estimate"
                    ),
                    "data/oracle-v18.json",
                    "data/oracle-v19-m6.json",
                    "docs/MCP-JUSTIFICATION.md",
                ),
                check(
                    "published_schema_conformance",
                    conformance["published_input_schemas_passed"]
                    == conformance["published_input_schemas_applicable"]
                    and conformance["response_schemas_passed"]
                    == conformance["response_schemas_applicable"]
                    and conformance["verification_passed_vendor_tools"]
                    == conformance["publicly_verifiable_vendor_tools"],
                    (
                        f"{conformance['published_input_schemas_passed']}/"
                        f"{conformance['published_input_schemas_applicable']} published input "
                        f"schemas and {conformance['verification_passed_vendor_tools']}/"
                        f"{conformance['publicly_verifiable_vendor_tools']} publicly verifiable "
                        "vendor targets pass"
                    ),
                    "data/conformance.json",
                    "tools/conformance/specs/manifest.json",
                ),
                check(
                    "wire_and_behavior",
                    wire["success_calls"] == wire["tools_checked"] == 91
                    and wire["harness_failures"] == 0
                    and behavior["passed"] == behavior["total"] == 19,
                    "91/91 success-wire calls and 19/19 vendor behavior fixtures pass",
                    "data/conformance-wire.json",
                    "data/conformance-behavior.json",
                ),
                check(
                    "courtlistener_live_diff",
                    courtlistener["passed"] == courtlistener["total"] == 13,
                    "13/13 CourtListener tools pass against pinned live-source serializers",
                    "data/conformance-courtlistener.json",
                ),
                check(
                    "fidelity_ceiling_disclosed",
                    "partner-gated" in (ROOT / "docs" / "MCP-JUSTIFICATION.md").read_text(),
                    "iManage partner-gated ceiling is public",
                    "docs/MCP-JUSTIFICATION.md",
                ),
            ],
            [
                "python3 tools/conformance/run.py --check",
                "python3 tools/conformance/check_fixtures.py",
                "python3 tools/check_pagination.py",
                "python3 tools/check_query_dsl.py",
                "python3 tools/check_auth_errors.py --base http://127.0.0.1:8988 --world world/blobfish/world-v19.json",
            ],
        ),
        milestone(
            "M3",
            "Court filing, deadline, and e-signature mocks",
            [
                check(
                    "three_product_families",
                    v18_report["added"] == {"deadlines": 5, "efiling": 5, "esign": 5},
                    "5 e-filing + 5 deadline + 5 e-signature tasks admitted",
                    "world/v18/build-report.json",
                ),
                check(
                    "m3_oracle",
                    oracle18_m3["passed"] == oracle18_m3["total"] == 15,
                    "15/15 new workflow reference walks pass",
                    "data/oracle-v18-m3.json",
                ),
                check(
                    "m3_discrimination",
                    disc18_m3_clean,
                    (
                        "0 broken guards/keys or harness errors; 5 e-filing wrong-value "
                        "mutations explicitly tool-rejected"
                    ),
                    "data/discrimination-v18-m3.json",
                ),
            ],
            [
                "python3 tools/check_m3_contracts.py",
                "python3 tools/check_v18_workflows.py",
            ],
        ),
        milestone(
            "M4",
            "Evidence and grounded grading",
            [
                check(
                    "lab_evidence_ingest",
                    ingest["documents"] == 51_683
                    and ingest["parsed_documents"] == ingest["documents"]
                    and ingest["failed_documents"] == 0
                    and ingest.get("recovered_documents") == 9
                    and ingest["parse_rate"] == 1.0,
                    (
                        f"{ingest['parsed_documents']:,}/{ingest['documents']:,} LAB documents "
                        f"text-parsed; {ingest['recovered_documents']} exact-hash OOXML recoveries "
                        "recorded; source bytes preserved"
                    ),
                    "world/ingest/lab-ingest-report.json",
                ),
                check(
                    "manifest_compiler",
                    compiler["policy"]["grade_time"] == "pure code"
                    and compiler["policy"]["judge_calls"] == 0,
                    "build-time proposal/validation; grade time is pure code with 0 judge calls",
                    "world/port/determinate/lab-report.json",
                    "world/manifest/schema.json",
                ),
                check(
                    "graph_walk_grounding",
                    grounding["graph_tasks"] == 117
                    and grounding["lab_grounded"] >= 110
                    and grounding["lab_grounded"] + grounding["exact_state"] == 117
                    and not grounding["exceptions"],
                    (
                        f"{grounding['lab_grounded']}/117 source-grounded text keys + "
                        f"{grounding['exact_state']} exact-state keys; 0 exceptions"
                    ),
                    "world/v17/build-report.json",
                ),
            ],
            [
                "python3 tools/check_lab_ingest.py",
                "python3 -m unittest discover -s world/manifest/tests -v",
                "python3 tools/check_existing_grounding.py",
            ],
        ),
        milestone(
            "M5",
            "Harvey LAB deterministic import",
            [
                check(
                    "lab_task_hosting",
                    v17_report["lab_hosted_tasks"] == 2009
                    and v17_report["lab_quarantined_tasks"] == 1
                    and not v17_report["lab_source_accounting"]["missing"],
                    "2,009/2,010 LAB tasks hosted; 1 quarantined with a published reason",
                    "world/v17/build-report.json",
                    "docs/PARITY.md",
                ),
                check(
                    "determinate_criteria_floor",
                    compiler["criteria_determinate"] / compiler["criteria"] >= 0.55,
                    (
                        f"{compiler['criteria_determinate']:,}/{compiler['criteria']:,} "
                        f"criteria ({100 * compiler['criteria_coverage']:.1f}%) clear the "
                        "executable 55% admission floor; the earlier ~60% was an estimate"
                    ),
                    "world/v17/build-report.json",
                    "docs/LAB-DETERMINIZATION.md",
                ),
                check(
                    "v17_oracle_and_discrimination",
                    oracle17["passed"] == oracle17["total"] == len(v17["tasks"])
                    and disc17_clean,
                    f"{oracle17['passed']}/{oracle17['total']} oracle; 0 broken guards/keys",
                    "data/oracle-v17.json",
                    "data/discrimination-v17.json",
                ),
                check(
                    "file_state_lanes",
                    file_lane["oracle"]["reward"] == 1.0
                    and file_lane["nop"]["reward"] == 0.0,
                    "Harbor file/state oracle=1.0 and no-op=0.0",
                    "data/harbor-v17-file-lane-smoke.json",
                ),
                check(
                    "retrieval_metrics",
                    v17_report["retrieval_tasks"] == 250
                    and v17_report["retrieval_grading"]["metric"] == "F-beta",
                    "250 firm-knowledge tasks use F-beta with P/R/over-inclusion channels",
                    "world/v17/build-report.json",
                    "tools/check_retrieval_grading.py",
                ),
                check(
                    "diligence_scale_grading",
                    len(diligence_sources) == 11
                    and len(diligence_tasks) == 15
                    and all(
                        task.get("capability_type") == 4
                        and (task.get("grading") or {}).get("scale_review") is True
                        and diligence_metrics.issubset(
                            set((task.get("grading") or {}).get("reports") or [])
                        )
                        for task in diligence_tasks
                    ),
                    (
                        "11/11 unique LAB diligence VDRs carry P/R/F-beta/over-inclusion "
                        "grading (15 executable tasks because one source seeds five migrated tasks)"
                    ),
                    "world/blobfish/world-v17.json",
                    "tools/check_practice_import.py",
                ),
            ],
            [
                "python3 tools/check_v17_import.py",
                "python3 tools/check_lab_extractor_parity.py --check",
                "python3 tools/check_harbor_file_lane.py",
                "python3 tools/check_retrieval_grading.py",
            ],
        ),
        milestone(
            "M6",
            "Long-horizon and multi-turn task families",
            [
                check(
                    "capstone_shape",
                    v19_report["added"]["capstones"] == 5
                    and set(v19_report["capstone_calls"].values()) == {50},
                    "5 capstones, each with a 50-call reference walk",
                    "world/v19/build-report.json",
                ),
                check(
                    "multi_turn_shape",
                    v19_report["added"]["multi_turn"] == 30
                    and v19_report["load_bearing_corrections"] >= 10,
                    (
                        f"30 multi-turn tasks; {v19_report['load_bearing_corrections']} "
                        "load-bearing corrections"
                    ),
                    "world/v19/build-report.json",
                ),
                check(
                    "m6_oracle_discrimination",
                    oracle19["passed"] == oracle19["total"] == 35 and disc19_clean,
                    "35/35 new tasks pass oracle and reject adversarial modes",
                    "data/oracle-v19-m6.json",
                    "data/discrimination-v19-m6.json",
                ),
                check(
                    "capstone_replay",
                    replay["all_passed"] is True
                    and replay["all_bit_identical"] is True
                    and replay["tasks"] == 5
                    and replay["runs"] == 15,
                    "5 capstones pass 3/3 with bit-identical state digests",
                    "data/capstone-replay-v19.json",
                ),
                check(
                    "superseded_instruction_rejection",
                    precorrection["tasks"] == precorrection["rejected"] == 35
                    and not precorrection["incorrectly_passed"],
                    "35/35 pre-correction walks rejected",
                    "data/precorrection-v19.json",
                ),
                check(
                    "harbor_multistep_smoke",
                    harbor_multistep["capstone"]["reward"]["reward"] == 1.0
                    and harbor_multistep["multi_turn"]["reward"]["reward"] == 1.0,
                    "Harbor capstone and multi-turn cumulative rewards both equal 1.0",
                    "data/harbor-v19-multistep-smoke.json",
                ),
            ],
            [
                "python3 tools/check_v19_multistep.py",
                "python3 tools/replay_v19_capstones.py --base http://127.0.0.1:8988 --world world/blobfish/world-v19.json",
            ],
        ),
        milestone(
            "M7",
            "Calibration, canaries, leaderboard, and public claim",
            [
                check(
                    "oracle_canary",
                    canary["clean_canary_exit"] == 0
                    and canary["seeded_defect_exit"] != 0
                    and canary["seeded_defect_model_episodes"] == 0
                    and canary["jsonrpc_error_is_failure"] is True,
                    "clean canary passes; seeded defect halts before model spend",
                    "data/leaderboard/canary-proof-v19.json",
                ),
                check(
                    "measurement_protocol",
                    protocol["status"] == "accepted"
                    and protocol["graded"] == protocol["episodes"] == 10
                    and protocol["infrastructure_errors"] == 0,
                    "10-family fixed-50/all-tools protocol proof accepted",
                    (
                        "data/leaderboard/protocol-proof/deepseek-chat/"
                        "v19-all-tools-fixed50-context-v4/manifest.json"
                    ),
                ),
                check(
                    "production_sweep_health",
                    sweep_health["classes"].get("graded") == checkpoint["episodes_valid"]
                    and sweep_health["classes"].get("infra_error", 0) >= 1
                    and sweep_health["canaries"]["failed"] == 0
                    and sweep_health["verifierCrashes"] == 0
                    and "HTTP 402" in str(sweep_health.get("haltedBy") or ""),
                    (
                        f"{checkpoint['episodes_valid']} graded records reconcile; "
                        f"{sweep_health['classes'].get('infra_error', 0)} infrastructure "
                        "outcomes excluded; 0 canary/verifier failures; "
                        f"friction={100 * sweep_health['friction']['rate']:.2f}% "
                        f"(configured {100 * sweep_health['friction']['expectedRate']:.2f}%, "
                        f"alert={str(sweep_health['friction']['driftAlert']).lower()})"
                    ),
                    "data/leaderboard/results/deepseek-chat@v19-triage.sweep-health.json",
                    "data/leaderboard/calibration-checkpoint-v19.json",
                ),
                check(
                    "three_episode_calibration",
                    checkpoint["complete"] is True
                    and checkpoint["episodes_valid"] == checkpoint["episodes_required"] == 6972
                    and triage["complete"] is True,
                    (
                        f"{checkpoint['episodes_valid']}/{checkpoint['episodes_required']} valid "
                        f"episodes; {checkpoint['episodes_remaining']} remain"
                    ),
                    "data/leaderboard/calibration-checkpoint-v19.json",
                    "data/triage/world-v19.json",
                    blocker=checkpoint.get("external_blocker"),
                ),
                check(
                    "leaderboard_pipeline",
                    leaderboard["worldVersion"] == 19
                    and leaderboard["measurementProtocol"]
                    == checkpoint["measurement_protocol"]
                    and leaderboard["toolScope"] == "all"
                    and leaderboard["coverage"]["tasksDefined"] == total19,
                    (
                        f"leaderboard is derivable for all {total19} tasks and honestly marks "
                        f"{leaderboard['coverage']['tasksMeasured']} partial observations"
                    ),
                    "data/leaderboard/results/deepseek-chat@v19-triage.v2.json",
                    "docs/leaderboard/index.html",
                ),
                check(
                    "suspect_audit_pipeline",
                    suspect_audit["complete"] is True and not suspect_audit["unresolved"],
                    "suspect-audit decision boundary is complete with 0 unresolved rows",
                    "data/triage/world-v19-suspect-audit.json",
                ),
            ],
            [
                "python3 tools/check_sweep_health.py --proof data/leaderboard/canary-proof-v19.json",
                "python3 tools/check_measurement_protocol_proof.py",
                "python3 tools/build_calibration_checkpoint.py",
                "python3 tools/check_triage_world.py",
                "python3 tools/check_leaderboard_v2.py",
                "python3 tools/check_superset_matrix.py",
            ],
        ),
        milestone(
            "M8",
            "Legal eval, skill, and MCP ecosystem adapters",
            [
                check(
                    "skill_census",
                    skill_census["counts"]["skills"] == 175
                    and skill_candidates["counts"]["candidates"] == 100
                    and skill_candidates["counts"]["admitted"] == 0,
                    "175/175 legal skills pinned; 100 candidates; 0 unsafe auto-admissions",
                    "data/ecosystem/skill-census.json",
                    "data/ecosystem/skill-task-candidates.json",
                ),
                check(
                    "mcp_schema_diff",
                    len(schema_diff["tools"]) == 27
                    and schema_diff["summary"]["exact_contracts"] == 0
                    and schema_diff["summary"]["executable_adapters"]
                    == ["search_live_case_law"],
                    "27 production-MCP tools classified without false exactness; 1 adapter",
                    "data/ecosystem/mcp-schema-diff.json",
                    "docs/MCP-SCHEMA-DIFF.md",
                ),
                check(
                    "byo_mcp",
                    byo["passed"] is True
                    and byo["configuration"]["base_url_swapped"] is True
                    and byo["external_network"] is False,
                    "legal-mcp base-URL swap passes with external network disabled",
                    "data/ecosystem/byo-mcp-proof.json",
                    "docs/BYO-MCP.md",
                ),
            ],
            [
                "python3 world/ecosystem/compile_skills.py --check",
                "python3 tools/check_skill_task_compiler.py",
                "python3 world/ecosystem/diff_mcp_schemas.py --check",
                "python3 tools/check_mcp_schema_diff.py",
                "python3 tools/check_byo_mcp.py --check-proof",
            ],
        ),
    ]

    open_gates = []
    for item in milestones:
        for row in item["checks"]:
            if row["passed"]:
                continue
            open_gates.append({
                "milestone": item["id"],
                "check": row["id"],
                "measure": row["measure"],
                **({"blocker": row["blocker"]} if "blocker" in row else {}),
            })

    local_complete = bool(open_gates) and all("blocker" in row for row in open_gates)
    if not open_gates:
        local_complete = True
    report = {
        "schema": "legal-agent-simulation.program-exit.v1",
        "world": "world-v19",
        "program_exit_ready": not open_gates,
        "local_implementation_complete": local_complete,
        "status": (
            "ready" if not open_gates
            else "blocked_external" if local_complete
            else "failed_local_gate"
        ),
        "milestones_passed": sum(item["passed"] for item in milestones),
        "milestones_total": len(milestones),
        "milestones": milestones,
        "open_gates": open_gates,
        "denominator_notes": {
            "milestone_numbering": (
                "the source plan says eight milestones but enumerates M0 through M8; "
                "this audit covers all nine labels"
            ),
            "lab_task_hosting": "2,009/2,010 source tasks (99.95%)",
            "lab_practice_criteria": (
                f"{compiler['criteria_determinate']:,}/{compiler['criteria']:,} criteria "
                f"({100 * compiler['criteria_coverage']:.1f}%); passes the executable 55% M5 "
                "admission floor; the earlier ~60% figure was an estimate, not a hidden pass"
            ),
            "tool_surface": (
                "the charter's ~150-170 end-state count was a planning estimate, not an "
                "acceptance threshold; the shipped task-driven T1 surface is 91 "
                "agent-visible tools plus 11 non-discoverable simulator/migration operations. "
                "All 2,324 admitted task walks close over that surface, while the plan's own "
                "T2 rule forbids adding endpoints no task exercises"
            ),
            "calibration": (
                f"{checkpoint['episodes_valid']}/{checkpoint['episodes_required']} valid "
                "single-model episodes under one frozen protocol"
            ),
            "friction_schedule": (
                f"world-v19 freezes the legacy deterministic (tool, call-index) schedule; "
                f"the production sweep observed {100 * sweep_health['friction']['rate']:.2f}% "
                f"against the configured {100 * sweep_health['friction']['expectedRate']:.2f}% "
                "and keeps the drift alert public. Changing schedule scope requires a new "
                "world/protocol namespace, never a mid-denominator runtime edit"
            ),
        },
        "handoff": {
            "world_server_command": (
                "python3 world/local/server.py --port 8988 --world "
                "world/blobfish/world-v19.json --v2-contracts mcp/v3/contracts"
            ),
            "resume_command": checkpoint["resume_command"],
            "episodes_committed": checkpoint["episodes_valid"],
            "episodes_required": checkpoint["episodes_required"],
            "do_not_mix_engines": True,
        },
    }
    return report


def render(report: dict[str, Any]) -> str:
    status = report["status"].upper().replace("_", " ")
    lines = [
        "# LAB-Superset program status",
        "",
        f"Program exit: **{status}**.",
        "",
        (
            f"Local implementation: **{'complete' if report['local_implementation_complete'] else 'incomplete'}**. "
            f"Milestones passed: **{report['milestones_passed']}/{report['milestones_total']}**."
        ),
        "",
        "This is generated from the committed gate artifacts. A milestone is green only when every listed binary check is green; CI executes the corresponding commands and rejects stale output.",
        "",
        "## Milestone gates",
        "",
        "| Milestone | Status | Checks | Evidence summary |",
        "|---|---|---:|---|",
    ]
    for item in report["milestones"]:
        evidence = "; ".join(row["measure"] for row in item["checks"])
        lines.append(
            f"| {item['id']} · {item['name']} | `{item['status']}` | "
            f"{item['checks_passed']}/{item['checks_total']} | {evidence} |"
        )

    lines.extend(["", "## Open gate", ""])
    if not report["open_gates"]:
        lines.append("None. The program exit gate is ready.")
    else:
        for row in report["open_gates"]:
            lines.append(f"- `{row['milestone']}/{row['check']}`: {row['measure']}.")
            blocker = row.get("blocker") or {}
            if blocker:
                lines.append(
                    f"  External blocker: {blocker['message']} (HTTP {blocker['provider_status']}). "
                    f"Recommended top-up: **${blocker['recommended_top_up_usd']}**."
                )

    lines.extend([
        "",
        "## Denominators that must not be conflated",
        "",
    ])
    for name, note in report["denominator_notes"].items():
        lines.append(f"- `{name}`: {note}.")

    lines.extend([
        "",
        "## Exact resume handoff",
        "",
        "Start or retain the pinned world server:",
        "",
        "```bash",
        report["handoff"]["world_server_command"],
        "```",
        "",
        "After the provider balance is available, resume the same model/protocol denominator:",
        "",
        "```bash",
        report["handoff"]["resume_command"],
        "```",
        "",
        (
            f"Do not mix another engine into the {report['handoff']['episodes_committed']:,} "
            "committed DeepSeek episodes. A provider switch requires a fresh "
            f"{report['handoff']['episodes_required']:,}-episode namespace."
        ),
        "",
        "## Rebuild and verify",
        "",
        "```bash",
        "python3 tools/build_program_exit_audit.py --check",
        "python3 tools/check_program_exit_audit.py",
        "```",
        "",
    ])
    return "\n".join(lines)


def outputs() -> dict[Path, str]:
    report = build()
    return {
        OUTPUT: json.dumps(report, indent=2, sort_keys=True) + "\n",
        DOC: render(report),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = outputs()
    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, value in expected.items()
            if not path.exists() or path.read_text() != value
        ]
        if stale:
            print("stale program-exit artifacts: " + ", ".join(stale))
            return 1
    else:
        for path, value in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
    report = json.loads(expected[OUTPUT])
    print(
        f"program exit audit: {report['milestones_passed']}/{report['milestones_total']} "
        f"milestones, status={report['status']}, open={len(report['open_gates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
