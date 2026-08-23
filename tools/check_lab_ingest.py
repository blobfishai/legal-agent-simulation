#!/usr/bin/env python3
"""Hermetic gate for the LAB evidence importer using trusted tiny fixtures."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "world" / "ingest" / "lab_ingest.py"


def write_task(root: Path, relative: str, documents: dict[str, bytes]) -> None:
    task = root / "tasks" / relative
    (task / "documents").mkdir(parents=True)
    (task / "task.json").write_text(json.dumps({
        "title": relative,
        "work_type": "analyze",
        "instructions": "Read the evidence.",
        "deliverables": {"answer.md": "answer.md"},
        "criteria": [{"id": "C-001", "match_criteria": "PASS if Alpha appears."}],
    }))
    for name, body in documents.items():
        path = task / "documents" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


def run(*arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["python3", str(INGEST), *arguments], cwd=ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != expect:
        raise AssertionError(
            f"expected exit {expect}, got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="lab-ingest-gate-") as temporary:
        base = Path(temporary)
        source = base / "source"
        destination = base / "store"
        lock = base / "source-lock.json"
        (source / "LICENSE").parent.mkdir(parents=True)
        (source / "LICENSE").write_text("MIT fixture\n")
        (source / "sandbox" / "parsers").mkdir(parents=True)
        (source / "sandbox" / "Dockerfile").write_text("FROM scratch\n")
        (source / "sandbox" / "parsers" / "parse_doc.py").write_text("# fixture parser\n")
        (source / "harness" / "skills" / "docx").mkdir(parents=True)
        (source / "harness" / "system_prompt.md").write_text("Fixture system prompt\n")
        (source / "harness" / "skills" / "docx" / "SKILL.md").write_text("# fixture skill\n")
        write_task(source, "antitrust/example", {
            "memo.txt": b"Alpha is 54 million dollars.\n",
            "facts.json": b'{"party":"Alpha"}\n',
        })
        # Repeated bytes prove that occurrence rows and content-addressed blobs
        # have intentionally different cardinalities.
        write_task(source, "contracts/example", {"same.txt": b"Alpha is 54 million dollars.\n"})

        common = ("--source", str(source), "--dest", str(destination), "--lock", str(lock))
        run(*common, "--inventory-only", "--write-lock")
        run(*common, "--parser", "host")
        checked = run(*common, "--check", "--deep")
        assert "3 documents, 2 unique blobs verified deeply" in checked.stdout

        connection = sqlite3.connect(destination / "index.sqlite")
        assert connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM blobs").fetchone()[0] == 2
        match = connection.execute(
            "SELECT COUNT(*) FROM blobs_fts WHERE blobs_fts MATCH 'Alpha'"
        ).fetchone()[0]
        assert match == 2
        provenance = connection.execute(
            "SELECT DISTINCT source_repo,source_commit,license FROM files"
        ).fetchall()
        assert provenance == [("harveyai/harvey-labs", json.loads((ROOT / "research/repos-commits.json").read_text())["harveyai@harvey-labs"], "MIT")]
        connection.close()

        # Any byte drift must fail against the frozen source lock.
        drift = source / "tasks" / "antitrust" / "example" / "documents" / "memo.txt"
        drift.write_text("Alpha is 55 million dollars.\n")
        failed = run(*common, "--check", expect=1)
        assert "source differs from the pinned lock" in failed.stderr

    print("LAB ingest gate: source lock, deduplication, provenance, FTS, and drift rejection pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
