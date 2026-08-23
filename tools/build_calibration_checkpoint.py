#!/usr/bin/env python3
"""Build/check the resumable world-v19 paid-calibration checkpoint."""

from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "world" / "blobfish" / "world-v19.json"
EPISODES = ROOT / "data" / "leaderboard" / "episodes" / "deepseek-chat" / "v19-triage"
HALT_PROOF = ROOT / "data" / "leaderboard" / "provider-halt-proof-v19.json"
RUN_HEALTH = (
    ROOT / "data" / "leaderboard" / "results" /
    "deepseek-chat@v19-triage.sweep-health.json"
)
OUTPUT = ROOT / "data" / "leaderboard" / "calibration-checkpoint-v19.json"
PROTOCOL = "v19-all-tools-fixed50-context-v4"
FILE_RE = re.compile(r"^(.+)-t([1-3])\.json\.gz$")


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)]


def read_record(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def build() -> dict[str, Any]:
    raw = json.loads(WORLD.read_text())
    world = raw.get("world", raw)
    task_ids = {task["task_id"] for task in world["tasks"]}
    required = len(task_ids) * 3
    paths = sorted(EPISODES.glob("*.json.gz"))
    digest = hashlib.sha256()
    slots: set[tuple[str, int]] = set()
    records = []
    protocol_errors = []
    for path in paths:
        match = FILE_RE.match(path.name)
        assert match, f"unexpected episode filename: {path.name}"
        task_id, episode_text = match.groups()
        episode = int(episode_text)
        assert task_id in task_ids, f"unknown task in checkpoint: {task_id}"
        assert (task_id, episode) not in slots, f"duplicate episode slot: {task_id}-t{episode}"
        slots.add((task_id, episode))
        record = read_record(path)
        if record.get("taskId") != task_id:
            protocol_errors.append(f"{path.name}: taskId")
        if record.get("worldVersion") != 19:
            protocol_errors.append(f"{path.name}: worldVersion")
        if record.get("measurementProtocol") != PROTOCOL:
            protocol_errors.append(f"{path.name}: protocol")
        if (record.get("toolScope") or {}).get("mode") != "all":
            protocol_errors.append(f"{path.name}: toolScope")
        if (record.get("model") != "deepseek-v4-flash"
                or record.get("servedModels") != ["deepseek-v4-flash"]):
            protocol_errors.append(f"{path.name}: servedModel")
        if record.get("infraError"):
            protocol_errors.append(f"{path.name}: infrastructure record")
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        records.append(record)
    assert not protocol_errors, "; ".join(protocol_errors[:20])

    costs = [float(record.get("costUsd") or 0) for record in records]
    durations = [float(record.get("durationMs") or 0) / 60_000 for record in records]
    prompt = sum(int((record.get("usage") or {}).get("prompt") or 0) for record in records)
    cache_hits = sum(int((record.get("usage") or {}).get("promptCacheHit") or 0)
                     for record in records)
    cache_misses = sum(int((record.get("usage") or {}).get("promptCacheMiss") or 0)
                       for record in records)
    ceiling = [record for record in records
               if record.get("turnsUsed") == record.get("maxTurns")]
    error_heavy = 0
    for record in ceiling:
        last = [step for step in record.get("steps") or []
                if step.get("tool") != "_final_answer"][-10:]
        errors = sum(
            step.get("ok") is False
            or re.search(r"error", str(step.get("observation") or ""), re.I) is not None
            for step in last
        )
        error_heavy += errors >= 5
    total_cost = sum(costs)
    remaining = required - len(records)
    mean_cost = total_cost / len(records) if records else None
    remaining_projection = mean_cost * remaining if mean_cost is not None else None
    # The focused one-call proof permanently tests terminal-provider
    # classification.  Once a production sweep exists, its health artifact is
    # the stronger checkpoint proof because it reconciles the complete valid
    # denominator and every excluded infrastructure outcome from that run.
    halt_path = RUN_HEALTH if RUN_HEALTH.exists() else HALT_PROOF
    halt = json.loads(halt_path.read_text()) if halt_path.exists() else None
    blocker = None
    if remaining and halt:
        halted_by = str(halt.get("haltedBy") or "")
        assert "HTTP 402" in halted_by and "Insufficient Balance" in halted_by
        classes = halt.get("classes") or {}
        assert int(classes.get("infra_error") or 0) >= 1
        if halt_path == RUN_HEALTH:
            assert classes.get("graded") == len(records)
            assert halt.get("episodes") == sum(int(value) for value in classes.values())
            assert halt.get("verifierCrashes") == 0
            assert math.isclose(
                float((halt.get("spend") or {}).get("reportedCostUsd") or 0),
                total_cost,
                abs_tol=0.00001,
            )
        assert (halt.get("canaries") or {}).get("failed") == 0
        recommended = math.ceil((remaining_projection or 0) * 1.25 / 50) * 50
        blocker = {
            "kind": "external_provider_billing",
            "provider_status": 402,
            "message": "DeepSeek API account reports Insufficient Balance",
            "proof": halt_path.relative_to(ROOT).as_posix(),
            "proof_sha256": hashlib.sha256(halt_path.read_bytes()).hexdigest(),
            "classification_proof": HALT_PROOF.relative_to(ROOT).as_posix(),
            "recommended_top_up_usd": recommended,
            "alternative": (
                "Choose another single reference model and restart all 6,972 episodes; "
                "engines cannot be mixed in one denominator."
            ),
        }

    complete = len(records) == required
    return {
        "schema_version": 1,
        "status": "complete" if complete else "paused_external_provider",
        "world": "world/blobfish/world-v19.json",
        "world_version": 19,
        "engine": "deepseek-chat",
        "served_model": "deepseek-v4-flash",
        "measurement_protocol": PROTOCOL,
        "tool_scope": "all",
        "episode_directory": EPISODES.relative_to(ROOT).as_posix(),
        "episode_sha256": digest.hexdigest(),
        "tasks": len(task_ids),
        "episodes_required": required,
        "episodes_valid": len(records),
        "episodes_remaining": remaining,
        "tasks_with_any_episode": len({task for task, _ in slots}),
        "tasks_with_three_episodes": sum(
            all((task_id, episode) in slots for episode in (1, 2, 3))
            for task_id in task_ids
        ),
        "passes": sum(record.get("passed") is True for record in records),
        "cost": {
            "actual_usd": round(total_cost, 5),
            "mean_usd_per_episode": round(mean_cost, 6) if mean_cost is not None else None,
            "remaining_projection_usd": round(remaining_projection, 2)
            if remaining_projection is not None else None,
            "full_projection_usd": round((mean_cost or 0) * required, 2)
            if records else None,
            "sweep_circuit_breaker_usd": 1500,
            "program_envelope_usd": 2000,
        },
        "usage": {
            "prompt_tokens": prompt,
            "prompt_cache_hit_tokens": cache_hits,
            "prompt_cache_miss_tokens": cache_misses,
            "cache_hit_rate": round(cache_hits / prompt, 6) if prompt else None,
        },
        "latency_minutes": {
            "p50": round(percentile(durations, 0.5) or 0, 6) if durations else None,
            "p90": round(percentile(durations, 0.9) or 0, 6) if durations else None,
            "max": round(max(durations), 6) if durations else None,
        },
        "turn_ceiling": {
            "hits": len(ceiling),
            "rate": round(len(ceiling) / len(records), 6) if records else None,
            "error_heavy_last_ten": error_heavy,
            "note": (
                "Reported as a model outcome, separate from infrastructure timeout; "
                "reference walks prove every admitted task within the fixed opportunity."
            ),
        },
        "sweep_health": {
            "proof": halt_path.relative_to(ROOT).as_posix() if halt else None,
            "episodes_seen": halt.get("episodes") if halt else None,
            "classes": halt.get("classes") if halt else None,
            "canaries": halt.get("canaries") if halt else None,
            "verifier_crashes": halt.get("verifierCrashes") if halt else None,
            "friction": halt.get("friction") if halt else None,
        },
        "external_blocker": blocker,
        "resume_command": (
            "node sim/run-leaderboard.mjs --engines deepseek-chat --tasks all --episodes 3 "
            "--concurrency 32 --world-file world/blobfish/world-v19.json "
            "--local-base http://127.0.0.1:8988 "
            "--label v19-triage --episode-namespace v19-triage --resume --retry-ungraded "
            "--compress-episodes --tool-scope all --max-cost-usd 1500 "
            "--max-episode-cost-usd 5 --min-free-disk-mb 1024 --canary-every 25"
        ),
        "complete": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(encoded)
    else:
        assert OUTPUT.exists(), f"missing {OUTPUT.relative_to(ROOT)}"
        assert OUTPUT.read_text() == encoded, "calibration checkpoint is stale"
    print(
        f"calibration checkpoint: {report['episodes_valid']}/{report['episodes_required']} valid, "
        f"${report['cost']['actual_usd']:.5f}, status={report['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
