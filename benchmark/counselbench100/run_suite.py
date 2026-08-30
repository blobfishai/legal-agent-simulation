#!/usr/bin/env python3
"""Qualify every CounselBench task against oracle and adversarial trajectories."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
if not RUNTIME.exists():
    RUNTIME = HERE.parent / "world"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RUNTIME))

try:
    from builder import verification_token
except ImportError:
    import hashlib

    def verification_token(task_id: str) -> str:
        return hashlib.sha256(
            f"CounselBench-100 verifier capability::{task_id}".encode()
        ).hexdigest()

from world import CounselWorld  # noqa: E402


RELEASE_VERSION = "3.2.4"


def checked_call(world: CounselWorld, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = world.call_tool(name, deepcopy(arguments))
    if result.get("isError"):
        raise RuntimeError(f"{name} failed: {result}")
    return result


def oracle(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del spec
    for call in reference["calls"]:
        checked_call(world, call["name"], call["arguments"])


def shortcut(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Commit perfect private state and read it back without investigating."""

    del spec
    for call in reference["calls"]:
        if call.get("phase", "").startswith(("state-transition", "postwrite-readback")):
            checked_call(world, call["name"], call["arguments"])


def noop(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del world, spec, reference


def state_only(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Investigate and patch the register, but omit the note and notification."""

    del spec
    for call in reference["calls"]:
        if call.get("phase") in {
            "state-transition:decision-note",
            "state-transition:notification",
            "postwrite-readback:decision-note",
            "postwrite-readback:notification",
        }:
            continue
        checked_call(world, call["name"], call["arguments"])


def incomplete_read(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    missing = next(asset for asset in reversed(spec["provider_assets"]) if asset["material"])
    skipped = False
    for call in reference["calls"]:
        if (
            not skipped
            and call["name"] == missing["read_tool"]
            and call["arguments"] == missing["read_arguments"]
        ):
            skipped = True
            continue
        checked_call(world, call["name"], call["arguments"])


def write_before_read(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Reach the exact final state, but mutate before investigating."""

    del spec
    writes = [
        call for call in reference["calls"]
        if call.get("phase", "").startswith("state-transition")
    ]
    readbacks = [
        call for call in reference["calls"]
        if call.get("phase", "").startswith("postwrite-readback")
    ]
    investigation = [
        call for call in reference["calls"]
        if call not in writes and call not in readbacks
    ]
    for call in [*writes, *investigation, *readbacks]:
        checked_call(world, call["name"], call["arguments"])


def premature_notification(
    world: CounselWorld,
    spec: dict[str, Any],
    reference: dict[str, Any],
) -> None:
    """Investigate first, but notify the team before committing core state."""

    del spec
    writes = [
        call
        for call in reference["calls"]
        if call.get("phase", "").startswith("state-transition")
    ]
    readbacks = [
        call
        for call in reference["calls"]
        if call.get("phase", "").startswith("postwrite-readback")
    ]
    investigation = [
        call for call in reference["calls"] if call not in writes and call not in readbacks
    ]
    notification = next(
        call for call in writes if call["phase"] == "state-transition:notification"
    )
    core = [call for call in writes if call is not notification]
    for call in [*investigation, notification, *core, *readbacks]:
        checked_call(world, call["name"], call["arguments"])


def missing_readback(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del spec
    skipped = False
    for call in reference["calls"]:
        if not skipped and call.get("phase", "").startswith("postwrite-readback"):
            skipped = True
            continue
        checked_call(world, call["name"], call["arguments"])
    if not skipped:
        raise RuntimeError("reference trajectory had no post-write readback")


def rejected_mutation(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Reach the exact state, then make one rejected out-of-scope mutation."""

    oracle(world, {}, reference)
    result = world.call_tool(
        "clio_manage.matters.update",
        {"id": spec["state_contract"]["matter_id"] + 99, "data": {"description": "out of scope"}},
    )
    if not result.get("isError"):
        raise RuntimeError("out-of-scope mutation unexpectedly succeeded")


def duplicate_mutation(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Repeat a valid provider write after a correct oracle trajectory."""

    del spec
    oracle(world, {}, reference)
    call = next(
        item for item in reference["calls"]
        if item.get("phase") == "state-transition:decision-note"
    )
    checked_call(world, call["name"], call["arguments"])


def _replay_with_state(
    world: CounselWorld,
    reference: dict[str, Any],
    *,
    decision: dict[str, Any] | None = None,
    register: dict[str, Any] | None = None,
) -> None:
    for call in reference["calls"]:
        arguments = deepcopy(call["arguments"])
        if call["name"] == "clio_manage.notes.create" and decision is not None:
            detail = json.loads(arguments["data"]["detail"])
            detail["decision"] = decision
            arguments["data"]["detail"] = json.dumps(
                detail,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        if call["name"] == "clio_manage.matters.update" and register is not None:
            arguments["data"]["custom_field_values"][0]["value"] = json.dumps(
                register,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        checked_call(world, call["name"], arguments)


def wrong_value(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del spec
    decision = deepcopy(reference["decision"])
    decision["actions"][0]["owner"] = "Unapproved Owner"
    _replay_with_state(world, reference, decision=decision)


def wrong_decision(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    wrong_option = next(
        option["id"]
        for option in spec["decision_options"]
        if option["id"] != reference["decision"]["decision"]["selected_option_id"]
    )
    decision = deepcopy(reference["decision"])
    register = deepcopy(reference["register"])
    decision["decision"]["selected_option_id"] = wrong_option
    for row in register["rows"]:
        row["decision_option_id"] = wrong_option
    _replay_with_state(world, reference, decision=decision, register=register)


def wrong_branch(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del spec
    decision = deepcopy(reference["decision"])
    register = deepcopy(reference["register"])
    moved = decision["actions"].pop(0)
    decision["holds"].append(
        {
            "id": f"HOLD-{moved['portfolio_key']}",
            "portfolio_key": moved["portfolio_key"],
            "issue": moved["issue"],
            "reason": "conservative hold despite complete evidence",
            "required_next_evidence": "another reviewer",
            "source_paths": moved["source_paths"],
        }
    )
    row = next(
        item for item in register["rows"]
        if item["portfolio_key"] == moved["portfolio_key"]
    )
    row.update(
        {
            "disposition": "evidence_hold",
            "owner": None,
            "due_date": None,
            "hold_reason": "conservative hold despite complete evidence",
        }
    )
    _replay_with_state(world, reference, decision=decision, register=register)


def wrong_evidence(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """Reach the exact work product after substituting a valid but wrong source record."""

    missing = next(asset for asset in reversed(spec["provider_assets"]) if asset["material"])
    wrong = next(
        asset
        for asset in spec["provider_assets"]
        if asset["material"]
        and asset["read_tool"] == missing["read_tool"]
        and asset["evidence_id"] != missing["evidence_id"]
    )
    replaced = False
    for call in reference["calls"]:
        arguments = deepcopy(call["arguments"])
        if (
            not replaced
            and call["name"] == missing["read_tool"]
            and arguments == missing["read_arguments"]
        ):
            arguments = deepcopy(wrong["read_arguments"])
            replaced = True
        checked_call(world, call["name"], arguments)
    if not replaced:
        raise RuntimeError("reference trajectory had no uniquely required evidence read")


def keyword_stuffing(
    world: CounselWorld,
    spec: dict[str, Any],
    reference: dict[str, Any],
) -> None:
    """Include every expected token without creating distinct business rows."""

    tokens = [spec["matter_number"]]
    for row in spec["semantic_state_contract"]:
        tokens.extend(
            str(value)
            for value in (
                row["portfolio_key"],
                row["topic"],
                row["disposition"],
                row["entity_id"],
                row.get("owner"),
                row.get("due_date"),
                row.get("hold_reason"),
                row.get("required_next_evidence"),
                *row["fact_anchors"],
                *(source["resource_id"] for source in row["source_records"]),
            )
            if value is not None
        )
    stuffed = " ".join(tokens)
    for call in reference["calls"]:
        arguments = deepcopy(call["arguments"])
        if call.get("phase") == "state-transition:matter-register":
            arguments["data"]["custom_field_values"][0]["value"] = stuffed
        checked_call(world, call["name"], arguments)


Runner = Callable[[CounselWorld, dict[str, Any], dict[str, Any]], None]


def execute(
    task_dir: Path,
    runner: Runner,
    *,
    trace_destination: Path | None = None,
) -> dict[str, Any]:
    spec_path = task_dir / "environment" / "world" / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    reference = json.loads(
        (task_dir / "solution" / "reference.json").read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory(prefix=f"{spec['task_id']}-") as temporary:
        temp = Path(temporary)
        world = CounselWorld(
            task_dir / "environment" / "documents",
            temp / "output",
            temp / "state",
            spec_path,
        )
        runner(world, spec, reference)
        report = world.verify(verification_token(spec["task_id"]))
        if trace_destination:
            trace_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(world.trace_path, trace_destination)
    return report


def failed_criteria(report: dict[str, Any]) -> list[str]:
    return sorted(
        row["id"] for row in report.get("atomic_checks", []) if not row["passed"]
    )


def run(release: Path) -> dict[str, Any]:
    tasks_root = release / "harbor" / "tasks"
    hf_root = release / "huggingface"
    task_dirs = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if len(task_dirs) != 100:
        raise ValueError(f"expected 100 generated tasks, found {len(task_dirs)}")

    negative_runners: list[tuple[str, Runner]] = [
        ("noop", noop),
        ("shortcut", shortcut),
        ("state_only", state_only),
        ("incomplete_read", incomplete_read),
        ("write_before_read", write_before_read),
        ("premature_notification", premature_notification),
        ("missing_readback", missing_readback),
        ("duplicate_mutation", duplicate_mutation),
        ("rejected_mutation", rejected_mutation),
        ("wrong_value", wrong_value),
        ("wrong_decision", wrong_decision),
        ("wrong_branch", wrong_branch),
        ("wrong_evidence", wrong_evidence),
        ("keyword_stuffing", keyword_stuffing),
    ]
    oracle_passes = 0
    determinism_matches = 0
    false_accepts = {name: 0 for name, _ in negative_runners}
    failure_samples: dict[str, list[dict[str, Any]]] = {
        name: [] for name, _ in negative_runners
    }
    task_results: list[dict[str, Any]] = []
    reference_counts: list[int] = []

    for task_dir in task_dirs:
        task_id = task_dir.name
        trace_path = hf_root / "trajectories" / f"{task_id}.jsonl"
        first = execute(task_dir, oracle, trace_destination=trace_path)
        second = execute(task_dir, oracle)
        oracle_passes += int(first["passed"])
        deterministic = first == second
        determinism_matches += int(deterministic)
        reference_counts.append(first["required_tool_calls"])
        negatives: dict[str, Any] = {}
        for name, runner in negative_runners:
            result = execute(task_dir, runner)
            false_accepts[name] += int(result["passed"])
            negatives[name] = {
                "passed": result["passed"],
                "score": result["score"],
                "successful_tool_calls": result["successful_tool_calls"],
                "failed_criteria": failed_criteria(result),
                "report_sha256": result["report_sha256"],
            }
            if not result["passed"] and len(failure_samples[name]) < 3:
                failure_samples[name].append({"task_id": task_id, **negatives[name]})
        task_results.append(
            {
                "task_id": task_id,
                "oracle_passed": first["passed"],
                "oracle_score": first["score"],
                "oracle_successful_tool_calls": first["successful_tool_calls"],
                "oracle_report_sha256": first["report_sha256"],
                "second_oracle_report_sha256": second["report_sha256"],
                "deterministic_replay_match": deterministic,
                "negative_executions": negatives,
            }
        )

    report = {
        "schema_version": "counselbench.qualification.v4",
        "metric": "CounselScore",
        "benchmark": "CounselBench-100",
        "version": RELEASE_VERSION,
        "task_count": len(task_dirs),
        "executions": len(task_dirs) * (2 + len(negative_runners)),
        "oracle": {
            "executions": len(task_dirs),
            "passes": oracle_passes,
            "failures": len(task_dirs) - oracle_passes,
            "reference_tool_calls_min": min(reference_counts),
            "reference_tool_calls_max": max(reference_counts),
        },
        "determinism": {
            "replays": len(task_dirs),
            "exact_report_matches": determinism_matches,
            "mismatches": len(task_dirs) - determinism_matches,
        },
        "negative_controls": {
            name: {
                "executions": len(task_dirs),
                "false_accepts": count,
                "correct_rejections": len(task_dirs) - count,
            }
            for name, count in false_accepts.items()
        },
        "failure_samples": failure_samples,
        "release_passed": (
            oracle_passes == len(task_dirs)
            and determinism_matches == len(task_dirs)
            and not any(false_accepts.values())
        ),
        "task_results": task_results,
    }
    for target in (
        release / "reports" / "qualification.json",
        hf_root / "reports" / "qualification.json",
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "release_passed": report["release_passed"],
                "executions": report["executions"],
                "oracle": report["oracle"],
                "determinism": report["determinism"],
                "negative_controls": report["negative_controls"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release",
        type=Path,
        default=HERE.parents[1] / "dist" / "counselbench-100",
    )
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args().release)
    raise SystemExit(0 if result["release_passed"] else 1)
