#!/usr/bin/env python3
"""Gate exact P/R, over-inclusion, empty-set, and structural veto behavior."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from world.v17.verifiers import retrieval_vcode


def run(
    code: str,
    body: str,
    read_id: int = 9,
    include_read: bool = True,
    deliverable_name: str = "response.md",
):
    namespace: dict = {}
    exec(code, namespace)
    trace = [
        {"tool": "documents_search_fulltext", "arguments": {"query": "x"},
         "observation": '{"data":{"has_more":false,"next_offset":null,"results":[{"id":9}]}}',
         "ok": True},
        *([{"tool": "documents_download", "arguments": {"id": read_id}, "ok": True}]
          if include_read else []),
        {"tool": "documents_create", "arguments": {"name": deliverable_name}, "ok": True},
    ]
    initial = {"dm_documents": []}
    final = {"dm_documents": [{"id": 1, "name": deliverable_name, "body": body}]}
    return namespace["verify"](initial, final, trace)


def main() -> int:
    keyed = retrieval_vcode("fixture", ["1001-00001", "1002-00002"], [9])
    perfect = run(keyed, "1001-00001\n1002-00002")
    assert perfect["passed"] and perfect["precision"] == perfect["recall"] == 1.0
    mixed = run(keyed, "1001-00001\n1999-99999")
    assert not mixed["passed"]
    assert mixed["precision"] == 0.5 and mixed["recall"] == 0.5
    assert mixed["over_included"] == ["1999-99999"] and mixed["missing"] == ["1002-00002"]
    assert mixed["reward"] == 0.5
    vetoed = run(keyed, "1001-00001\n1002-00002", include_read=False)
    assert vetoed["reward"] == 0.0 and "required_documents_read" in vetoed["failed_conditions"]

    empty = retrieval_vcode("empty", [], [9], [["no qualifying", "none found"]])
    abstained = run(empty, "No qualifying matters were found after exhaustive review.")
    assert abstained["passed"] and abstained["reward"] == 1.0
    fabricated = run(empty, "No qualifying matters except 1999-99999.")
    assert not fabricated["passed"] and fabricated["precision"] == 0.0

    paging = retrieval_vcode("paging", [], [], [["complete"]], paging_required=True)
    namespace: dict = {}
    exec(paging, namespace)
    initial = {"dm_documents": []}
    final = {"dm_documents": [{"id": 1, "name": "response.md", "body": "complete"}]}
    first_page = [
        {"tool": "documents_search_fulltext", "arguments": {"query": "*", "offset": 0},
         "observation": '{"data":{"has_more":true,"next_offset":100,"results":[]}}', "ok": True},
        {"tool": "documents_create", "arguments": {"name": "response.md"}, "ok": True},
    ]
    stopped = namespace["verify"](initial, final, first_page)
    assert stopped["reward"] == 0.0 and not stopped["paging_complete"]
    completed = namespace["verify"](initial, final, [
        first_page[0],
        {"tool": "documents_search_fulltext", "arguments": {"query": "*", "offset": 100},
         "observation": '{"data":{"has_more":false,"next_offset":null,"results":[]}}', "ok": True},
        first_page[1],
    ])
    assert completed["passed"] and completed["paging_complete"]

    print("retrieval grading: P/R, F2, over-inclusion, empty-set, and path vetoes pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
