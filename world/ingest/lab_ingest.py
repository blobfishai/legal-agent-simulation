#!/usr/bin/env python3
"""Build the immutable Harvey LAB evidence store.

The Harvey task repository is deliberately excluded from git because it is a
multi-gigabyte source corpus.  This program turns the pinned local snapshot
into a reproducible, content-addressed store:

    world/corpus/lab/
      blobs/aa/<sha256>             exact source bytes (hard-linked by default)
      text/aa/<sha256>.txt          extracted text
      index.sqlite                  task/file/provenance index + FTS5
      ingest-report.json            measured outcome, including every failure

Office documents are parsed inside the vendored Harvey sandbox image.  The
host process only enumerates, hashes, and hard-links opaque bytes.  A small,
explicit ``--parser host`` escape hatch exists solely for synthetic fixtures.

Examples:

  # Freeze or intentionally refresh the source snapshot identity.
  python3 world/ingest/lab_ingest.py --inventory-only --write-lock

  # Build the parser image once, then ingest all tasks.
  python3 world/ingest/lab_ingest.py --build-parser-image
  python3 world/ingest/lab_ingest.py

  # Recompute source identity and verify a materialized store if present.
  python3 world/ingest/lab_ingest.py --check
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Iterable


SCRIPT_PATH = Path(__file__).resolve()
ROOT = (SCRIPT_PATH.parents[2] if len(SCRIPT_PATH.parents) > 2 else
        Path(os.environ.get("LAB_PROJECT_ROOT", "/")))
HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "research" / "repos" / "harveyai@harvey-labs"
DEFAULT_DEST = ROOT / "world" / "corpus" / "lab"
DEFAULT_LOCK = HERE / "lab-source-lock.json"
DEFAULT_COMMITTED_REPORT = HERE / "lab-ingest-report.json"
REPO_COMMITS = ROOT / "research" / "repos-commits.json"
SOURCE_REPO = "harveyai/harvey-labs"
SOURCE_LOCK_KEY = "harveyai@harvey-labs"
SCHEMA_VERSION = 1
EXTRACTOR_VERSION = "lab-compatible-v5-recorded-ooxml-ampersand-recovery"

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".pptx", ".xlsx", ".eml", ".txt", ".md", ".json"}
RAW_XML_AMPERSAND_RE = re.compile(
    br"&(?!amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9A-Fa-f]+;)"
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pinned_commit() -> str:
    commit = None
    if REPO_COMMITS.is_file():
        data = json.loads(REPO_COMMITS.read_text())
        commit = data.get(SOURCE_LOCK_KEY)
    if not commit:
        commit = os.environ.get("LAB_SOURCE_COMMIT")
    if not isinstance(commit, str) or len(commit) < 12:
        raise RuntimeError(f"{REPO_COMMITS} does not pin {SOURCE_REPO}")
    return commit


def find_task_dirs(tasks_root: Path) -> list[Path]:
    return sorted({path.parent for path in tasks_root.rglob("task.json")})


def stable_task_id(relative_task: str) -> str:
    digest = hashlib.sha256(relative_task.encode()).hexdigest()[:16]
    readable = relative_task.replace("/", "__")
    return f"lab__{readable}__{digest}"


def stable_file_id(task_id: str, relative_path: str) -> str:
    digest = hashlib.sha256(f"{task_id}\0{relative_path}".encode()).hexdigest()[:24]
    return f"labdoc_{digest}"


def build_inventory(source: Path, limit_tasks: int = 0) -> tuple[dict[str, Any], list[dict], list[dict]]:
    tasks_root = source / "tasks"
    if not tasks_root.is_dir():
        raise RuntimeError(f"Harvey LAB tasks directory missing: {tasks_root}")
    license_path = source / "LICENSE"
    if not license_path.is_file():
        raise RuntimeError(f"Harvey LAB license missing: {license_path}")

    task_dirs = find_task_dirs(tasks_root)
    if limit_tasks:
        task_dirs = task_dirs[:limit_tasks]

    tree = hashlib.sha256()
    tasks: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    ext_counts: Counter[str] = Counter()
    work_type_counts: Counter[str] = Counter()
    total_criteria = 0
    total_bytes = 0
    shared_sets: dict[str, dict[str, Any]] = {}

    def add_tree_entry(relative_path: str, digest: str, size: int) -> None:
        tree.update(relative_path.encode("utf-8"))
        tree.update(b"\0")
        tree.update(digest.encode("ascii"))
        tree.update(b"\0")
        tree.update(str(size).encode("ascii"))
        tree.update(b"\n")

    for task_dir in task_dirs:
        task_path = task_dir / "task.json"
        relative_task = task_dir.relative_to(tasks_root).as_posix()
        source_task_path = task_path.relative_to(source).as_posix()
        raw = task_path.read_bytes()
        task_sha = hashlib.sha256(raw).hexdigest()
        add_tree_entry(source_task_path, task_sha, len(raw))
        try:
            task_data = json.loads(raw)
        except Exception as exc:
            raise RuntimeError(f"invalid JSON in {task_path}: {exc}") from exc

        task_id = stable_task_id(relative_task)
        parts = relative_task.split("/")
        criteria = task_data.get("criteria") or []
        docs_dir_setting = task_data.get("docs_dir")
        if docs_dir_setting:
            documents_dir = (task_dir / str(docs_dir_setting)).resolve()
            try:
                document_set_path = documents_dir.relative_to(source).as_posix()
            except ValueError as exc:
                raise RuntimeError(f"task {relative_task} points outside the LAB snapshot: {documents_dir}") from exc
            if not documents_dir.is_dir():
                raise RuntimeError(f"task {relative_task} shared docs_dir is missing: {documents_dir}")
            if document_set_path not in shared_sets:
                shared_paths = sorted(path for path in documents_dir.rglob("*") if path.is_file())
                shared_tree = hashlib.sha256()
                shared_bytes = 0
                shared_extensions: Counter[str] = Counter()
                for shared_path in shared_paths:
                    source_path = shared_path.relative_to(source).as_posix()
                    size = shared_path.stat().st_size
                    digest = sha256_file(shared_path)
                    add_tree_entry(source_path, digest, size)
                    shared_tree.update(f"{source_path}\0{digest}\0{size}\n".encode())
                    shared_bytes += size
                    shared_extensions[shared_path.suffix.lower() or "(none)"] += 1
                shared_sets[document_set_path] = {
                    "corpus_id": "ch" if document_set_path == "tasks/firm-knowledge/dms" else
                                 f"lab-shared-{hashlib.sha256(document_set_path.encode()).hexdigest()[:12]}",
                    "source_path": document_set_path,
                    "documents": len(shared_paths),
                    "bytes": shared_bytes,
                    "extensions": dict(sorted(shared_extensions.items())),
                    "tree_sha256": shared_tree.hexdigest(),
                    "consumer_tasks": 0,
                }
            shared_sets[document_set_path]["consumer_tasks"] += 1
            document_paths: list[Path] = []
            document_set_kind = "shared"
            document_count = shared_sets[document_set_path]["documents"]
        else:
            documents_dir = task_dir / "documents"
            document_paths = (
                sorted(path for path in documents_dir.rglob("*") if path.is_file())
                if documents_dir.is_dir() else []
            )
            document_set_kind = "task-local"
            document_set_path = documents_dir.relative_to(source).as_posix()
            document_count = len(document_paths)
        task_row = {
            "task_id": task_id,
            "source_task": relative_task,
            "source_task_json": source_task_path,
            "task_json_sha256": task_sha,
            "area": parts[0],
            "slug": "/".join(parts[1:]),
            "title": str(task_data.get("title") or ""),
            "work_type": str(task_data.get("work_type") or
                             ("contracting" if parts[0] == "contracts" else "unspecified")),
            "instructions": str(task_data.get("instructions") or ""),
            "deliverables": task_data.get("deliverables") or {},
            "criteria_count": len(criteria),
            "document_count": document_count,
            "document_set_kind": document_set_kind,
            "document_set_path": document_set_path,
            "task_json": canonical_json(task_data),
        }
        tasks.append(task_row)
        work_type_counts[task_row["work_type"]] += 1
        total_criteria += len(criteria)

        for ordinal, path in enumerate(document_paths):
            relative_document = path.relative_to(documents_dir).as_posix()
            source_path = path.relative_to(source).as_posix()
            size = path.stat().st_size
            digest = sha256_file(path)
            extension = path.suffix.lower()
            add_tree_entry(source_path, digest, size)
            ext_counts[extension or "(none)"] += 1
            total_bytes += size
            files.append({
                "file_id": stable_file_id(task_id, relative_document),
                "task_id": task_id,
                "source_task": relative_task,
                "ordinal": ordinal,
                "relative_path": relative_document,
                "source_path": source_path,
                "filename": path.name,
                "folder": path.parent.relative_to(documents_dir).as_posix(),
                "ext": extension,
                "bytes": size,
                "sha256": digest,
            })

    license_sha = sha256_file(license_path)
    add_tree_entry("LICENSE", license_sha, license_path.stat().st_size)
    harness_paths = [source / "sandbox" / "Dockerfile",
                     source / "sandbox" / "parsers" / "parse_doc.py",
                     source / "harness" / "system_prompt.md"]
    harness_paths.extend(sorted(path for path in (source / "harness" / "skills").rglob("*")
                                if path.is_file()))
    harness_tree = hashlib.sha256()
    harness_bytes = 0
    for path in sorted(set(harness_paths)):
        relative_path = path.relative_to(source).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        harness_tree.update(f"{relative_path}\0{digest}\0{size}\n".encode())
        harness_bytes += size
    unique_blobs = {row["sha256"] for row in files}
    shared_documents = sum(item["documents"] for item in shared_sets.values())
    shared_bytes = sum(item["bytes"] for item in shared_sets.values())
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "source_repo": SOURCE_REPO,
        "source_commit": pinned_commit(),
        "source_tree_sha256": tree.hexdigest(),
        "license": "MIT",
        "license_sha256": license_sha,
        "harness_contract_sha256": harness_tree.hexdigest(),
        "harness_files": len(set(harness_paths)),
        "harness_bytes": harness_bytes,
        "tasks": len(tasks),
        "documents": len(files),
        "shared_documents": shared_documents,
        "total_input_files": len(files) + shared_documents,
        "unique_blobs": len(unique_blobs),
        "bytes": total_bytes,
        "shared_bytes": shared_bytes,
        "total_input_bytes": total_bytes + shared_bytes,
        "criteria": total_criteria,
        "document_extensions": dict(sorted(ext_counts.items())),
        "work_types": dict(sorted(work_type_counts.items())),
        "shared_document_sets": [shared_sets[key] for key in sorted(shared_sets)],
        "limited_inventory": bool(limit_tasks),
    }
    return snapshot, tasks, files


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def verify_or_write_lock(snapshot: dict[str, Any], lock_path: Path, write_lock: bool) -> None:
    if write_lock:
        if snapshot.get("limited_inventory"):
            raise RuntimeError("refusing to write a source lock from --limit-tasks")
        write_json(lock_path, snapshot)
        print(f"source lock     : {lock_path}")
        return
    if not lock_path.is_file():
        raise RuntimeError(f"source lock missing: {lock_path}; run with --inventory-only --write-lock")
    expected = json.loads(lock_path.read_text())
    if snapshot != expected:
        keys = sorted(set(snapshot) | set(expected))
        differences = [f"  {key}: expected {expected.get(key)!r}, got {snapshot.get(key)!r}"
                       for key in keys if snapshot.get(key) != expected.get(key)]
        raise RuntimeError("Harvey LAB source differs from the pinned lock:\n" + "\n".join(differences))


def materialize_blobs(source: Path, dest: Path, files: list[dict], mode: str) -> None:
    unique: dict[str, dict] = {}
    for row in files:
        unique.setdefault(row["sha256"], row)
    for index, row in enumerate(sorted(unique.values(), key=lambda item: item["sha256"]), 1):
        target = dest / "blobs" / row["sha256"][:2] / row["sha256"]
        if target.exists():
            if target.stat().st_size != row["bytes"] or sha256_file(target) != row["sha256"]:
                raise RuntimeError(f"corrupt existing blob: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source_path = source / row["source_path"]
        if mode == "hardlink":
            try:
                os.link(source_path, target)
            except OSError:
                shutil.copyfile(source_path, target)
        elif mode == "copy":
            shutil.copyfile(source_path, target)
        else:
            raise RuntimeError(f"unknown blob mode: {mode}")
        if index % 5000 == 0:
            print(f"  materialized {index}/{len(unique)} unique blobs", flush=True)


def parse_eml(path: Path) -> str:
    with path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)
    headers = [f"{name}: {message.get(name, '')}" for name in ("From", "To", "Cc", "Date", "Subject")]
    try:
        body = message.get_body(preferencelist=("plain", "html"))
        text = body.get_content() if body else ""
    except Exception:
        text = ""
    return "\n".join(header for header in headers if header.split(": ", 1)[1]) + "\n\n" + text


def parse_docx_ooxml_with_recovery(path: Path) -> tuple[str, dict[str, Any] | None]:
    """Extract all Word text nodes in document order, including headers/notes.

    The exact OOXML bytes remain in the blob store. This derivative is for
    full-text search and deterministic anchor checks, so preserving every text
    node matters more than reproducing pandoc's Markdown decoration.
    """
    from defusedxml import ElementTree
    parts: list[str] = []
    recovered_parts: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if (
            name == "word/document.xml" or
            name.startswith("word/header") or
            name.startswith("word/footer") or
            name in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
        ) and name.endswith(".xml")]
        members.sort(key=lambda name: (name != "word/document.xml", name))
        for member in members:
            payload = archive.read(member)
            try:
                root = ElementTree.fromstring(payload)
            except Exception:
                repaired, occurrences = RAW_XML_AMPERSAND_RE.subn(b"&amp;", payload)
                if not occurrences:
                    raise
                root = ElementTree.fromstring(repaired)
                recovered_parts.append({"part": member, "occurrences": occurrences})
            for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                text = "".join(
                    node.text or "" for node in
                    paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                ).strip()
                if text:
                    parts.append(text)
    recovery = ({
        "kind": "escaped_unescaped_xml_ampersands",
        "parts": recovered_parts,
        "occurrences": sum(row["occurrences"] for row in recovered_parts),
    } if recovered_parts else None)
    return "\n".join(parts), recovery


def parse_docx_ooxml(path: Path) -> str:
    return parse_docx_ooxml_with_recovery(path)[0]


def parse_xlsx_openpyxl(path: Path) -> str:
    import openpyxl
    workbook = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        parts: list[str] = []
        for sheet in workbook.worksheets:
            parts.append(f"=== Sheet: {sheet.title} ===")
            for row in sheet.iter_rows(values_only=True):
                cells = ["" if value is None else str(value) for value in row]
                if any(cell.strip() for cell in cells):
                    parts.append("\t".join(cells).rstrip("\t"))
    finally:
        workbook.close()
    return "\n".join(parts)


def sanitized_ooxml_copy(source: Path, destination: Path) -> list[dict[str, Any]]:
    recovered_parts: list[dict[str, Any]] = []
    with zipfile.ZipFile(source) as input_archive, zipfile.ZipFile(destination, "w") as output_archive:
        output_archive.comment = input_archive.comment
        for info in input_archive.infolist():
            payload = input_archive.read(info.filename)
            if info.filename.lower().endswith((".xml", ".rels")):
                payload, occurrences = RAW_XML_AMPERSAND_RE.subn(b"&amp;", payload)
                if occurrences:
                    recovered_parts.append({
                        "part": info.filename,
                        "occurrences": occurrences,
                    })
            output_archive.writestr(info, payload)
    return recovered_parts


def parse_xlsx_with_recovery(path: Path) -> tuple[str, dict[str, Any] | None]:
    try:
        return parse_xlsx_openpyxl(path), None
    except Exception:
        with tempfile.TemporaryDirectory(prefix="lab-xlsx-recovery-") as temporary:
            repaired = Path(temporary) / path.name
            recovered_parts = sanitized_ooxml_copy(path, repaired)
            if not recovered_parts:
                raise
            text = parse_xlsx_openpyxl(repaired)
    return text, {
        "kind": "escaped_unescaped_xml_ampersands",
        "parts": recovered_parts,
        "occurrences": sum(row["occurrences"] for row in recovered_parts),
    }


def parse_document_with_recovery(
    path: Path, extension: str
) -> tuple[str, dict[str, Any] | None]:
    if extension == ".docx":
        return parse_docx_ooxml_with_recovery(path)
    if extension == ".xlsx":
        return parse_xlsx_with_recovery(path)
    return parse_document(path, extension), None


def parse_document(path: Path, extension: str) -> str:
    if extension in {".txt", ".md", ".json"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if extension == ".eml":
        return parse_eml(path)
    if extension == ".docx":
        return parse_docx_ooxml(path)
    if extension == ".pdf":
        import pdfplumber
        parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
                for table in page.extract_tables():
                    parts.extend("\t".join(cell or "" for cell in row) for row in table)
        return "\n".join(parts)
    if extension == ".pptx":
        # Keep Harvey's exact converter here. PPTX is only ~2% of the corpus;
        # its converter captures notes/structure that python-pptx text-only
        # extraction drops, as the parity gate demonstrated.
        from markitdown import MarkItDown
        return MarkItDown().convert(str(path)).text_content
    if extension == ".xlsx":
        return parse_xlsx_with_recovery(path)[0]
    raise RuntimeError(f"unsupported extension {extension or '(none)'}")


def parse_one(argument: tuple[str, str, str, str]) -> dict[str, Any]:
    source_string, dest_string, source_path, extension = argument
    source = Path(source_string)
    dest = Path(dest_string)
    path = source / source_path
    digest = sha256_file(path)
    text_path = dest / "text-v4" / digest[:2] / f"{digest}.txt"
    recovery_path = text_path.with_suffix(".recovery.json")
    if text_path.is_file():
        text = text_path.read_text(encoding="utf-8", errors="replace")
        recovery = (
            json.loads(recovery_path.read_text(encoding="utf-8"))
            if recovery_path.is_file()
            else None
        )
        return {
            "sha256": digest,
            "status": "parsed",
            "chars": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_path": text_path.relative_to(dest).as_posix(),
            "parse_error": None,
            "recovery": recovery,
        }
    try:
        text, recovery = parse_document_with_recovery(path, extension)
        text_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = text_path.with_suffix(".tmp")
        temporary.write_text(text, encoding="utf-8", errors="replace")
        temporary.replace(text_path)
        if recovery:
            recovery_path.write_text(
                json.dumps(recovery, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return {
            "sha256": digest,
            "status": "parsed",
            "chars": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text_path": text_path.relative_to(dest).as_posix(),
            "parse_error": None,
            "recovery": recovery,
        }
    except Exception as exc:
        return {
            "sha256": digest,
            "status": "failed" if extension in SUPPORTED_EXTENSIONS else "unsupported",
            "chars": 0,
            "text_sha256": None,
            "text_path": None,
            "parse_error": f"{type(exc).__name__}: {exc}"[:500],
            "recovery": None,
        }


def run_parse_worker(source: Path, dest: Path, records_path: Path, workers: int) -> int:
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    unique: dict[str, dict] = {}
    for record in records:
        unique.setdefault(record["sha256"], record)
    ordered = [unique[key] for key in sorted(unique)]
    arguments = [(str(source), str(dest), row["source_path"], row["ext"]) for row in ordered]
    results_path = dest / "parse-results.jsonl"
    results: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, workers)) as executor:
        for index, result in enumerate(executor.map(parse_one, arguments, chunksize=8), 1):
            results.append(result)
            if index % 500 == 0:
                parsed = sum(item["status"] == "parsed" for item in results)
                print(f"  parsed {index}/{len(arguments)} unique blobs ({parsed} ok)", flush=True)
    with results_path.open("w") as handle:
        for result in results:
            handle.write(canonical_json(result) + "\n")
    failed = sum(result["status"] != "parsed" for result in results)
    print(f"parser result   : {len(results) - failed}/{len(results)} unique blobs parsed")
    return 0


def docker_image_id(image: str) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"parser image {image!r} is unavailable; rerun with --build-parser-image"
        )
    return result.stdout.strip()


def build_parser_image(source: Path, image: str) -> None:
    sandbox = source / "sandbox"
    subprocess.run(["docker", "build", "-t", image, str(sandbox)], check=True)


def run_docker_parser(source: Path, dest: Path, records_path: Path, workers: int, image: str) -> str:
    image_id = docker_image_id(image)
    command = [
        "docker", "run", "--rm", "--network=none",
        "--mount", f"type=bind,src={source},dst=/source,readonly",
        "--mount", f"type=bind,src={dest},dst=/dest",
        "--mount", f"type=bind,src={Path(__file__).resolve()},dst=/ingest/lab_ingest.py,readonly",
        "--env", f"LAB_SOURCE_COMMIT={pinned_commit()}",
        image, "python3", "/ingest/lab_ingest.py", "--worker",
        "--source", "/source", "--dest", "/dest",
        "--records", f"/dest/{records_path.name}", "--workers", str(workers),
    ]
    subprocess.run(command, check=True)
    return image_id


def build_index(dest: Path, snapshot: dict, tasks: list[dict], files: list[dict],
                parser_image: str, with_fts: bool) -> dict[str, Any]:
    results_path = dest / "parse-results.jsonl"
    results = {
        row["sha256"]: row
        for row in (json.loads(line) for line in results_path.read_text().splitlines() if line.strip())
    }
    expected_blobs = {row["sha256"] for row in files}
    if set(results) != expected_blobs:
        missing = sorted(expected_blobs - set(results))[:10]
        extra = sorted(set(results) - expected_blobs)[:10]
        raise RuntimeError(f"parse result coverage mismatch; missing={missing}, extra={extra}")

    database = dest / "index.sqlite"
    temporary = dest / "index.sqlite.tmp"
    if temporary.exists():
        temporary.unlink()
    connection = sqlite3.connect(temporary)
    connection.executescript("""
      PRAGMA journal_mode=OFF;
      PRAGMA synchronous=OFF;
      CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE tasks (
        task_id TEXT PRIMARY KEY, source_task TEXT UNIQUE NOT NULL,
        source_task_json TEXT NOT NULL, task_json_sha256 TEXT NOT NULL,
        area TEXT NOT NULL, slug TEXT NOT NULL, title TEXT NOT NULL,
        work_type TEXT NOT NULL, instructions TEXT NOT NULL,
        deliverables_json TEXT NOT NULL, criteria_count INTEGER NOT NULL,
        document_count INTEGER NOT NULL, document_set_kind TEXT NOT NULL,
        document_set_path TEXT NOT NULL, task_json TEXT NOT NULL
      );
      CREATE TABLE blobs (
        sha256 TEXT PRIMARY KEY, bytes INTEGER NOT NULL, blob_path TEXT NOT NULL,
        text_path TEXT, chars INTEGER NOT NULL, text_sha256 TEXT,
        parse_status TEXT NOT NULL, parse_error TEXT
      );
      CREATE TABLE files (
        file_id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(task_id),
        ordinal INTEGER NOT NULL, relative_path TEXT NOT NULL,
        source_path TEXT NOT NULL, filename TEXT NOT NULL, folder TEXT NOT NULL,
        ext TEXT NOT NULL, bytes INTEGER NOT NULL,
        blob_sha256 TEXT NOT NULL REFERENCES blobs(sha256),
        source_repo TEXT NOT NULL, source_commit TEXT NOT NULL,
        source_task TEXT NOT NULL, license TEXT NOT NULL,
        UNIQUE(task_id, relative_path)
      );
      CREATE INDEX idx_files_task ON files(task_id, ordinal);
      CREATE INDEX idx_files_blob ON files(blob_sha256);
      CREATE INDEX idx_tasks_area ON tasks(area);
    """)
    metadata = {
        **snapshot,
        "parser_image": parser_image,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_sha256": sha256_file(Path(__file__).resolve()),
        "fts_enabled": with_fts,
    }
    connection.executemany(
        "INSERT INTO metadata(key,value) VALUES (?,?)",
        ((key, canonical_json(value)) for key, value in sorted(metadata.items())),
    )
    connection.executemany(
        "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((row["task_id"], row["source_task"], row["source_task_json"],
          row["task_json_sha256"], row["area"], row["slug"], row["title"],
          row["work_type"], row["instructions"], canonical_json(row["deliverables"]),
          row["criteria_count"], row["document_count"], row["document_set_kind"],
          row["document_set_path"], row["task_json"])
         for row in tasks),
    )
    representative: dict[str, dict] = {}
    for row in files:
        representative.setdefault(row["sha256"], row)
    for digest in sorted(expected_blobs):
        row = representative[digest]
        parsed = results[digest]
        connection.execute(
            "INSERT INTO blobs VALUES (?,?,?,?,?,?,?,?)",
            (digest, row["bytes"], f"blobs/{digest[:2]}/{digest}",
             parsed["text_path"], parsed["chars"], parsed["text_sha256"],
             parsed["status"], parsed["parse_error"]),
        )
    connection.executemany(
        "INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((row["file_id"], row["task_id"], row["ordinal"], row["relative_path"],
          row["source_path"], row["filename"], row["folder"], row["ext"],
          row["bytes"], row["sha256"], SOURCE_REPO, snapshot["source_commit"],
          row["source_task"], snapshot["license"])
         for row in files),
    )
    if with_fts:
        connection.execute(
            "CREATE VIRTUAL TABLE blobs_fts USING fts5(sha256 UNINDEXED, content, tokenize='unicode61')"
        )
        for digest in sorted(expected_blobs):
            parsed = results[digest]
            if parsed["status"] != "parsed" or not parsed["text_path"]:
                continue
            text = (dest / parsed["text_path"]).read_text(encoding="utf-8", errors="replace")
            connection.execute("INSERT INTO blobs_fts(sha256,content) VALUES (?,?)", (digest, text))
    connection.commit()
    connection.execute("VACUUM")
    connection.close()
    temporary.replace(database)

    unique_failures = [
        {"sha256": digest, "source_path": representative[digest]["source_path"],
         "status": result["status"], "error": result["parse_error"]}
        for digest, result in sorted(results.items()) if result["status"] != "parsed"
    ]
    failures = [
        {"file_id": row["file_id"], "source_task": row["source_task"],
         "source_path": row["source_path"], "sha256": row["sha256"],
         "status": results[row["sha256"]]["status"],
         "error": results[row["sha256"]]["parse_error"]}
        for row in files if results[row["sha256"]]["status"] != "parsed"
    ]
    parsed_documents = sum(results[row["sha256"]]["status"] == "parsed" for row in files)
    text_tree = hashlib.sha256()
    for digest, result in sorted(results.items()):
        text_tree.update(canonical_json({
            "sha256": digest,
            "status": result["status"],
            "chars": result["chars"],
            "text_sha256": result["text_sha256"],
            "parse_error": result["parse_error"],
            "recovery": result.get("recovery"),
        }).encode())
        text_tree.update(b"\n")
    unique_recoveries = [
        {
            "sha256": digest,
            "source_path": representative[digest]["source_path"],
            **result["recovery"],
        }
        for digest, result in sorted(results.items())
        if result.get("recovery")
    ]
    recovered_documents = sum(
        bool(results[row["sha256"]].get("recovery")) for row in files
    )
    report = {
        **snapshot,
        "parser_image": parser_image,
        "extractor_version": EXTRACTOR_VERSION,
        "extractor_sha256": sha256_file(Path(__file__).resolve()),
        "parsed_documents": parsed_documents,
        "failed_documents": len(files) - parsed_documents,
        "parse_rate": round(parsed_documents / max(1, len(files)), 8),
        "text_tree_sha256": text_tree.hexdigest(),
        "binary_integrity": "source bytes preserved verbatim and addressed by sha256",
        "canary_policy": "no source-byte rewriting; embedded benchmark canaries preserved",
        "parse_failures": failures,
        "unique_parse_failures": unique_failures,
        "recovered_documents": recovered_documents,
        "unique_recoveries": unique_recoveries,
        "index": "index.sqlite",
        "fts_enabled": with_fts,
    }
    write_json(dest / "ingest-report.json", report)
    if dest.resolve() == DEFAULT_DEST.resolve():
        write_json(DEFAULT_COMMITTED_REPORT, report)
    return report


def verify_store(dest: Path, snapshot: dict[str, Any], deep: bool) -> None:
    database = dest / "index.sqlite"
    report_path = dest / "ingest-report.json"
    if not database.exists() and not report_path.exists():
        print("materialized store: absent (source lock only)")
        return
    if not database.is_file() or not report_path.is_file():
        raise RuntimeError("partial LAB store: index.sqlite and ingest-report.json must both exist")
    report = json.loads(report_path.read_text())
    for key, value in snapshot.items():
        if report.get(key) != value:
            raise RuntimeError(f"store metadata mismatch for {key}: {report.get(key)!r} != {value!r}")
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    counts = {
        "tasks": connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        "documents": connection.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        "unique_blobs": connection.execute("SELECT COUNT(*) FROM blobs").fetchone()[0],
    }
    for key, value in counts.items():
        if value != snapshot[key]:
            raise RuntimeError(f"index {key} mismatch: {value} != {snapshot[key]}")
    broken = connection.execute(
        "SELECT sha256,blob_path,text_path,parse_status FROM blobs ORDER BY sha256"
    ).fetchall()
    connection.close()
    for digest, blob_path, text_path, status in broken:
        blob = dest / blob_path
        if not blob.is_file():
            raise RuntimeError(f"missing materialized blob: {blob}")
        if deep and sha256_file(blob) != digest:
            raise RuntimeError(f"blob digest mismatch: {blob}")
        if status == "parsed" and (not text_path or not (dest / text_path).is_file()):
            raise RuntimeError(f"missing extracted text for {digest}")
    print(f"materialized store: {counts['tasks']} tasks, {counts['documents']} documents, "
          f"{counts['unique_blobs']} unique blobs verified" + (" deeply" if deep else ""))


def write_records(dest: Path, files: Iterable[dict]) -> Path:
    path = dest / "records.jsonl"
    with path.open("w") as handle:
        for row in files:
            handle.write(canonical_json(row) + "\n")
    return path


def print_snapshot(snapshot: dict[str, Any]) -> None:
    print(f"source          : {snapshot['source_repo']}@{snapshot['source_commit']}")
    print(f"evidence tree   : sha256:{snapshot['source_tree_sha256']}")
    print(f"tasks           : {snapshot['tasks']:,}")
    print(f"documents       : {snapshot['documents']:,} ({snapshot['unique_blobs']:,} unique)")
    print(f"shared evidence : {snapshot['shared_documents']:,} files across "
          f"{len(snapshot['shared_document_sets'])} corpus set(s)")
    print(f"source bytes    : {snapshot['bytes']:,}")
    print(f"criteria        : {snapshot['criteria']:,}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--write-lock", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--deep", action="store_true", help="rehash every materialized blob")
    parser.add_argument("--parser", choices=("docker", "host"), default="docker")
    parser.add_argument("--parser-image", default=f"legal-agent-lab-parser:{pinned_commit()}")
    parser.add_argument("--build-parser-image", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--blob-mode", choices=("hardlink", "copy"), default="hardlink")
    parser.add_argument("--no-fts", action="store_true")
    parser.add_argument("--limit-tasks", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--records", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    source = args.source.resolve()
    dest = args.dest.resolve()
    if args.worker:
        if not args.records:
            parser.error("--worker requires --records")
        return run_parse_worker(source, dest, args.records.resolve(), args.workers)

    snapshot, tasks, files = build_inventory(source, args.limit_tasks)
    print_snapshot(snapshot)
    verify_or_write_lock(snapshot, args.lock.resolve(), args.write_lock)
    if args.inventory_only:
        return 0
    if args.check:
        verify_store(dest, snapshot, args.deep)
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    materialize_blobs(source, dest, files, args.blob_mode)
    records = write_records(dest, files)
    if args.build_parser_image:
        build_parser_image(source, args.parser_image)
    if args.parser == "docker":
        parser_identity = run_docker_parser(source, dest, records, args.workers, args.parser_image)
    else:
        print("WARNING: --parser host is for trusted synthetic fixtures only", file=sys.stderr)
        run_parse_worker(source, dest, records, args.workers)
        parser_identity = "host-parser-unsafe"
    report = build_index(dest, snapshot, tasks, files, parser_identity, not args.no_fts)
    print(f"parse rate      : {report['parse_rate']:.4%}")
    print(f"index           : {dest / 'index.sqlite'}")
    return 0 if report["parse_rate"] >= 0.99 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
