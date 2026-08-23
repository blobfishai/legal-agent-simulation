#!/usr/bin/env python3
"""Structural and verifier-compilation gate for the 15 M3 workflows."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "world" / "blobfish" / "world-v18.json"
REPORT = ROOT / "world" / "v18" / "build-report.json"
ORACLE = ROOT / "data" / "oracle-v18-m3.json"
DISCRIMINATION = ROOT / "data" / "discrimination-v18-m3.json"


def main() -> int:
    raw = json.loads(WORLD.read_text("utf-8"))
    world = raw.get("world", raw)
    report = json.loads(REPORT.read_text("utf-8"))
    assert report["world_sha256"] == hashlib.sha256(WORLD.read_bytes()).hexdigest()
    assert report["added"] == {"deadlines": 5, "efiling": 5, "esign": 5}
    assert world["version"] == 18
    assert len(world["tasks"]) == len(world["verifiers"]) == report["total_tasks"]
    methods = Counter(task.get("method") for task in world["tasks"])
    assert methods["m3_efiling_workflow"] == 5
    assert methods["m3_deadline_workflow"] == 5
    assert methods["m3_esign_closing_workflow"] == 5
    verifier_by_id = {row["task_id"]: row for row in world["verifiers"]}
    m3 = [task for task in world["tasks"] if str(task.get("method") or "").startswith("m3_")]
    assert len(m3) == 15
    for task in m3:
        assert len(task["walk"]) == len(task["reference_args"])
        assert task["acceptance_label"].startswith("admitted_deterministic")
        namespace: dict = {}
        exec(verifier_by_id[task["task_id"]]["vcode"], namespace)
        assert callable(namespace.get("verify"))
    oracle = json.loads(ORACLE.read_text("utf-8"))
    assert oracle["total"] == oracle["passed"] == 15
    assert oracle["pass_rate"] == 1.0 and oracle["failures"] == []
    sweep = json.loads(DISCRIMINATION.read_text("utf-8"))
    assert sweep["summary"]["tasks"] == 15
    assert sweep["summary"]["discrimination_failures"] == []
    assert sweep["summary"]["harness_errors"] == []
    assert set(sweep["summary"]["wrong_value_inconclusive"]) == {
        f"task_v18_ef_{index:03d}" for index in range(1, 6)
    }
    assert {row["task_id"] for row in sweep["rows"]} == {task["task_id"] for task in m3}
    for row in sweep["rows"]:
        assert all(row[mode]["passed"] is False
                   for mode in ("noop", "text_only", "blind_write", "wrong_value"))
        if row["task_id"].startswith("task_v18_ef_"):
            assert row["wrong_value"]["write_errored"] is True
    print("v18 M3 workflows: 5 e-filing + 5 deadline + 5 e-signature tasks "
          "compile, solve, and reject adversarial behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
