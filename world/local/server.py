#!/usr/bin/env python3
"""Product-contract runtime for the legal-agent simulation world.

The selected world embeds product-table state, tasks and VCode verifiers. Every exposed
tool is loaded from a cited contract in ``mcp/v3/contracts``; this server has
no synthesized name-family dispatcher. Fidelity and task solvability are
proved independently by the conformance suite and oracle.

Surface (matches mcp/blobfish-lawfirm-bridge.mjs BLOBFISH_LOCAL=1 mode):
  GET  /health                 — {ok, world_id, tables, tools, tasks}
  GET  /world                  — world summary
  POST /sessions               — {} -> session id + bearer/refresh tokens
  POST /sessions/{id}/refresh  — one-use refresh-token exchange
  DELETE /sessions/{id}        — authenticated session teardown
  POST /mcp                    — JSON-RPC: initialize | notifications/initialized |
                                 tools/list | tools/call   (session via Mcp-Session-Id)
  POST /verify/{task_id}       — {"trace":[...]} -> VCode verdict for the session

Friction (from world.friction, seeded, deterministic per tool+call-index):
  tool_failure_signature_rate  — injected `rate_limited` / `stale_reference` errors
  ambiguous_ack_rate           — write acks that don't echo the created id
  delegation_write_cap         — hard cap on writes per session

Run:  python3 world/local/server.py [--port 8971]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evidence import ExternalEvidence
from paging import paging_diagnostic
from wire_errors import friction_http

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))
# State is namespaced per world/configuration. Concurrent servers must never
# share a partially built seed: that would poison initial-state baselines and
# every verifier guard built on them.
STATE_DIR = os.path.join(BASE, "state")  # finalized per-world in main()
SESS_DIR = os.path.join(STATE_DIR, "sessions")
SEED_DB = os.path.join(STATE_DIR, "seed.db")


def set_state_dir(world_path: str) -> None:
    global STATE_DIR, SESS_DIR, SEED_DB
    slug = os.path.splitext(os.path.basename(world_path))[0]
    STATE_DIR = os.path.join(BASE, "state", slug)
    SESS_DIR = os.path.join(STATE_DIR, "sessions")
    SEED_DB = os.path.join(STATE_DIR, "seed.db")

# ---------------------------------------------------------------------------
# World loading / seed DB
# ---------------------------------------------------------------------------

def load_world(path: str) -> dict:
    with open(path) as f:
        raw = json.load(f)
    return raw.get("world", raw)


def build_seed_db(world: dict, v2=None) -> None:
    """Build a complete seed and publish it atomically.

    Multiple local servers may legitimately run the same world on different
    ports.  Building SEED_DB in place lets one server copy another server's
    partially written database.  A private temporary build plus os.replace
    guarantees readers observe either the previous complete seed or the new
    complete seed, never an intermediate file.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    os.makedirs(SESS_DIR, exist_ok=True)
    pending = f"{SEED_DB}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    conn = sqlite3.connect(pending)
    build_ok = False
    try:
        for table in world["tables"]:
            cols = table["columns"]
            defs = []
            for c in cols:
                d = f'"{c["name"]}" {c.get("type", "TEXT")}'
                if c.get("pk"):
                    d += " PRIMARY KEY"
                defs.append(d)
            conn.execute(f'CREATE TABLE "{table["name"]}" ({", ".join(defs)})')
            col_names = [c["name"] for c in cols]
            for row in table.get("sample_rows") or []:
                vals = []
                for cn in col_names:
                    v = row.get(cn)
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v)
                    vals.append(v)
                ph = ", ".join("?" for _ in col_names)
                cq = ", ".join(f'"{c}"' for c in col_names)
                conn.execute(
                    f'INSERT INTO "{table["name"]}" ({cq}) VALUES ({ph})', vals
                )
        conn.commit()
        if v2 is not None:
            # A product-only world embeds its exact contract seed plus migrated
            # records. Create every contract table, but do not seed an embedded
            # table twice. Legacy worlds have no overlap and behave unchanged.
            embedded_tables = {table["name"] for table in world["tables"]}
            v2.create_and_seed(conn, skip_seed_tables=embedded_tables)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"new seed failed integrity check: {integrity}")
        build_ok = True
    finally:
        conn.close()
        if not build_ok:
            try:
                os.remove(pending)
            except OSError:
                pass
    try:
        os.replace(pending, SEED_DB)
    except Exception:
        try:
            os.remove(pending)
        except OSError:
            pass
        raise


