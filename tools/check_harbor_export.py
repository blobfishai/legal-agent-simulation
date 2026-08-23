#!/usr/bin/env python3
"""Deterministically audit a generated Harbor task export."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tomllib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PINNED_PYTHON = (
    "python:3.12-slim@sha256:"
    "229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_inventory(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        fail(f"required source/export tree missing: {root}")
    result: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            fail(f"symlink forbidden in Harbor export: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
    return result


def assert_tree_equal(exported: Path, source: Path, label: str) -> int:
    exported_files = file_inventory(exported)
    source_files = file_inventory(source)
    if set(exported_files) != set(source_files):
        fail(f"{label}: file paths differ")
    for relative, exported_path in exported_files.items():
        source_path = source_files[relative]
        if exported_path.stat().st_size != source_path.stat().st_size:
            fail(f"{label}: byte count differs for {relative}")
        if not os.path.samefile(exported_path, source_path):
            if sha256_file(exported_path) != sha256_file(source_path):
                fail(f"{label}: SHA-256 differs for {relative}")
    return len(exported_files)


def resolve_source(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def skills_source(config: dict[str, Any]) -> Path:
    configured = config.get("skills_source")
    if configured:
        return resolve_source(str(configured))
    candidate = ROOT / "research" / "repos" / "harveyai@harvey-labs" / "harness" / "skills"
    if candidate.is_dir():
        return candidate.resolve()
    return (ROOT / "research" / "harvey-recovery" / "skills").resolve()


def assert_executable(path: Path) -> None:
    if not path.is_file() or not (path.stat().st_mode & stat.S_IXUSR):
        fail(f"required executable missing or not executable: {path}")


def audit_task(
    directory: Path,
    task: dict[str, Any],
    world_image: str,
    lab_image: str,
) -> tuple[int, int, int]:
    task_id = task["task_id"]
    manifest_path = directory / "task.toml"
    try:
        manifest = tomllib.loads(manifest_path.read_text("utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        fail(f"{task_id}: invalid task.toml: {error}")
    metadata = manifest.get("metadata") or {}
    if metadata.get("task_id") != task_id:
        fail(f"{task_id}: manifest task ID mismatch")
    if metadata.get("world_image") != world_image:
        fail(f"{task_id}: world image reference mismatch")
    expected_file_lane = bool(task.get("file_lane"))
    if metadata.get("file_lane") is not expected_file_lane:
        fail(f"{task_id}: file-lane metadata mismatch")

    environment = directory / "environment"
    for relative in ("Dockerfile", "tool", "docker-compose.yaml"):
        if not (environment / relative).is_file():
            fail(f"{task_id}: missing environment/{relative}")
    assert_executable(environment / "tool")
    dockerfile = (environment / "Dockerfile").read_text("utf-8")
    expected_from = lab_image if expected_file_lane else PINNED_PYTHON
    if f"FROM {expected_from}" not in dockerfile:
        fail(f"{task_id}: agent base image mismatch")
    compose = (environment / "docker-compose.yaml").read_text("utf-8")
    if f"image: {world_image}" not in compose or "TASK_ID" not in compose:
        fail(f"{task_id}: compose world routing mismatch")

    phases = (task.get("multi_step") or {}).get("phases") or []
    if phases:
        manifest_steps = manifest.get("steps") or []
        expected_names = [phase["name"] for phase in phases]
        if [step.get("name") for step in manifest_steps] != expected_names:
            fail(f"{task_id}: multistep manifest topology mismatch")
        if (directory / "instruction.md").exists():
            fail(f"{task_id}: multistep task leaked a top-level instruction")
        for name in expected_names:
            step = directory / "steps" / name
            if not (step / "instruction.md").is_file():
                fail(f"{task_id}/{name}: instruction missing")
            assert_executable(step / "tests" / "test.sh")
            assert_executable(step / "solution" / "solve.sh")
    else:
        if not (directory / "instruction.md").is_file():
            fail(f"{task_id}: instruction missing")
        assert_executable(directory / "tests" / "test.sh")
        assert_executable(directory / "solution" / "solve.sh")

    staged_documents = 0
    staged_skills = 0
    if expected_file_lane:
        config = task["file_lane"]
        staged_documents = assert_tree_equal(
            environment / "documents",
            resolve_source(str(config["documents_source"])),
            f"{task_id}: staged input documents",
        )
        wanted_skills = list(config["skills"] if "skills" in config else ("docx", "xlsx", "pptx"))
        exported_skill_root = environment / "skills"
        exported_skill_names = sorted(
            path.name for path in exported_skill_root.iterdir() if path.is_dir()
        ) if exported_skill_root.is_dir() else []
        if exported_skill_names != sorted(wanted_skills):
            fail(f"{task_id}: staged skill names differ from the task contract")
        source_skill_root = skills_source(config)
        for name in wanted_skills:
            assert_tree_equal(
                exported_skill_root / name,
                source_skill_root / name,
                f"{task_id}: staged {name} skill",
            )
        staged_skills = len(exported_skill_names)
    return staged_documents, staged_skills, len(phases)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--world", type=Path, required=True)
    parser.add_argument("--expected-tasks", type=int, required=True)
    parser.add_argument("--world-image", required=True)
    parser.add_argument("--lab-image", required=True)
    parser.add_argument("--require-all-world-tasks", action="store_true")
    parser.add_argument("--verify-evidence", action="store_true")
    args = parser.parse_args()

    export_root = args.root.resolve()
    tasks_root = export_root / "tasks"
    world_path = args.world.resolve()
    world = json.loads(world_path.read_text("utf-8"))
    world_tasks = {task["task_id"]: task for task in world["tasks"]}
    task_directories = sorted(
        path for path in tasks_root.iterdir() if path.is_dir() and (path / "task.toml").is_file()
    )
    if len(task_directories) != args.expected_tasks:
        fail(f"task directory count {len(task_directories)} != {args.expected_tasks}")
    exported_ids = {path.name for path in task_directories}
    unknown = sorted(exported_ids - set(world_tasks))
    if unknown:
        fail(f"export contains unknown task IDs: {unknown[:10]}")
    if args.require_all_world_tasks and exported_ids != set(world_tasks):
        missing = sorted(set(world_tasks) - exported_ids)
        fail(f"full export is missing canonical tasks: {missing[:10]}")
    leaked = list(tasks_root.rglob("world.json"))
    if leaked:
        fail(f"agent-side world.json leak: {leaked[0]}")

    names: set[str] = set()
    file_lanes = multistep_tasks = phase_count = document_count = skill_count = 0
    for directory in task_directories:
        manifest = tomllib.loads((directory / "task.toml").read_text("utf-8"))
        name = str((manifest.get("task") or {}).get("name"))
        if not name or name in names:
            fail(f"{directory.name}: missing or duplicate Harbor task name")
        names.add(name)
        task = world_tasks[directory.name]
        documents, skills, phases = audit_task(
            directory, task, args.world_image, args.lab_image
        )
        document_count += documents
        skill_count += skills
        file_lanes += bool(task.get("file_lane"))
        multistep_tasks += bool(phases)
        phase_count += phases

    image_world = export_root / "world-image" / "world.json"
    if sha256_file(image_world) != sha256_file(world_path):
        fail("world-image/world.json is not the canonical world byte-for-byte")
    source_contracts = resolve_source("mcp/v5/contracts")
    assert_tree_equal(
        export_root / "world-image" / "contracts",
        source_contracts,
        "world-image product contracts",
    )

    if args.verify_evidence:
        evidence = json.loads(
            (ROOT / "world" / "corpus" / "v21-production-evidence.json").read_text("utf-8")
        )
        for kind, record in sorted(evidence["indexes"].items()):
            path = export_root / "world-image" / "corpus" / kind / "index.sqlite"
            if path.stat().st_size != record["sqlite_bytes"]:
                fail(f"{kind}: packaged evidence byte count mismatch")
            if sha256_file(path) != record["sqlite_sha256"]:
                fail(f"{kind}: packaged evidence SHA-256 mismatch")

    report = {
        "tasks": len(task_directories),
        "file_lanes": file_lanes,
        "staged_documents": document_count,
        "staged_skill_trees": skill_count,
        "multistep_tasks": multistep_tasks,
        "multistep_phases": phase_count,
        "world_sha256": sha256_file(world_path),
        "agent_world_leaks": 0,
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
