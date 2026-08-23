#!/usr/bin/env python3
"""Validate real Harbor multi-step smoke jobs and emit a compact proof artifact."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import json
from pathlib import Path


def validate(job: Path, expected_steps: list[str]) -> dict:
    root = json.loads((job / "result.json").read_text("utf-8"))
    stats = root.get("stats") or {}
    assert stats.get("n_completed_trials") == 1, stats
    assert all(stats.get(name) == 0 for name in (
        "n_errored_trials", "n_running_trials", "n_pending_trials", "n_cancelled_trials")), stats
    paths = sorted(job.glob("*/result.json"))
    assert len(paths) == 1, paths
    result = json.loads(paths[0].read_text("utf-8"))
    assert result.get("exception_info") is None
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    assert rewards.get("reward") == rewards.get("passed") == rewards.get("state_passed") == 1.0
    steps = result.get("step_results") or []
    assert [step.get("step_name") for step in steps] == expected_steps
    for step in steps:
        assert step.get("exception_info") is None
        step_rewards = (step.get("verifier_result") or {}).get("rewards") or {}
        assert step_rewards.get("reward") == step_rewards.get("passed") == 1.0
    return {
        "job": str(job),
        "trial": result.get("trial_name"),
        "reward": rewards,
        "steps": [{"name": step["step_name"],
                   "reward": step["verifier_result"]["rewards"]["reward"]}
                  for step in steps],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capstone", type=Path, required=True)
    parser.add_argument("--turn", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    proof = {
        "schema_version": 1,
        "capstone": validate(args.capstone, [
            "01-intake-conflicts", "02-authority", "03-file-and-confirm",
            "04-superseding-deadline", "05-closeout-billing",
        ]),
        "multi_turn": validate(args.turn, ["01-initial-review", "02-user-followup"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", "utf-8")
    print("Harbor multi-step smoke: capstone 5/5 phases and multi-turn 2/2 phases, reward=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
