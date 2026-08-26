#!/usr/bin/env python3
"""Execute every CounselBench task against positive and adversarial trajectories."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
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


def checked_call(world: CounselWorld, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = world.call_tool(name, arguments)
    if result.get("isError"):
        raise RuntimeError(f"{name} failed: {result}")
    return result


def common_discovery(world: CounselWorld) -> None:
    checked_call(world, "list_allowed_directories", {})
    checked_call(
        world,
        "directory_tree",
        {"path": "/workspace/documents", "excludePatterns": []},
    )
    checked_call(
        world,
        "search_files",
        {
            "path": "/workspace/documents",
            "pattern": "**/*.eml",
            "excludePatterns": [],
        },
    )


def write_reference_outputs(world: CounselWorld, reference: dict[str, Any]) -> None:
    checked_call(
        world,
        "write_file",
        {"path": "/workspace/output/findings.json", "content": reference["findings_text"]},
    )
    checked_call(
        world,
        "write_file",
        {"path": "/workspace/output/advice.md", "content": reference["memo_text"]},
    )


def oracle(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    common_discovery(world)
    for path in spec["required_document_paths"]:
        checked_call(world, "read_text_file", {"path": path})
    for path in spec["metadata_check_paths"]:
        checked_call(world, "get_file_info", {"path": path})
    write_reference_outputs(world, reference)


def shortcut(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    del spec
    write_reference_outputs(world, reference)


def incomplete_read(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    common_discovery(world)
    for path in spec["required_document_paths"][:-1]:
        checked_call(world, "read_text_file", {"path": path})
    for path in spec["metadata_check_paths"]:
        checked_call(world, "get_file_info", {"path": path})
    write_reference_outputs(world, reference)


def wrong_fact(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    common_discovery(world)
    for path in spec["required_document_paths"]:
        checked_call(world, "read_text_file", {"path": path})
    for path in spec["metadata_check_paths"]:
        checked_call(world, "get_file_info", {"path": path})
    wrong = json.loads(reference["findings_text"])
    wrong["findings"][0]["determination"] += " The file also establishes a $99,999,999 exposure."
    checked_call(
        world,
        "write_file",
        {
            "path": "/workspace/output/findings.json",
            "content": json.dumps(wrong, indent=2, ensure_ascii=False) + "\n",
        },
    )
    checked_call(
        world,
        "write_file",
        {"path": "/workspace/output/advice.md", "content": reference["memo_text"]},
    )


def bounded_reviewer(world: CounselWorld, spec: dict[str, Any], reference: dict[str, Any]) -> None:
    """A plausible but time-bounded baseline that stops after one-third of the record."""

    common_discovery(world)
    for path in spec["required_document_paths"][:32]:
        checked_call(world, "read_text_file", {"path": path})
    for path in spec["metadata_check_paths"][:4]:
        checked_call(world, "get_file_info", {"path": path})
    partial = json.loads(reference["findings_text"])
    partial["findings"] = partial["findings"][:4]
    memo = (
        f"# Preliminary review — {spec['matter_number']}\n\n"
        "## Executive assessment\n\nThe initial sample contains four possible exceptions.\n\n"
        "## Method and record coverage\n\nReview stopped after 32 records due to the baseline action budget.\n\n"
        "## Findings\n\nSee the partial JSON tracker.\n\n"
        "## Recommended next actions\n\nComplete the remaining review.\n\n"
        "## Assumptions and limitations\n\nThis is an incomplete synthetic benchmark work product.\n"
    )
    checked_call(
        world,
        "write_file",
        {
            "path": "/workspace/output/findings.json",
            "content": json.dumps(partial, indent=2, ensure_ascii=False) + "\n",
        },
    )
    checked_call(
        world,
        "write_file",
        {"path": "/workspace/output/advice.md", "content": memo},
    )


Runner = Callable[[CounselWorld, dict[str, Any], dict[str, Any]], None]


def execute(
    task_dir: Path,
    runner: Runner,
    *,
    trace_destination: Path | None = None,
) -> dict[str, Any]:
    spec_path = task_dir / "environment" / "world" / "spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    reference = json.loads((task_dir / "solution" / "reference.json").read_text(encoding="utf-8"))
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


def run(release: Path) -> dict[str, Any]:
    tasks_root = release / "harbor" / "tasks"
    hf_root = release / "huggingface"
    task_dirs = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if len(task_dirs) != 100:
        raise ValueError(f"expected 100 generated tasks, found {len(task_dirs)}")

    task_results: list[dict[str, Any]] = []
    oracle_passes = 0
    determinism_matches = 0
    false_accepts = {"shortcut": 0, "incomplete_read": 0, "wrong_fact": 0, "bounded_reviewer": 0}
    failure_samples: dict[str, list[dict[str, Any]]] = {name: [] for name in false_accepts}
    negative_runners: list[tuple[str, Runner]] = [
        ("shortcut", shortcut),
        ("incomplete_read", incomplete_read),
        ("wrong_fact", wrong_fact),
        ("bounded_reviewer", bounded_reviewer),
    ]

    for task_dir in task_dirs:
        task_id = task_dir.name
        trace_path = hf_root / "trajectories" / f"{task_id}.jsonl"
        first = execute(task_dir, oracle, trace_destination=trace_path)
        second = execute(task_dir, oracle)
        oracle_passes += int(first["passed"])
        deterministic = first == second
        determinism_matches += int(deterministic)
        negatives: dict[str, Any] = {}
        for name, runner in negative_runners:
            report = execute(task_dir, runner)
            false_accepts[name] += int(report["passed"])
            negatives[name] = {
                "passed": report["passed"],
                "successful_tool_calls": report["successful_tool_calls"],
                "failed_checks": sorted(
                    check for check, passed in report["checks"].items() if not passed
                ),
                "report_sha256": report["report_sha256"],
            }
            if not report["passed"] and len(failure_samples[name]) < 5:
                failure_samples[name].append({"task_id": task_id, **negatives[name]})
        task_results.append(
            {
                "task_id": task_id,
                "oracle_passed": first["passed"],
                "oracle_successful_tool_calls": first["successful_tool_calls"],
                "oracle_report_sha256": first["report_sha256"],
                "second_oracle_report_sha256": second["report_sha256"],
                "deterministic_replay_match": deterministic,
                "negative_executions": negatives,
            }
        )

    report = {
        "schema_version": "1.0",
        "benchmark": "CounselBench-100",
        "version": "1.1.0",
        "task_count": len(task_dirs),
        "executions": len(task_dirs) * (2 + len(negative_runners)),
        "oracle": {
            "executions": len(task_dirs),
            "passes": oracle_passes,
            "failures": len(task_dirs) - oracle_passes,
            "expected_tool_calls_per_task": 109,
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
    write_targets = [
        release / "reports" / "qualification.json",
        hf_root / "reports" / "qualification.json",
    ]
    for target in write_targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
