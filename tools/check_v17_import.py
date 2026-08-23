#!/usr/bin/env python3
"""Fail-closed accounting and grading gate for the published world-v17 import."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "world" / "blobfish" / "world-v17.json"
BUILD_REPORT = ROOT / "world" / "v17" / "build-report.json"
COMPILER_REPORT = ROOT / "world" / "port" / "determinate" / "lab-report.json"
ASSERTIONS = ROOT / "world" / "port" / "determinate" / "lab-assertions.jsonl"


def load(path: Path):
    return json.loads(path.read_text("utf-8"))


def main() -> int:
    raw = load(WORLD)
    world = raw.get("world", raw)
    report = load(BUILD_REPORT)
    compiler = load(COMPILER_REPORT)

    world_bytes = WORLD.read_bytes()
    assert report["world_sha256"] == hashlib.sha256(world_bytes).hexdigest()
    assert compiler["output_sha256"] == hashlib.sha256(ASSERTIONS.read_bytes()).hexdigest()
    assert compiler["compiler_sha256"] == hashlib.sha256(
        (ROOT / "world" / "port" / "lab_determinize.py").read_bytes()).hexdigest()
    assert compiler["tasks"] == 1760 and compiler["criteria"] == 111814
    assert compiler["criteria_coverage"] >= 0.55
    assert compiler["work_types"]["contracting"]["tasks"] == 498
    assert compiler["work_types"]["contracting"]["coverage"] >= 0.55
    compiled_rows = [json.loads(line) for line in ASSERTIONS.read_text("utf-8").splitlines() if line]
    standard = [row for row in compiled_rows if row["family"] == "standard"]
    contracts = [row for row in compiled_rows if row["family"] == "contracts"]
    assert len(standard) == 1262 and len(contracts) == 498
    assert sum(row["admission"] == "compiled" for row in standard) / len(standard) >= 0.70

    tasks = world["tasks"]
    verifiers = world["verifiers"]
    task_ids = [row["task_id"] for row in tasks]
    verifier_ids = [row["task_id"] for row in verifiers]
    assert len(task_ids) == len(set(task_ids)) == report["total_tasks"]
    assert len(verifier_ids) == len(set(verifier_ids)) == report["verifiers"]
    assert set(task_ids) == set(verifier_ids)
    assert world["version"] == 17

    accounting = report["lab_source_accounting"]
    assert accounting["source_tasks"] == accounting["accounted"] == 1760
    assert not accounting["missing"] and not accounting["overlaps"]
    assert report["retrieval_tasks"] == 250
    assert report["lab_hosted_tasks"] + report["lab_quarantined_tasks"] == 2010
    assert report["lab_hosted_tasks"] / 2010 >= 0.95

    quarantine = report["practice_import"]["quarantine"]
    assert len(quarantine) == report["lab_quarantined_tasks"]
    assert all(row.get("source_task") and row.get("reason") for row in quarantine)

    imported = [row for row in tasks if row.get("method") == "harvey_lab_determinate_import"]
    retrieval = [row for row in tasks if row.get("method") == "harvey_lab_firm_knowledge_deterministic"]
    grounded = [row for row in tasks if row.get("method") == "graph_walk_grounded_lab"]
    assert len(imported) == report["practice_tasks"]
    assert len(retrieval) == 250
    assert len(grounded) == report["existing_graph_grounding"]["lab_grounded"] >= 110

    for task in imported + grounded:
        assert task["provenance"]["source_repo"] == "harveyai/harvey-labs"
        assert task["contamination"] == {
            "status": "public", "public_since": "2026", "lane": "verbatim_lab"}
        assert task["evidence_store"]["kind"] == "lab"
        assert task["file_lane"]["deliverables"]
        assert task["grading"]["kind"] == "determinate_grounding"
        if task["acceptance_label"] == "admitted_thin_excluded_headline":
            assert task["grading"]["headline_eligible"] is False
    for task in retrieval:
        assert task["evidence_store"]["kind"] == "ch"
        assert task["contamination"]["lane"] == "verbatim_lab"
        assert task["grading"]["kind"] in {"gold_set", "determinate_empty_or_anchor_set"}

    assert report["practice_import"]["headline"] + report["practice_import"]["thin"] == len(imported)
    assert report["practice_import"]["quarantined"] == len(quarantine)
    print(
        "v17 LAB import: "
        f"{report['lab_hosted_tasks']:,}/2,010 hosted, "
        f"{compiler['criteria_determinate']:,}/{compiler['criteria']:,} practice criteria determinized, "
        f"{len(quarantine)} quarantined with reasons"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
