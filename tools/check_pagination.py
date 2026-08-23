#!/usr/bin/env python3
"""M2.3 acceptance checks for real dialect cursors and trace diagnostics."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "world" / "local"))

from paging import paging_diagnostic  # noqa: E402
from v2runtime import V2Runtime  # noqa: E402


def call(runtime, connection, tool, arguments):
    ok, text = runtime.call(connection, tool, arguments)
    assert ok, text
    return json.loads(text), {"tool": tool, "arguments": arguments, "ok": True, "observation": text}


def disjoint_ids(first, second, path):
    def descend(value):
        for key in path:
            value = value[key]
        return {str(item.get("id", item.get("ArtifactID"))) for item in value}
    assert descend(first).isdisjoint(descend(second))


def main() -> int:
    runtime = V2Runtime(str(ROOT / "mcp" / "v3" / "contracts"))
    connection = sqlite3.connect(":memory:")
    runtime.create_and_seed(connection)
    trace = []

    first, step = call(runtime, connection, "matters_list", {"limit": 2})
    trace.append(step)
    next_url = first["meta"]["paging"]["next"]
    token = parse_qs(urlparse(next_url).query)["page_token"][0]
    second, step = call(runtime, connection, "matters_list", {"limit": 100, "page_token": token})
    trace.append(step)
    disjoint_ids(first, second, ["data"])

    first, step = call(runtime, connection, "dockets_list", {"limit": 2})
    trace.append(step)
    page = int(parse_qs(urlparse(first["next"]).query)["page"][0])
    second, step = call(runtime, connection, "dockets_list", {"limit": 2, "page": page})
    trace.append(step)
    disjoint_ids(first, second, ["results"])
    while second["next"]:
        page = int(parse_qs(urlparse(second["next"]).query)["page"][0])
        second, step = call(runtime, connection, "dockets_list", {"limit": 2, "page": page})
        trace.append(step)

    first, step = call(runtime, connection, "spreadsheets_list", {"pageSize": 2})
    trace.append(step)
    second, step = call(runtime, connection, "spreadsheets_list", {
        "pageSize": 100, "pageToken": first["nextPageToken"],
    })
    trace.append(step)
    disjoint_ids(first, second, ["files"])

    first, step = call(runtime, connection, "productions_list", {"start": 1, "length": 2})
    trace.append(step)
    second, step = call(runtime, connection, "productions_list", {
        "start": first["NextStartIndex"], "length": 100,
    })
    trace.append(step)
    disjoint_ids(first, second, ["Objects"])

    first, step = call(runtime, connection, "documents_list", {"limit": 2, "offset": 0})
    trace.append(step)
    next_offset = first["data"]["next_offset"]
    second, step = call(runtime, connection, "documents_list", {"limit": 100, "offset": next_offset})
    trace.append(step)
    disjoint_ids(first, second, ["data", "results"])

    diagnostic = paging_diagnostic(trace)
    assert diagnostic["paging_complete"], diagnostic
    incomplete = paging_diagnostic(trace[:-1])
    assert not incomplete["paging_complete"] and incomplete["missing_page_followups"]
    ok, text = runtime.call(connection, "matters_list", {"page_token": "not-a-cursor"})
    assert not ok and "400" in text

    schemas = {item["name"]: item["inputSchema"]["properties"] for item in runtime.mcp_tools()}
    assert "page_token" in schemas["matters_list"]
    assert "page" in schemas["dockets_list"]
    assert {"pageToken", "pageSize"} <= set(schemas["spreadsheets_list"])
    assert {"start", "length"} <= set(schemas["productions_list"])
    assert "offset" in schemas["documents_list"]
    connection.close()
    print("pagination: Clio, CourtListener, Google, Relativity, iManage cursors + discipline clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
