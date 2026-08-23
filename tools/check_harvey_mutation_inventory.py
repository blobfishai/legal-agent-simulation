#!/usr/bin/env python3
"""Fail closed over planned and intentionally blocked Harvey mutation maps."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = ROOT / "research" / "mutation-configs"
PLAN = CONFIG_ROOT / "seed-plan.json"
STATUS = CONFIG_ROOT / "candidate-status.json"
HARVEY = ROOT / "research" / "repos" / "harveyai@harvey-labs"


def load(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing: {path}")
    return json.loads(path.read_text("utf-8"))


def fail(message: str) -> None:
    raise ValueError(message)


def regular_document_files(documents_root: Path) -> list[Path]:
    if documents_root.is_symlink() or not documents_root.is_dir():
        fail(f"planned Harvey source documents are missing or symlinked: {documents_root}")
    entries = list(documents_root.rglob("*"))
    symlink = next((path for path in entries if path.is_symlink()), None)
    if symlink is not None:
        fail(f"planned Harvey source documents contain a symlink: {symlink}")
    documents = [path for path in entries if path.is_file()]
    if not documents:
        fail(f"planned Harvey source documents are empty: {documents_root}")
    return documents


def main() -> int:
    plan = load(PLAN)
    status = load(STATUS)
    if plan.get("schema_version") != 1 or status.get("schema_version") != 1:
        fail("mutation inventory schema version is unsupported")

    planned_rows = plan.get("variants") or []
    blocked_rows = status.get("blocked") or []
    planned = {row.get("entities") for row in planned_rows}
    blocked = {row.get("entities") for row in blocked_rows}
    if None in planned or None in blocked:
        fail("every mutation candidate requires an entities path")
    if len(planned) != len(planned_rows) or len(blocked) != len(blocked_rows):
        fail("mutation candidate paths must be unique")
    if planned & blocked:
        fail(f"planned and blocked candidates overlap: {sorted(planned & blocked)}")

    entity_paths = list(CONFIG_ROOT.rglob("entities.json"))
    unsafe = [path for path in entity_paths if path.is_symlink() or not path.is_file()]
    if unsafe:
        fail(f"unsafe mutation entity maps: {unsafe}")
    discovered = {path.relative_to(CONFIG_ROOT).as_posix() for path in entity_paths}
    expected = planned | blocked
    if discovered != expected:
        fail(
            "mutation entity inventory drifted; "
            f"missing={sorted(expected - discovered)}, "
            f"unclassified={sorted(discovered - expected)}"
        )

    source_document_occurrences = 0
    generated_document_instances = 0
    for row in [*planned_rows, *blocked_rows]:
        task = row.get("task")
        entities = row["entities"]
        if not task or Path(entities).parent.as_posix() != task:
            fail(f"task/entities mismatch: task={task!r}, entities={entities!r}")
        load(CONFIG_ROOT / entities)
        source_task = HARVEY / "tasks" / task / "task.json"
        if source_task.is_symlink() or not source_task.is_file():
            fail(f"pinned Harvey source task is missing: {source_task}")
        if entities in planned:
            documents_root = source_task.parent / "documents"
            documents = regular_document_files(documents_root)
            seeds = row.get("seeds") or []
            if (
                len(seeds) != len(set(seeds))
                or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
            ):
                fail(f"planned Harvey seeds must be unique nonnegative integers: {task}")
            source_document_occurrences += len(documents)
            generated_document_instances += len(documents) * len(seeds)

    for row in blocked_rows:
        if row.get("status") != "blocked_upstream_source_defect":
            fail(f"blocked candidate has an unsupported status: {row}")
        if not row.get("reason_code") or not row.get("reason"):
            fail(f"blocked candidate lacks a reason: {row.get('task')}")

    seed_count = sum(len(row.get("seeds") or []) for row in planned_rows)
    practice_areas = {str(row["task"]).split("/", 1)[0] for row in planned_rows}
    if (
        len(planned_rows), len(practice_areas), seed_count,
        source_document_occurrences, generated_document_instances, len(blocked_rows),
    ) != (14, 12, 31, 73, 158, 2):
        fail("frozen mutation inventory totals drifted")

    print(json.dumps({
        "planned_source_tasks": len(planned_rows),
        "planned_practice_areas": len(practice_areas),
        "planned_variants": seed_count,
        "source_document_occurrences": source_document_occurrences,
        "generated_document_instances": generated_document_instances,
        "blocked_candidates": len(blocked_rows),
        "classified_entity_maps": len(discovered),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
