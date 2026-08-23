#!/usr/bin/env python3
"""Hermetic gate for deterministic LAB practice-task admission and grading."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from world.local.evidence import LAB_ID_BASE
from world.v17 import practice


def fixture_index(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript("""
      CREATE TABLE tasks(task_id TEXT PRIMARY KEY,task_json TEXT);
      CREATE TABLE files(task_id TEXT,ordinal INTEGER,file_id TEXT,filename TEXT,
                         blob_sha256 TEXT);
      CREATE TABLE blobs(sha256 TEXT PRIMARY KEY,parse_status TEXT);
    """)
    source = {
        "instructions": "Prepare the requested memo.",
        "deliverables": {"answer.md": "answer.md"},
        "criteria": [{"id": "C-001", "deliverables": ["answer.md"]}],
    }
    connection.execute("INSERT INTO tasks VALUES (?,?)", ("lab__fixture", json.dumps(source)))
    connection.execute("INSERT INTO files VALUES (?,?,?,?,?)",
                       ("lab__fixture", 0, "doc-fixture", "source.docx", "sha-fixture"))
    connection.execute("INSERT INTO blobs VALUES (?,?)", ("sha-fixture", "parsed"))
    connection.commit()
    connection.close()


def main() -> int:
    alternative_reads = practice._minimum_reads(
        [{"criterion_id": "C-alt", "assertions": [{
            "source_files": [{"file_id": "doc-a"}],
            "alternatives": [{"source_file": {"file_id": "doc-a"}},
                             {"source_file": {"file_id": "doc-b"}}],
        }]}],
        {"doc-a": {"parsed": True}, "doc-b": {"parsed": True}},
    )
    assert set(alternative_reads) == {"doc-a", "doc-b"}
    with tempfile.TemporaryDirectory(prefix="practice-import-") as temporary:
        database = Path(temporary) / "index.sqlite"
        fixture_index(database)
        original = practice.LAB_INDEX
        practice.LAB_INDEX = database
        try:
            compiled = [{
                "source_task": "fixture/task",
                "task_id": "lab__fixture",
                "title": "Fixture task",
                "instructions": "Prepare the requested memo.",
                "criteria_total": 1,
                "assertion_count": 1,
                "coverage": 1.0,
                "admission": "compiled",
                "reference_output": "$54M",
                "criteria": [{
                    "criterion_id": "C-001",
                    "reference_fragment": "$54M",
                    "assertions": [{
                        "variants": ["$54M", "$54 million"],
                        "source_files": [{"file_id": "doc-fixture", "relative_path": "source.docx"}],
                    }],
                }],
            }]
            world = {"tasks": [], "verifiers": []}
            result = practice.append_practice_tasks(world, compiled, set())
        finally:
            practice.LAB_INDEX = original

        assert {key: result[key] for key in ("added", "headline", "thin", "quarantined")} == {
            "added": 1, "headline": 1, "thin": 0, "quarantined": 0,
        }
        assert result["quarantine"] == []
        task = world["tasks"][0]
        assert task["contamination"]["lane"] == "verbatim_lab"
        assert task["capability_type"] == 1
        assert task["walk"] == ["documents_search_fulltext", "documents_download", "documents_create"]
        assert task["reference_args"][0] == {"query": "source.docx", "limit": 20}
        assert task["file_lane"]["assertions"][0]["deliverables"] == ["answer.md"]
        namespace: dict = {}
        exec(world["verifiers"][0]["vcode"], namespace)
        initial = {"dm_documents": []}
        final = {"dm_documents": [{"id": 1, "name": "answer.md", "body": "Approved: $54M."}]}
        trace = [
            {"tool": "documents_search_fulltext", "arguments": {"query": "source.docx"},
             "observation": json.dumps({"data": {"results": [{"id": LAB_ID_BASE}]}}), "ok": True},
            {"tool": "documents_download", "arguments": {"id": LAB_ID_BASE},
             "observation": json.dumps({"data": {"body": "The approved amount is $54M."}}), "ok": True},
            {"tool": "documents_create", "arguments": {"name": "answer.md"}, "ok": True},
        ]
        verdict = namespace["verify"](initial, final, trace)
        assert verdict["passed"] and verdict["reward"] == 1.0
        assert (verdict["precision"], verdict["recall"], verdict["f_beta"]) == (1.0, 1.0, 1.0)
        blind = [dict(trace[0], observation='{"data":{"results":[]}}'), *trace[1:]]
        blind_verdict = namespace["verify"](initial, final, blind)
        assert blind_verdict["reward"] == 0.0
        assert "required_search_discovery" in blind_verdict["failed_conditions"]
        wrong = {"dm_documents": [{"id": 1, "name": "answer.md", "body": "Approved: $53M."}]}
        wrong_verdict = namespace["verify"](initial, wrong, trace)
        assert wrong_verdict["reward"] == 0.0 and wrong_verdict["grounding_veto_failed"]
        fabricated = {"dm_documents": [{"id": 1, "name": "answer.md",
                                         "body": "Approved: $54M; invented exposure: $99M."}]}
        fabricated_verdict = namespace["verify"](initial, fabricated, trace)
        assert fabricated_verdict["reward"] == 0.0
        assert fabricated_verdict["fabrication_veto_failed"]
        assert fabricated_verdict["precision"] == 0.5 and fabricated_verdict["recall"] == 1.0
        assert len(fabricated_verdict["over_included"]) == 1
        assert fabricated_verdict["filed_text_sha256"]["answer.md"]

        thin = [{**compiled[0], "source_task": "fixture/thin", "criteria_total": 3,
                 "assertion_count": 0, "coverage": 0.0, "admission": "thin_grading",
                 "criteria": [], "reference_output": ""}]
        source = json.loads(sqlite3.connect(database).execute(
            "SELECT task_json FROM tasks WHERE task_id='lab__fixture'").fetchone()[0])
        connection = sqlite3.connect(database)
        connection.execute("INSERT INTO tasks VALUES (?,?)", ("lab__thin", json.dumps(source)))
        connection.execute("INSERT INTO files VALUES (?,?,?,?,?)",
                           ("lab__thin", 0, "doc-thin", "thin-source.docx", "sha-fixture"))
        connection.commit()
        connection.close()
        thin[0]["task_id"] = "lab__thin"
        original = practice.LAB_INDEX
        practice.LAB_INDEX = database
        try:
            thin_world = {"tasks": [], "verifiers": []}
            thin_result = practice.append_practice_tasks(thin_world, thin, set())
        finally:
            practice.LAB_INDEX = original
        assert thin_result["added"] == thin_result["thin"] == 1
        assert thin_result["quarantined"] == 0
        assert thin_world["tasks"][0]["grading"]["headline_eligible"] is False
        namespace = {}
        exec(thin_world["verifiers"][0]["vcode"], namespace)
        thin_verdict = namespace["verify"](
            {"dm_documents": []},
            {"dm_documents": [{"id": 1, "name": "answer.md", "body": "Completed."}]},
            [{"tool": "documents_search_fulltext", "arguments": {"query": "thin-source.docx"},
              "observation": json.dumps({"data": {"results": [{"id": LAB_ID_BASE}]}}), "ok": True},
             {"tool": "documents_download", "arguments": {"id": LAB_ID_BASE},
              "observation": json.dumps({"data": {"body": "Thin source."}}), "ok": True},
             {"tool": "documents_create", "arguments": {"name": "answer.md"}, "ok": True}],
        )
        assert thin_verdict["passed"] and thin_verdict["all_determinate_pass"] is None
        assert thin_verdict["precision"] is thin_verdict["recall"] is None

    print("practice import: search/read/write path, source discovery, grounding veto pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
