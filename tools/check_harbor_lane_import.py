#!/usr/bin/env python3
"""Prove Harbor lane evidence remains separate from pass^k denominators."""

from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="harbor-lane-import-") as temporary:
        base = Path(temporary)
        world = base / "world.json"
        world.write_text(json.dumps({"world": {
            "version": 19,
            "tasks": [{
                "task_id": "fixture_task", "capability_type": 5,
                "method": "fixture", "walk": ["read", "write"],
            }],
            "task_taxonomy": {"types": {str(i): f"capability_{i}" for i in range(1, 11)}},
        }}))
        job = base / "job"
        trial = job / "fixture_task__abc"
        (trial / "verifier").mkdir(parents=True)
        result = {
            "trial_name": "fixture_task__abc",
            "task_id": {"path": "tasks/fixture_task"},
            "task_checksum": "fixture-sha",
            "agent_info": {"name": "fixture-agent", "model_info": {"name": "fixture-model"}},
            "agent_result": {"cost_usd": 0.01},
            "verifier_result": {"rewards": {
                "reward": 0.0, "passed": 0.0, "file_passed": 1.0,
                "state_passed": 0.0, "lane_split": 1.0,
            }},
            "exception_info": None,
            "started_at": "2026-08-12T00:00:00Z",
            "finished_at": "2026-08-12T00:00:01Z",
        }
        (trial / "result.json").write_text(json.dumps(result))
        (trial / "verifier" / "file-lane.json").write_text(json.dumps({
            "file_passed": True, "state_passed": False, "lane_split": True,
        }))
        (trial / "verifier" / "verdict.json").write_text(json.dumps({
            "passed": False, "reward": 0.0, "precision": 1.0, "recall": 1.0,
        }))
        lanes = base / "lanes"
        import_command = [
            "node", "sim/import-harbor-lanes.mjs", "--job", str(job),
            "--engine", "deepseek-chat", "--namespace", "fixture",
            "--world", str(world), "--out", str(lanes), "--episode", "1",
        ]
        subprocess.run(import_command, cwd=ROOT, check=True, capture_output=True, text=True)
        imported = json.loads((lanes / "fixture_task-h1.json").read_text())
        assert imported["fileLane"]["file_passed"] is True
        assert imported["fileLane"]["state_passed"] is False
        first = (lanes / "fixture_task-h1.json").read_bytes()
        subprocess.run(import_command, cwd=ROOT, check=True, capture_output=True, text=True)
        assert (lanes / "fixture_task-h1.json").read_bytes() == first

        episodes = base / "episodes"
        episodes.mkdir()
        for index, passed in enumerate((True, True, False), 1):
            (episodes / f"fixture_task-t{index}.json").write_text(json.dumps({
                "taskId": "fixture_task", "worldVersion": 19,
                "passed": passed, "reward": 1.0 if passed else 0.0,
                "toolCalls": 2, "toolScope": {"mode": "all"},
                "measurementProtocol": "v19-all-tools-fixed50-context-v4",
            }))
        triage = base / "triage.json"
        triage.write_text(json.dumps({"labels": {"fixture_task": {"label": "boundary"}}}))
        output = base / "leaderboard.json"
        subprocess.run([
            "node", "sim/build-leaderboard-v2.mjs", "--engine", "deepseek-chat",
            "--namespace", "fixture", "--world", str(world),
            "--episodes", str(episodes), "--harbor-lanes", str(lanes),
            "--triage", str(triage), "--out", str(output),
        ], cwd=ROOT, check=True, capture_output=True, text=True)
        report = json.loads(output.read_text())
        assert report["coverage"]["episodesFound"] == 3
        assert report["coverage"]["tasksWithThreeEpisodes"] == 1
        assert report["laneSplit"]["eligibleEpisodes"] == 1
        assert report["laneSplit"]["filePassStateFail"] == 1
        assert report["harborLaneInput"]["files"] == 1
        assert report["tasks"][0]["laneEpisodeFiles"]

    print("Harbor lane import: separate feed is deterministic and cannot alter pass^k denominators")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
