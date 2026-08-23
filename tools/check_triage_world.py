#!/usr/bin/env python3
"""Pure fixture gate for M7.2 triage rules."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import importlib.util
import gzip
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("triage_world", ROOT / "tools" / "triage_world.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


def episode(passed: bool, calls: int, conditions=()):
    return {"passed": passed, "toolCalls": calls,
            "failedConditions": list(conditions), "worldVersion": 19}


task = {"task_id": "fixture", "walk": ["read", "write"]}
assert module.classify_task(task, [episode(True, 2)] * 3)["label"] == "easy"
assert module.classify_task(task, [episode(True, 7)] * 3)["label"] == "medium"
assert module.classify_task(task, [episode(True, 2), episode(False, 2, ["x"]), episode(True, 3)])["label"] == "boundary"
assert module.classify_task(task, [
    episode(False, 2, ["a"]), episode(False, 2, ["b"]), episode(False, 2, ["c"]),
])["label"] == "hard"
suspect = module.classify_task(task, [
    episode(False, 2, ["shared", "a"]),
    episode(False, 2, ["shared", "b"]),
    episode(False, 2, ["shared", "c"]),
])
assert suspect["label"] == "suspect"
assert suspect["systematic_failed_assertions"] == ["shared"]
assert module.classify_task(task, [episode(True, 2)] * 2)["label"] == "unmeasured"
assert module.usable({"infraError": True}, 19) == (False, "infrastructure")
assert module.usable({"toolCalls": 0, "finalText": "I cannot assist with this."}, 19) == (False, "refusal")
assert module.usable({"toolCalls": 0, "finalText": "No action taken.", "worldVersion": 19}, 19) == (True, "measured")
assert module.usable({"toolCalls": 1, "worldVersion": 18}, 19) == (False, "wrong_world_version")
assert module.usable({"toolCalls": 1, "worldVersion": 19,
                      "toolScope": {"mode": "systems"}}, 19, "all") == (False, "wrong_tool_scope")
assert module.usable({"toolCalls": 1, "worldVersion": 19,
                      "toolScope": {"mode": "all"}}, 19, "all", module.DEFAULT_PROTOCOL) == (False, "wrong_measurement_protocol")

with tempfile.TemporaryDirectory(prefix="triage-gzip-") as temporary:
    root = Path(temporary)
    raw = {"taskId": "fixture", "passed": True, "toolCalls": 2, "worldVersion": 19,
           "toolScope": {"mode": "all"}}
    raw["measurementProtocol"] = module.DEFAULT_PROTOCOL
    gzip_path = root / "fixture-t1.json.gz"
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_path.open("wb"), mtime=0) as handle:
        handle.write(json.dumps(raw).encode())
    loaded, excluded = module.load_episodes(root, 19, "all", module.DEFAULT_PROTOCOL)
    assert loaded == {"fixture": [raw]} and not excluded
    (root / "fixture-t1.json").write_text(json.dumps(raw))
    try:
        module.episode_paths(root)
        raise AssertionError("raw/gzip collision was accepted")
    except ValueError as error:
        assert "duplicate raw/compressed" in str(error)

print("triage fixture gate: easy/medium/boundary/hard/suspect/unmeasured and exclusions clean")
