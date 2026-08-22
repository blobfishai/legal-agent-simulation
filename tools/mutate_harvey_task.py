#!/usr/bin/env python3
"""Create deterministic, provenance-rich Harvey LAB task derivatives.

The tool never edits the Harvey mirror.  It copies one task into a separate
augmentation tree, applies fail-closed text substitutions to text/OOXML parts,
updates task metadata and rubric criteria from a declarative recipe, then
records source/output hashes and package-topology checks in a manifest.

Text substitutions in OOXML are performed on raw XML bytes.  The XML is not
parsed and reserialized, so run, style, relationship, drawing, worksheet, and
section structures remain byte-for-byte untouched outside matched text.

Usage:
    python3 tools/mutate_harvey_task.py --recipe path/to/recipe.json
    python3 tools/mutate_harvey_task.py --check path/to/generated/task
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "research" / "repos" / "harveyai@harvey-labs"
DEFAULT_OUTPUT = ROOT / "research" / "harvey-augmentation" / "generated"
OOXML_EXTENSIONS = {".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm"}
TEXT_EXTENSIONS = {".eml", ".txt", ".md", ".json", ".csv", ".xml", ".html", ".htm"}
XML_PART_EXTENSIONS = {".xml", ".rels"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def safe_relative(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe {label}: {value!r}")
    return path


def git_commit(source: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate_recipe(recipe: dict[str, Any]) -> None:
    if recipe.get("schema_version") != 1:
        raise ValueError("recipe schema_version must be 1")
    for field in ("variant_id", "source_task", "output_task"):
        if not isinstance(recipe.get(field), str) or not recipe[field].strip():
            raise ValueError(f"recipe requires non-empty {field}")
    safe_relative(recipe["source_task"], "source_task")
    safe_relative(recipe["output_task"], "output_task")

    seen = set()
    for index, replacement in enumerate(recipe.get("replacements") or []):
        old = replacement.get("old")
        new = replacement.get("new")
        if not isinstance(old, str) or not old:
            raise ValueError(f"replacement {index} requires non-empty old text")
        if not isinstance(new, str):
            raise ValueError(f"replacement {index} requires string new text")
        if old in seen:
            raise ValueError(f"duplicate replacement source: {old!r}")
        seen.add(old)
        if recipe.get("layout_preserving", True) and len(old) != len(new):
            raise ValueError(
                f"layout-preserving recipe requires equal-length text: {old!r} -> {new!r}"
            )


def deep_replace(value: Any, replacements: list[dict[str, Any]], counts: Counter[str]) -> Any:
    if isinstance(value, str):
        for replacement in replacements:
            old, new = replacement["old"], replacement["new"]
            occurrences = value.count(old)
            if occurrences:
                value = value.replace(old, new)
                counts[old] += occurrences
        return value
    if isinstance(value, list):
        return [deep_replace(item, replacements, counts) for item in value]
    if isinstance(value, dict):
        return {key: deep_replace(item, replacements, counts) for key, item in value.items()}
    return value


def replacement_applies(replacement: dict[str, Any], extension: str) -> bool:
    extensions = replacement.get("extensions")
    return not extensions or extension in {str(value).lower() for value in extensions}


def package_topology(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        rows = [
            {
                "name": info.filename,
                "compression": info.compress_type,
                "date_time": info.date_time,
                "flag_bits": info.flag_bits,
                "create_system": info.create_system,
                "create_version": info.create_version,
                "extract_version": info.extract_version,
                "external_attr": info.external_attr,
                "internal_attr": info.internal_attr,
                "extra": info.extra.hex(),
                "comment": info.comment.hex(),
                "directory": info.is_dir(),
            }
            for info in archive.infolist()
        ]
        archive_comment = archive.comment.hex()
    return {
        "parts": len(rows),
        "archive_comment": archive_comment,
        "sha256": sha256_bytes(canonical_json(rows)),
    }


def validate_ooxml(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC failure in {bad}")
        for name in archive.namelist():
            if PurePosixPath(name).suffix.lower() in XML_PART_EXTENSIONS:
                ElementTree.fromstring(archive.read(name))


def mutate_ooxml(
    source: Path,
    destination: Path,
    replacements: list[dict[str, Any]],
) -> tuple[Counter[str], list[str]]:
    counts: Counter[str] = Counter()
    changed_parts: list[str] = []
    with zipfile.ZipFile(source) as input_archive, zipfile.ZipFile(destination, "w") as output_archive:
        for info in input_archive.infolist():
            payload = input_archive.read(info.filename)
            original = payload
            if PurePosixPath(info.filename).suffix.lower() in XML_PART_EXTENSIONS:
                for replacement in replacements:
                    old = xml_escape(replacement["old"]).encode("utf-8")
                    new = xml_escape(replacement["new"]).encode("utf-8")
                    occurrences = payload.count(old)
                    if occurrences:
                        payload = payload.replace(old, new)
                        counts[replacement["old"]] += occurrences
            if payload != original:
                changed_parts.append(info.filename)
            output_archive.writestr(info, payload)
    if package_topology(source) != package_topology(destination):
        raise ValueError(f"OOXML package topology changed: {source.name}")
    validate_ooxml(destination)
    return counts, changed_parts


def mutate_text(
    source: Path,
    destination: Path,
    replacements: list[dict[str, Any]],
) -> tuple[Counter[str], list[str]]:
    payload = source.read_bytes()
    counts: Counter[str] = Counter()
    for replacement in replacements:
        old = replacement["old"].encode("utf-8")
        new = replacement["new"].encode("utf-8")
        occurrences = payload.count(old)
        if occurrences:
            payload = payload.replace(old, new)
            counts[replacement["old"]] += occurrences
    destination.write_bytes(payload)
    if destination.suffix.lower() == ".json":
        json.loads(destination.read_text(encoding="utf-8"))
    elif destination.suffix.lower() == ".eml":
        with destination.open("rb") as handle:
            BytesParser(policy=policy.default).parse(handle)
    return counts, [destination.name] if counts else []


def copy_or_mutate(
    source: Path,
    destination: Path,
    replacements: list[dict[str, Any]],
) -> tuple[Counter[str], list[str]]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    extension = source.suffix.lower()
    applicable = [item for item in replacements if replacement_applies(item, extension)]
    if not applicable:
        shutil.copy2(source, destination)
        return Counter(), []
    if extension in OOXML_EXTENSIONS:
        return mutate_ooxml(source, destination, applicable)
    if extension in TEXT_EXTENSIONS:
        return mutate_text(source, destination, applicable)

    payload = source.read_bytes()
    matched = [item["old"] for item in applicable if item["old"].encode("utf-8") in payload]
    if matched:
        raise ValueError(
            f"refusing unsupported binary mutation for {source.name}; matched {matched}"
        )
    shutil.copy2(source, destination)
    return Counter(), []


def verify_document_derivative(
    source: Path,
    output: Path,
    replacements: list[dict[str, Any]],
) -> tuple[Counter[str], list[str]]:
    """Re-derive expected content and reject any unrecorded document change."""
    extension = source.suffix.lower()
    applicable = [item for item in replacements if replacement_applies(item, extension)]
    counts: Counter[str] = Counter()
    changed_parts: list[str] = []

    if extension in OOXML_EXTENSIONS:
        with zipfile.ZipFile(source) as source_archive, zipfile.ZipFile(output) as output_archive:
            if source_archive.namelist() != output_archive.namelist():
                raise ValueError(f"OOXML part order differs from source: {source.name}")
            for name in source_archive.namelist():
                expected = source_archive.read(name)
                original = expected
                if PurePosixPath(name).suffix.lower() in XML_PART_EXTENSIONS:
                    for replacement in applicable:
                        old = xml_escape(replacement["old"]).encode("utf-8")
                        new = xml_escape(replacement["new"]).encode("utf-8")
                        occurrences = expected.count(old)
                        if occurrences:
                            expected = expected.replace(old, new)
                            counts[replacement["old"]] += occurrences
                if expected != original:
                    changed_parts.append(name)
                if output_archive.read(name) != expected:
                    raise ValueError(
                        f"OOXML content has a non-recipe change: {source.name}:{name}"
                    )
        return counts, changed_parts

    expected = source.read_bytes()
    original = expected
    if extension in TEXT_EXTENSIONS:
        for replacement in applicable:
            old = replacement["old"].encode("utf-8")
            new = replacement["new"].encode("utf-8")
            occurrences = expected.count(old)
            if occurrences:
                expected = expected.replace(old, new)
                counts[replacement["old"]] += occurrences
    if output.read_bytes() != expected:
        raise ValueError(f"document content has a non-recipe change: {source.name}")
    if expected != original:
        changed_parts.append(output.name)
    return counts, changed_parts


def validate_task(task: dict[str, Any]) -> None:
    if not str(task.get("title") or "").strip():
        raise ValueError("generated task title is empty")
    if not str(task.get("instructions") or "").strip():
        raise ValueError("generated task instructions are empty")
    deliverables = task.get("deliverables")
    if not isinstance(deliverables, dict) or not deliverables:
        raise ValueError("generated task requires deliverables mapping")
    criteria = task.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("generated task requires criteria")
    identifiers = [criterion.get("id") for criterion in criteria]
    if any(not identifier for identifier in identifiers) or len(identifiers) != len(set(identifiers)):
        raise ValueError("generated criterion IDs must be non-empty and unique")
    for criterion in criteria:
        if not isinstance(criterion.get("deliverables"), list):
            raise ValueError(f"criterion {criterion.get('id')} requires a deliverables list")
        if not str(criterion.get("match_criteria") or "").startswith("PASS if"):
            raise ValueError(f"criterion {criterion.get('id')} requires fail-closed PASS if text")


def apply_task_recipe(
    source_task: dict[str, Any],
    recipe: dict[str, Any],
    source_commit: str,
    recipe_sha256: str,
) -> tuple[dict[str, Any], Counter[str]]:
    counts: Counter[str] = Counter()
    task = deep_replace(source_task, recipe.get("replacements") or [], counts)
    for key, value in (recipe.get("task_overrides") or {}).items():
        task[key] = value

    overrides = recipe.get("criterion_overrides") or {}
    found = set()
    for criterion in task.get("criteria") or []:
        identifier = criterion.get("id")
        if identifier in overrides:
            criterion.update(overrides[identifier])
            found.add(identifier)
    missing = sorted(set(overrides) - found)
    if missing:
        raise ValueError(f"criterion overrides reference missing IDs: {missing}")

    task["augmentation"] = {
        "variant_id": recipe["variant_id"],
        "source_repo": "harveyai/harvey-labs",
        "source_commit": source_commit,
        "source_task": recipe["source_task"],
        "recipe_sha256": recipe_sha256,
        "mutation_axes": recipe.get("mutation_axes") or [],
        "originals_immutable": True,
    }
    validate_task(task)
    return task, counts


def generate(recipe_path: Path, source_root: Path, output_root: Path) -> Path:
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    validate_recipe(recipe)
    serialized_recipe = canonical_json(recipe)
    recipe_sha256 = sha256_bytes(serialized_recipe)
    source_commit = git_commit(source_root)
    expected_commit = recipe.get("source_commit")
    if expected_commit and not source_commit.startswith(expected_commit):
        raise ValueError(f"source commit mismatch: expected {expected_commit}, got {source_commit}")

    source_task_relative = safe_relative(recipe["source_task"], "source_task")
    output_task_relative = safe_relative(recipe["output_task"], "output_task")
    source_task_dir = source_root / "tasks" / Path(*source_task_relative.parts)
    source_task_json = source_task_dir / "task.json"
    source_documents = source_task_dir / "documents"
    if not source_task_json.is_file() or not source_documents.is_dir():
        raise ValueError("pilot generator currently requires a task-local documents directory")

    output_task_dir = output_root / "tasks" / Path(*output_task_relative.parts)
    if output_task_dir.exists():
        raise FileExistsError(f"output task already exists: {output_task_dir}")

    source_paths = sorted(path for path in source_documents.rglob("*") if path.is_file())
    source_hashes = {path: sha256_file(path) for path in source_paths}
    source_task = json.loads(source_task_json.read_text(encoding="utf-8"))
    generated_task, task_counts = apply_task_recipe(
        source_task, recipe, source_commit, recipe_sha256
    )

    output_task_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="harvey-augmentation-", dir=output_task_dir.parent) as temporary:
        staging = Path(temporary) / output_task_dir.name
        staging_documents = staging / "documents"
        staging_documents.mkdir(parents=True)
        aggregate_counts: Counter[str] = Counter()
        file_rows = []

        for source_path in source_paths:
            relative = source_path.relative_to(source_documents)
            destination = staging_documents / relative
            counts, changed_parts = copy_or_mutate(
                source_path, destination, recipe.get("replacements") or []
            )
            aggregate_counts.update(counts)
            file_rows.append({
                "path": relative.as_posix(),
                "extension": source_path.suffix.lower(),
                "source_sha256": source_hashes[source_path],
                "output_sha256": sha256_file(destination),
                "source_bytes": source_path.stat().st_size,
                "output_bytes": destination.stat().st_size,
                "replacement_counts": dict(sorted(counts.items())),
                "changed_package_parts": sorted(changed_parts),
                "package_topology_preserved": (
                    package_topology(source_path) == package_topology(destination)
                    if source_path.suffix.lower() in OOXML_EXTENSIONS else None
                ),
            })

        for replacement in recipe.get("replacements") or []:
            old = replacement["old"]
            if aggregate_counts[old] < int(replacement.get("min_document_occurrences", 0)):
                raise ValueError(
                    f"document replacement count for {old!r} is {aggregate_counts[old]}, "
                    f"expected at least {replacement.get('min_document_occurrences', 0)}"
                )
            if task_counts[old] < int(replacement.get("min_task_occurrences", 0)):
                raise ValueError(
                    f"task replacement count for {old!r} is {task_counts[old]}, "
                    f"expected at least {replacement.get('min_task_occurrences', 0)}"
                )

        for source_path, digest in source_hashes.items():
            if sha256_file(source_path) != digest:
                raise RuntimeError(f"source changed during generation: {source_path}")

        (staging / "task.json").write_bytes(canonical_json(generated_task))
        (staging / "augmentation-recipe.json").write_bytes(serialized_recipe)
        manifest = {
            "schema_version": 1,
            "variant_id": recipe["variant_id"],
            "source_repo": "harveyai/harvey-labs",
            "source_commit": source_commit,
            "source_task": recipe["source_task"],
            "output_task": recipe["output_task"],
            "recipe_sha256": recipe_sha256,
            "source_task_json_sha256": sha256_file(source_task_json),
            "output_task_json_sha256": sha256_file(staging / "task.json"),
            "document_replacement_counts": dict(sorted(aggregate_counts.items())),
            "task_replacement_counts": dict(sorted(task_counts.items())),
            "files": file_rows,
        }
        (staging / "mutation-manifest.json").write_bytes(canonical_json(manifest))
        staging.replace(output_task_dir)

    return output_task_dir


def check_generated(task_dir: Path, source_root: Path = DEFAULT_SOURCE) -> None:
    manifest_path = task_dir / "mutation-manifest.json"
    task_path = task_dir / "task.json"
    recipe_path = task_dir / "augmentation-recipe.json"
    if not manifest_path.is_file() or not task_path.is_file() or not recipe_path.is_file():
        raise ValueError(f"not a generated Harvey task: {task_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    task = json.loads(task_path.read_text(encoding="utf-8"))
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    validate_recipe(recipe)
    validate_task(task)

    if sha256_file(recipe_path) != manifest["recipe_sha256"]:
        raise ValueError("generated recipe differs from its manifest")
    if sha256_file(task_path) != manifest["output_task_json_sha256"]:
        raise ValueError("generated task.json differs from its manifest")

    for field in ("variant_id", "source_task", "output_task"):
        if recipe[field] != manifest[field]:
            raise ValueError(f"recipe and manifest disagree on {field}")
    augmentation = task.get("augmentation") or {}
    for field in ("variant_id", "source_task", "source_commit", "recipe_sha256"):
        if augmentation.get(field) != manifest[field]:
            raise ValueError(f"task augmentation and manifest disagree on {field}")

    current_commit = git_commit(source_root)
    if current_commit != manifest["source_commit"]:
        raise ValueError(
            f"source mirror moved: expected {manifest['source_commit']}, got {current_commit}"
        )
    source_task_relative = safe_relative(manifest["source_task"], "source_task")
    source_task_dir = source_root / "tasks" / Path(*source_task_relative.parts)
    source_task_json = source_task_dir / "task.json"
    source_documents = source_task_dir / "documents"
    if not source_task_json.is_file() or not source_documents.is_dir():
        raise ValueError("manifest source task or documents are missing")
    if sha256_file(source_task_json) != manifest["source_task_json_sha256"]:
        raise ValueError("source task.json differs from the generation-time hash")

    source_task = json.loads(source_task_json.read_text(encoding="utf-8"))
    expected_task, expected_task_counts = apply_task_recipe(
        source_task,
        recipe,
        manifest["source_commit"],
        manifest["recipe_sha256"],
    )
    if canonical_json(expected_task) != task_path.read_bytes():
        raise ValueError("generated task.json contains a non-recipe change")
    if dict(sorted(expected_task_counts.items())) != manifest["task_replacement_counts"]:
        raise ValueError("task replacement counts differ from the manifest")

    rows = {row["path"]: row for row in manifest["files"]}
    if len(rows) != len(manifest["files"]):
        raise ValueError("manifest contains duplicate document paths")
    actual = {
        path.relative_to(task_dir / "documents").as_posix(): path
        for path in (task_dir / "documents").rglob("*")
        if path.is_file()
    }
    if set(rows) != set(actual):
        raise ValueError("generated document paths differ from manifest")
    aggregate_counts: Counter[str] = Counter()
    for relative, path in sorted(actual.items()):
        row = rows[relative]
        source_path = source_documents / Path(*PurePosixPath(relative).parts)
        if not source_path.is_file():
            raise ValueError(f"source document is missing: {relative}")
        if sha256_file(source_path) != row["source_sha256"]:
            raise ValueError(f"source document differs from manifest: {relative}")
        if sha256_file(path) != row["output_sha256"]:
            raise ValueError(f"generated document differs from manifest: {relative}")
        counts, changed_parts = verify_document_derivative(
            source_path, path, recipe.get("replacements") or []
        )
        aggregate_counts.update(counts)
        if dict(sorted(counts.items())) != row["replacement_counts"]:
            raise ValueError(f"document replacement counts differ from manifest: {relative}")
        if sorted(changed_parts) != row["changed_package_parts"]:
            raise ValueError(f"changed document parts differ from manifest: {relative}")
        if path.suffix.lower() in OOXML_EXTENSIONS:
            if row["package_topology_preserved"] is not True:
                raise ValueError(f"manifest does not confirm OOXML topology: {relative}")
            if package_topology(source_path) != package_topology(path):
                raise ValueError(f"OOXML package topology differs from source: {relative}")
            validate_ooxml(source_path)
            validate_ooxml(path)
    if dict(sorted(aggregate_counts.items())) != manifest["document_replacement_counts"]:
        raise ValueError("aggregate document replacement counts differ from the manifest")
    print(
        f"generated Harvey task valid: {manifest['variant_id']} "
        f"({len(actual)} documents, source {manifest['source_commit'][:12]})"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    if bool(args.recipe) == bool(args.check):
        parser.error("pass exactly one of --recipe or --check")
    if args.check:
        check_generated(args.check.resolve(), args.source.resolve())
        return 0
    output = generate(args.recipe.resolve(), args.source.resolve(), args.output_root.resolve())
    print(f"generated Harvey task: {output}")
    check_generated(output, args.source.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
