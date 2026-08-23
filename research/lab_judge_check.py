#!/usr/bin/env python3
"""Score a deliverable against a (possibly mutated) Harvey LAB task's rubric
using the LAB mirror's own judge pipeline.

Validates that a generated task variant is still judgeable end-to-end: a
reference (oracle) deliverable should pass all or nearly all criteria; a
large failure count means the mutation broke rubric/document alignment.

Usage:
    python3 research/lab_judge_check.py \
        --task-dir research/mutations/<area>/<slug>__seed-001 \
        --deliverable research/mutations/<...>/oracle-output/memo.docx \
        [--judge-model claude-sonnet-4-6] [--parallel 6]

Reads ANTHROPIC_API_KEY (etc.) from the repo .env if not already set.
Writes judge-run/scores.json under --task-dir and prints a per-criterion
summary. Exit 0 iff every criterion passes.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "research" / "repos" / "harveyai@harvey-labs"


def load_env() -> None:
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-dir", required=True, type=Path,
                    help="dir containing task.json (original or mutated)")
    ap.add_argument("--deliverable", required=True, type=Path, nargs="+",
                    help="deliverable file(s) to judge")
    ap.add_argument("--judge-model", default="claude-sonnet-4-6")
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()

    load_env()
    sys.path.insert(0, str(LAB))
    from evaluation.judge import Judge          # noqa: E402
    from evaluation.scoring import score_rubric  # noqa: E402

    task = json.loads((args.task_dir / "task.json").read_text(encoding="utf-8"))
    run_dir = args.task_dir / "judge-run"
    out_dir = run_dir / "output"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for deliverable in args.deliverable:
        shutil.copy2(deliverable, out_dir / deliverable.name)

    judge = Judge(model=args.judge_model)
    result = score_rubric(task["criteria"], run_dir, judge, task["title"],
                          parallel=args.parallel)

    n_pass = sum(1 for c in result.criteria_results if c["verdict"] == "pass")
    n_total = len(result.criteria_results)
    (run_dir / "scores.json").write_text(json.dumps({
        "task_title": task["title"],
        "judge_model": args.judge_model,
        "score": result.score,
        "n_passed": n_pass,
        "n_criteria": n_total,
        "criteria_results": result.criteria_results,
    }, indent=2) + "\n", encoding="utf-8")

    for c in result.criteria_results:
        marker = "PASS" if c["verdict"] == "pass" else "FAIL"
        print(f"{marker} {c['id']} {c['title']}")
        if c["verdict"] != "pass":
            print(f"     reason: {c['reasoning'][:300]}")
    print(f"\nall-pass score: {result.score} | criteria: {n_pass}/{n_total}"
          f" | scores: {run_dir / 'scores.json'}")
    return 0 if n_pass == n_total and n_total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
