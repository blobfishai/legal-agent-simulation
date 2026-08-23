#!/usr/bin/env python3
"""Executable acceptance checks for the three M3 product systems."""
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


def parsed(result: tuple[bool, str]) -> tuple[bool, dict]:
    ok, text = result
    try:
        return ok, json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - clearer assertion output
        raise AssertionError(f"response was not JSON: {text}") from exc


def fresh() -> tuple[V2Runtime, sqlite3.Connection]:
    runtime = V2Runtime(str(ROOT / "mcp" / "v3" / "contracts"))
    connection = sqlite3.connect(":memory:")
    runtime.create_and_seed(connection)
    return runtime, connection


def check_efiling(runtime: V2Runtime, connection: sqlite3.Connection) -> None:
    ok, case = parsed(runtime.call(connection, "efiling_cases_get", {"case_id": 1}))
    assert ok and case["case"]["status"] == "open"
    ok, error = parsed(runtime.call(connection, "efiling_filings_create", {
        "case_id": 1, "event_type": "answer_to_complaint", "document_name": "answer.docx",
        "document_mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }))
    assert not ok and error["error"] == "DOCUMENT_FORMAT_REJECTED"
    before_read_side = connection.execute("SELECT COUNT(*) FROM cl_docket_entries").fetchone()[0]
    ok, filing = parsed(runtime.call(connection, "efiling_filings_create", {
        "case_id": 1, "event_type": "answer_to_complaint", "document_name": "answer.pdf",
        "document_mime_type": "application/pdf", "document_sha256": "a" * 64,
        "description": "Answer to Complaint",
    }))
    assert ok and filing["status"] == "filed"
    assert connection.execute("SELECT COUNT(*) FROM ef_filings").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM ef_docket_entries").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM ef_nef_notices").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM cl_docket_entries").fetchone()[0] == before_read_side + 1
    ok, nef = parsed(runtime.call(connection, "efiling_nef_notices_list", {"filing_id": filing["filing_id"]}))
    assert ok and nef["count"] == 1 and nef["results"][0]["status"] == "sent"


def check_deadlines(runtime: V2Runtime, connection: sqlite3.Connection) -> None:
    def due(trigger: str, method: str, on: str) -> tuple[str, int]:
        ok, result = parsed(runtime.call(connection, "deadlines_compute", {
            "trigger_event": trigger, "jurisdiction": "US-FEDERAL-CIVIL",
            "service_method": method, "trigger_date": on,
        }))
        assert ok and result["deadlines"][0]["rule_citation"].startswith("Fed. R. Civ. P.")
        return result["deadlines"][0]["date"], result["service_extension_days"]

    assert due("complaint_and_summons_served", "personal", "2026-08-14") == ("2026-09-04", 0)
    assert due("interrogatories_served", "electronic", "2026-08-12") == ("2026-09-11", 0)
    assert due("interrogatories_served", "mail", "2026-08-12") == ("2026-09-14", 3)
    assert due("requests_for_production_served", "electronic", "2026-08-14") == ("2026-09-14", 0)
    ok, error = parsed(runtime.call(connection, "deadlines_compute", {
        "trigger_event": "complaint_and_summons_served", "jurisdiction": "US-CALIFORNIA",
        "service_method": "personal", "trigger_date": "2026-08-14",
    }))
    assert not ok and error["error"] == "UNSUPPORTED_JURISDICTION"


def check_esign(runtime: V2Runtime, connection: sqlite3.Connection) -> None:
    recipients = json.dumps([
        {"name": "Client Signer", "email": "client@example.com", "recipientId": "1", "routingOrder": "1"},
        {"name": "Firm Signer", "email": "firm@example.com", "recipientId": "2", "routingOrder": "2"},
    ])
    ok, created = parsed(runtime.call(connection, "esign_envelopes_create", {
        "accountId": "sim-account-001", "emailSubject": "Execute settlement agreement",
        "documentName": "settlement.pdf", "recipients": recipients, "status": "created",
    }))
    assert ok and created["status"] == "created"
    envelope_id = created["envelopeId"]
    ok, sent = parsed(runtime.call(connection, "esign_envelopes_send", {
        "accountId": "sim-account-001", "envelopeId": envelope_id, "status": "sent",
    }))
    assert ok and sent["status"] == "sent"
    ok, routing_error = parsed(runtime.call(connection, "esign_simulate_recipient_complete", {
        "accountId": "sim-account-001", "envelopeId": envelope_id, "recipientId": "2",
    }))
    assert not ok and routing_error["errorCode"] == "RECIPIENT_ROUTING_ORDER_INVALID"
    statuses = []
    for _ in range(4):
        ok, envelope = parsed(runtime.call(connection, "esign_envelopes_get", {
            "accountId": "sim-account-001", "envelopeId": envelope_id,
        }))
        assert ok
        statuses.append(envelope["status"])
    assert statuses == ["delivered", "sent", "delivered", "completed"]
    ok, listed = parsed(runtime.call(connection, "esign_recipients_list", {
        "accountId": "sim-account-001", "envelopeId": envelope_id,
    }))
    assert ok and [item["status"] for item in listed["signers"]] == ["completed", "completed"]


def main() -> int:
    runtime, connection = fresh()
    public_expected = {
        "efiling_cases_get", "efiling_filings_create", "efiling_docket_entries_list",
        "efiling_nef_notices_list", "deadlines_compute", "esign_envelopes_create",
        "esign_envelopes_get", "esign_envelopes_send", "esign_recipients_list",
    }
    assert public_expected <= set(runtime.tools)
    assert "esign_simulate_recipient_complete" in runtime.tools
    schemas = {item["name"]: item for item in runtime.mcp_tools()}
    assert public_expected <= set(schemas)
    assert "esign_simulate_recipient_complete" not in schemas
    assert schemas["deadlines_compute"]["inputSchema"]["required"] == [
        "trigger_event", "jurisdiction", "service_method", "trigger_date"
    ]
    check_efiling(runtime, connection)
    check_deadlines(runtime, connection)
    check_esign(runtime, connection)
    connection.close()
    print("M3 contracts: 9/9 agent tools + 1 internal actuator; filing/NEF, FRCP dates, and ordered signing clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
