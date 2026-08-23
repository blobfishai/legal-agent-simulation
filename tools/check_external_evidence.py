#!/usr/bin/env python3
"""Hermetic gate for task-scoped LAB/C&H evidence behind DMS tools."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "world" / "local"))

from evidence import CH_ID_BASE, LAB_ID_BASE, ExternalEvidence, _fts_query  # noqa: E402


def lab_store(root: Path) -> Path:
    store = root / "lab"
    (store / "text").mkdir(parents=True)
    (store / "text" / "one.txt").write_text("Escrow releases after board approval.")
    (store / "text" / "two.txt").write_text("The escrow amount is $54 million.")
    (store / "text" / "other.txt").write_text("Escrow in another task must stay scoped out.")
    connection = sqlite3.connect(store / "index.sqlite")
    connection.executescript("""
      CREATE TABLE files(task_id TEXT,ordinal INTEGER,filename TEXT,relative_path TEXT,blob_sha256 TEXT);
      CREATE TABLE blobs(sha256 TEXT PRIMARY KEY,text_path TEXT,parse_status TEXT);
      CREATE VIRTUAL TABLE blobs_fts USING fts5(sha256 UNINDEXED,content);
    """)
    rows = [
        ("task-a", 0, "approval.docx", "approval.docx", "a", "text/one.txt", "Escrow releases after board approval."),
        ("task-a", 1, "amount.xlsx", "amount.xlsx", "b", "text/two.txt", "The escrow amount is $54 million."),
        ("task-b", 0, "other.docx", "other.docx", "c", "text/other.txt", "Escrow in another task must stay scoped out."),
    ]
    for task, ordinal, filename, relative, digest, text_path, content in rows:
        connection.execute("INSERT INTO files VALUES (?,?,?,?,?)", (task, ordinal, filename, relative, digest))
        connection.execute("INSERT INTO blobs VALUES (?,?,?)", (digest, text_path, "parsed"))
        connection.execute("INSERT INTO blobs_fts VALUES (?,?)", (digest, content))
    connection.commit()
    connection.close()
    return store


def ch_store(root: Path) -> Path:
    store = root / "ch"
    (store / "text" / "1001-00001").mkdir(parents=True)
    (store / "text" / "1001-00001" / "memo.txt").write_text("Patent litigation strategy and claim chart.")
    connection = sqlite3.connect(store / "index.sqlite")
    connection.executescript("""
      CREATE TABLE files(id INTEGER PRIMARY KEY,matter_id TEXT,client_id TEXT,filename TEXT,text_path TEXT,parse_error TEXT);
      CREATE VIRTUAL TABLE files_fts USING fts5(file_id UNINDEXED,content);
      INSERT INTO files VALUES (7,'1001-00001','1001','strategy.docx','text/1001-00001/memo.txt',NULL);
      INSERT INTO files_fts VALUES (7,'Patent litigation strategy and claim chart.');
    """)
    connection.commit()
    connection.close()
    return store


def main() -> int:
    assert _fts_query('"springing lien"') == '"springing lien"'
    assert _fts_query('"semiconductor" AND "injunction" AND litigat*') == (
        '"semiconductor" AND "injunction" AND "litigat"*'
    )
    assert _fts_query('"patent" AND') == ""
    with tempfile.TemporaryDirectory(prefix="external-evidence-") as temporary:
        root = Path(temporary)
        lab = ExternalEvidence({"kind": "lab", "task_id": "task-a", "path": str(lab_store(root))}, ROOT)
        ok, raw = lab.call("documents_search_fulltext", {"query": "escrow", "limit": 1})
        assert ok
        page = json.loads(raw)["data"]
        assert page["total"] == 2 and len(page["results"]) == 1
        assert page["has_more"] and page["next_offset"] == 1
        ok, raw = lab.call("documents_search_fulltext", {"query": "another task"})
        assert ok and json.loads(raw)["data"]["total"] == 0
        ok, raw = lab.call("documents_search_fulltext", {"query": "amount.xlsx"})
        exact = json.loads(raw)["data"]
        assert ok and exact["total"] == 1 and exact["results"][0]["id"] == LAB_ID_BASE + 1
        ok, raw = lab.call("documents_search_fulltext", {"query": "*", "limit": 1, "offset": 1})
        exhaustive = json.loads(raw)["data"]
        assert ok and exhaustive["total"] == 2 and exhaustive["offset"] == 1
        ok, raw = lab.call("documents_get", {"id": LAB_ID_BASE})
        assert ok and "body" not in json.loads(raw)["data"]
        ok, raw = lab.call("documents_download", {"id": LAB_ID_BASE + 1})
        assert ok and "$54 million" in json.loads(raw)["data"]["body"]
        # The Harbor world image intentionally packages only index.sqlite,
        # not tens of thousands of duplicate extracted-text files.  Downloads
        # must therefore fall back to the body embedded in the FTS index.
        (lab.store / "text" / "two.txt").unlink()
        ok, raw = lab.call("documents_download", {"id": LAB_ID_BASE + 1})
        assert ok and "$54 million" in json.loads(raw)["data"]["body"]
        ok, raw = lab.call("documents_download", {"id": LAB_ID_BASE + 99})
        assert not ok and "404" in raw
        assert lab.call("documents_create", {}) is None

        ch = ExternalEvidence({"kind": "ch", "path": str(ch_store(root))}, ROOT)
        ok, raw = ch.call("documents_search", {"name": "patent litigation"})
        result = json.loads(raw)["data"]["results"][0]
        assert ok and result["matter_id"] == "1001-00001" and result["client_id"] == "1001"
        ok, raw = ch.call("documents_search_fulltext", {"query": "1001-00001"})
        assert ok and json.loads(raw)["data"]["total"] == 1
        ok, raw = ch.call("documents_search_fulltext", {"query": '"patent" AND "claim"'})
        assert ok and json.loads(raw)["data"]["total"] == 1
        ok, raw = ch.call("documents_download", {"id": CH_ID_BASE + 7})
        assert ok and "claim chart" in json.loads(raw)["data"]["body"]
        (ch.store / "text" / "1001-00001" / "memo.txt").unlink()
        ok, raw = ch.call("documents_download", {"id": CH_ID_BASE + 7})
        assert ok and "claim chart" in json.loads(raw)["data"]["body"]

    print("external evidence: task scope, exact-name/FTS paging, DMS envelopes, full-body reads pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
