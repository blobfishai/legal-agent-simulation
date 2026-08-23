#!/usr/bin/env python3
"""Hermetic build/query gate for the C&H FTS compiler."""
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

from world.corpus.build_ch_fts import build  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ch-fts-") as temporary:
        root = Path(temporary)
        store = root / "ch"
        (store / "text" / "1001-00001").mkdir(parents=True)
        (store / "text" / "1001-00001" / "one.txt").write_text("patent litigation claim chart")
        (store / "text" / "1002-00002").mkdir(parents=True)
        (store / "text" / "1002-00002" / "two.txt").write_text("merger filing HSR analysis")
        connection = sqlite3.connect(store / "index.sqlite")
        connection.execute("CREATE TABLE files(id INTEGER PRIMARY KEY,text_path TEXT,chars INTEGER,parse_error TEXT)")
        connection.executemany("INSERT INTO files VALUES (?,?,?,NULL)", [
            (1, "text/1001-00001/one.txt", 29),
            (2, "text/1002-00002/two.txt", 26),
        ])
        connection.commit()
        connection.close()
        # The production source lock belongs to the real corpus; isolate only
        # build mechanics here and inspect the returned deterministic counts.
        import world.corpus.build_ch_fts as module
        original = module.source_tree
        module.source_tree = lambda: "fixture-tree"
        try:
            report = build(store, root / "report.json")
        finally:
            module.source_tree = original
        assert report["indexed_files"] == 2 and report["parse_failures"] == 0
        connection = sqlite3.connect(store / "index.sqlite")
        rows = connection.execute(
            "SELECT file_id FROM files_fts WHERE files_fts MATCH 'patent'"
        ).fetchall()
        connection.close()
        assert rows == [(1,)]
        assert json.loads((root / "report.json").read_text())["text_tree_sha256"]
    print("C&H FTS compiler: deterministic counts, metadata, and retrieval pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
