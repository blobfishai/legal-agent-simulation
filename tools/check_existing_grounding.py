#!/usr/bin/env python3
"""Hermetic gate for v17 grounding of the 117 legacy graph tasks."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import world.v17.ground_existing as grounding  # noqa: E402


def main() -> int:
    raw = json.loads((ROOT / "world" / "blobfish" / "world-v16.json").read_text())
    source = raw.get("world", raw)
    exact_ids = {"task_015", "task_075", "task_076", "task_085", "task_086", "task_095", "task_096"}
    exact_world = copy.deepcopy(source)
    exact_world["tasks"] = [task for task in exact_world["tasks"] if task["task_id"] in exact_ids]
    exact_world["verifiers"] = [row for row in exact_world["verifiers"] if row["task_id"] in exact_ids]
    exact = grounding.ground_existing_graph_tasks(exact_world, [])
    assert exact["exact_state"] == 7 and not exact["exceptions"]
    for verifier in exact_world["verifiers"]:
        namespace: dict = {}
        exec(verifier["vcode"], namespace)
        assert callable(namespace["verify"])

    fixture_world = {
        "tasks": [{"task_id": "legacy", "method": "graph_walk", "difficulty_tier": "medium",
                   "provenance": {"source_workflow": "harvey_lab: fixture/source"}}],
        "verifiers": [{"task_id": "legacy", "vcode": ""}],
    }
    template = {
        "task_id": "generated", "method": "harvey_lab_determinate_import", "difficulty_tier": "medium",
        "provenance": {"source_task": "fixture/source"},
        "file_lane": {"deliverables": ["answer.md"], "assertions": [{
            "criterion_id": "C-1", "deliverables": ["answer.md"], "anchor_groups": [["$54M"]],
        }]},
        "relevant_data": [{"required_document_ids": [1_700_000_000]}],
    }
    original = grounding.append_practice_tasks
    def fake_append(world, rows, existing):
        world["tasks"].append(copy.deepcopy(template))
        world["verifiers"].append({"task_id": "generated", "vcode": ""})
        return {"added": 1, "headline": 1, "thin": 0, "quarantined": 0, "quarantine": []}
    grounding.append_practice_tasks = fake_append
    try:
        result = grounding.ground_existing_graph_tasks(
            fixture_world, [{"source_task": "fixture/source"}])
    finally:
        grounding.append_practice_tasks = original
    assert result["lab_grounded"] == 1 and not result["exceptions"]
    assert fixture_world["tasks"][0]["task_id"] == "legacy"
    assert fixture_world["tasks"][0]["method"] == "graph_walk_grounded_lab"
    namespace = {}
    exec(fixture_world["verifiers"][0]["vcode"], namespace)
    assert callable(namespace["verify"])

    print("existing grounding: 7 exact-state tasks and LAB retarget regeneration pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
