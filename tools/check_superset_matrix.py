#!/usr/bin/env python3
"""Fail closed on stale or overstated M7.4 superset claims."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/superset-matrix-v19.json"


def main() -> int:
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_program_exit_audit.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "tools/build_superset_matrix.py"), "--check"],
        cwd=ROOT,
        check=True,
    )
    report = json.loads(DATA.read_text())
    program = json.loads((ROOT / "data" / "program-exit-v19.json").read_text())
    v17 = json.loads((ROOT / "world" / "v17" / "build-report.json").read_text())
    ingest = json.loads((ROOT / "world" / "ingest" / "lab-ingest-report.json").read_text())
    lab = report["lab_import"]
    world = report["world_scope"]
    if len(report["instruments"]) != 8:
        raise AssertionError("the public matrix must name exactly the eight additional instruments")
    if lab["hosted_tasks"] != 2009 or lab["source_tasks"] != 2010:
        raise AssertionError("LAB task parity drift")
    if lab["rubric_criteria_determinized"] != v17["lab_compiler"]["criteria_determinate"]:
        raise AssertionError("determinized criterion count differs from the v17 build report")
    if lab["rubric_criteria_total_practice"] != v17["lab_compiler"]["criteria"]:
        raise AssertionError("practice criterion total differs from the v17 build report")
    if (
        lab["documents_binary_preserved"] != ingest["documents"]
        or lab["documents_text_parsed"] != ingest["parsed_documents"]
        or lab["documents_parse_failed"] != ingest["failed_documents"]
        or lab["documents_recovered"] != ingest["recovered_documents"]
    ):
        raise AssertionError("LAB document accounting differs from the ingest report")
    if lab["documents_parse_failed"] != 0 or lab["documents_recovered"] != 9:
        raise AssertionError("LAB extraction must be complete with nine recorded source recoveries")
    if lab["rubric_criteria_dropped"] <= 0 or lab["judge_lane"] != "excluded_from_headline_and_not_implemented":
        raise AssertionError("the report must expose dropped prose criteria and the absent judge lane")
    if world["tasks"] != 2324 or world["oracle_passed"] != 2324:
        raise AssertionError("world-v19 task/oracle accounting drift")
    if world["tools"] != 91 or world["internal_operations"] != 11 or world["mirrored_systems"] != 9:
        raise AssertionError("public tool/system accounting differs from the product contract surface")
    if not any("not a superset of lab's prose-quality judgment" in item.lower()
               for item in [report["claim"]]):
        # Preserve an explicit negative claim; a missing caveat is a build failure.
        raise AssertionError("prose-quality non-claim disappeared")
    if not report["program_exit_ready"] and not report["program_exit_blockers"]:
        raise AssertionError("an open program gate must name its blocker")
    if report["program_exit_ready"] != program["program_exit_ready"]:
        raise AssertionError("public matrix readiness disagrees with the M0-M8 program audit")
    if report["program_exit_audit"]["status"] != program["status"]:
        raise AssertionError("public matrix embeds a stale M0-M8 status")
    expected_blockers = [
        f"{row['milestone']}/{row['check']}: {row['measure']}"
        for row in program["open_gates"]
    ]
    if report["program_exit_blockers"] != expected_blockers:
        raise AssertionError("public matrix does not expose every failed M0-M8 gate")
    for item in report["instruments"]:
        for proof in item["proof"]:
            if not (ROOT / proof).exists():
                raise AssertionError(f"missing proof artifact for {item['id']}: {proof}")

    module_path = ROOT / "tools/build_superset_matrix.py"
    spec = importlib.util.spec_from_file_location("build_superset_matrix", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load matrix builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.outputs() != module.outputs():
        raise AssertionError("superset matrix is not bit-identical")
    print(
        f"superset matrix accepted: 2,009/2,010 LAB tasks, "
        f"{lab['rubric_criteria_determinized']:,} determinate criteria, "
        f"8 instruments, exit_ready={str(report['program_exit_ready']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
