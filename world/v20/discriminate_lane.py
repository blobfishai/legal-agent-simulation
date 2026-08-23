#!/usr/bin/env python3
"""Four-mode discrimination probe for v20 task lanes.

For each task, runs against a live server:
  noop        — open the task session and verify with no calls;
  text_only   — replay only the read steps of the reference walk;
  blind_write — replay only the write steps (no reads);
  wrong_value — replay the full walk with the write payloads' content values
                corrupted (bodies/details replaced, dates shifted one day,
                non-id numerics perturbed).

Every mode must FAIL for every task.  A passing noop/text_only/blind_write is a
discrimination failure; a passing wrong_value is recorded as inconclusive
(the corruption may not have touched a pinned field).  Output schema matches
data/discrimination-v20-retail.json.

Run: python3 world/v20/discriminate_lane.py --base http://127.0.0.1:8979 \
       --world world/blobfish/world-v20-draft.json \
       --tasks task_a,task_b --out data/discrimination-x.json
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "world" / "local"))

from oracle import OracleSession  # noqa: E402

CONTRACTS_DIR = ROOT / "mcp" / "v4" / "contracts"
CONTENT_KEYS = {"body", "detail", "display_text", "refund_text", "verification_note",
                "corrective_action", "evidence", "rationale", "change_reason"}
DATE_KEYS = {"start_at", "end_at", "due_at", "audit_date", "occurred_at", "updated_at"}
ID_SUFFIXES = ("_id", "id")
WRONG_TEXT = ("WRONG-VALUE PROBE: this deliverable intentionally omits every "
              "pinned value, phrase, and determination.")


def load_write_tools() -> set[str]:
    writes: set[str] = set()
    for path in CONTRACTS_DIR.glob("*.json"):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text("utf-8"))
        for tool in (data.get("tools") or []):
            kind = ((tool.get("op") or {}).get("kind") or "").lower()
            if kind in {"create", "update", "delete"}:
                writes.add(tool["name"])
    return writes


def shift_date(value: str) -> str:
    try:
        day = dt.date.fromisoformat(value[:10])
        return (day + dt.timedelta(days=1)).isoformat() + value[10:]
    except ValueError:
        return value


def corrupt(args: dict) -> dict:
    out = copy.deepcopy(args)
    for key, value in list(out.items()):
        if key in CONTENT_KEYS and isinstance(value, str):
            out[key] = WRONG_TEXT
        elif key in DATE_KEYS and isinstance(value, str):
            out[key] = shift_date(value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool) \
                and not key.endswith(ID_SUFFIXES) and key != "limit":
            out[key] = value * 3 + 1
        elif isinstance(value, dict):
            out[key] = corrupt(value)
    return out


def run_mode(base: str, task: dict, steps: list[tuple[str, dict]]) -> dict:
    session = OracleSession(base, task_id=task["task_id"])
    write_tools = run_mode.write_tools
    write_errored = False
    for tool, args in steps:
        ok, _text = session.call(tool, args)
        if not ok and tool in write_tools:
            write_errored = True
    verdict = session.verify(task["task_id"])
    session.close()
    return {"passed": bool(verdict.get("passed")),
            "reward": verdict.get("reward"),
            "failed": (verdict.get("failed_conditions") or [])[:12],
            "write_errored": write_errored}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8979")
    parser.add_argument("--world", default=str(ROOT / "world" / "blobfish" / "world-v20-draft.json"))
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--out", required=True)
    arguments = parser.parse_args()

    raw = json.loads(Path(arguments.world).read_text("utf-8"))
    world = raw.get("world", raw)
    wanted = [t for t in arguments.tasks.split(",") if t]
    tasks = {t["task_id"]: t for t in world["tasks"] if t["task_id"] in wanted}
    missing = [t for t in wanted if t not in tasks]
    if missing:
        raise SystemExit(f"tasks not in world: {missing}")

    write_tools = load_write_tools()
    run_mode.write_tools = write_tools

    rows, failures, inconclusive, harness_errors = [], [], [], []
    for task_id in wanted:
        task = tasks[task_id]
        walk = list(zip(task["walk"], task["reference_args"]))
        reads = [(t, a) for t, a in walk if t not in write_tools]
        writes = [(t, a) for t, a in walk if t in write_tools]
        modes = {
            "noop": [],
            "text_only": reads,
            "blind_write": writes,
            "wrong_value": [(t, corrupt(a) if t in write_tools else a) for t, a in walk],
        }
        row: dict = {"task_id": task_id}
        for mode, steps in modes.items():
            try:
                row[mode] = run_mode(arguments.base, task, steps)
            except Exception as error:  # noqa: BLE001
                harness_errors.append(f"{task_id}:{mode}: {error!r}")
                row[mode] = {"passed": None, "reward": None, "failed": [],
                             "write_errored": False, "error": repr(error)}
                continue
            if row[mode]["passed"]:
                if mode == "wrong_value":
                    inconclusive.append(task_id)
                else:
                    failures.append(f"{task_id}:{mode}")
        rows.append(row)
        print(f"{task_id}: " + " ".join(
            f"{m}={'FAIL(ok)' if row[m].get('passed') is False else 'PASSED(bad)' if row[m].get('passed') else 'ERR'}"
            for m in ("noop", "text_only", "blind_write", "wrong_value")), file=sys.stderr)

    payload = {
        "summary": {
            "tasks": len(rows),
            "modes": ["noop", "text_only", "blind_write", "wrong_value"],
            "discrimination_failures": failures,
            "wrong_value_inconclusive": inconclusive,
            "harness_errors": harness_errors,
        },
        "rows": rows,
    }
    Path(arguments.out).write_text(json.dumps(payload, indent=1) + "\n", "utf-8")
    print(json.dumps(payload["summary"]))
    return 0 if not failures and not harness_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
