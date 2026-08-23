#!/usr/bin/env python3
"""Harbor trial shim — the task-facing surface of the world container.

One shim instance serves ONE Harbor trial for ONE task (TASK_ID env). It:

  * waits for the world server (server.py on :8971), creates the trial's
    session (per-task seeded baseline), and pins every forwarded call to it;
  * proxies MCP JSON-RPC on :8972/mcp, recording each tools/call into the
    trace exactly as sim/run-simulation.mjs does
    ({tool, requested_tool, arguments, observation<=4000, ok});
  * POST /verify — runs the task's shipped VCode verifier against the
    session state + recorded trace, returns the verdict;
  * POST /solve (X-Solve-Token gated) — executes the task's oracle
    reference walk through the same session/trace, so the Harbor Oracle
    agent can prove solvability without the answers ever entering the
    agent container.

The agent container never sees world.json (tasks, walks, verifiers); it only
reaches this HTTP surface over the compose network.
"""
from __future__ import annotations

import json
import hashlib
import hmac
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle  # noqa: E402  (derive_args, vcode_walk, pinned_update, world_tool_targets)

WORLD_BASE = os.environ.get("WORLD_BASE", "http://127.0.0.1:8971")
PORT = int(os.environ.get("SHIM_PORT", "8972"))
TASK_ID = os.environ["TASK_ID"]
ORACLE_PROOF_SHA256 = os.environ.get("ORACLE_PROOF_SHA256", "")
WORLD_DOC_PATH = os.environ.get("WORLD_DOC", os.path.join(HERE, "world.json"))
TRACE_LOG = os.environ.get("TRACE_LOG", os.path.join(HERE, "state", "trace.jsonl"))


def http(method: str, path: str, body=None, session: str | None = None,
         token: str | None = None, timeout=120):
    req = urllib.request.Request(WORLD_BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if session:
        req.add_header("Mcp-Session-Id", session)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=timeout) as res:
        return json.loads(res.read().decode() or "{}")


