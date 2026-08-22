#!/usr/bin/env python3
"""Deep, read-only integrity audit for the local Harvey LAB input corpus.

The Harvey task tree mixes task-local ``documents/`` directories with shared
``docs_dir`` corpora.  Counting path names containing ``/documents/`` therefore
does not describe the physical input boundary.  This tool resolves every task's
actual document set, deduplicates shared paths, verifies that every input is
tracked at the checked-out Git commit, hashes every byte, and exercises each
container format.

OOXML inputs are fully decompressed so ZIP CRCs are checked, not merely opened.
The source tree is never modified.

Usage:
    python3 tools/audit_harvey_inputs.py
    python3 tools/audit_harvey_inputs.py --report reports/harvey-input-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "research" / "repos" / "harveyai@harvey-labs"
DEFAULT_REPORT = ROOT / "reports" / "harvey-input-audit.json"
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"
OOXML_REQUIRED = {
    ".docx": {"[Content_Types].xml", "_rels/.rels", "word/document.xml"},
    ".docm": {"[Content_Types].xml", "_rels/.rels", "word/document.xml"},
    ".xlsx": {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"},
    ".xlsm": {"[Content_Types].xml", "_rels/.rels", "xl/workbook.xml"},
    ".pptx": {"[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"},
    ".pptm": {"[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"},
}
CFB_EXTENSIONS = {".doc", ".xls", ".ppt"}
CFB_HEADER = bytes.fromhex("d0cf11e0a1b11ae1")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(source: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(source), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def tracked_paths(source: Path) -> set[str]:
    """Return exact Git path bytes without core.quotePath escaping."""
    payload = subprocess.run(
        ["git", "-C", str(source), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return {
        value.decode("utf-8", errors="surrogateescape")
        for value in payload.split(b"\0")
        if value
    }


def resolve_document_sets(source: Path) -> tuple[list[dict[str, Any]], dict[Path, list[str]], list[str]]:
    tasks_root = source / "tasks"
    tasks: list[dict[str, Any]] = []
    document_sets: dict[Path, list[str]] = defaultdict(list)
    errors: list[str] = []

    for task_json in sorted(tasks_root.rglob("task.json")):
        relative_task = task_json.parent.relative_to(tasks_root).as_posix()
        try:
            task = json.loads(task_json.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{task_json.relative_to(source)}: invalid task JSON: {exc}")
            continue
        setting = task.get("docs_dir")
        documents_dir = (task_json.parent / str(setting)).resolve() if setting else (
            task_json.parent / "documents"
        ).resolve()
        try:
            relative_documents = documents_dir.relative_to(source).as_posix()
        except ValueError:
            errors.append(f"{relative_task}: document set points outside source: {documents_dir}")
            continue
        if not documents_dir.is_dir():
            errors.append(f"{relative_task}: missing document set: {relative_documents}")
            continue
        document_sets[documents_dir].append(relative_task)
        tasks.append({
            "task": relative_task,
            "document_set": relative_documents,
            "shared": bool(setting),
            "criteria": len(task.get("criteria") or []),
        })
    return tasks, document_sets, errors


def validate_pdf(path: Path) -> None:
    with path.open("rb") as handle:
        if not handle.read(8).startswith(b"%PDF-"):
            raise ValueError("missing PDF header")
    subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def validate_input(path: Path) -> dict[str, Any]:
    extension = path.suffix.lower() or "(none)"
    size = path.stat().st_size
    if size == 0:
        raise ValueError("zero-byte input")
    with path.open("rb") as handle:
        header = handle.read(200)
    if header.startswith(LFS_HEADER):
        raise ValueError("Git LFS pointer, not materialized content")

    if extension in OOXML_REQUIRED:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            missing = sorted(OOXML_REQUIRED[extension] - names)
            if missing:
                raise ValueError(f"OOXML package missing {missing}")
            bad_member = archive.testzip()
            if bad_member:
                raise ValueError(f"ZIP CRC failure in {bad_member}")
    elif extension == ".pdf":
        validate_pdf(path)
    elif extension in CFB_EXTENSIONS:
        if not header.startswith(CFB_HEADER):
            raise ValueError("legacy Office file missing Compound File signature")
    elif extension == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    elif extension == ".eml":
        with path.open("rb") as handle:
            BytesParser(policy=policy.default).parse(handle, headersonly=False)
    else:
        # Other source formats are byte-hashed and checked for non-empty/LFS
        # content. Their extension is still surfaced in the report.
        pass

    return {
        "path": path,
        "bytes": size,
        "extension": extension,
        "sha256": sha256_file(path),
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    args = parser.parse_args()

    source = args.source.resolve()
    if not (source / ".git").is_dir():
        raise RuntimeError(f"Harvey mirror is not a Git worktree: {source}")

    commit = git(source, "rev-parse", "HEAD")
    tracked = tracked_paths(source)
    dirty = git(source, "status", "--porcelain", "--untracked-files=no")
    tasks, document_sets, discovery_errors = resolve_document_sets(source)

    physical_inputs: set[Path] = set()
    document_set_rows = []
    for directory, consumers in sorted(document_sets.items(), key=lambda item: str(item[0])):
        files = sorted(path for path in directory.rglob("*") if path.is_file())
        physical_inputs.update(files)
        document_set_rows.append({
            "path": directory.relative_to(source).as_posix(),
            "consumer_tasks": len(consumers),
            "physical_files": len(files),
            "shared": len(consumers) > 1,
        })

    errors = list(discovery_errors)
    missing_from_git = sorted(
        path.relative_to(source).as_posix()
        for path in physical_inputs
        if path.relative_to(source).as_posix() not in tracked
    )
    errors.extend(f"input is not tracked at HEAD: {path}" for path in missing_from_git)

    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    digest_counts: Counter[str] = Counter()
    input_tree = hashlib.sha256()
    largest: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    ordered_inputs = sorted(physical_inputs)
    print(f"auditing {len(ordered_inputs):,} physical inputs across {len(document_sets):,} document sets")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_paths = {executor.submit(validate_input, path): path for path in ordered_inputs}
        completed = 0
        results = []
        for future in as_completed(future_paths):
            path = future_paths[future]
            try:
                results.append(future.result())
            except Exception as exc:
                validation_errors.append(
                    f"{path.relative_to(source).as_posix()}: {type(exc).__name__}: {exc}"
                )
            completed += 1
            if completed % 5000 == 0:
                print(f"  validated {completed:,}/{len(ordered_inputs):,}", flush=True)

    for row in sorted(results, key=lambda value: str(value["path"])):
        relative = row["path"].relative_to(source).as_posix()
        extension_counts[row["extension"]] += 1
        extension_bytes[row["extension"]] += row["bytes"]
        digest_counts[row["sha256"]] += 1
        input_tree.update(f"{relative}\0{row['sha256']}\0{row['bytes']}\n".encode())
        largest.append({"path": relative, "bytes": row["bytes"]})

    errors.extend(sorted(validation_errors))
    total_bytes = sum(extension_bytes.values())
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_repo": "harveyai/harvey-labs",
        "source_commit": commit,
        "source_git_clean": not bool(dirty),
        "tracked_files": len(tracked),
        "tasks": len(tasks),
        "document_sets": len(document_sets),
        "shared_document_sets": sum(row["shared"] for row in document_set_rows),
        "physical_inputs": len(ordered_inputs),
        "physical_input_bytes": total_bytes,
        "physical_input_tree_sha256": input_tree.hexdigest(),
        "unique_input_blobs": len(digest_counts),
        "duplicate_input_occurrences": sum(count - 1 for count in digest_counts.values()),
        "extensions": {
            extension: {"files": extension_counts[extension], "bytes": extension_bytes[extension]}
            for extension in sorted(extension_counts)
        },
        "format_validation": {
            "ooxml_crc_checked": sum(extension_counts[ext] for ext in OOXML_REQUIRED),
            "pdfs_checked": extension_counts[".pdf"],
            "legacy_office_checked": sum(extension_counts[ext] for ext in CFB_EXTENSIONS),
            "lfs_pointers": sum("Git LFS pointer" in error for error in errors),
            "zero_byte_inputs": sum("zero-byte input" in error for error in errors),
            "errors": errors,
        },
        "largest_inputs": sorted(largest, key=lambda row: (-row["bytes"], row["path"]))[:20],
        "largest_document_sets": sorted(
            document_set_rows,
            key=lambda row: (-row["physical_files"], row["path"]),
        )[:20],
    }
    write_report(args.report.resolve(), report)
    print(f"report: {args.report.resolve()}")
    print(f"tasks: {len(tasks):,}")
    print(f"physical inputs: {len(ordered_inputs):,} ({total_bytes:,} bytes)")
    print("formats: " + ", ".join(
        f"{extension}={extension_counts[extension]:,}" for extension in sorted(extension_counts)
    ))
    print(f"OOXML packages CRC-checked: {report['format_validation']['ooxml_crc_checked']:,}")
    print(f"validation errors: {len(errors):,}")
    return 1 if errors or dirty or len(results) != len(ordered_inputs) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
