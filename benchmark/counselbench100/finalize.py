#!/usr/bin/env python3
"""Consolidate execution evidence and seal a CounselBench-100 release."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

RELEASE_VERSION = "3.2.5"
DEFAULT_MODEL_JOBS: list[str] = []


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def criterion_counts(verifier: dict[str, Any]) -> tuple[int, int]:
    values = [row["passed"] for row in verifier["atomic_checks"]]
    return sum(bool(value) for value in values), len(values)


def build_model_report(release: Path, job_names: list[str]) -> dict[str, Any]:
    job_root = release / "real-agent"
    task_index = {
        row["task_id"]: row for row in read_json(release / "task-index.json")
    }
    trials: list[dict[str, Any]] = []
    for job_name in job_names:
        job = job_root / job_name
        aggregate = read_json(job / "result.json")
        if aggregate["stats"]["n_errored_trials"] != 0:
            raise ValueError(f"valid model job contains errored trials: {job}")
        for trial_dir in sorted(path for path in job.iterdir() if path.is_dir()):
            result_path = trial_dir / "result.json"
            verifier_path = trial_dir / "verifier" / "report.json"
            if not result_path.is_file() or not verifier_path.is_file():
                continue
            result = read_json(result_path)
            verifier = read_json(verifier_path)
            if result.get("exception_info") is not None:
                raise ValueError(f"trial is not a valid model execution: {trial_dir}")
            task_id = verifier["task_id"]
            info = task_index[task_id]
            criteria_passed, criteria_total = criterion_counts(verifier)
            failed_checks = sorted(
                name for name, passed in verifier["checks"].items() if not passed
            )
            trials.append(
                {
                    "task_id": task_id,
                    "practice_area": info["practice_area"],
                    "title": info["title"],
                    "job": job_name,
                    "trial_name": result["trial_name"],
                    "task_checksum": result["task_checksum"],
                    "passed": verifier["passed"],
                    "metric": verifier["metric"],
                    "score": verifier["score"],
                    "reward": verifier["reward"],
                    "category_scores": verifier["category_scores"],
                    "criteria_passed": criteria_passed,
                    "criteria_total": criteria_total,
                    "successful_tool_calls": verifier["successful_tool_calls"],
                    "documents_read": verifier["documents_read"],
                    "required_documents": verifier["required_documents"],
                    "failed_checks": failed_checks,
                    "verifier_report_sha256": verifier["report_sha256"],
                    "model": result["agent_info"]["model_info"]["name"],
                    "provider": result["agent_info"]["model_info"]["provider"],
                    "agent": result["agent_info"]["name"],
                    "agent_version": result["agent_info"]["version"],
                    "input_tokens": result["agent_result"]["n_input_tokens"],
                    "cache_tokens": result["agent_result"]["n_cache_tokens"],
                    "output_tokens": result["agent_result"]["n_output_tokens"],
                    "cost_usd": result["agent_result"]["cost_usd"],
                    "started_at": result["started_at"],
                    "finished_at": result["finished_at"],
                }
            )
    trials.sort(key=lambda row: row["task_id"])
    if len(trials) != 100:
        raise ValueError(f"expected 100 valid model trials, found {len(trials)}")
    if len({trial["task_id"] for trial in trials}) != 100:
        raise ValueError("model trials must cover every released task exactly once")
    if len({trial["practice_area"] for trial in trials}) != 10:
        raise ValueError("model trials do not cover all ten practice areas")

    gates = sorted({gate for trial in trials for gate in trial["failed_checks"]})
    report = {
        "schema_version": "counselbench.model-report.v4",
        "benchmark": "CounselBench-100",
        "benchmark_version": RELEASE_VERSION,
        "metric": "CounselScore",
        "evaluation": {
            "agent": "codex",
            "agent_version": sorted({trial["agent_version"] for trial in trials}),
            "model": sorted({trial["model"] for trial in trials}),
            "provider": sorted({trial["provider"] for trial in trials}),
            "selection": "all 100 released matters",
            "attempts_per_task": 1,
            "gold_available_to_agent": False,
            "verifier_unchanged_from_release": True,
        },
        "summary": {
            "trials": len(trials),
            "infrastructure_exceptions": 0,
            "passes": sum(bool(trial["passed"]) for trial in trials),
            "failures": sum(not trial["passed"] for trial in trials),
            "pass_rate": round(sum(bool(trial["passed"]) for trial in trials) / len(trials), 4),
            "mean_reward": round(sum(trial["reward"] for trial in trials) / len(trials), 6),
            "mean_score": round(sum(trial["score"] for trial in trials) / len(trials), 6),
            "mean_category_scores": {
                category: round(
                    sum(trial["category_scores"][category] for trial in trials) / len(trials),
                    6,
                )
                for category in sorted(trials[0]["category_scores"])
            },
            "criteria_passed": sum(trial["criteria_passed"] for trial in trials),
            "criteria_total": sum(trial["criteria_total"] for trial in trials),
            "all_required_evidence_read_trials": sum(
                trial["documents_read"] == trial["required_documents"] for trial in trials
            ),
            "minimum_successful_tool_calls": min(trial["successful_tool_calls"] for trial in trials),
            "maximum_successful_tool_calls": max(trial["successful_tool_calls"] for trial in trials),
            "total_input_tokens": sum(trial["input_tokens"] or 0 for trial in trials),
            "total_cache_tokens": sum(trial["cache_tokens"] or 0 for trial in trials),
            "total_output_tokens": sum(trial["output_tokens"] or 0 for trial in trials),
            "total_reported_cost_usd": round(sum(trial["cost_usd"] or 0 for trial in trials), 6),
        },
        "failed_gate_counts": {
            gate: sum(gate in trial["failed_checks"] for trial in trials) for gate in gates
        },
        "trials": trials,
        "excluded_runs": [],
    }
    return report


def copy_report(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def export_model_trajectories(
    release: Path, hf: Path, model_report: dict[str, Any]
) -> None:
    """Publish complete model traces alongside compact leaderboard metadata."""

    trajectory_root = hf / "trajectories" / "model"
    index: list[dict[str, Any]] = []
    for trial in model_report["trials"]:
        source = release / "real-agent" / trial["job"] / trial["trial_name"]
        destination = trajectory_root / trial["task_id"]
        files = {
            "codex.txt": source / "agent" / "codex.txt",
            "trial-result.json": source / "result.json",
            "verifier-report.json": source / "verifier" / "report.json",
        }
        optional_trajectory = source / "trajectory.json"
        if optional_trajectory.is_file():
            files["harbor-trajectory.json"] = optional_trajectory
        for name, path in files.items():
            if not path.is_file():
                raise FileNotFoundError(path)
            copy_report(path, destination / name)
        index.append(
            {
                "task_id": trial["task_id"],
                "practice_area": trial["practice_area"],
                "model": trial["model"],
                "agent": trial["agent"],
                "passed": trial["passed"],
                "reward": trial["reward"],
                "documents_read": trial["documents_read"],
                "successful_tool_calls": trial["successful_tool_calls"],
                "files": sorted(files),
            }
        )
    write_json(trajectory_root / "index.json", index)


def seal_manifest(release: Path) -> dict[str, Any]:
    manifest_path = release / "release-manifest.json"
    files = sorted(
        path
        for path in release.rglob("*")
        if path.is_file()
        and path != manifest_path
        and ".cache" not in path.relative_to(release).parts
    )
    manifest = {
        "schema_version": "1.0",
        "benchmark": "CounselBench-100",
        "version": RELEASE_VERSION,
        "files": [
            {
                "path": path.relative_to(release).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    write_json(manifest_path, manifest)
    return manifest


def finalize(arguments: argparse.Namespace) -> dict[str, Any]:
    release = arguments.release.resolve()
    hf = release / "huggingface"
    model_jobs = arguments.model_job or DEFAULT_MODEL_JOBS
    model_report = build_model_report(release, model_jobs)
    write_json(release / "reports" / "real-agent.json", model_report)
    write_json(hf / "reports" / "real-agent.json", model_report)
    export_model_trajectories(release, hf, model_report)

    evidence = {
        "provider_contract_audit": release / "reports" / "provider-contract-audit.json",
        "qualification": release / "reports" / "qualification.json",
        "harbor_all_oracle": release / "harbor-all" / "counselbench-all-oracle" / "result.json",
        "harbor_public_download_smoke": release
        / "harbor-cleanroom"
        / "published-workspace-download-smoke"
        / "result.json",
    }
    evidence.update({
        f"model_job_{index + 1}": release / "real-agent" / job_name / "result.json"
        for index, job_name in enumerate(model_jobs)
    })
    for name, path in evidence.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        copy_report(path, hf / "reports" / "raw" / f"{name}.json")

    oracle = read_json(evidence["harbor_all_oracle"])
    public_smoke = read_json(evidence["harbor_public_download_smoke"])
    qualification = read_json(evidence["qualification"])
    conformance = read_json(evidence["provider_contract_audit"])
    oracle_stats = next(iter(oracle["stats"]["evals"].values()))
    summary = {
        "schema_version": "1.1",
        "benchmark": "CounselBench-100",
        "version": RELEASE_VERSION,
        "build": read_json(release / "reports" / "build.json"),
        "qualification": {
            "passed": qualification["release_passed"],
            "executions": qualification["executions"],
            "oracle_passes": qualification["oracle"]["passes"],
            "determinism_matches": qualification["determinism"]["exact_report_matches"],
            "negative_false_accepts": sum(
                row["false_accepts"] for row in qualification["negative_controls"].values()
            ),
        },
        "provider_contract_audit": {
            "passed": conformance["passed"],
            "contract_checks": len(conformance["checks"]),
            "operation_checks": len(conformance["operation_checks"]),
        },
        "harbor_oracle": {
            "trials": oracle["n_total_trials"],
            "exceptions": oracle["stats"]["n_errored_trials"],
            "mean_reward": oracle_stats["metrics"][0]["reward"],
            "passes": len(oracle_stats["reward_stats"]["reward"]["1.0"]),
        },
        "harbor_public_download_smoke": {
            "trials": public_smoke["n_total_trials"],
            "exceptions": public_smoke["stats"]["n_errored_trials"],
            "passes": public_smoke["stats"]["n_completed_trials"],
            "mean_reward": next(
                iter(public_smoke["stats"]["evals"].values())
            )["metrics"][0]["reward"],
        },
        "real_agent": model_report["summary"],
    }
    write_json(release / "reports" / "release-summary.json", summary)
    write_json(hf / "reports" / "release-summary.json", summary)

    publication = {
        "harbor": {
            "url": arguments.harbor_url,
            "digest": arguments.harbor_digest,
        },
        "hugging_face": {
            "url": arguments.hf_url,
            "data_commit": arguments.hf_commit,
        },
        "benchmark_page": {"url": arguments.site_url, "version": arguments.site_version},
    }
    write_json(release / "reports" / "publication.json", publication)
    write_json(hf / "reports" / "publication.json", publication)
    manifest = seal_manifest(release)
    return {
        "model": model_report["summary"],
        "summary": summary,
        "manifest_sha256": manifest["manifest_sha256"],
        "file_count": len(manifest["files"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "dist" / "counselbench-100",
    )
    parser.add_argument("--harbor-url", default="https://hub.harborframework.com/datasets/blobfishai/counselbench-100")
    parser.add_argument("--harbor-digest")
    parser.add_argument("--hf-url")
    parser.add_argument("--hf-commit")
    parser.add_argument("--site-url")
    parser.add_argument("--site-version")
    parser.add_argument(
        "--model-job",
        action="append",
        help="Harbor job directory name to include; repeat for multiple jobs",
    )
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(finalize(parse_args()), indent=2, sort_keys=True))
