#!/usr/bin/env python3
"""Audit CounselBench's provider allowlist against its pinned operation metadata.

Live provider calls would require credentials and mutate external systems. This
release audit instead enforces that every sandbox tool is a resource-level
operation with a published provider method/path/source, strict input schema,
and accurate read/write annotations. Runtime behavior is covered by the oracle
and adversarial qualification suite over the closed synthetic state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RUNTIME = HERE.parent / "runtime"
if not RUNTIME.exists():
    RUNTIME = HERE.parent / "world"
sys.path.insert(0, str(RUNTIME))

from contracts import MCP_PIN, MUTATION_TOOLS, TOOLS_BY_NAME  # noqa: E402


REQUIRED_OPERATIONS = {
    "clio_manage.matters.list": ("GET", "/api/v4/matters.json"),
    "clio_manage.matters.get": ("GET", "/api/v4/matters/{id}.json"),
    "clio_manage.matters.update": ("PATCH", "/api/v4/matters/{id}.json"),
    "clio_manage.notes.list": ("GET", "/api/v4/notes.json"),
    "clio_manage.notes.get": ("GET", "/api/v4/notes/{id}.json"),
    "clio_manage.notes.create": ("POST", "/api/v4/notes.json"),
    "gmail.messages.list": ("GET", "/gmail/v1/users/{userId}/messages"),
    "gmail.messages.get": ("GET", "/gmail/v1/users/{userId}/messages/{id}"),
    "gmail.messages.send": ("POST", "/gmail/v1/users/{userId}/messages/send"),
    "google_drive.files.list": ("GET", "/drive/v3/files"),
    "google_drive.files.get": ("GET", "/drive/v3/files/{fileId}"),
    "google_drive.comments.list": ("GET", "/drive/v3/files/{fileId}/comments"),
    "google_drive.comments.get": ("GET", "/drive/v3/files/{fileId}/comments/{commentId}"),
    "google_drive.comments.create": ("POST", "/drive/v3/files/{fileId}/comments"),
    "slack.search_messages": ("GET", "/api/search.messages"),
    "slack.conversations_history": ("GET", "/api/conversations.history"),
    "slack.conversations_replies": ("GET", "/api/conversations.replies"),
    "slack.chat_postMessage": ("POST", "/api/chat.postMessage"),
}


def strict_schema(value: Any) -> bool:
    if isinstance(value, list):
        return all(strict_schema(item) for item in value)
    if not isinstance(value, dict):
        return True
    if value.get("type") == "object":
        properties = value.get("properties")
        required = value.get("required")
        if (
            value.get("additionalProperties") is not False
            or not isinstance(properties, dict)
            or not isinstance(required, list)
            or not set(required) <= set(properties)
        ):
            return False
    return all(strict_schema(item) for item in value.values())


def run(report_path: Path | None = None) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "four_providers": set(MCP_PIN["providers"])
        == {"clio_manage", "gmail", "google_drive", "slack"},
        "required_operations_present": REQUIRED_OPERATIONS.keys() <= TOOLS_BY_NAME.keys(),
        "operation_allowlist_exact": set(REQUIRED_OPERATIONS) == set(TOOLS_BY_NAME),
        "no_business_decision_pseudotools": not any(
            token in name.casefold()
            for name in TOOLS_BY_NAME
            for token in ("approve_", "resolve_", "decide_", "complete_task", "submit_answer")
        ),
        "strict_json_schemas": all(
            strict_schema(tool["inputSchema"])
            for tool in TOOLS_BY_NAME.values()
        ),
        "documented_upstream_metadata": all(
            tool.get("_meta", {}).get("counselbench", {}).get("contractMode")
            == "documented-operation"
            and tool["_meta"]["counselbench"]["upstream"].get("method")
            in {"GET", "POST", "PATCH"}
            and str(tool["_meta"]["counselbench"]["upstream"].get("path", "")).startswith("/")
            and str(tool["_meta"]["counselbench"]["upstream"].get("source", "")).startswith("https://")
            for tool in TOOLS_BY_NAME.values()
        ),
        "mutation_annotations_exact": all(
            (name in MUTATION_TOOLS)
            == (not bool(tool["annotations"]["readOnlyHint"]))
            for name, tool in TOOLS_BY_NAME.items()
        ),
    }
    operation_checks: dict[str, bool] = {}
    for name, (method, path) in REQUIRED_OPERATIONS.items():
        tool = TOOLS_BY_NAME.get(name, {})
        upstream = tool.get("_meta", {}).get("counselbench", {}).get("upstream", {})
        operation_checks[name] = upstream.get("method") == method and upstream.get("path") == path
    report = {
        "schema_version": "counselbench.provider-contract-audit.v1",
        "benchmark": "CounselBench-100",
        "benchmark_version": "3.2.3",
        "providers": MCP_PIN,
        "tool_count": len(TOOLS_BY_NAME),
        "mutation_tools": sorted(MUTATION_TOOLS),
        "checks": checks,
        "operation_checks": operation_checks,
        "passed": all(checks.values()) and all(operation_checks.values()),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(encoded, encoding="utf-8")
        release = report_path.parent.parent
        hf_reports = release / "huggingface" / "reports"
        if report_path.parent.name == "reports" and hf_reports.parent.is_dir():
            hf_reports.mkdir(parents=True, exist_ok=True)
            (hf_reports / report_path.name).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args().report)
    raise SystemExit(0 if result["passed"] else 1)
