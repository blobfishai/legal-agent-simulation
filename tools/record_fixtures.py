#!/usr/bin/env python3
"""M0.1 recorder — freeze today's correct behavior as executable truth.

For every task in the world document, runs FIVE episodes against a live world
server and records each episode's full tool trace and verifier verdict:

    oracle        the reference walk (must pass)
    noop          no calls at all              (must fail)
    text_only     reads only                   (must fail)
    blind_write   writes only                  (must fail)
    wrong_value   walk with corrupted payload  (must fail or be inconclusive)

Fixtures land in tools/fixtures/verdicts/<task_id>.json. They are the input to
tools/check_fixtures.py, which replays the recorded traces against a live
server and asserts the verdicts are identical — the regression net under every
future change to server.py, the verifiers, or the world document.

Run (server must be up with --v2-contracts):
  python3 tools/record_fixtures.py --base http://127.0.0.1:8974 \
      --world world/blobfish/world-v16.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "world", "local"))

import discriminate as D  # noqa: E402
import oracle as O  # noqa: E402

MODES = ("oracle", "noop", "text_only", "blind_write", "wrong_value")


def oracle_episode(base: str, world: dict, task: dict, verifier: dict) -> dict:
    """The reference walk, mirroring oracle.run_task but keeping the trace."""
    sess = O.OracleSession(base, task_id=task["task_id"])
    try:
        state = {"read_bodies": []}
        tables = {t["name"] for t in world["tables"]}
        pin = O.pinned_update(verifier or {}, tables)
        walk = O.vcode_walk(verifier or {}) or task.get("walk") or []
        ref_args = task.get("reference_args")
        for i, tool in enumerate(walk):
            if ref_args and i < len(ref_args):
                args = ref_args[i]
            else:
                args = O.derive_args(world, task, tool, state)
            if pin and tool.startswith("update_") and pin["table"] in (
                    O.world_tool_targets(world, tool)):
                args["id"] = pin["id"]
                if "new_status" in args and pin["field"] == "status":
                    args["new_status"] = pin["value"]
                elif pin["field"] in args:
                    args[pin["field"]] = pin["value"]
            ok, text = sess.call(tool, args)
            if ok and tool in ("documents_download", "drive_files_get"):
                state["read_bodies"].append(text)
        verdict = sess.verify(task["task_id"])
        return {"trace": sess.trace, "verdict": verdict}
    finally:
        sess.close()


def adversarial_episode(base: str, world: dict, task: dict, verifier: dict,
                        mode: str) -> dict:
    plan, pin, _ = D.build_walk(world, task, verifier)
    sess = O.OracleSession(base, task_id=task["task_id"])
    try:
        state = {"read_bodies": []}
        if mode == "text_only":
            D.realize(sess, world, task, plan, pin, state, skip_writes=True)
        elif mode == "blind_write":
            D.realize(sess, world, task, plan, pin, state, skip_reads=True)
        elif mode == "wrong_value":
            D.realize(sess, world, task, plan, pin, state, corrupt_last_write=True)
        # noop: no calls
        verdict = sess.verify(task["task_id"])
        return {"trace": sess.trace, "verdict": verdict}
    finally:
        sess.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8974")
    ap.add_argument("--world", default=os.path.join(
        ROOT, "world", "blobfish", "world-v16.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "fixtures", "verdicts"))
    ap.add_argument("--tasks", default="", help="comma-separated task_id filter")
    ap.add_argument("--resume", action="store_true",
                    help="skip tasks whose fixture for THIS world already exists")
    ap.add_argument("--max-seconds", type=float, default=0,
                    help="stop cleanly after this budget (chunked runs); 0 = no limit")
    ap.add_argument("--gzip", action="store_true",
                    help="write .json.gz fixtures (checker reads both)")
    ap.add_argument("--workers", type=int, default=1,
                    help="record independent task sessions concurrently")
    args = ap.parse_args()
    if args.workers < 1:
        ap.error("--workers must be at least 1")
    if args.workers > 1 and args.max_seconds:
        ap.error("--max-seconds is supported only with --workers 1")
    t0 = time.monotonic()

    raw = json.load(open(args.world))
    world = raw.get("world", raw)
    verifiers = {v["task_id"]: v for v in world.get("verifiers") or []}
    tasks = world["tasks"]
    if args.tasks:
        want = set(args.tasks.split(","))
        tasks = [t for t in tasks if t["task_id"] in want]

    os.makedirs(args.out, exist_ok=True)
    world_name = os.path.basename(args.world)
    # Fixtures are keyed to world CONTENT, not filename: a rebuilt world with
    # the same name must invalidate them (learned live — a verifier was
    # regenerated between recording and replay and filename-keyed resume
    # happily skipped the stale fixture).
    world_sha = hashlib.sha256(open(args.world, "rb").read()).hexdigest()

    def fixture_current(tid: str) -> bool:
        for suffix, opener in ((".json.gz", gzip.open), (".json", open)):
            p = os.path.join(args.out, f"{tid}{suffix}")
            if os.path.exists(p):
                try:
                    with opener(p, "rt") as f:
                        return json.load(f).get("world_sha256") == world_sha
                except Exception:
                    return False
        return False

    if args.resume:
        before = len(tasks)
        tasks = [t for t in tasks if not fixture_current(t["task_id"])]
        print(f"resume: {before - len(tasks)} current, {len(tasks)} to record")

    def record_task(task: dict) -> tuple[str, bool]:
        tid = task["task_id"]
        v = verifiers.get(tid)
        episodes: dict[str, dict] = {}
        for mode in MODES:
            if mode == "oracle":
                episodes[mode] = oracle_episode(args.base, world, task, v)
            else:
                episodes[mode] = adversarial_episode(args.base, world, task, v, mode)
        payload = {"task_id": tid, "world": world_name,
                   "world_sha256": world_sha, "episodes": episodes}
        # NO sort_keys: argument insertion order must be preserved exactly —
        # the server echoes rows in merge order, so alphabetizing recorded
        # args makes replayed observation strings diverge spuriously.
        if args.gzip:
            # remove a stale plain-json twin so the checker never reads both
            stale = os.path.join(args.out, f"{tid}.json")
            if os.path.exists(stale):
                os.remove(stale)
            encoded = json.dumps(payload, indent=1, default=str).encode("utf-8")
            compressed = gzip.compress(encoded, compresslevel=9, mtime=0)
            with open(os.path.join(args.out, f"{tid}.json.gz"), "wb") as f:
                f.write(compressed)
        else:
            with open(os.path.join(args.out, f"{tid}.json"), "w") as f:
                json.dump(payload, f, indent=1, default=str)
        return tid, not episodes["oracle"]["verdict"].get("passed")

    n_bad_oracle = 0
    recorded = 0

    def accept_result(n: int, result: tuple[str, bool]) -> None:
        nonlocal n_bad_oracle, recorded
        tid, bad_oracle = result
        if bad_oracle:
            n_bad_oracle += 1
            print(f"  !! {tid}: ORACLE EPISODE DID NOT PASS — fixture suspect",
                  file=sys.stderr)
        recorded += 1
        if n % 25 == 0:
            print(f"  [{n}/{len(tasks)}] recorded", flush=True)

    if args.workers == 1:
        for n, task in enumerate(tasks, 1):
            if args.max_seconds and time.monotonic() - t0 > args.max_seconds:
                print(f"budget reached after {recorded} tasks — resume to continue",
                      flush=True)
                break
            accept_result(n, record_task(task))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            for n, result in enumerate(pool.map(record_task, tasks), 1):
                accept_result(n, result)

    print(f"recorded {recorded} tasks x {len(MODES)} episodes -> {args.out}")
    if n_bad_oracle:
        print(f"WARNING: {n_bad_oracle} oracle episodes did not pass", file=sys.stderr)
    return 2 if n_bad_oracle else 0


if __name__ == "__main__":
    sys.exit(main())
