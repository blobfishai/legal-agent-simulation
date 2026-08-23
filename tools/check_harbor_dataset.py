#!/usr/bin/env python3
"""Verify every full-export task digest in a Harbor dataset manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
ROOT = Path(__file__).resolve().parents[1]
DATASET_NAME = "legal-agent-simulation/v21"
DATASET_DESCRIPTION = (
    "23,310 deterministic legal-agent simulation tasks with Harbor-isolated "
    "MCP worlds, Harvey-derived file lanes, and v21 seeded documents."
)


def file_inventory(root: Path) -> dict[str, Path]:
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"required directory is missing, unsafe, or symlinked: {root}")
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in Harbor dataset input: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path
        elif not path.is_dir():
            raise RuntimeError(f"special file forbidden in Harbor dataset input: {path}")
    return files


def discover_task_directories(tasks_root: Path) -> list[Path]:
    if tasks_root.is_symlink() or not tasks_root.is_dir():
        raise RuntimeError(f"tasks root is missing, unsafe, or symlinked: {tasks_root}")
    directories: list[Path] = []
    invalid: list[str] = []
    for path in sorted(tasks_root.iterdir()):
        if path.is_symlink() or not path.is_dir() or not (path / "task.toml").is_file():
            invalid.append(path.name)
        else:
            directories.append(path)
    if invalid:
        raise RuntimeError(f"tasks root contains non-task entries: {invalid[:10]}")
    return directories


def validate_dataset_tree(dataset_root: Path) -> Path:
    files = file_inventory(dataset_root)
    expected = {"README.md", "dataset.toml"}
    if set(files) != expected:
        raise RuntimeError(
            "dataset package topology differs: "
            f"missing={sorted(expected - set(files))} "
            f"unexpected={sorted(set(files) - expected)}"
        )
    return files["dataset.toml"]


def validate_dataset_manifest(dataset: dict[str, Any], expected_tasks: int) -> list[dict]:
    if set(dataset) != {"dataset", "tasks"}:
        raise RuntimeError("dataset manifest contains missing or unknown top-level sections")
    expected_metadata = {
        "name": DATASET_NAME,
        "version": "1.0.0",
        "description": DATASET_DESCRIPTION,
        "authors": [],
        "keywords": [],
    }
    if dataset.get("dataset") != expected_metadata:
        raise RuntimeError("dataset metadata differs from the production contract")
    rows = dataset.get("tasks")
    if not isinstance(rows, list):
        raise RuntimeError("dataset tasks must be an array")
    if any(set(row) != {"name", "digest"} for row in rows if isinstance(row, dict)):
        raise RuntimeError("dataset task rows contain missing or unknown fields")
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("dataset task rows must be objects")
    if len(rows) != expected_tasks:
        raise RuntimeError(f"dataset task row count {len(rows)} != {expected_tasks}")
    names = [str(row["name"]) for row in rows]
    if names != sorted(names):
        raise RuntimeError("dataset task rows are not in canonical name order")
    return rows


def task_record(task_dir: Path, packager: Any) -> tuple[str, str, int]:
    actual_files = file_inventory(task_dir)
    manifest = tomllib.loads((task_dir / "task.toml").read_text("utf-8"))
    name = str((manifest.get("task") or {}).get("name") or "")
    expected_name = "legal-agent-simulation/" + task_dir.name.replace("_", "-")
    if name != expected_name:
        raise RuntimeError(f"invalid task package name in {task_dir}")
    content_hash, packaged_files = packager.compute_content_hash(task_dir)
    packaged = {
        path.resolve().relative_to(task_dir.resolve()).as_posix()
        for path in packaged_files
    }
    if set(actual_files) != packaged:
        raise RuntimeError(
            f"{task_dir.name}: task tree contains unpublished files: "
            f"{sorted(set(actual_files) - packaged)[:10]}"
        )
    return name, "sha256:" + content_hash, len(actual_files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-tasks", type=int, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--report", type=Path,
                        help="Optionally write the successful machine-readable audit report")
    args = parser.parse_args()

    if not 1 <= args.workers <= 128:
        parser.error("--workers must be between 1 and 128")
    if args.root.is_symlink():
        raise RuntimeError(f"dataset export root may not be a symlink: {args.root}")
    root = args.root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"dataset export root is missing: {root}")
    tasks_root = root / "tasks"
    task_dirs = discover_task_directories(tasks_root)
    if len(task_dirs) != args.expected_tasks:
        raise RuntimeError(
            f"task directory count {len(task_dirs)} != {args.expected_tasks}"
        )

    dataset_path = validate_dataset_tree(root / "dataset")
    dataset = tomllib.loads(dataset_path.read_text("utf-8"))
    manifest_rows = validate_dataset_manifest(dataset, args.expected_tasks)
    manifest_records = {
        str(row.get("name")): str(row.get("digest")) for row in manifest_rows
    }
    if len(manifest_records) != args.expected_tasks:
        raise RuntimeError("dataset task names are missing or duplicated")
    if not all(DIGEST.fullmatch(value) for value in manifest_records.values()):
        raise RuntimeError("dataset contains an invalid task digest")

    from harbor.publisher.packager import Packager

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        records = list(executor.map(lambda path: task_record(path, Packager), task_dirs))
    actual_records = {name: digest for name, digest, _ in records}
    if len(actual_records) != args.expected_tasks:
        raise RuntimeError("exported task package names are duplicated")
    if actual_records != manifest_records:
        missing = sorted(set(actual_records) - set(manifest_records))
        extra = sorted(set(manifest_records) - set(actual_records))
        changed = sorted(
            name for name in set(actual_records) & set(manifest_records)
            if actual_records[name] != manifest_records[name]
        )
        raise RuntimeError(
            f"dataset manifest differs from task packages: "
            f"missing={missing[:3]} extra={extra[:3]} changed={changed[:3]}"
        )
    if len(set(actual_records.values())) != args.expected_tasks:
        raise RuntimeError("dataset contains duplicate task content digests")

    report = {
        "schema_version": 2,
        "dataset": DATASET_NAME,
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "tasks": len(actual_records),
        "unique_digests": len(set(actual_records.values())),
        "task_package_files": sum(count for _, _, count in records),
        "task_digest_manifest_sha256": hashlib.sha256(
            "".join(
                f"{name}\0{actual_records[name]}\n" for name in sorted(actual_records)
            ).encode()
        ).hexdigest(),
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "harbor_lock_sha256": hashlib.sha256(
            (ROOT / "harbor" / "runner" / "uv.lock").read_bytes()
        ).hexdigest(),
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
