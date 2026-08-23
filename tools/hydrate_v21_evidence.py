#!/usr/bin/env python3
"""Hydrate and verify the immutable v21 production evidence indexes.

The materialized Harvey LAB and C&H FTS databases are too large for ordinary
Git history.  Their release assets are nevertheless deterministic inputs:
this tool verifies the compressed asset, decompresses it to a temporary file,
verifies the exact SQLite bytes and schema counts, and only then atomically
publishes it under ``world/corpus``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "world" / "corpus" / "v21-production-evidence.json"
DEFAULT_DESTINATION = ROOT / "world" / "corpus"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SQL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text("utf-8"))
    if manifest.get("schema_version") != 1:
        raise RuntimeError("unsupported v21 evidence manifest schema")
    release = manifest.get("release") or {}
    if not release.get("repository") or not release.get("tag"):
        raise RuntimeError("evidence manifest release identity is incomplete")
    indexes = manifest.get("indexes") or {}
    if set(indexes) != {"ch", "lab"}:
        raise RuntimeError("evidence manifest must pin exactly the ch and lab indexes")
    for kind, record in indexes.items():
        if Path(str(record.get("asset", ""))).name != record.get("asset"):
            raise RuntimeError(f"{kind}: unsafe release asset name")
        if record.get("target") != f"{kind}/index.sqlite":
            raise RuntimeError(f"{kind}: unexpected destination")
        for key in ("compressed_sha256", "sqlite_sha256"):
            if not HEX_SHA256.fullmatch(str(record.get(key, ""))):
                raise RuntimeError(f"{kind}: invalid {key}")
        for key in ("compressed_bytes", "sqlite_bytes"):
            if not isinstance(record.get(key), int) or record[key] <= 0:
                raise RuntimeError(f"{kind}: invalid {key}")
        counts = record.get("table_counts") or {}
        if not counts or any(not SQL_NAME.fullmatch(name) for name in counts):
            raise RuntimeError(f"{kind}: unsafe or empty table-count contract")
        if any(not isinstance(value, int) or value < 0 for value in counts.values()):
            raise RuntimeError(f"{kind}: invalid table-count contract")
        metadata_table = record.get("metadata_table")
        metadata = record.get("metadata") or {}
        if not SQL_NAME.fullmatch(str(metadata_table)) or not metadata:
            raise RuntimeError(f"{kind}: missing metadata contract")
    return manifest


def validate_index(path: Path, record: dict[str, Any]) -> None:
    if not path.is_file():
        raise RuntimeError(f"evidence index missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != record["sqlite_bytes"]:
        raise RuntimeError(
            f"{path}: byte count {actual_size} != {record['sqlite_bytes']}"
        )
    actual_hash = sha256_file(path)
    if actual_hash != record["sqlite_sha256"]:
        raise RuntimeError(f"{path}: SHA-256 {actual_hash} is not the pinned index")
    uri = f"file:{urllib.parse.quote(str(path.resolve()))}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    try:
        integrity = connection.execute("PRAGMA quick_check(1)").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"{path}: SQLite quick_check failed: {integrity}")
        for table, expected in sorted(record["table_counts"].items()):
            actual = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if actual != expected:
                raise RuntimeError(f"{path}: {table} count {actual} != {expected}")
        metadata_table = record["metadata_table"]
        for key, expected in sorted(record["metadata"].items()):
            row = connection.execute(
                f"SELECT value FROM {metadata_table} WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                raise RuntimeError(f"{path}: metadata key {key!r} is missing")
            actual = json.loads(row[0])
            if actual != expected:
                raise RuntimeError(f"{path}: metadata {key} {actual!r} != {expected!r}")
    finally:
        connection.close()


def verify_asset(path: Path, record: dict[str, Any]) -> None:
    if not path.is_file():
        raise RuntimeError(f"evidence release asset missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != record["compressed_bytes"]:
        raise RuntimeError(
            f"{path}: compressed byte count {actual_size} != {record['compressed_bytes']}"
        )
    actual_hash = sha256_file(path)
    if actual_hash != record["compressed_sha256"]:
        raise RuntimeError(f"{path}: compressed SHA-256 {actual_hash} is not pinned")


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "legal-agent-simulation-v21"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(8 * 1024 * 1024):
            output.write(chunk)


def hydrate_index(
    kind: str,
    record: dict[str, Any],
    release: dict[str, Any],
    destination_root: Path,
    asset_dir: Path | None,
) -> None:
    target = destination_root / record["target"]
    if target.is_file():
        try:
            validate_index(target, record)
            print(f"{kind}: pinned index already materialized")
            return
        except RuntimeError:
            pass
    if shutil.which("zstd") is None:
        raise RuntimeError("zstd is required to hydrate production evidence")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"v21-{kind}-evidence-") as temporary:
        temporary_root = Path(temporary)
        if asset_dir is not None:
            asset = asset_dir / record["asset"]
        else:
            asset = temporary_root / record["asset"]
            repository = release["repository"].strip("/")
            tag = urllib.parse.quote(release["tag"], safe="")
            name = urllib.parse.quote(record["asset"], safe="")
            url = f"https://github.com/{repository}/releases/download/{tag}/{name}"
            print(f"{kind}: downloading pinned production evidence")
            download(url, asset)
        verify_asset(asset, record)
        staged = target.parent / f".{target.name}.hydrate-{os.getpid()}"
        try:
            subprocess.run(
                ["zstd", "--long=31", "-d", "--no-progress", "-f",
                 str(asset), "-o", str(staged)],
                check=True,
            )
            validate_index(staged, record)
            os.replace(staged, target)
        finally:
            staged.unlink(missing_ok=True)
    print(f"{kind}: hydrated and verified {record['sqlite_bytes']:,} SQLite bytes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--destination-root", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--asset-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest.resolve())
    destination = args.destination_root.resolve()
    asset_dir = args.asset_dir.resolve() if args.asset_dir else None
    if args.check:
        for kind, record in sorted(manifest["indexes"].items()):
            validate_index(destination / record["target"], record)
            print(f"{kind}: exact production index verified")
        return 0
    for kind, record in sorted(manifest["indexes"].items()):
        hydrate_index(kind, record, manifest["release"], destination, asset_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
