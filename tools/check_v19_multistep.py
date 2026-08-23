#!/usr/bin/env python3
"""Release gate for v19 capstones and multi-turn tasks."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "world" / "blobfish" / "world-v19.json"
REPORT = ROOT / "world" / "v19" / "build-report.json"
ORACLE = ROOT / "data" / "oracle-v19-m6.json"
SWEEP = ROOT / "data" / "discrimination-v19-m6.json"
PRECORRECTION = ROOT / "data" / "precorrection-v19.json"
REPLAY = ROOT / "data" / "capstone-replay-v19.json"
HARBOR = ROOT / "data" / "harbor-v19-multistep-smoke.json"


def main() -> int:
    payload = WORLD.read_bytes()
    world = json.loads(payload).get("world") or json.loads(payload)
    report = json.loads(REPORT.read_text("utf-8"))
    assert report["world_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["base_tasks"] == 2289
    assert report["added"] == {"capstones": 5, "multi_turn": 30}
    assert report["total_tasks"] == 2324
    assert report["load_bearing_corrections"] == 35
    assert report["unclassified_capability_tasks"] == 0
    assert sum(report["capability_counts"].values()) == 2324
    assert set(report["capability_counts"]) == {str(index) for index in range(1, 11)}
    assert all(task.get("capability_type") in range(1, 11) for task in world["tasks"])
    assert all(task.get("capability_name") for task in world["tasks"])

    tasks = [task for task in world["tasks"] if task.get("method") in {
        "m6_checkpointed_capstone", "m6_native_multiturn"}]
    capstones = [task for task in tasks if task["method"] == "m6_checkpointed_capstone"]
    turns = [task for task in tasks if task["method"] == "m6_native_multiturn"]
    assert len(capstones) == 5 and len(turns) == 30
    assert all(task["capability_type"] == 10 for task in capstones)
    assert all(task["capability_type"] == 9 for task in turns)
    assert all(len(task["walk"]) == 50 for task in capstones)
    assert all(len(task["multi_step"]["phases"]) == 5 for task in capstones)
    assert all(len(task["multi_step"]["phases"]) == 2 for task in turns)
    assert all(task["multi_step"]["reward_strategy"] == "mean" for task in tasks)
    assert all(task.get("pre_correction_walk") for task in tasks)
    turn_kinds = [task["session"][0]["kind"] for task in turns]
    assert {kind: turn_kinds.count(kind) for kind in set(turn_kinds)} == {
        "fragment": 8, "correction": 8, "supersede": 7, "withdrawal": 7,
    }

    verifier_by_id = {item["task_id"]: item for item in world["verifiers"]}
    for task in tasks:
        verifier = verifier_by_id[task["task_id"]]
        namespace: dict = {}
        exec(verifier["vcode"], namespace)
        assert callable(namespace.get("verify"))
        phases = task["multi_step"]["phases"]
        assert set(verifier["phase_vcodes"]) == {phase["name"] for phase in phases}
        for vcode in verifier["phase_vcodes"].values():
            namespace = {}
            exec(vcode, namespace)
            assert callable(namespace.get("verify"))

    oracle = json.loads(ORACLE.read_text("utf-8"))
    assert oracle["total"] == oracle["passed"] == 35 and oracle["failures"] == []
    sweep = json.loads(SWEEP.read_text("utf-8"))
    assert sweep["summary"]["tasks"] == 35
    assert sweep["summary"]["discrimination_failures"] == []
    assert sweep["summary"]["harness_errors"] == []
    assert all(not row[mode]["passed"] for row in sweep["rows"]
               for mode in ("noop", "text_only", "blind_write", "wrong_value"))
    precorrection = json.loads(PRECORRECTION.read_text("utf-8"))
    assert precorrection["tasks"] == precorrection["rejected"] == 35
    assert precorrection["incorrectly_passed"] == []
    replay = json.loads(REPLAY.read_text("utf-8"))
    assert replay["tasks"] == 5 and replay["runs"] == 15
    assert replay["all_passed"] is True and replay["all_bit_identical"] is True
    harbor = json.loads(HARBOR.read_text("utf-8"))
    assert len(harbor["capstone"]["steps"]) == 5
    assert len(harbor["multi_turn"]["steps"]) == 2
    assert harbor["capstone"]["reward"]["reward"] == 1.0
    assert harbor["multi_turn"]["reward"]["reward"] == 1.0
    print("v19 M6: 5×50-call capstones and 30 native multi-turn tasks pass oracle, "
          "reject adversarial modes, and reject every superseded-instruction walk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
