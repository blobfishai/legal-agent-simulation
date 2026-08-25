#!/usr/bin/env python3
"""Compare the offline mock with the pinned live MCP filesystem package."""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE.parent
RUNTIME = SOURCE_ROOT / "runtime"
if not RUNTIME.exists():
    # Hugging Face release layout: tests/ and world/ are siblings.
    RUNTIME = HERE.parent / "world"
sys.path.insert(0, str(RUNTIME.parent))
sys.path.insert(0, str(RUNTIME))

from contracts import MCP_PIN, TOOLS_BY_NAME  # noqa: E402
from world import CounselWorld  # noqa: E402


class StdioMCP:
    def __init__(self, allowed_root: Path) -> None:
        package = f"{MCP_PIN['package']}@{MCP_PIN['version']}"
        self.process = subprocess.Popen(
            ["npx", "-y", package, str(allowed_root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.next_id = 0

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.next_id += 1
        request: dict[str, Any] = {
            "jsonrpc": "2.0", "id": self.next_id, "method": method,
        }
        if params is not None:
            request["params"] = params
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 60
        assert self.process.stdout is not None
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.process.stdout], [], [], 1)
            if not ready:
                if self.process.poll() is not None:
                    stderr = self.process.stderr.read() if self.process.stderr else ""
                    raise RuntimeError(f"upstream MCP exited {self.process.returncode}: {stderr}")
                continue
            line = self.process.stdout.readline()
            if not line:
                continue
            response = json.loads(line)
            if response.get("id") == self.next_id:
                if response.get("error"):
                    raise RuntimeError(json.dumps(response["error"]))
                return response["result"]
        raise TimeoutError(f"no response to {method}")

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        request: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = params
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()


def normalized_tool(tool: dict[str, Any]) -> dict[str, Any]:
    # The SDK may add an explicit JSON Schema dialect marker. It does not alter
    # accepted input/output JSON, so compare the executable schema after removing it.
    value = json.loads(json.dumps(tool))
    for key in ("inputSchema", "outputSchema"):
        if isinstance(value.get(key), dict):
            value[key].pop("$schema", None)
    return value


def text_result(result: dict[str, Any]) -> str:
    assert result.get("content") and result["content"][0].get("type") == "text"
    text = result["content"][0]["text"]
    assert result.get("structuredContent") == {"content": text}
    return text


def normalize_info(value: str) -> dict[str, str]:
    parsed = dict(line.split(": ", 1) for line in value.splitlines())
    return {
        "size": parsed["size"],
        "isDirectory": parsed["isDirectory"],
        "isFile": parsed["isFile"],
        "permissions_present": str(bool(parsed.get("permissions"))).lower(),
        "created_present": str(bool(parsed.get("created"))).lower(),
        "modified_present": str(bool(parsed.get("modified"))).lower(),
        "accessed_present": str(bool(parsed.get("accessed"))).lower(),
    }


def run(report_path: Path | None = None) -> dict[str, Any]:
    if shutil.which("npx") is None:
        raise RuntimeError("npx is required to launch the pinned upstream MCP package")
    with tempfile.TemporaryDirectory(prefix="counselbench-mcp-conformance-") as temporary:
        root = Path(temporary)
        actual_root = root / "actual"
        mock_documents = root / "mock-documents"
        mock_output = root / "mock-output"
        mock_state = root / "mock-state"
        actual_root.mkdir()
        mock_documents.mkdir()
        mock_output.mkdir()
        fixture = "Matter CB-CONFORMANCE\nLine two with $1,250.00.\n"
        (actual_root / "fixture.txt").write_text(fixture, encoding="utf-8")
        (mock_documents / "fixture.txt").write_text(fixture, encoding="utf-8")
        spec_path = root / "spec.json"
        spec_path.write_text(
            json.dumps(
                {
                    "task_id": "conformance",
                    "fixed_file_timestamp": "2026-08-25T12:00:00.000Z",
                    "verify_token_sha256": "unused",
                    "minimum_tool_calls": 0,
                    "required_document_paths": [],
                    "metadata_check_paths": [],
                    "deliverables": [],
                    "expected_findings": {},
                    "memo_sections": [],
                    "memo_anchors": [],
                    "forbidden_claims": [],
                }
            ),
            encoding="utf-8",
        )
        mock = CounselWorld(mock_documents, mock_output, mock_state, spec_path)
        upstream = StdioMCP(actual_root)
        try:
            initialized = upstream.send(
                "initialize",
                {
                    "protocolVersion": MCP_PIN["protocol_version"],
                    "capabilities": {},
                    "clientInfo": {"name": "counselbench-conformance", "version": "1.0.0"},
                },
            )
            upstream.notify("notifications/initialized")
            actual_tools = {
                tool["name"]: tool for tool in upstream.send("tools/list")["tools"]
            }
            contract_checks: dict[str, bool] = {}
            contract_diffs: dict[str, Any] = {}
            for name, expected in TOOLS_BY_NAME.items():
                actual = actual_tools.get(name)
                matches = actual is not None and normalized_tool(actual) == normalized_tool(expected)
                contract_checks[name] = matches
                if not matches:
                    contract_diffs[name] = {
                        "expected": normalized_tool(expected),
                        "actual": normalized_tool(actual or {}),
                    }

            behavior_checks: dict[str, bool] = {}
            actual_read = upstream.send(
                "tools/call", {"name": "read_text_file", "arguments": {"path": str(actual_root / "fixture.txt")}}
            )
            mock_read = mock.call_tool("read_text_file", {"path": "/workspace/documents/fixture.txt"})
            behavior_checks["read_text_file"] = text_result(actual_read) == text_result(mock_read) == fixture

            actual_write_path = actual_root / "result.txt"
            actual_write = upstream.send(
                "tools/call", {"name": "write_file", "arguments": {"path": str(actual_write_path), "content": "grounded\n"}}
            )
            mock_write = mock.call_tool(
                "write_file", {"path": "/workspace/output/result.txt", "content": "grounded\n"}
            )
            behavior_checks["write_file"] = (
                text_result(actual_write) == f"Successfully wrote to {actual_write_path}"
                and text_result(mock_write) == "Successfully wrote to /workspace/output/result.txt"
                and actual_write_path.read_text(encoding="utf-8") == (mock_output / "result.txt").read_text(encoding="utf-8")
            )

            actual_tree = upstream.send(
                "tools/call", {"name": "directory_tree", "arguments": {"path": str(actual_root), "excludePatterns": []}}
            )
            mock_tree = mock.call_tool(
                "directory_tree", {"path": "/workspace/documents", "excludePatterns": []}
            )
            actual_tree_value = json.loads(text_result(actual_tree))
            # result.txt belongs to the upstream write root; compare the common fixture entry.
            behavior_checks["directory_tree"] = (
                {entry["name"]: entry["type"] for entry in actual_tree_value}.get("fixture.txt") == "file"
                and json.loads(text_result(mock_tree)) == [{"name": "fixture.txt", "type": "file"}]
            )

            actual_search = upstream.send(
                "tools/call", {"name": "search_files", "arguments": {"path": str(actual_root), "pattern": "**/*.txt", "excludePatterns": []}}
            )
            mock_search = mock.call_tool(
                "search_files", {"path": "/workspace/documents", "pattern": "**/*.txt", "excludePatterns": []}
            )
            actual_names = sorted(Path(line).name for line in text_result(actual_search).splitlines())
            mock_names = sorted(Path(line).name for line in text_result(mock_search).splitlines())
            behavior_checks["search_files"] = "fixture.txt" in actual_names and mock_names == ["fixture.txt"]

            actual_info = upstream.send(
                "tools/call", {"name": "get_file_info", "arguments": {"path": str(actual_root / "fixture.txt")}}
            )
            mock_info = mock.call_tool("get_file_info", {"path": "/workspace/documents/fixture.txt"})
            behavior_checks["get_file_info"] = normalize_info(text_result(actual_info)) == normalize_info(text_result(mock_info))

            actual_allowed = text_result(
                upstream.send("tools/call", {"name": "list_allowed_directories", "arguments": {}})
            )
            mock_allowed = text_result(mock.call_tool("list_allowed_directories", {}))
            behavior_checks["list_allowed_directories"] = (
                actual_allowed.startswith("Allowed directories:\n")
                and mock_allowed == "Allowed directories:\n/workspace/documents\n/workspace/output"
            )
        finally:
            upstream.close()

    report = {
        "schema_version": "1.0",
        "upstream": MCP_PIN,
        "upstream_initialize": initialized,
        "contract_checks": contract_checks,
        "behavior_checks": behavior_checks,
        "contract_diffs": contract_diffs,
        "passed": all(contract_checks.values()) and all(behavior_checks.values()),
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args().report)
    raise SystemExit(0 if result["passed"] else 1)
