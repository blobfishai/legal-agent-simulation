#!/usr/bin/env python3
"""Stateless Streamable HTTP MCP adapter for a CounselBench trial."""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from contracts import MCP_PIN
from world import CounselWorld


WORLD = CounselWorld(
    os.environ.get("COUNSELBENCH_DOCUMENTS", "/workspace/documents"),
    os.environ.get("COUNSELBENCH_OUTPUT", "/workspace/output"),
    os.environ.get("COUNSELBENCH_STATE", "/workspace/state"),
    os.environ.get("COUNSELBENCH_SPEC", "/opt/counselbench/spec.json"),
)


def rpc_response(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    if request_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return None
    if request.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": MCP_PIN["protocol_version"],
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {
                    "name": MCP_PIN["runtime_server_name"],
                    "version": MCP_PIN["runtime_server_version"],
                },
                "instructions": (
                    "Review the allowlisted seeded matter files and write final deliverables "
                    "only under /workspace/output."
                ),
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": WORLD.list_tools()},
        }
    if method == "tools/call":
        params = request.get("params") or {}
        if not isinstance(params, dict):
            params = {}
        result = WORLD.call_tool(params.get("name", ""), params.get("arguments"))
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "CounselBenchMCP/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _json(self, status: int, value: Any) -> None:
        payload = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("MCP-Protocol-Version", MCP_PIN["protocol_version"])
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok", "task_id": WORLD.spec["task_id"]})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        if self.path == "/verify":
            try:
                report = WORLD.verify(self.headers.get("X-Verify-Token"))
            except PermissionError:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._json(HTTPStatus.OK, report)
            return
        if self.path != "/mcp":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            request = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            )
            return
        if isinstance(request, list):
            responses = [response for item in request if (response := rpc_response(item)) is not None]
            self._json(HTTPStatus.OK, responses)
            return
        response = rpc_response(request)
        if response is None:
            self.send_response(HTTPStatus.ACCEPTED)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._json(HTTPStatus.OK, response)


if __name__ == "__main__":
    host = os.environ.get("COUNSELBENCH_HOST", "0.0.0.0")
    port = int(os.environ.get("COUNSELBENCH_PORT", "8972"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()