def snapshot(db_path: str) -> dict:
    """{table: [row-dicts]} — the state shape the VCode verifiers consume."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    out: dict[str, list] = {}
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        for t in tables:
            out[t] = [dict(r) for r in conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid')]
    finally:
        conn.close()
    return out


# ---------------------------------------------------------------------------
# Deterministic friction
# ---------------------------------------------------------------------------

class Friction:
    def __init__(self, spec: dict):
        self.fail_rate = float(spec.get("tool_failure_signature_rate") or 0.0)
        self.ack_rate = float(spec.get("ambiguous_ack_rate") or 0.0)
        self.write_cap = int(spec.get("delegation_write_cap") or 0)
        self.seed = str(spec.get("tool_failure_seed") or "seed")

    def _h(self, kind: str, tool: str, idx: int) -> float:
        h = hashlib.sha256(f"{self.seed}:{kind}:{tool}:{idx}".encode()).hexdigest()
        return int(h[:12], 16) / float(16 ** 12)

    def fails(self, tool: str, idx: int) -> str | None:
        """Return an error signature if this call is scheduled to fail."""
        v = self._h("fail", tool, idx)
        if v < self.fail_rate:
            return "rate_limited" if int(v * 1e9) % 2 == 0 else "stale_reference"
        return None

    def ambiguous_ack(self, tool: str, idx: int) -> bool:
        return self._h("ack", tool, idx) < self.ack_rate


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class Session:
    """One episode's world state. With a task, the task's seed bundle
    (documents + core_data rows) is upserted over the base world at creation
    — idempotent for tasks derived from the base world, and the mechanism by
    which future tasks ship their own data without touching global tables."""

    def __init__(self, sid: str, task: dict | None = None,
                 document_rows_by_id: dict | None = None,
                 table_defs: dict | None = None,
                 contract_probe: bool = False, auth_ttl: int | None = None):
        self.id = sid
        self.task_id = (task or {}).get("task_id")
        self.contract_probe = bool(contract_probe)
        self.access_token = hashlib.sha256(f"access:0:{sid}".encode()).hexdigest()
        self.refresh_token = hashlib.sha256(f"refresh:{sid}".encode()).hexdigest()
        self.auth_generation = 0
        self.refresh_used = False
        self.auth_ttl = int(auth_ttl) if auth_ttl is not None else None
        self.auth_calls = 0
        self.db_path = os.path.join(SESS_DIR, f"{sid}.db")
        try:
            shutil.copyfile(SEED_DB, self.db_path)
            self.call_index = 0
            self.write_count = 0
            self.evidence = ExternalEvidence.for_task(task, Path(ROOT))
            seed = (task or {}).get("seed") or {}
            if seed:
                self._apply_seed(seed, document_rows_by_id or {}, table_defs or {})
        except Exception:
            try:
                os.remove(self.db_path)
            except OSError:
                pass
            raise

    def _apply_seed(
        self, seed: dict, document_rows_by_id: dict, table_defs: dict
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            def upsert(table: str, row: dict) -> None:
                cols = [c["name"] for c in table_defs[table]["columns"]]
                vals = [json.dumps(row.get(c)) if isinstance(row.get(c), (dict, list))
                        else row.get(c) for c in cols]
                cq = ", ".join(f'"{c}"' for c in cols)
                ph = ", ".join("?" for _ in cols)
                conn.execute(
                    f'INSERT OR REPLACE INTO "{table}" ({cq}) VALUES ({ph})', vals)

            for doc_id in seed.get("documents") or []:
                row = document_rows_by_id.get(doc_id)
                if row and "dm_documents" in table_defs:
                    upsert("dm_documents", row)
            for table, rows in (seed.get("core_data") or {}).items():
                if table not in table_defs:
                    continue
                for row in rows:
                    upsert(table, row)
            conn.commit()
        finally:
            conn.close()

    def close(self):
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def authorize(self, authorization: str | None) -> tuple[bool, str]:
        if authorization != f"Bearer {self.access_token}":
            return False, "invalid_token"
        if self.auth_ttl is not None and self.auth_calls >= self.auth_ttl:
            return False, "token_expired"
        self.auth_calls += 1
        return True, "ok"

    def refresh(self, supplied: str | None) -> tuple[bool, str]:
        if supplied != self.refresh_token:
            return False, "invalid_refresh_token"
        if self.refresh_used:
            return False, "refresh_token_already_used"
        self.refresh_used = True
        self.auth_generation += 1
        self.access_token = hashlib.sha256(
            f"access:{self.auth_generation}:{self.id}".encode()
        ).hexdigest()
        self.auth_calls = 0
        self.auth_ttl = None
        return True, self.access_token


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

def make_handler(world: dict, friction: Friction, initial_state: dict,
                 verifiers: dict, v2):
    sessions: dict[str, Session] = {}
    visible_tool_count = len(v2.mcp_tools())
    tasks_by_id = {t["task_id"]: t for t in world.get("tasks") or []}
    table_defs = {t["name"]: t for t in world["tables"]}
    document_rows_by_id = {
        row["id"]: row
        for row in (table_defs.get("dm_documents") or {}).get("sample_rows") or []
    }
    # initial-state baseline per task seed (deterministic → cache by task_id);
    # sessions without a task use the base-world baseline.
    initial_cache: dict[str, dict] = {"__base__": initial_state}

    def baseline_for(sess: Session) -> dict:
        key = sess.task_id or "__base__"
        if key not in initial_cache:
            initial_cache[key] = snapshot(sess.db_path)
        return initial_cache[key]
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *a):  # quiet
            pass

        def _json(self, code: int, obj, headers: dict[str, str] | None = None) -> None:
            data = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n).decode() or "{}")
            except json.JSONDecodeError:
                return {}

        def _session(self) -> Session | None:
            sid = (self.headers.get("Mcp-Session-Id")
                   or self.headers.get("X-Blobfish-Session"))
            return sessions.get(sid) if sid else None

        def _authorized_session(self) -> Session | None:
            sess = self._session()
            if not sess:
                self._json(401, {"auth_error": "missing_or_unknown_session"},
                           {"WWW-Authenticate": "Bearer"})
                return None
            ok, reason = sess.authorize(self.headers.get("Authorization"))
            if not ok:
                self._json(401, {"auth_error": reason}, {"WWW-Authenticate": "Bearer"})
                return None
            return sess

        # ------------------------------------------------------------- GET
        def do_GET(self):
            if self.path == "/health":
                return self._json(200, {
                    "ok": True, "world_id": world.get("world_id"),
                    "tables": len(world["tables"]), "tools": visible_tool_count,
                    "internal_operations": len(v2.tools) - visible_tool_count,
                    "tasks": len(world["tasks"]), "sessions": len(sessions),
                })
            if self.path == "/world":
                return self._json(200, {
                    "world_id": world.get("world_id"),
                    "company": (world.get("thesis") or {}).get("company"),
                    "tables": len(world["tables"]), "tools": visible_tool_count,
                    "internal_operations": len(v2.tools) - visible_tool_count,
                    "tasks": len(world["tasks"]),
                })
            context = re.match(r"^/internal/task-context/([\w\-]+)$", self.path)
            if context:
                task_id = context.group(1)
                task = tasks_by_id.get(task_id)
                verifier = verifiers.get(task_id)
                if task is None or verifier is None:
                    return self._json(404, {"error": "task_context_not_found"})
                # The server binds 127.0.0.1 inside the world container, so
                # this endpoint is reachable by the co-resident shim only,
                # never by the agent container. It prevents the shim from
                # parsing a second 250+ MB copy of the v21 world document.
                return self._json(200, {
                    "task": task,
                    "verifier": verifier,
                    "world": {
                        "tables": [{"name": table["name"]} for table in world["tables"]],
                        "tools": world.get("tools") or [],
                    },
                })
            return self._json(404, {"error": "not_found"})

        # ---------------------------------------------------------- DELETE
        def do_DELETE(self):
            self._body()  # drain any body — see do_POST
            m = re.match(r"^/sessions/([\w\-]+)$", self.path)
            if m:
                s = sessions.get(m.group(1))
                if s:
                    ok, reason = s.authorize(self.headers.get("Authorization"))
                    if not ok:
                        return self._json(401, {"auth_error": reason}, {"WWW-Authenticate": "Bearer"})
                    sessions.pop(m.group(1), None)
                if s:
                    s.close()
                return self._json(200, {"deleted": bool(s)})
            return self._json(404, {"error": "not_found"})

        # ------------------------------------------------------------- POST
        def do_POST(self):
            # Always drain the request body FIRST: an unread body on a
            # keep-alive connection corrupts the next request on it (the
            # leftover bytes parse as a garbage request line → HTML 400).
            body = self._body()

            if self.path == "/sessions":
                sid = uuid.uuid4().hex[:16]
                task = tasks_by_id.get((body or {}).get("task_id"))
                contract_probe = (
                    task is None and (body or {}).get("profile") == "contract"
                )
                sess = Session(sid, task=task, document_rows_by_id=document_rows_by_id,
                               table_defs=table_defs,
                               contract_probe=contract_probe,
                               auth_ttl=(body or {}).get("auth_ttl"))
                sessions[sid] = sess
                baseline_for(sess)  # warm the per-task baseline cache
                return self._json(200, {"session_id": sid, "task_id": sess.task_id,
                                        "access_token": sess.access_token,
                                        "refresh_token": sess.refresh_token,
                                        "token_type": "Bearer"})

            refresh = re.match(r"^/sessions/([\w\-]+)/refresh$", self.path)
            if refresh:
                sess = sessions.get(refresh.group(1))
                if not sess:
                    return self._json(401, {"auth_error": "missing_or_unknown_session"},
                                      {"WWW-Authenticate": "Bearer"})
                ok, value = sess.refresh((body or {}).get("refresh_token"))
                if not ok:
                    return self._json(401, {"auth_error": value}, {"WWW-Authenticate": "Bearer"})
                return self._json(200, {"access_token": value, "token_type": "Bearer"})

            m = re.match(r"^/verify/([\w\-]+)$", self.path)
            if m:
                return self._verify(m.group(1), body)

            if self.path == "/mcp":
                return self._mcp(body)

            return self._json(404, {"error": "not_found"})

        # ------------------------------------------------------------ verify
        def _verify(self, task_id: str, body: dict):
            v = verifiers.get(task_id)
            if not v:
                return self._json(404, {"error": f"no verifier for {task_id}"})
            sess = self._authorized_session()
            if not sess:
                return
            trace = body.get("trace") or []
            final_state = snapshot(sess.db_path)
            ns: dict = {}
            try:
                phase = body.get("phase")
                phase_vcodes = v.get("phase_vcodes") or {}
                if phase is not None and phase not in phase_vcodes:
                    return self._json(400, {"error": f"unknown verifier phase {phase!r}"})
                vcode = phase_vcodes[phase] if phase is not None else v["vcode"]
                exec(vcode, ns)  # shipped verifier code, executed verbatim
                verdict = ns["verify"](copy.deepcopy(baseline_for(sess)), final_state, trace)
                if phase is not None:
                    verdict["phase"] = phase
                diagnostic = paging_diagnostic(trace)
                verdict["paging_discipline"] = diagnostic
                verdict.setdefault("paging_complete", diagnostic["paging_complete"])
            except Exception as e:  # noqa: BLE001 — surface verifier bugs
                return self._json(500, {"error": f"verifier crashed: {e!r}"})
            return self._json(200, verdict)

        # --------------------------------------------------------------- mcp
        def _mcp(self, body: dict):
            msg = body
            mid = msg.get("id")
            method = msg.get("method", "")
            params = msg.get("params") or {}
            protected_session = None
            if method in {"tools/list", "tools/call"}:
                protected_session = self._authorized_session()
                if not protected_session:
                    return

            def rpc(result):
                return self._json(200, {"jsonrpc": "2.0", "id": mid, "result": result})

            def rpc_err(code, message):
                return self._json(200, {"jsonrpc": "2.0", "id": mid,
                                        "error": {"code": code, "message": message}})

            if method == "initialize":
                return rpc({
                    "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "lawfirm-local-world", "version": "1.0.0"},
                    "world": {
                        "worldId": world.get("world_id"),
                        "company": (world.get("thesis") or {}).get("company")
                                   or "Eve Litigation (SIMULATED)",
                        "runtime": f"local — world-v{world.get('version')} + product contracts",
                    },
                })
            if method.startswith("notifications/"):
                return self._json(200, {"ok": True})
            if method == "ping":
                return rpc({})
            if method == "tools/list":
                return rpc({"tools": v2.mcp_tools()})
            if method == "tools/call":
                sess = protected_session
                name = params.get("name")
                args = params.get("arguments") or {}
                tool = v2.tools.get(name)
                if tool is None or (tool.get("agent_visible") is False and not sess.contract_probe):
                    return rpc_err(-32602, f"Unknown tool '{name}'")
                sess.call_index += 1
                sig = None if sess.contract_probe else friction.fails(name, sess.call_index)
                if sig:
                    status, error_body, headers = friction_http(sig, tool.get("_dialect"))
                    return self._json(status, error_body, headers)
                is_write = v2.is_write(name)
                if is_write:
                    if (not sess.contract_probe and friction.write_cap
                            and sess.write_count >= friction.write_cap):
                        return rpc({"content": [{"type": "text",
                                                 "text": "ERROR delegation_write_cap: "
                                                         "write budget for this session "
                                                         "is exhausted"}],
                                    "isError": True})
                conn = sqlite3.connect(sess.db_path)
                try:
                    external = sess.evidence.call(name, args) if sess.evidence else None
                    ok, text = external if external is not None else v2.call(conn, name, args)
                finally:
                    conn.close()
                if ok and is_write:
                    sess.write_count += 1
                    if (not sess.contract_probe
                            and friction.ambiguous_ack(name, sess.call_index)):
                        text = ("Request accepted and queued for processing. "
                                "The record change will be reflected shortly.")
                return rpc({"content": [{"type": "text", "text": text}],
                            "isError": not ok})
            return rpc_err(-32601, f"Method not found: {method}")

    return Handler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8971)
    ap.add_argument("--world", default=os.path.join(
        ROOT, "world", "blobfish", "world-v16.json"))
    ap.add_argument("--v2-contracts", default="",
        help="directory of product contracts; inferred as v5 for world v21+, "
             "v4 for world v20, and v3 for historical worlds")
    args = ap.parse_args()

    set_state_dir(args.world.replace(".json", "-product.json"))
    world = load_world(args.world)
    if world.get("tools"):
        sys.exit(
            "product runtime refuses embedded synthesized tools; migrate with "
            "world/migrate/gen1_to_v16.py"
        )
    if args.v2_contracts:
        contracts_dir = args.v2_contracts
    else:
        version = int(world.get("version") or 0)
        suite = "v5" if version >= 21 else ("v4" if version >= 20 else "v3")
        contracts_dir = os.path.join(ROOT, "mcp", suite, "contracts")
    print(f"[local-world] loading {args.world} (state: {STATE_DIR})", file=sys.stderr)
    from v2runtime import V2Runtime
    v2 = V2Runtime(contracts_dir)
    build_seed_db(world, v2=v2)
    visible_tool_count = len(v2.mcp_tools())
    print(f"[local-world] product contracts: {len(v2.contracts)} products, "
          f"{visible_tool_count} agent tools, "
          f"{len(v2.tools) - visible_tool_count} internal operations, "
          f"{len(v2.tables)} tables seeded", file=sys.stderr)
    initial_state = snapshot(SEED_DB)
    friction = Friction(world.get("friction") or {})
    verifiers = {v["task_id"]: v for v in world.get("verifiers") or []}

    rows = sum(len(t) for t in initial_state.values())
    print(f"[local-world] world {world.get('world_id')} — "
          f"{len(world['tables'])} tables / {rows} rows / "
          f"{visible_tool_count} tools / {len(world['tasks'])} tasks / "
          f"{len(verifiers)} verifiers", file=sys.stderr)

    handler = make_handler(world, friction, initial_state, verifiers, v2)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"[local-world] serving on http://127.0.0.1:{args.port}", file=sys.stderr)
    srv.serve_forever()


if __name__ == "__main__":
    main()
