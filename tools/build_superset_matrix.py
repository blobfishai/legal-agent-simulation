#!/usr/bin/env python3
"""Build the evidence-backed world-v19 LAB superset claim and write-up."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORLD_REPORT = ROOT / "world/v19/build-report.json"
V17_REPORT = ROOT / "world/v17/build-report.json"
# Prefer the live corpus report; fall back to the committed twin (identical by
# construction — lab_ingest writes both) so the matrix builds on CI runners
# where the gitignored corpus is absent.
_CORPUS_REPORT = ROOT / "world/corpus/lab/ingest-report.json"
_COMMITTED_REPORT = ROOT / "world/ingest/lab-ingest-report.json"
INGEST_REPORT = _CORPUS_REPORT if _CORPUS_REPORT.exists() else _COMMITTED_REPORT
ORACLE_BASE = ROOT / "data/oracle-v18.json"
ORACLE_M6 = ROOT / "data/oracle-v19-m6.json"
DISC_BASE = ROOT / "data/discrimination-v18.json"
DISC_M6 = ROOT / "data/discrimination-v19-m6.json"
FILE_LANE = ROOT / "data/harbor-v17-file-lane-smoke.json"
MULTISTEP = ROOT / "data/harbor-v19-multistep-smoke.json"
CANARY = ROOT / "data/leaderboard/canary-proof-v19.json"
TRIAGE = ROOT / "data/triage/world-v19.json"
PROGRAM_EXIT = ROOT / "data/program-exit-v19.json"
MATRIX_OUT = ROOT / "data/superset-matrix-v19.json"
DOC_OUT = ROOT / "docs/WHY-BEYOND-HARVEY-LAB.md"
CONTRACTS = ROOT / "mcp/v3/contracts"
ROUTES = ROOT / "mcp/systems.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def build() -> tuple[dict[str, Any], str]:
    world = load(WORLD_REPORT)
    v17 = load(V17_REPORT)
    ingest = load(INGEST_REPORT)
    oracle_base = load(ORACLE_BASE)
    oracle_m6 = load(ORACLE_M6)
    disc_base = load(DISC_BASE)["summary"]
    disc_m6 = load(DISC_M6)["summary"]
    file_lane = load(FILE_LANE)
    multistep = load(MULTISTEP)
    canary = load(CANARY)
    triage = load(TRIAGE)
    program_exit = load(PROGRAM_EXIT)
    contract_tools = [
        tool
        for path in sorted(CONTRACTS.glob("*.json"))
        for tool in (load(path).get("tools") or [])
    ]
    agent_tools = sum(tool.get("agent_visible") is not False for tool in contract_tools)
    internal_operations = len(contract_tools) - agent_tools
    mirrored_systems = len(load(ROUTES).get("systems") or {})

    total_tasks = int(world["total_tasks"])
    oracle_total = int(oracle_base["total"]) + int(oracle_m6["total"])
    oracle_passed = int(oracle_base["passed"]) + int(oracle_m6["passed"])
    discrimination_tasks = int(disc_base["tasks"]) + int(disc_m6["tasks"])
    discrimination_failures = len(disc_base["discrimination_failures"]) + len(disc_m6["discrimination_failures"])
    discrimination_errors = len(disc_base["harness_errors"]) + len(disc_m6["harness_errors"])
    inconclusive_keys = len(disc_base["wrong_value_inconclusive"]) + len(disc_m6["wrong_value_inconclusive"])
    fixture_files = list((ROOT / "tools/fixtures/verdicts").glob("*.json"))
    fixture_files += list((ROOT / "tools/fixtures/verdicts").glob("*.json.gz"))
    fixture_count = len({path.name.removesuffix(".gz").removesuffix(".json") for path in fixture_files})

    compiler = v17["lab_compiler"]
    criteria = int(compiler["criteria"])
    determinate = int(compiler["criteria_determinate"])
    dropped = criteria - determinate
    hosted = int(v17["lab_hosted_tasks"])
    source_tasks = hosted + int(v17["lab_quarantined_tasks"])
    parsed_documents = int(ingest["parsed_documents"])
    recovered_documents = int(ingest.get("recovered_documents", 0))
    triage_measured = sum(
        1 for row in triage.get("labels", {}).values()
        if int(row.get("episodes", 0)) >= int(triage["expected_episodes_per_task"])
    )

    instruments = [
        {
            "id": "system_of_record_state",
            "name": "System-of-record state verification",
            "status": "proven",
            "measure": f"{oracle_passed}/{oracle_total} reference walks persist the required final state",
            "proof": ["data/oracle-v18.json", "data/oracle-v19-m6.json"],
        },
        {
            "id": "file_state_split",
            "name": "Independent file/state lanes",
            "status": "proven_harness_model_measurement_pending",
            "measure": "file-only fixture produces lane_split=true and reward=0; oracle and no-op Harbor trials preserve both channels",
            "proof": ["tools/check_harbor_file_lane.py", "data/harbor-v17-file-lane-smoke.json"],
        },
        {
            "id": "bit_identical_replay",
            "name": "Bit-identical deterministic replay",
            "status": "proven" if fixture_count == total_tasks else "incomplete",
            "measure": f"{fixture_count}/{total_tasks} task verdict fixtures recorded",
            "proof": ["tools/fixtures/verdicts", "tools/check_fixtures.py"],
        },
        {
            "id": "pass_k",
            "name": "Repeated-trial pass^k and empirical difficulty",
            "status": "proven" if triage.get("complete") else "implemented_calibration_pending",
            "measure": f"{triage_measured}/{total_tasks} tasks have three usable world-v19 model episodes",
            "proof": ["data/triage/world-v19.json", "docs/TRIAGE-v19.md", "docs/leaderboard/index.html"],
        },
        {
            "id": "fault_injection",
            "name": "Seeded fault injection on vendor-shaped errors",
            "status": "proven",
            "measure": "deterministic 429/stale-reference/auth/async schedules; infrastructure errors have a separate signature",
            "proof": ["tools/check_auth_errors.py", "tools/check_sweep_health.py", "data/leaderboard/canary-proof-v19.json"],
        },
        {
            "id": "step_attribution",
            "name": "Per-step failure attribution",
            "status": "proven",
            "measure": "every episode records ordered tool, arguments, observation, outcome, and verifier conditions",
            "proof": ["sim/run-simulation.mjs", "docs/evidence/traces.html"],
        },
        {
            "id": "adversarial_admission",
            "name": "Adversarial admission gates",
            "status": "proven",
            "measure": (
                f"{discrimination_tasks}/{total_tasks} tasks tested; {discrimination_failures} broken guards/keys, "
                f"{discrimination_errors} harness errors, {inconclusive_keys} explicitly inconclusive wrong-value probes"
            ),
            "proof": ["data/discrimination-v18.json", "data/discrimination-v19-m6.json", "tools/check_gates.py"],
        },
        {
            "id": "retrieval_discipline",
            "name": "Retrieval precision/recall and paging discipline",
            "status": "proven_harness_model_measurement_pending",
            "measure": "gold-set F-beta, over-inclusion, and page-completion channels are separate verdict fields",
            "proof": ["tools/check_retrieval_grading.py", "tools/check_pagination.py", "sim/build-leaderboard-v2.mjs"],
        },
    ]

    # Program readiness is owned by the M0-M8 audit, which aggregates every
    # milestone rather than only the four headline signals used here.  Its
    # checker runs before this builder in CI and proves the artifact is current.
    blockers = [
        f"{row['milestone']}/{row['check']}: {row['measure']}"
        for row in program_exit["open_gates"]
    ]

    report = {
        "schema": "legal-agent-simulation.lab-superset-matrix.v1",
        "world": "world-v19",
        "claim": (
            "A strict operational superset of the source-grounded LAB subset that this project can "
            "grade deterministically; not a superset of LAB's prose-quality judgment."
        ),
        "program_exit_ready": not blockers,
        "program_exit_blockers": blockers,
        "program_exit_audit": {
            "status": program_exit["status"],
            "milestones_passed": program_exit["milestones_passed"],
            "milestones_total": program_exit["milestones_total"],
            "proof": "data/program-exit-v19.json",
        },
        "lab_import": {
            "source_tasks": source_tasks,
            "hosted_tasks": hosted,
            "quarantined_tasks": int(v17["lab_quarantined_tasks"]),
            "hosted_percent": round(100 * hosted / source_tasks, 2),
            "documents_binary_preserved": int(ingest["documents"]),
            "documents_text_parsed": parsed_documents,
            "documents_parse_failed": int(ingest["failed_documents"]),
            "documents_recovered": recovered_documents,
            "rubric_criteria_total_practice": criteria,
            "rubric_criteria_determinized": determinate,
            "rubric_criteria_dropped": dropped,
            "rubric_criteria_determinized_percent": pct(determinate, criteria),
            "rubric_criteria_total_all_lab": int(ingest["criteria"]),
            "judge_lane": "excluded_from_headline_and_not_implemented",
        },
        "world_scope": {
            "tasks": total_tasks,
            "capability_types": len(world["capability_counts"]),
            "tools": agent_tools,
            "internal_operations": internal_operations,
            "mirrored_systems": mirrored_systems,
            "long_horizon_capstones": int(world["added"]["capstones"]),
            "multi_turn_tasks": int(world["added"]["multi_turn"]),
            "oracle_passed": oracle_passed,
            "discrimination_tasks": discrimination_tasks,
            "fixture_tasks": fixture_count,
        },
        "instruments": instruments,
        "proof_health": {
            "canary_clean_exit": canary["clean_canary_exit"],
            "canary_seeded_defect_exit": canary["seeded_defect_exit"],
            "seeded_defect_model_episodes": canary["seeded_defect_model_episodes"],
            "harbor_capstone_reward": multistep["capstone"]["reward"]["reward"],
            "harbor_multi_turn_reward": multistep["multi_turn"]["reward"]["reward"],
            "file_lane_oracle_reward": file_lane["oracle"]["reward"],
            "file_lane_noop_reward": file_lane["nop"]["reward"],
        },
        "non_claims": [
            "No prose style, persuasion, or legal-writing-quality score is produced.",
            f"The {dropped:,} residual practice criteria are not silently treated as passing.",
            "Verbatim public LAB tasks are contamination-caveated and reported separately.",
            "iManage fidelity is capped by the public connector specification; the full API is partner-gated.",
            "Conformance applies to task-used endpoints, not every endpoint in each vendor product.",
            "The original 291 tasks include synthetic evidence; hosted LAB provenance applies only where recorded.",
        ],
    }
    return report, render_doc(report)


def render_doc(report: dict[str, Any]) -> str:
    lab = report["lab_import"]
    world = report["world_scope"]
    status = "READY" if report["program_exit_ready"] else "NOT YET READY"
    lines = [
        "# What world-v19 proves beyond Harvey LAB",
        "",
        "> **Precise claim:** this world is a strict operational superset of the source-grounded LAB subset that is mechanically determinized here. It is **not** a superset of LAB's prose-quality judgment, and it does not call an LLM judge at grade time.",
        "",
        f"Program exit status: **{status}**.",
    ]
    if report["program_exit_blockers"]:
        lines.append("")
        lines.append("Open gate(s): " + "; ".join(report["program_exit_blockers"]) + ".")

    lines.extend([
        "",
        "## Imported LAB surface",
        "",
        "| Measure | Result | Proof |",
        "|---|---:|---|",
        f"| LAB tasks hosted | {lab['hosted_tasks']:,}/{lab['source_tasks']:,} ({lab['hosted_percent']:.2f}%) | `docs/PARITY.md`, `world/v17/build-report.json` |",
        f"| LAB documents preserved as source bytes | {lab['documents_binary_preserved']:,} | `world/corpus/lab/ingest-report.json` |",
        f"| Documents text-parsed | {lab['documents_text_parsed']:,}/{lab['documents_binary_preserved']:,} | same report; {lab['documents_parse_failed']} failures and {lab['documents_recovered']} exact-hash recoveries |",
        f"| Practice criteria compiled to assertions | {lab['rubric_criteria_determinized']:,}/{lab['rubric_criteria_total_practice']:,} ({lab['rubric_criteria_determinized_percent']:.1f}%) | `world/port/determinate/lab-report.json` |",
        f"| Residual practice criteria dropped and counted | {lab['rubric_criteria_dropped']:,} | never judged or silently passed |",
        "| LAB prose-quality judge | excluded | this benchmark's headline is judge-free |",
        "",
        "Hosting and deterministic criterion coverage are different denominators. A task can preserve LAB's inputs and instruction while only its mechanically validated determinations contribute reward.",
        "",
        "## Eight additional instruments",
        "",
        "| Instrument | Status | Evidence |",
        "|---|---|---|",
    ])
    for item in report["instruments"]:
        proofs = ", ".join(f"`{path}`" for path in item["proof"])
        lines.append(f"| {item['name']} | `{item['status']}` | {item['measure']} — {proofs} |")

    lines.extend([
        "",
        "## What the executable world adds",
        "",
        f"The released world contains **{world['tasks']:,} tasks** across all **{world['capability_types']} capability types**, **{world['tools']} agent-visible tools** plus **{world['internal_operations']} non-discoverable simulator/migration operations** over **{world['mirrored_systems']} mirrored systems**, **{world['long_horizon_capstones']}** 50-call capstones, and **{world['multi_turn_tasks']}** load-bearing interruption tasks. Its reference proof is {world['oracle_passed']:,}/{world['tasks']:,}; adversarial probes cover {world['discrimination_tasks']:,}/{world['tasks']:,}.",
        "",
        "LAB asks whether a file satisfies expert-written criteria. This world additionally asks whether the agent read the right evidence, paged through all qualifying records, handled real-shaped failures, changed the correct system state, avoided collateral writes, filed the same grounded deliverable it produced, and retained corrections over a multi-phase matter.",
        "",
        "## Deterministic grading boundary",
        "",
        "The compiler validates money, dates, numbers, named entities, section references, planted issue sets, retrieval gold sets, redline diffs, and grounded anchors against the task's own evidence. Oracle and discrimination gates then prove the assertion accepts the constructed solution and rejects no-op, text-only, blind-write, and corrupted-value behavior. LLMs may propose build-time interpretations; only code can admit or grade them.",
        "",
        "This deliberately gives up argument elegance, tone, persuasion, and open-ended synthesis quality. Those are not approximated with an unreliable automatic judge.",
        "",
        "## Caveats that travel with every score",
        "",
    ])
    lines.extend(f"- {item}" for item in report["non_claims"])
    lines.extend([
        f"- {lab['documents_parse_failed']} LAB files failed text extraction; {lab['documents_recovered']} malformed upstream OOXML packages were recovered only in temporary parser derivatives, with exact paths and hashes published and source bytes preserved.",
        "- The file/state split is proven by Harbor fixtures and an oracle/no-op smoke; model-level lane-split coverage remains null until Harbor model episodes are imported.",
        "- Difficulty labels and the world-v19 pass³ headline remain provisional until `data/triage/world-v19.json` says `complete: true`.",
        "",
        "## Rebuild the claim",
        "",
        "```bash",
        "python3 tools/build_superset_matrix.py --check",
        "python3 tools/check_superset_matrix.py",
        "```",
        "",
        "Every claim above is also available in `data/superset-matrix-v19.json`; no value is maintained separately in prose.",
        "",
    ])
    return "\n".join(lines)


def outputs() -> dict[Path, str]:
    report, doc = build()
    return {
        MATRIX_OUT: json.dumps(report, indent=2, sort_keys=True) + "\n",
        DOC_OUT: doc,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, value in expected.items()
                 if not path.exists() or path.read_text() != value]
        if stale:
            print("stale superset artifacts: " + ", ".join(stale))
            return 1
        report = json.loads(expected[MATRIX_OUT])
        print(
            f"superset matrix current: {report['lab_import']['hosted_tasks']}/"
            f"{report['lab_import']['source_tasks']} LAB tasks; exit_ready="
            f"{str(report['program_exit_ready']).lower()}"
        )
        return 0
    for path, value in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    report = json.loads(expected[MATRIX_OUT])
    print(
        f"built world-v19 superset matrix; {len(report['instruments'])} instruments, "
        f"exit_ready={str(report['program_exit_ready']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
