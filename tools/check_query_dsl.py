#!/usr/bin/env python3
"""M2.4 acceptance checks for bounded vendor query languages."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "world" / "local"))

from v2runtime import V2Runtime  # noqa: E402


def invoke(runtime, connection, name, arguments):
    ok, text = runtime.call(connection, name, arguments)
    return ok, json.loads(text)


def main() -> int:
    runtime = V2Runtime(str(ROOT / "mcp" / "v3" / "contracts"))
    connection = sqlite3.connect(":memory:")
    runtime.create_and_seed(connection)

    connection.execute(
        """INSERT INTO ws_messages
           (thread_id,from_addr,to_addr,subject,body,sent_at,label) VALUES (?,?,?,?,?,?,?)""",
        (999, "rennick@example.com", "team@example.com", "Settlement Update",
         "Attached is the signed term sheet.", "2026-08-10", "INBOX"),
    )
    ok, gmail = invoke(runtime, connection, "gmail_messages_list", {
        "q": 'from:rennick subject:"Settlement Update" after:2026-08-01 has:attachment',
        "maxResults": 10,
    })
    assert ok and gmail["resultSizeEstimate"] == 1 and len(gmail["messages"]) == 1
    ok, error = invoke(runtime, connection, "gmail_messages_list", {"q": "weird:("})
    assert not ok and error["error"]["code"] == 400 and error["error"]["status"] == "INVALID_ARGUMENT"

    connection.execute(
        """INSERT INTO ed_documents
           (workspace_id,control_number,custodian,doc_date,subject,extracted_text,responsive,privileged,reviewed_by)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (1, "DSL-0001", "Rennick", "2026-08-01", "Settlement", "term sheet", "yes", "no", "Aiko"),
    )
    ok, relativity = invoke(runtime, connection, "documents_query", {
        "condition": "'Custodian' == 'Rennick' AND 'Responsive' == 'yes' AND 'Document Date' >= '2026-07-01'",
        "start": 1, "length": 20,
    })
    field_values = {
        item["Field"]["Name"]: item["Value"]
        for item in relativity["Objects"][0]["FieldValues"]
    }
    assert ok and relativity["TotalCount"] == 1 and field_values["control_number"] == "DSL-0001"
    ok, error = invoke(runtime, connection, "documents_query", {"condition": "'Secret SQL' == 'x'"})
    assert not ok and error["ErrorCode"] == 400

    ok, dockets = invoke(runtime, connection, "dockets_list", {
        "date_filed__gte": "2026-01-01", "date_filed__lte": "2026-12-31", "limit": 100,
    })
    assert ok and dockets["results"] and all("2026-01-01" <= row["date_filed"] <= "2026-12-31" for row in dockets["results"])

    ok, sparse = invoke(runtime, connection, "matters_list", {"limit": 2, "fields": "display_name,status"})
    assert ok and sparse["data"] and set(sparse["data"][0]) <= {"id", "display_name", "status"}
    ok, error = invoke(runtime, connection, "matters_list", {"fields": "display_name,password_hash"})
    assert not ok and error["error"]["type"] == "invalid_request"
    connection.close()
    print("query DSL: Gmail, Relativity, Django filters, and Clio sparse fields clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
