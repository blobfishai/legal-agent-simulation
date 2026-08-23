#!/usr/bin/env python3
"""Execute documentation and published-standard behavior fixtures."""

from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE = HERE / "fixtures" / "vendor-behavior.json"
REPORT = ROOT / "data" / "conformance-behavior.json"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "world" / "local"))

import live  # noqa: E402
from oracle import OracleSession  # noqa: E402
from product_workflows import LEDES_1998B_FIELDS  # noqa: E402


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def digest(value: object) -> str:
    raw = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def relativity_object(value: Any) -> None:
    assert isinstance(value, dict)
    assert isinstance(value.get("ArtifactID"), int)
    fields = value.get("FieldValues")
    assert isinstance(fields, list)
    for item in fields:
        assert set(item) == {"Field", "Value"}
        assert isinstance(item["Field"].get("Name"), str)


def validate(kind: str, value: Any) -> None:
    if kind == "relativity_query":
        assert set(value) == {"Objects", "TotalCount", "CurrentStartIndex", "ResultCount", "NextStartIndex"}
        assert value["ResultCount"] == len(value["Objects"])
        assert value["TotalCount"] >= value["ResultCount"]
        for item in value["Objects"]:
            relativity_object(item)
    elif kind == "relativity_object":
        relativity_object(value)
    elif kind == "relativity_write":
        assert value.get("Success") is True and value.get("Message") == ""
        relativity_object(value.get("Object"))
    elif kind == "relativity_job":
        relativity_object(value)
        assert value.get("JobState") in {"staged", "running", "completed"}
    elif kind == "cmecf_case":
        assert set(value) == {"case"}
        assert {"id", "docket_number", "court_id", "status"} <= set(value["case"])
    elif kind == "cmecf_filing":
        assert value.get("status") == "filed"
        assert {"filing_id", "docket_entry_id", "nef_notice_id", "entry_number", "filed_at"} <= set(value)
    elif kind in {"cmecf_docket", "cmecf_nef"}:
        assert {"count", "total", "results", "limit", "offset", "has_more"} <= set(value)
        assert isinstance(value["results"], list)
    elif kind == "frcp_deadline":
        assert value.get("jurisdiction") == "US-FEDERAL-CIVIL"
        assert value.get("trigger_date") == "2026-08-12"
        first = value["deadlines"][0]
        assert first["date"] == "2026-09-02"
        assert "Fed. R. Civ. P." in first["rule_citation"]
        assert first["source_url"].startswith("https://www.uscourts.gov/")
    elif kind == "utbms_codes":
        rows = value.get("results")
        assert isinstance(rows, list) and rows
        codes = {row["code"]: row["kind"] for row in rows}
        assert codes.get("L110") == "task"
        assert codes.get("A101") == "activity"
        assert codes.get("E101") == "expense"
        assert len(codes) == len(rows)
    elif kind == "ledes_1998b":
        assert isinstance(value, str) and value.isascii()
        lines = value.splitlines()
        assert lines[0] == "LEDES1998B[]"
        header = lines[1].split("|")
        assert header[-1] == "" and tuple(header[:-1]) == LEDES_1998B_FIELDS
        assert len(lines) >= 3
        for line in lines[2:]:
            fields = line.split("|")
            assert fields[-1] == "" and len(fields[:-1]) == 24
            assert re.fullmatch(r"\d{8}", fields[0])
            assert re.fullmatch(r"-?\d+\.\d{2}", fields[4])
    else:  # pragma: no cover - fixture schema guard
        raise AssertionError(f"unknown validator {kind}")


def call_value(session: OracleSession, name: str, args: dict[str, object]) -> Any:
    ok, text = session.call(name, args)
    assert ok, text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def build(base: str) -> tuple[dict[str, Any], list[str]]:
    fixture = json.loads(FIXTURE.read_text())
    contracts = live.load_contract_documents()
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for name, kind in fixture["tools"].items():
        session = OracleSession(base, profile="contract")
        arguments = live.sample_arguments(contracts[name])
        try:
            value = call_value(session, name, arguments)
            validate(kind, value)
            results.append({"name": name, "passed": True, "validator": kind,
                            "arguments": arguments, "response_digest": digest(value)})
        except Exception as exc:  # noqa: BLE001 - report every fixture failure
            failures.append(f"{name}: {exc}")
            results.append({"name": name, "passed": False, "validator": kind,
                            "arguments": arguments, "error": str(exc)[:500]})
        finally:
            session.close()
    return {
        "schema_version": 1,
        "fixture_source": str(FIXTURE.relative_to(ROOT)),
        "summary": {"passed": sum(item["passed"] for item in results), "total": len(results)},
        "failures": failures,
        "tools": results,
    }, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--base", default="http://127.0.0.1:8974")
    args = parser.parse_args()
    report, failures = build(args.base)
    rendered = canonical(report)
    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(rendered)
    elif not REPORT.is_file() or REPORT.read_text() != rendered:
        failures.append(f"stale {REPORT.relative_to(ROOT)}; run --write")
    print(f"behavior fixtures {report['summary']['passed']}/{report['summary']['total']}")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
