#!/usr/bin/env python3
"""Deep, read-only integrity audit for the local Harvey LAB input corpus.

The Harvey task tree mixes task-local ``documents/`` directories with shared
``docs_dir`` corpora.  Counting path names containing ``/documents/`` therefore
does not describe the physical input boundary.  This tool resolves every task's
actual document set, deduplicates shared paths, verifies that every input is
tracked at the checked-out Git commit, hashes every byte, and exercises each
container format.

OOXML inputs are fully decompressed so ZIP CRCs are checked, and every XML
package part is parsed. The source tree is never modified.

Usage:
    python3 tools/audit_harvey_inputs.py
    python3 tools/audit_harvey_inputs.py --report reports/harvey-input-audit.json
    python3 tools/audit_harvey_inputs.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "research" / "repos" / "harveyai@harvey-labs"
DEFAULT_REPORT = ROOT / "reports" / "harvey-input-audit.json"
DEFAULT_PIN_FILE = ROOT / "research" / "repos-commits.json"
DEFAULT_DEFECT_FILE = (
    ROOT / "research" / "harvey-augmentation" / "upstream-ooxml-defects.json"
)
PIN_KEY = "harveyai@harvey-labs"
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
XML_PART_EXTENSIONS = {".xml", ".rels"}
RAW_AMPERSAND_RE = re.compile(
    br"&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9A-Fa-f]+;)"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_xml_part(name: str) -> bool:
    return name.lower().endswith((".xml", ".rels"))


def normalized_remote(remote: str) -> str:
    value = remote.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    return value.lower()


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
        if task_json.is_symlink():
            errors.append(f"{relative_task}: task.json is a symlink")
            continue
        try:
            task = json.loads(task_json.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{task_json.relative_to(source)}: invalid task JSON: {exc}")
            continue
        setting = task.get("docs_dir")
        documents_path = task_json.parent / str(setting) if setting else task_json.parent / "documents"
        if documents_path.is_symlink():
            errors.append(f"{relative_task}: document set is a symlink: {documents_path}")
            continue
        documents_dir = documents_path.resolve()
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
    if path.is_symlink():
        raise ValueError("input is a symlink")
    extension = path.suffix.lower() or "(none)"
    size = path.stat().st_size
    if size == 0:
        raise ValueError("zero-byte input")
    with path.open("rb") as handle:
        header = handle.read(200)
    if header.startswith(LFS_HEADER):
        raise ValueError("Git LFS pointer, not materialized content")

    xml_parts = 0
    xml_parts_failed = 0
    defects: list[dict[str, Any]] = []
    if extension in OOXML_REQUIRED:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            missing = sorted(OOXML_REQUIRED[extension] - names)
            if missing:
                raise ValueError(f"OOXML package missing {missing}")
            bad_member = archive.testzip()
            if bad_member:
                raise ValueError(f"ZIP CRC failure in {bad_member}")
            for name in archive.namelist():
                if is_xml_part(name):
                    payload = archive.read(name)
                    try:
                        ElementTree.fromstring(payload)
                    except ElementTree.ParseError as error:
                        xml_parts_failed += 1
                        raw_ampersands = len(RAW_AMPERSAND_RE.findall(payload))
                        defect = {
                            "kind": (
                                "unescaped_ampersand"
                                if raw_ampersands
                                else "xml_parse_error"
                            ),
                            "part": name,
                            "occurrences": raw_ampersands or 1,
                        }
                        if not raw_ampersands:
                            defect["error"] = str(error)
                        defects.append(defect)
                    else:
                        xml_parts += 1
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
        "xml_parts": xml_parts,
        "xml_parts_failed": xml_parts_failed,
        "defects": defects,
    }


def inventory_document_set(directory: Path, source: Path) -> tuple[list[Path], list[str]]:
    """List regular inputs and surface every nested symlink without following it."""
    entries = sorted(directory.rglob("*"))
    links = [path for path in entries if path.is_symlink()]
    errors = [
        f"document set contains a symlink: {path.relative_to(source).as_posix()}"
        for path in links
    ]
    files = [path for path in entries if path.is_file() and not path.is_symlink()]
    return files, errors


def load_expected_defects(path: Path, commit: str) -> tuple[list[dict[str, Any]], str]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"upstream defect allowlist is missing or unsafe: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("upstream defect allowlist schema_version must be 1")
    if value.get("source_repo") != "harveyai/harvey-labs":
        raise ValueError("upstream defect allowlist has an invalid source_repo")
    expected_commit = value.get("source_commit")
    if not isinstance(expected_commit, str) or not commit.startswith(expected_commit):
        raise ValueError("upstream defect allowlist does not match the source commit")
    defects = value.get("defects")
    required = {"path", "sha256", "part", "kind", "occurrences"}
    if (
        not isinstance(defects, list)
        or any(not isinstance(row, dict) or set(row) != required for row in defects)
        or len({(row["path"], row["part"]) for row in defects}) != len(defects)
    ):
        raise ValueError("upstream defect allowlist contains invalid or duplicate rows")
    for row in defects:
        if (
            not isinstance(row["path"], str)
            or not row["path"].startswith("tasks/")
            or not isinstance(row["part"], str)
            or not row["part"]
            or row["kind"] != "unescaped_ampersand"
            or isinstance(row["occurrences"], bool)
            or not isinstance(row["occurrences"], int)
            or row["occurrences"] < 1
            or not isinstance(row["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        ):
            raise ValueError("upstream defect allowlist contains an invalid row")
    return sorted(defects, key=lambda row: (row["path"], row["part"])), sha256_file(path)


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
    parser.add_argument("--expected-commit")
    parser.add_argument(
        "--known-defects",
        type=Path,
        help="exact-hash allowlist for known malformed upstream OOXML parts",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the existing report exactly matches a fresh audit",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least 1")

    source = args.source.resolve()
    try:
        inside_worktree = git(source, "rev-parse", "--is-inside-work-tree")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Harvey mirror is not a Git worktree: {source}") from exc
    if inside_worktree != "true":
        raise RuntimeError(f"Harvey mirror is not a Git worktree: {source}")

    commit = git(source, "rev-parse", "HEAD")
    commit_time = git(source, "show", "-s", "--format=%cI", "HEAD")
    remote = git(source, "remote", "get-url", "origin")
    expected_commit = args.expected_commit
    source_identity_errors: list[str] = []
    if expected_commit is None and source == DEFAULT_SOURCE.resolve():
        pins = json.loads(DEFAULT_PIN_FILE.read_text(encoding="utf-8"))
        expected_commit = pins.get(PIN_KEY)
        if normalized_remote(remote) != "https://github.com/harveyai/harvey-labs":
            source_identity_errors.append(f"unexpected Harvey origin: {remote}")
    if expected_commit is not None and (
        not isinstance(expected_commit, str)
        or len(expected_commit) < 7
        or any(character not in "0123456789abcdefABCDEF" for character in expected_commit)
        or len(expected_commit) > 40
    ):
        raise ValueError("expected commit must be a 7-40 character hexadecimal prefix")
    if args.known_defects and (
        not args.known_defects.is_file() or args.known_defects.is_symlink()
    ):
        raise ValueError(f"known-defects file is missing or unsafe: {args.known_defects}")
    defect_path = args.known_defects.resolve() if args.known_defects else None
    if defect_path is None and source == DEFAULT_SOURCE.resolve():
        defect_path = DEFAULT_DEFECT_FILE.resolve()
    if defect_path is not None:
        expected_defects, defect_allowlist_hash = load_expected_defects(
            defect_path, commit
        )
        try:
            defect_allowlist_name = defect_path.relative_to(ROOT).as_posix()
        except ValueError:
            defect_allowlist_name = str(defect_path)
    else:
        expected_defects = []
        defect_allowlist_hash = None
        defect_allowlist_name = None
    tracked = tracked_paths(source)
    dirty = git(source, "status", "--porcelain", "--untracked-files=all")
    tasks, document_sets, discovery_errors = resolve_document_sets(source)

    physical_inputs: set[Path] = set()
    document_set_rows = []
    document_tree_errors: list[str] = []
    for directory, consumers in sorted(document_sets.items(), key=lambda item: str(item[0])):
        files, tree_errors = inventory_document_set(directory, source)
        document_tree_errors.extend(tree_errors)
        physical_inputs.update(files)
        document_set_rows.append({
            "path": directory.relative_to(source).as_posix(),
            "consumer_tasks": len(consumers),
            "physical_files": len(files),
            "shared": len(consumers) > 1,
        })

    errors = list(discovery_errors) + source_identity_errors + document_tree_errors
    if expected_commit and not commit.startswith(expected_commit):
        errors.append(f"source commit does not match pin {expected_commit}: {commit}")
    if dirty:
        errors.append("source Git worktree has tracked or untracked changes")
    missing_from_git = sorted(
        path.relative_to(source).as_posix()
        for path in physical_inputs
        if path.relative_to(source).as_posix() not in tracked
    )
    errors.extend(f"input is not tracked at HEAD: {path}" for path in missing_from_git)
    tracked_task_files = {path for path in tracked if path.startswith("tasks/")}
    tracked_task_configs = {
        path for path in tracked_task_files if path.endswith("/task.json")
    }
    referenced_input_paths = {
        path.relative_to(source).as_posix() for path in physical_inputs
    }
    other_tracked_task_files = sorted(
        tracked_task_files - tracked_task_configs - referenced_input_paths
    )
    if len(tracked_task_configs) != len(tasks):
        errors.append(
            "resolved task count differs from tracked task.json count: "
            f"resolved={len(tasks)}, tracked={len(tracked_task_configs)}"
        )

    extension_counts: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    digest_counts: Counter[str] = Counter()
    xml_parts_parsed = 0
    xml_parts_failed = 0
    observed_defects: list[dict[str, Any]] = []
    input_tree = hashlib.sha256()
    largest: list[dict[str, Any]] = []
    validation_errors: list[str] = []

    ordered_inputs = sorted(physical_inputs)
    print(f"auditing {len(ordered_inputs):,} physical inputs across {len(document_sets):,} document sets")
    # XML parsing is CPU-bound. Processes avoid serializing 1M+ package-part
    # parses behind the GIL while keeping each input independently fail-closed.
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
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
        xml_parts_parsed += row["xml_parts"]
        xml_parts_failed += row["xml_parts_failed"]
        observed_defects.extend({
            "path": relative,
            "sha256": row["sha256"],
            **defect,
        } for defect in row["defects"])
        input_tree.update(
            f"{relative}\0{row['sha256']}\0{row['bytes']}\n".encode(
                "utf-8", errors="surrogateescape"
            )
        )
        largest.append({"path": relative, "bytes": row["bytes"]})

    errors.extend(sorted(validation_errors))
    observed_defects.sort(key=lambda row: (row["path"], row["part"]))
    defects_match = observed_defects == expected_defects
    if not defects_match:
        expected_keys = {
            (row["path"], row["part"], row["sha256"], row["kind"], row["occurrences"])
            for row in expected_defects
        }
        observed_keys = {
            (row["path"], row["part"], row["sha256"], row["kind"], row["occurrences"])
            for row in observed_defects
        }
        errors.append(
            "upstream OOXML defect inventory differs from its exact-hash allowlist: "
            f"missing={len(expected_keys - observed_keys)}, "
            f"unexpected={len(observed_keys - expected_keys)}"
        )
    total_bytes = sum(extension_bytes.values())
    report = {
        "schema_version": 3,
        "source_commit_time": commit_time,
        "source_repo": "harveyai/harvey-labs",
        "source_remote": remote,
        "source_commit": commit,
        "source_expected_commit": expected_commit,
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
        "task_tree_coverage": {
            "tracked_files": len(tracked_task_files),
            "tracked_task_configs": len(tracked_task_configs),
            "referenced_inputs": len(referenced_input_paths),
            "other_tracked_files": other_tracked_task_files,
            "all_tracked_task_files_classified": (
                len(tracked_task_files)
                == len(tracked_task_configs)
                + len(referenced_input_paths)
                + len(other_tracked_task_files)
            ),
        },
        "known_source_defects": {
            "allowlist": defect_allowlist_name,
            "allowlist_sha256": defect_allowlist_hash,
            "matched": defects_match,
            "count": len(observed_defects),
            "items": observed_defects,
        },
        "extensions": {
            extension: {"files": extension_counts[extension], "bytes": extension_bytes[extension]}
            for extension in sorted(extension_counts)
        },
        "format_validation": {
            "ooxml_crc_checked": sum(extension_counts[ext] for ext in OOXML_REQUIRED),
            "ooxml_xml_parts_parsed": xml_parts_parsed,
            "ooxml_xml_parts_failed": xml_parts_failed,
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
    if args.report.is_symlink():
        raise RuntimeError(f"audit report path is a symlink: {args.report}")
    report_path = args.report.resolve()
    if args.check:
        if not report_path.is_file() or report_path.is_symlink():
            raise RuntimeError(f"audit report is missing or unsafe: {report_path}")
        existing = json.loads(report_path.read_text(encoding="utf-8"))
        if existing != report:
            raise RuntimeError(f"audit report is stale: {report_path}")
        print(f"report current: {report_path}")
    else:
        write_report(report_path, report)
        print(f"report: {report_path}")
    print(f"tasks: {len(tasks):,}")
    print(f"physical inputs: {len(ordered_inputs):,} ({total_bytes:,} bytes)")
    print("formats: " + ", ".join(
        f"{extension}={extension_counts[extension]:,}" for extension in sorted(extension_counts)
    ))
    print(f"OOXML packages CRC-checked: {report['format_validation']['ooxml_crc_checked']:,}")
    print(f"OOXML XML parts parsed: {xml_parts_parsed:,}")
    print(f"known upstream OOXML defects: {len(observed_defects):,}")
    print(f"validation errors: {len(errors):,}")
    return 1 if errors or len(results) != len(ordered_inputs) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
        zipfile.BadZipFile,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
