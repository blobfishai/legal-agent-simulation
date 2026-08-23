#!/usr/bin/env python3
"""Rebuild the canonical 2,331-task v20 retail/Harvey world from v19.

The checked-in overlay contains only the seven added tasks/verifiers, nine
RetailGuard tables, and changed top-level metadata.  It exists because world
snapshots are intentionally gitignored; a clean checkout must not depend on a
previous Harbor export to recover canonical v20.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASE = ROOT / "world" / "blobfish" / "world-v19.json"
DEFAULT_OVERLAY = ROOT / "world" / "v20" / "retail-overlay.json"
DEFAULT_OUTPUT = ROOT / "world" / "blobfish" / "world-v20.json"
DEFAULT_REPORT = ROOT / "world" / "v20" / "build-report.json"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text("utf-8"))
    return data.get("world", data)


def extract(base_path: Path, source_path: Path, overlay_path: Path) -> dict[str, Any]:
    base = load(base_path)
    source = load(source_path)
    base_tasks = {task["task_id"]: task for task in base["tasks"]}
    source_tasks = {task["task_id"]: task for task in source["tasks"]}
    base_verifiers = {verifier["task_id"]: verifier for verifier in base["verifiers"]}
    source_verifiers = {verifier["task_id"]: verifier for verifier in source["verifiers"]}
    for task_id, task in base_tasks.items():
        if source_tasks.get(task_id) != task:
            raise SystemExit(f"canonical v20 mutates frozen v19 task: {task_id}")
    for task_id, verifier in base_verifiers.items():
        if source_verifiers.get(task_id) != verifier:
            raise SystemExit(f"canonical v20 mutates frozen v19 verifier: {task_id}")

    base_tables = {table["name"]: table for table in base["tables"]}
    added_tables = []
    row_additions: dict[str, list[dict]] = {}
    for table in source["tables"]:
        name = table["name"]
        if name not in base_tables:
            added_tables.append(copy.deepcopy(table))
            continue
        baseline = base_tables[name]
        if table["columns"] != baseline["columns"]:
            raise SystemExit(f"canonical v20 mutates frozen table columns: {name}")
        key = next((column["name"] for column in table["columns"] if column.get("pk")), "id")
        before = {str(row.get(key)): row for row in baseline.get("sample_rows") or []}
        additions = []
        for row in table.get("sample_rows") or []:
            row_id = str(row.get(key))
            if row_id in before:
                if row != before[row_id]:
                    raise SystemExit(f"canonical v20 mutates frozen table row: {name}:{row_id}")
            else:
                additions.append(copy.deepcopy(row))
        if additions:
            row_additions[name] = additions

    metadata = {
        key: copy.deepcopy(value)
        for key, value in source.items()
        if key not in {"tables", "tasks", "verifiers"} and base.get(key) != value
    }
    added_tasks = [copy.deepcopy(task) for task in source["tasks"] if task["task_id"] not in base_tasks]
    added_verifiers = [copy.deepcopy(verifier) for verifier in source["verifiers"]
                       if verifier["task_id"] not in base_verifiers]
    overlay = {
        "schema_version": 1,
        "base": str(base_path.relative_to(ROOT)),
        "base_sha256": hashlib.sha256(base_path.read_bytes()).hexdigest(),
        "source_world_id": source["world_id"],
        "metadata": metadata,
        "added_tables": added_tables,
        "row_additions": row_additions,
        "added_tasks": added_tasks,
        "added_verifiers": added_verifiers,
    }
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(json.dumps(overlay, indent=2, sort_keys=True) + "\n", "utf-8")
    return overlay


def build(base_path: Path, overlay_path: Path, output: Path, report_path: Path) -> dict[str, Any]:
    world = copy.deepcopy(load(base_path))
    overlay = json.loads(overlay_path.read_text("utf-8"))
    actual_base_hash = hashlib.sha256(base_path.read_bytes()).hexdigest()
    if actual_base_hash != overlay["base_sha256"]:
        raise SystemExit(f"v19 base hash mismatch: {actual_base_hash} != {overlay['base_sha256']}")
    for key, value in overlay["metadata"].items():
        world[key] = copy.deepcopy(value)
    tables = {table["name"]: table for table in world["tables"]}
    for table in overlay["added_tables"]:
        if table["name"] in tables:
            raise SystemExit(f"overlay table collision: {table['name']}")
        world["tables"].append(copy.deepcopy(table))
        tables[table["name"]] = world["tables"][-1]
    for name, rows in overlay["row_additions"].items():
        table = tables[name]
        key = next((column["name"] for column in table["columns"] if column.get("pk")), "id")
        existing = {str(row.get(key)) for row in table.get("sample_rows") or []}
        for row in rows:
            row_id = str(row.get(key))
            if row_id in existing:
                raise SystemExit(f"overlay row collision: {name}:{row_id}")
            table.setdefault("sample_rows", []).append(copy.deepcopy(row))
            existing.add(row_id)
    world["tasks"].extend(copy.deepcopy(overlay["added_tasks"]))
    world["verifiers"].extend(copy.deepcopy(overlay["added_verifiers"]))
    task_ids = [task["task_id"] for task in world["tasks"]]
    verifier_ids = [verifier["task_id"] for verifier in world["verifiers"]]
    if len(task_ids) != 2331 or len(task_ids) != len(set(task_ids)):
        raise SystemExit(f"canonical v20 task count/uniqueness failure: {len(task_ids)}")
    if len(verifier_ids) != 2331 or set(verifier_ids) != set(task_ids):
        raise SystemExit("canonical v20 verifier coverage failure")
    payload = json.dumps(world, ensure_ascii=False, separators=(",", ":")) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, "utf-8")
    report = {
        "schema_version": 1,
        "base_tasks": 2324,
        "added_tasks": len(overlay["added_tasks"]),
        "added_verifiers": len(overlay["added_verifiers"]),
        "added_tables": len(overlay["added_tables"]),
        "total_tasks": len(task_ids),
        "total_verifiers": len(verifier_ids),
        "world_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "world_bytes": len(payload.encode()),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--extract-from", type=Path)
    arguments = parser.parse_args()
    if arguments.extract_from:
        overlay = extract(arguments.base, arguments.extract_from, arguments.overlay)
        print(json.dumps({"added_tasks": len(overlay["added_tasks"]),
                          "added_tables": len(overlay["added_tables"]),
                          "overlay": str(arguments.overlay)}, sort_keys=True))
        return 0
    print(json.dumps(build(arguments.base, arguments.overlay, arguments.out, arguments.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
