#!/usr/bin/env python3
"""Measure the fast LAB text indexer against Harvey's own parser.

Exact input bytes—not extracted text—are the file-lane source of truth. This
gate nevertheless prevents the faster search-index extraction from silently
dropping source facts: a deterministic, format-stratified sample is parsed by
both implementations and high-signal token recall is measured.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] if len(Path(__file__).resolve().parents) > 1 else Path("/")
SOURCE = ROOT / "research" / "repos" / "harveyai@harvey-labs"
INGEST = ROOT / "world" / "ingest" / "lab_ingest.py"
REPORT = ROOT / "world" / "ingest" / "lab-extractor-parity.json"
COMMITS = ROOT / "research" / "repos-commits.json"
FORMATS = {".docx": 32, ".xlsx": 16, ".pptx": 16}
MIN_MEAN_RECALL = 0.97
MIN_DOCUMENT_RECALL = 0.90


def pinned_commit() -> str:
    if COMMITS.is_file():
        value = json.loads(COMMITS.read_text()).get("harveyai@harvey-labs")
    else:
        value = os.environ.get("LAB_SOURCE_COMMIT")
    if not isinstance(value, str) or len(value) < 12:
        raise RuntimeError("Harvey LAB source commit is not pinned")
    return value


def import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tokens(text: str) -> collections.Counter[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    values = re.findall(r"[$€£¥]?\d+(?:[.,]\d+)*(?:%|bps)?|§+|[a-z][\w.'’-]{2,}", normalized)
    canonical = []
    for value in values:
        if value in {"nan", "none", "unnamed"}:
            continue
        numeric = re.fullmatch(r"([$€£¥]?)(\d+(?:[.,]\d+)*)(%|bps)?", value)
        if numeric:
            prefix, number, suffix = numeric.groups()
            number = number.replace(",", "")
            if "." in number:
                number = number.rstrip("0").rstrip(".")
            value = f"{prefix}{number}{suffix or ''}"
        canonical.append(value)
    return collections.Counter(canonical)


def recall(reference: str, candidate: str) -> float:
    expected = tokens(reference)
    actual = tokens(candidate)
    denominator = sum(expected.values())
    if not denominator:
        return 1.0 if not candidate.strip() else 0.0
    overlap = sum(min(count, actual[token]) for token, count in expected.items())
    return overlap / denominator


def sample_paths(source: Path) -> list[Path]:
    task_dirs = sorted(path.parent for path in (source / "tasks").rglob("task.json"))
    by_format: dict[str, list[Path]] = {extension: [] for extension in FORMATS}
    for task_dir in task_dirs:
        documents = task_dir / "documents"
        if not documents.is_dir():
            continue
        for path in documents.rglob("*"):
            if path.is_file() and path.suffix.lower() in by_format:
                by_format[path.suffix.lower()].append(path)
    selected: list[Path] = []
    for extension, count in FORMATS.items():
        ordered = sorted(
            by_format[extension],
            key=lambda path: hashlib.sha256(path.relative_to(source).as_posix().encode()).hexdigest(),
        )
        if len(ordered) < count:
            raise RuntimeError(f"only {len(ordered)} {extension} documents; need {count}")
        step = len(ordered) / count
        selected.extend(ordered[int(index * step)] for index in range(count))
    return selected


def worker(source: Path, ingest_path: Path) -> dict:
    ingest = import_file("lab_ingest_worker", ingest_path)
    harvey = import_file("harvey_parse_doc", source / "sandbox" / "parsers" / "parse_doc.py")
    reference_parsers = {
        ".docx": harvey.parse_docx,
        ".xlsx": harvey.parse_xlsx,
        ".pptx": harvey.parse_pptx,
    }
    rows = []
    for path in sample_paths(source):
        extension = path.suffix.lower()
        relative = path.relative_to(source).as_posix()
        try:
            reference = reference_parsers[extension](str(path))
            candidate = ingest.parse_document(path, extension)
            score = recall(reference, candidate)
            rows.append({
                "path": relative,
                "ext": extension,
                "recall": round(score, 8),
                "reference_chars": len(reference),
                "candidate_chars": len(candidate),
                "error": None,
            })
        except Exception as exc:
            rows.append({"path": relative, "ext": extension, "recall": 0.0,
                         "reference_chars": 0, "candidate_chars": 0,
                         "error": f"{type(exc).__name__}: {exc}"[:500]})
    formats = {}
    for extension in FORMATS:
        matches = [row for row in rows if row["ext"] == extension]
        formats[extension] = {
            "documents": len(matches),
            "mean_token_recall": round(sum(row["recall"] for row in matches) / len(matches), 8),
            "minimum_token_recall": min(row["recall"] for row in matches),
            "errors": sum(bool(row["error"]) for row in matches),
            "worst": sorted(matches, key=lambda row: (row["recall"], row["path"]))[:3],
        }
    return {"extractor_version": ingest.EXTRACTOR_VERSION,
            "extractor_sha256": hashlib.sha256(ingest_path.read_bytes()).hexdigest(),
            "formats": formats, "samples": rows}


def validate(report: dict) -> None:
    failures = []
    for extension, metrics in report["formats"].items():
        if metrics["errors"]:
            failures.append(f"{extension}: {metrics['errors']} parser errors")
        if metrics["mean_token_recall"] < MIN_MEAN_RECALL:
            failures.append(f"{extension}: mean recall {metrics['mean_token_recall']:.4f} < {MIN_MEAN_RECALL}")
        if metrics["minimum_token_recall"] < MIN_DOCUMENT_RECALL:
            failures.append(
                f"{extension}: minimum recall {metrics['minimum_token_recall']:.4f} < {MIN_DOCUMENT_RECALL}"
            )
    if failures:
        raise RuntimeError("LAB extractor parity failed: " + "; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--ingest", type=Path, default=INGEST)
    parser.add_argument("--image", default=f"legal-agent-lab-parser:{pinned_commit()}")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.source, args.ingest), sort_keys=True))
        return 0
    if args.check:
        report = json.loads(REPORT.read_text())
        expected_thresholds = {"mean_token_recall": MIN_MEAN_RECALL,
                               "minimum_document_token_recall": MIN_DOCUMENT_RECALL}
        if report.get("thresholds") != expected_thresholds:
            raise RuntimeError("extractor thresholds changed without regenerating parity report")
        ingest = import_file("lab_ingest_check", INGEST)
        if report.get("candidate_extractor") != ingest.EXTRACTOR_VERSION:
            raise RuntimeError("extractor version changed without regenerating parity report")
        if report.get("extractor_sha256") != hashlib.sha256(INGEST.read_bytes()).hexdigest():
            raise RuntimeError("extractor implementation changed without regenerating parity report")
        if report.get("source_commit") != pinned_commit():
            raise RuntimeError("parity report source commit differs from the checked-in Harvey pin")
        validate(report)
        print("LAB extractor parity: committed report passes")
        return 0
    if not SOURCE.is_dir():
        raise RuntimeError(f"LAB source missing: {SOURCE}")
    commit = pinned_commit()
    image_id = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", args.image],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    command = [
        "docker", "run", "--rm", "--network=none",
        "--mount", f"type=bind,src={SOURCE},dst=/source,readonly",
        "--mount", f"type=bind,src={INGEST},dst=/ingest/lab_ingest.py,readonly",
        "--mount", f"type=bind,src={Path(__file__).resolve()},dst=/gate/check.py,readonly",
        "--env", f"LAB_SOURCE_COMMIT={commit}",
        args.image, "python3", "/gate/check.py", "--worker",
        "--source", "/source", "--ingest", "/ingest/lab_ingest.py",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    report = {
        "schema_version": 1,
        "source_repo": "harveyai/harvey-labs",
        "source_commit": commit,
        "parser_image": image_id,
        "candidate_extractor": payload.pop("extractor_version"),
        "reference_extractor": "Harvey LAB sandbox/parsers/parse_doc.py",
        "thresholds": {"mean_token_recall": MIN_MEAN_RECALL,
                       "minimum_document_token_recall": MIN_DOCUMENT_RECALL},
        **payload,
    }
    validate(report)
    REPORT.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("LAB extractor parity:")
    for extension, metrics in report["formats"].items():
        print(f"  {extension}: mean={metrics['mean_token_recall']:.4%} "
              f"minimum={metrics['minimum_token_recall']:.4%} errors={metrics['errors']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
