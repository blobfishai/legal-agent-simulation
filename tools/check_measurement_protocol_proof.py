#!/usr/bin/env python3
"""Verify the paid, representative acceptance proof for calibration protocol v4."""

from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "v19-all-tools-fixed50-context-v4"
PROOF_DIR = (ROOT / "data" / "leaderboard" / "protocol-proof" /
             "deepseek-chat" / PROTOCOL)
MANIFEST = PROOF_DIR / "manifest.json"
EXPECTED_TASKS = {
    "task_003", "task_157", "task_v3_001", "task_v18_deadline_001",
    "task_v18_ef_001", "task_v18_esign_001", "task_v19_capstone_001",
    "task_v19_turn_001", "lab_fk_001", "labp_386a313d37374789",
}


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    episode_paths = sorted(PROOF_DIR.glob("*.json.gz"))
    records = [read_gzip_json(path) for path in episode_paths]
    task_ids = [str(record.get("taskId")) for record in records]
    assert len(records) == 10, f"expected 10 proof records, found {len(records)}"
    assert set(task_ids) == EXPECTED_TASKS and len(set(task_ids)) == len(task_ids), task_ids

    rows = []
    for path, record in zip(episode_paths, records, strict=True):
        task_id = str(record["taskId"])
        assert record.get("worldVersion") == 19, task_id
        assert record.get("measurementProtocol") == PROTOCOL, task_id
        protocol = record.get("measurementProtocolConfig") or {}
        assert protocol.get("id") == PROTOCOL, task_id
        assert protocol.get("toolScope") == "all", task_id
        assert protocol.get("wallClockTimeoutMinutes") == 30, task_id
        assert (record.get("toolScope") or {}).get("mode") == "all", task_id
        assert (record.get("toolScope") or {}).get("tools") == 91, task_id
        assert record.get("model") == "deepseek-v4-flash", task_id
        assert record.get("servedModels") == ["deepseek-v4-flash"], task_id
        assert not record.get("infraError"), task_id
        assert record.get("maxTurns") == 50, task_id
        assert 1 <= int(record.get("turnsUsed") or 0) <= 50, task_id
        usage = record.get("usage") or {}
        assert usage.get("cacheBreakdownTurns") == record.get("turnsUsed"), task_id
        assert usage.get("promptUnclassified") == 0, task_id
        cost = record.get("cost") or {}
        assert cost.get("pricingAsOf") == "2026-08-12", task_id
        assert cost.get("pricingSource") == "https://api-docs.deepseek.com/quick_start/pricing/", task_id
        assert 0 <= float(record.get("costUsd") or -1) < 5, task_id
        duration = float(record.get("durationMs") or 0) / 60_000
        assert 0 < duration < 30, task_id
        rows.append({
            "task_id": task_id,
            "passed": record.get("passed") is True,
            "turns_used": record["turnsUsed"],
            "tool_calls": record.get("toolCalls"),
            "duration_minutes": round(duration, 6),
            "cost_usd": record["costUsd"],
            "file": path.name,
            "sha256": digest(path),
        })

    by_task = {row["task_id"]: row for row in rows}
    assert by_task["task_003"]["duration_minutes"] > 12
    assert any(row["turns_used"] == 50 for row in rows)
    assert any(row["turns_used"] < 50 for row in rows)

    health_path = PROOF_DIR / "sweep-health.json"
    aggregate_path = PROOF_DIR / "aggregate.json"
    health = json.loads(health_path.read_text())
    aggregate = json.loads(aggregate_path.read_text())
    assert health.get("classes") == {"graded": 10}
    assert (health.get("canaries") or {}).get("failed") == 0
    assert aggregate.get("tasksMeasured") == 10
    assert (aggregate.get("overall") or {}).get("infraErrors") == 0
    assert (aggregate.get("overall") or {}).get("refusals") == 0

    rows.sort(key=lambda row: row["task_id"])
    costs = [float(row["cost_usd"]) for row in rows]
    durations = sorted(float(row["duration_minutes"]) for row in rows)
    return {
        "schema_version": 1,
        "status": "accepted",
        "protocol": PROTOCOL,
        "world_version": 19,
        "engine": "deepseek-chat",
        "served_model": "deepseek-v4-flash",
        "episodes": len(rows),
        "graded": 10,
        "passes": sum(row["passed"] for row in rows),
        "infrastructure_errors": 0,
        "refusals": 0,
        "oracle_canaries": health["canaries"],
        "total_cost_usd": round(sum(costs), 5),
        "turn_ceiling_hits": sum(row["turns_used"] == 50 for row in rows),
        "duration_minutes": {
            "min": durations[0],
            "median": durations[len(durations) // 2],
            "max": durations[-1],
        },
        "note": (
            "The ten-family proof is an admission test, not a score. The small-sample "
            "friction-rate alert is retained in sweep-health.json and is not a protocol failure."
        ),
        "aggregate": {"file": aggregate_path.name, "sha256": digest(aggregate_path)},
        "sweep_health": {"file": health_path.name, "sha256": digest(health_path)},
        "records": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = build()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        MANIFEST.write_text(encoded)
    else:
        assert MANIFEST.exists(), f"missing {MANIFEST.relative_to(ROOT)}"
        assert MANIFEST.read_text() == encoded, "protocol proof manifest is stale"
    print(
        f"measurement-protocol proof: {report['episodes']}/10 graded, "
        f"infra=0, ${report['total_cost_usd']:.5f}, "
        f"max={report['duration_minutes']['max']:.2f}m — accepted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
