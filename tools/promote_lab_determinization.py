#!/usr/bin/env python3
"""Validate a complete LAB compile and atomically publish its two artifacts."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import json
import os
import shutil
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from world.port import lab_determinize  # noqa: E402


DESTINATION = ROOT / "world" / "port" / "determinate"


def validate(source: Path) -> dict:
    assertions = source / "lab-assertions.jsonl"
    report_path = source / "lab-report.json"
    lab_determinize.check(ROOT / "world" / "corpus" / "lab", assertions, report_path)
    report = json.loads(report_path.read_text("utf-8"))
    assert report["compiler_version"] == lab_determinize.COMPILER_VERSION
    assert report["limited"] is False
    assert report["tasks"] == 1760
    assert report["criteria"] == 111814
    assert report["criteria_coverage"] >= 0.55
    assert report["work_types"]["contracting"]["tasks"] == 498
    assert report["work_types"]["contracting"]["coverage"] >= 0.55

    task_ids: set[str] = set()
    sources: set[str] = set()
    criteria = determinate = assertions_count = 0
    standard_tasks = standard_headline = contracts_tasks = 0
    with assertions.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            assert row["task_id"] not in task_ids, f"duplicate task id on line {line_number}"
            assert row["source_task"] not in sources, f"duplicate source task on line {line_number}"
            task_ids.add(row["task_id"])
            sources.add(row["source_task"])
            if row["family"] == "standard":
                standard_tasks += 1
                standard_headline += row["admission"] == "compiled"
            elif row["family"] == "contracts":
                contracts_tasks += 1
            criteria += row["criteria_total"]
            determinate += row["criteria_determinate"]
            assertions_count += row["assertion_count"]
            assert row["criteria_determinate"] == len(row["criteria"])
            assert row["coverage"] == round(row["criteria_determinate"] / max(1, row["criteria_total"]), 8)
            for criterion in row["criteria"]:
                assert criterion["discrimination"] == {"reference_passes": True, "corrupted_fails": True}
                assert criterion["assertions"]
                for assertion in criterion["assertions"]:
                    assert assertion["variants"]
                    assert len(assertion["source_files"]) == 1
                    relative = PurePosixPath(assertion["source_files"][0]["relative_path"])
                    assert not relative.is_absolute() and ".." not in relative.parts
    assert len(task_ids) == report["tasks"]
    assert contracts_tasks == 498 and standard_tasks == 1262
    assert standard_headline / standard_tasks >= 0.70
    assert (criteria, determinate, assertions_count) == (
        report["criteria"], report["criteria_determinate"], report["assertions"])
    return report


def promote(source: Path) -> dict:
    report = validate(source)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name in ("lab-assertions.jsonl", "lab-report.json"):
        destination = DESTINATION / name
        temporary = destination.with_suffix(destination.suffix + ".promoting")
        shutil.copyfile(source / name, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        temporary.replace(destination)
    lab_determinize.check(ROOT / "world" / "corpus" / "lab",
                          DESTINATION / "lab-assertions.jsonl",
                          DESTINATION / "lab-report.json")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    report = validate(args.source.resolve()) if args.check_only else promote(args.source.resolve())
    action = "validated" if args.check_only else "promoted"
    print(f"LAB determinization {action}: {report['tasks']:,} tasks, "
          f"{report['criteria_coverage']:.1%} criteria coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