def main() -> None:
    # ---- wait for the world server, then open the trial session ----------
    for _ in range(240):
        try:
            if http("GET", "/health", timeout=5).get("ok"):
                break
        except Exception:
            time.sleep(0.5)
    else:
        sys.exit("[shim] world server never became healthy")
    context = http("GET", f"/internal/task-context/{TASK_ID}")
    world = context["world"]
    task = context["task"]
    verifier = context["verifier"]
    phase_defs = ((task.get("multi_step") or {}).get("phases") or [])
    phase_by_name = {phase["name"]: phase for phase in phase_defs}
    phase_order = [phase["name"] for phase in phase_defs]
    completed_phases: list[str] = []

    opened = http("POST", "/sessions", {"task_id": TASK_ID})
    session_id = opened["session_id"]
    access_token = opened["access_token"]
    print(f"[shim] task={TASK_ID} session={session_id}", file=sys.stderr)

    trace: list[dict] = []
    lock = threading.Lock()
    os.makedirs(os.path.dirname(TRACE_LOG), exist_ok=True)

    def record(entry: dict) -> None:
        with lock:
            trace.append(entry)
            with open(TRACE_LOG, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def forward(msg: dict) -> dict:
        try:
            res = http("POST", "/mcp", msg, session=session_id, token=access_token)
        except urllib.error.HTTPError as exc:
            signature = exc.headers.get("X-Simulator-Failure")
            if signature not in {"rate_limited", "stale_reference"}:
                raise
            text = exc.read().decode(errors="replace")
            res = {"jsonrpc": "2.0", "id": msg.get("id"), "result": {
                "content": [{"type": "text", "text": text}], "isError": True,
            }}
        if msg.get("method") == "tools/call":
            params = msg.get("params") or {}
            r = res.get("result") or {}
            rpc_error = res.get("error")
            text = (json.dumps(rpc_error, sort_keys=True) if rpc_error is not None else
                    "".join(c.get("text", "") for c in r.get("content", [])))
            record({
                "tool": params.get("name"), "requested_tool": params.get("name"),
                "arguments": params.get("arguments") or {},
                "observation": text[:4000],
                "ok": rpc_error is None and not r.get("isError"),
            })
        return res

    def call_tool(name: str, args: dict, retries: int = 2) -> tuple[bool, str]:
        """Reference-walk call with the oracle's transient-friction retry."""
        text = ""
        for attempt in range(retries + 1):
            res = forward({"jsonrpc": "2.0", "id": f"solve-{name}-{attempt}",
                           "method": "tools/call",
                           "params": {"name": name, "arguments": args}})
            r = res.get("result") or {}
            rpc_error = res.get("error")
            text = (json.dumps(rpc_error, sort_keys=True) if rpc_error is not None else
                    "".join(c.get("text", "") for c in r.get("content", [])))
            ok = rpc_error is None and not r.get("isError")
            transient = any(marker in text for marker in (
                "rate_limited", "stale_reference", "rate_limit",
                "RESOURCE_EXHAUSTED", "HOURLY_APIINVOCATION_LIMIT_EXCEEDED",
                "retry after", "stale_object", "FAILED_PRECONDITION",
                "ENVELOPE_LOCKED", "referenced resource changed",
            ))
            if ok or not transient or attempt == retries:
                return ok, text
        return False, text

    def solve(phase: str | None = None) -> dict:
        """The oracle reference walk (oracle.run_task, minus verify/close)."""
        state = {"read_bodies": []}
        tables = {t["name"] for t in world["tables"]}
        pin = oracle.pinned_update(verifier or {}, tables)
        if phase is not None:
            phase_def = phase_by_name.get(phase)
            if phase_def is None:
                raise ValueError(f"unknown phase {phase!r}")
            walk = phase_def.get("walk") or []
            ref_args = phase_def.get("reference_args")
        else:
            walk = oracle.vcode_walk(verifier or {}) or task.get("walk") or []
            ref_args = task.get("reference_args")
        steps = []
        for step_i, tool_name in enumerate(walk):
            try:
                if ref_args and step_i < len(ref_args):
                    args = ref_args[step_i]
                else:
                    args = oracle.derive_args(world, task, tool_name, state)
                if pin and tool_name.startswith("update_") and pin["table"] in (
                        oracle.world_tool_targets(world, tool_name)):
                    args["id"] = pin["id"]
                    if "new_status" in args and pin["field"] == "status":
                        args["new_status"] = pin["value"]
                    elif pin["field"] in args:
                        args[pin["field"]] = pin["value"]
            except Exception as e:  # noqa: BLE001 — keep walking
                steps.append({"step": step_i, "tool": tool_name,
                              "ok": False, "error": f"derive_args: {e!r}"})
                continue
            ok, text = call_tool(tool_name, args)
            if ok and tool_name in ("documents_download", "drive_files_get"):
                state["read_bodies"].append(text)
            steps.append({"step": step_i, "tool": tool_name, "ok": ok})
        return {"task_id": TASK_ID, "phase": phase, "steps": steps,
                "all_ok": all(s["ok"] for s in steps)}

    def verify(phase: str | None = None) -> dict:
        if phase is not None:
            if phase not in phase_by_name:
                raise ValueError(f"unknown phase {phase!r}")
            expected = next((name for name in phase_order if name not in completed_phases), None)
            if phase != expected:
                raise ValueError(f"out-of-order phase {phase!r}; expected {expected!r}")
        with lock:
            request_body = {"trace": list(trace)}
            if phase is not None:
                request_body["phase"] = phase
        verdict = http("POST", f"/verify/{TASK_ID}", request_body,
                       session=session_id, token=access_token)
        if phase is not None and verdict.get("passed"):
            with lock:
                if phase not in completed_phases:
                    completed_phases.append(phase)
        return verdict

    def step_state() -> dict:
        with lock:
            current = next((name for name in phase_order if name not in completed_phases), None)
            definition = phase_by_name.get(current) or {}
            return {
                "multi_step": bool(phase_order),
                "current": current,
                "index": (phase_order.index(current) + 1) if current else len(phase_order),
                "total": len(phase_order),
                "completed": list(completed_phases),
                "instruction": definition.get("instruction") if current else None,
            }

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # noqa: A002
            print(f"[shim] {fmt % args}", file=sys.stderr)

        def _json(self, code: int, obj) -> None:
            payload = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode() or "{}")
            except json.JSONDecodeError:
                return {}

        def do_GET(self):
            if self.path == "/health":
                return self._json(200, {"ok": True, "task_id": TASK_ID,
                                        "session": session_id,
                                        "trace_calls": len(trace)})
            if self.path == "/trace":
                with lock:
                    return self._json(200, {"trace": list(trace)})
            if self.path == "/step":
                return self._json(200, step_state())
            if self.path == "/mcp":
                # No SSE stream: plain JSON responses only (spec-permitted).
                return self._json(405, {"error": "SSE not supported; POST JSON-RPC"})
            return self._json(404, {"error": "not_found"})

        def do_DELETE(self):
            self._body()
            return self._json(200, {"ok": True})

        def do_POST(self):
            body = self._body()  # always drain first (keep-alive hygiene)
            if self.path == "/mcp":
                try:
                    return self._json(200, forward(body))
                except urllib.error.URLError as e:
                    return self._json(502, {"error": f"world unreachable: {e}"})
            if self.path == "/verify":
                try:
                    return self._json(200, verify(body.get("phase")))
                except ValueError as e:
                    return self._json(409, {"error": str(e), "step": step_state()})
                except Exception as e:  # noqa: BLE001
                    return self._json(500, {"error": f"verify failed: {e!r}"})
            if self.path == "/solve":
                supplied = self.headers.get("X-Solve-Token", "")
                supplied_hash = hashlib.sha256(supplied.encode()).hexdigest()
                if not ORACLE_PROOF_SHA256 or not hmac.compare_digest(
                        supplied_hash, ORACLE_PROOF_SHA256):
                    return self._json(403, {"error": "forbidden"})
                try:
                    return self._json(200, solve(body.get("phase")))
                except ValueError as e:
                    return self._json(400, {"error": str(e)})
                except Exception as e:  # noqa: BLE001
                    return self._json(500, {"error": f"solve failed: {e!r}"})
            return self._json(404, {"error": "not_found"})

    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[shim] serving on :{PORT}", file=sys.stderr)
    srv.serve_forever()


if __name__ == "__main__":
    main()
