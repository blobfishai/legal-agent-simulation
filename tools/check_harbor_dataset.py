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

from harbor.publisher.packager import Packager


DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def task_record(task_dir: Path) -> tuple[str, str]:
    manifest = tomllib.loads((task_dir / "task.toml").read_text("utf-8"))
    name = str((manifest.get("task") or {}).get("name") or "")
    if not name.startswith("legal-agent-simulation/"):
        raise RuntimeError(f"invalid task package name in {task_dir}")
    content_hash, _ = Packager.compute_content_hash(task_dir)
    return name, "sha256:" + content_hash


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-tasks", type=int, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    root = args.root.resolve()
    tasks_root = root / "tasks"
    task_dirs = sorted(
        path for path in tasks_root.iterdir()
        if path.is_dir() and (path / "task.toml").is_file()
    )
    if len(task_dirs) != args.expected_tasks:
        raise RuntimeError(
            f"task directory count {len(task_dirs)} != {args.expected_tasks}"
        )

    dataset_path = root / "dataset" / "dataset.toml"
    dataset = tomllib.loads(dataset_path.read_text("utf-8"))
    if (dataset.get("dataset") or {}).get("name") != "legal-agent-simulation/v21":
        raise RuntimeError("dataset package name is not legal-agent-simulation/v21")
    manifest_rows = dataset.get("tasks") or []
    manifest_records = {
        str(row.get("name")): str(row.get("digest")) for row in manifest_rows
    }
    if len(manifest_rows) != args.expected_tasks or len(manifest_records) != args.expected_tasks:
        raise RuntimeError("dataset task names are missing or duplicated")
    if not all(DIGEST.fullmatch(value) for value in manifest_records.values()):
        raise RuntimeError("dataset contains an invalid task digest")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        actual_records = dict(executor.map(task_record, task_dirs))
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

    print(json.dumps({
        "dataset": "legal-agent-simulation/v21",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "tasks": len(actual_records),
        "unique_digests": len(set(actual_records.values())),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
