#!/usr/bin/env python3
"""Fail-closed structural gate for the commit-pinned LAB port bundles."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text())


def main() -> int:
    lock = load("world/ingest/lab-source-lock.json")
    practice = load("world/port/bundles/harvey-practice.json")
    knowledge = load("world/port/bundles/harvey-firm-knowledge.json")
    ingest_report = load("world/ingest/lab-ingest-report.json")
    known_defects = load("research/harvey-augmentation/upstream-ooxml-defects.json")
    commits = load("research/repos-commits.json")
    commit = commits["harveyai@harvey-labs"]

    assert lock["source_commit"] == commit
    assert practice["source"]["commit"] == knowledge["source"]["commit"] == commit
    assert all(task.get("deliverables") == ["response.md"] for task in knowledge["tasks"])
    assert len(practice["tasks"]) == 1760
    assert len(knowledge["tasks"]) == 250
    assert len(practice["tasks"]) + len(knowledge["tasks"]) == lock["tasks"] == 2010
    practice_criteria = sum(task["criteria_count"] for task in practice["tasks"])
    knowledge_criteria = sum(len(task["criteria"]) for task in knowledge["tasks"])
    assert practice_criteria + knowledge_criteria == lock["criteria"] == 114437
    assert practice["documents"]["external_store"] == "world/corpus/lab"
    assert knowledge["documents"]["external_store"] == "world/corpus/ch"
    assert lock["documents"] == 51683
    assert lock["shared_documents"] == 9288
    assert ingest_report["source_commit"] == commit
    assert ingest_report["documents"] == 51683
    assert ingest_report["parsed_documents"] == 51683
    assert ingest_report["failed_documents"] == 0
    assert ingest_report["recovered_documents"] == 9
    assert all(
        row["kind"] == "escaped_unescaped_xml_ampersands"
        for row in ingest_report["unique_recoveries"]
    )
    observed_recoveries = {
        (row["sha256"], part["part"], part["occurrences"])
        for row in ingest_report["unique_recoveries"]
        for part in row["parts"]
    }
    expected_recoveries = {
        (row["sha256"], row["part"], row["occurrences"])
        for row in known_defects["defects"]
    }
    assert observed_recoveries == expected_recoveries

    lane = practice["file_lane"]
    assert lane["tasks"] == 1760
    assert lane["exact_filename_contracts"] == 1758
    assert lane["missing_filename_contracts"] == [
        "lab_contracts__commercial-vendor-customer__master-services-agreement-counterparty-paper-review__scenario-02",
        "lab_contracts__commercial-vendor-customer__vendor-services-agreement-term-negotiation__scenario-03",
    ]
    assert all(task["file_lane"]["source_commit"] == commit for task in practice["tasks"])
    assert all(task["provenance"]["path"] ==
               f"tasks/{task['file_lane']['source_task']}/task.json"
               for task in practice["tasks"])

    ch_index = ROOT / "world" / "corpus" / "ch" / "index.sqlite"
    if ch_index.is_file():
        connection = sqlite3.connect(f"file:{ch_index}?mode=ro", uri=True)
        count = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        failures = connection.execute("SELECT COUNT(*) FROM files WHERE parse_error IS NOT NULL").fetchone()[0]
        connection.close()
        assert (count, failures) == (9288, 0)

    lab_index = ROOT / "world" / "corpus" / "lab" / "index.sqlite"
    if lab_index.is_file():
        connection = sqlite3.connect(f"file:{lab_index}?mode=ro", uri=True)
        count = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        failures = connection.execute(
            "SELECT COUNT(*) FROM blobs WHERE parse_status != 'parsed'"
        ).fetchone()[0]
        commits = {
            row[0] for row in connection.execute("SELECT DISTINCT source_commit FROM files")
        }
        connection.close()
        assert (count, failures, commits) == (51683, 0, {commit})

    print("LAB port: 2,010/2,010 tasks, 114,437 criteria, 60,971 input files, 1,758 exact output contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
