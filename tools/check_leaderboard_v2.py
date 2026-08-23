#!/usr/bin/env python3
"""M7.3 fixture gate and byte-identical rebuild proof."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import gzip
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="leaderboard-v2-") as temporary:
        base = Path(temporary)
        episodes = base / "episodes"
        episodes.mkdir()
        tasks = []
        triage_labels = {}
        for capability in range(1, 11):
            task_id = f"fixture_{capability:02d}"
            tasks.append({
                "task_id": task_id,
                "capability_type": capability,
                "capability_name": f"capability_{capability}",
                "method": "fixture",
                "walk": ["read", "write"],
            })
            triage_labels[task_id] = {"label": "boundary" if capability == 1 else "easy"}
            outcomes = [True, False, True] if capability == 1 else [True, True, True]
            for index, passed in enumerate(outcomes, 1):
                record = {
                    "taskId": task_id,
                    "worldVersion": 19,
                    "passed": passed,
                    "reward": 1 if passed else 0,
                    "toolCalls": 2,
                    "turnsUsed": 50 if index == 3 else 2,
                    "maxTurns": 50,
                    "toolScope": {"mode": "all"},
                    "measurementProtocol": "v19-all-tools-fixed50-context-v4",
                    "steps": [{"tool": "read", "observation": "{}"}],
                    "verdict": {"paging_complete": index != 2},
                }
                if capability == 4:
                    record["verdict"].update({
                        "precision": 0.5, "recall": 1.0, "f_beta": 0.8,
                        "over_included": ["extra"],
                    })
                if capability == 5:
                    record["fileLane"] = {
                        "file_passed": True,
                        "state_passed": index != 2,
                        "lane_split": index == 2,
                    }
                path = episodes / f"{task_id}-t{index}.json"
                if capability == 4 and index == 1:
                    gzip_path = Path(str(path) + ".gz")
                    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_path.open("wb"), mtime=0) as handle:
                        handle.write(json.dumps(record).encode())
                else:
                    path.write_text(json.dumps(record))

        # Public-LAB lane stays separate; it must not change the boundary headline.
        tasks.append({
            "task_id": "fixture_lab", "capability_type": 1,
            "capability_name": "capability_1", "method": "fixture",
            "walk": ["read"], "contamination": {"public": True},
        })
        triage_labels["fixture_lab"] = {"label": "boundary"}
        for index in range(1, 4):
            (episodes / f"fixture_lab-t{index}.json").write_text(json.dumps({
                "taskId": "fixture_lab", "worldVersion": 19,
                "passed": False, "reward": 0, "toolCalls": 1,
                "toolScope": {"mode": "all"},
                "measurementProtocol": "v19-all-tools-fixed50-context-v4",
            }))

        # Refusal is excluded; zero-call non-refusal remains a failure.
        (episodes / "fixture_02-refusal.json").write_text(json.dumps({
            "taskId": "fixture_02", "worldVersion": 19, "passed": False,
            "toolCalls": 0, "finalText": "I cannot assist with that request.",
            "toolScope": {"mode": "all"},
            "measurementProtocol": "v19-all-tools-fixed50-context-v4",
        }))
        (episodes / "fixture_03-zero.json").write_text(json.dumps({
            "taskId": "fixture_03", "worldVersion": 19, "passed": False,
            "toolCalls": 0, "finalText": "No action taken.",
            "toolScope": {"mode": "all"},
            "measurementProtocol": "v19-all-tools-fixed50-context-v4",
        }))
        (episodes / "fixture_03-old-world.json").write_text(json.dumps({
            "taskId": "fixture_03", "worldVersion": 18, "passed": True,
            "toolCalls": 1,
            "toolScope": {"mode": "all"},
            "measurementProtocol": "v19-all-tools-fixed50-context-v4",
        }))
        (episodes / "fixture_04-wrong-scope.json").write_text(json.dumps({
            "taskId": "fixture_04", "worldVersion": 19, "passed": True,
            "toolCalls": 1, "toolScope": {"mode": "systems"},
            "measurementProtocol": "v19-all-tools-fixed50-context-v4",
        }))
        (episodes / "fixture_05-wrong-protocol.json").write_text(json.dumps({
            "taskId": "fixture_05", "worldVersion": 19, "passed": True,
            "toolCalls": 1, "toolScope": {"mode": "all"},
            "measurementProtocol": "obsolete-protocol",
        }))

        world_path = base / "world.json"
        world_path.write_text(json.dumps({"world": {
            "version": 19,
            "tasks": tasks,
            "task_taxonomy": {"types": {str(index): f"capability_{index}"
                                               for index in range(1, 11)}},
        }}))
        triage_path = base / "triage.json"
        triage_path.write_text(json.dumps({"labels": triage_labels}))
        out = base / "fixture.v2.json"
        command = [
            "node", "sim/build-leaderboard-v2.mjs", "--engine", "deepseek-chat",
            "--namespace", "fixture", "--world", str(world_path),
            "--episodes", str(episodes), "--triage", str(triage_path),
            "--out", str(out),
        ]
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        first = out.read_bytes()
        report = json.loads(first)
        subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        assert out.read_bytes() == first, "leaderboard rebuild was not byte-identical"

        assert report["coverage"]["tasksDefined"] == 11
        assert report["coverage"]["refusalsExcluded"] == 1
        assert report["coverage"]["versionMismatchesExcluded"] == 1
        assert report["coverage"]["toolScopeMismatchesExcluded"] == 1
        assert report["coverage"]["measurementProtocolMismatchesExcluded"] == 1
        assert report["coverage"]["zeroCallFailures"] == 1
        assert report["headline"]["tasks"] == 1
        assert report["headline"]["passCubed"] == 0.0
        assert report["contaminatedLab"]["tasksMeasured"] == 1
        assert len(report["byCapabilityClean"]) == 10
        assert all(row["tasksMeasured"] >= 1 for row in report["byCapabilityClean"].values())
        assert report["laneSplit"]["eligibleEpisodes"] == 3
        assert report["laneSplit"]["filePassStateFail"] == 1
        assert report["pagingDiscipline"]["eligibleEpisodes"] == 30
        assert report["turnCeiling"] == {
            "tasksWithEvidence": 10,
            "eligibleEpisodes": 30,
            "hits": 10,
            "rate": 33.3,
            "note": "A ceiling hit is a terminal model outcome, reported separately from infrastructure timeouts.",
        }
        assert report["retrieval"] == {
            "tasksWithEvidence": 1,
            "meanPrecision": 50.0,
            "meanRecall": 100.0,
            "meanFBeta": 80.0,
            "overIncluded": 3,
        }
        assert all(row["episodeFiles"] for row in report["tasks"])
        type_four = next(row for row in report["tasks"] if row["taskId"] == "fixture_04")
        assert type_four["episodeFiles"][0].endswith(".json.gz")

        page = base / "index.html"
        page_command = [
            "node", "docs/leaderboard/build-v2-page.mjs",
            "--results", str(base), "--out", str(page),
        ]
        subprocess.run(page_command, cwd=ROOT, check=True, capture_output=True, text=True)
        page_first = page.read_bytes()
        subprocess.run(page_command, cwd=ROOT, check=True, capture_output=True, text=True)
        assert page.read_bytes() == page_first, "leaderboard page rebuild was not byte-identical"
        page_text = page_first.decode()
        assert "Ten-capability reliability grid" in page_text
        assert "Lane split" in page_text and "Retrieval P / R" in page_text
        assert "Turn ceiling" in page_text
        assert "fixture_01" in page_text and "e1</a>" in page_text

    print("leaderboard-v2 gate: byte-identical rebuild, pass^3, 10 capabilities, lane split, paging, P/R, contamination and refusal clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
