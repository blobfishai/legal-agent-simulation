#!/usr/bin/env python3
"""Build world-v20-draft: the real-world consumer-protection task families.

Appends two families (16 tasks, ~48 seeded documents, 6 matters) to the frozen
world-v19 base, exactly in the v18/v19 native lane: tasks carry a `walk` plus
`reference_args` the oracle replays verbatim, and verifiers are compiled by the
generic declarative VCode compiler.  The v19 artifact is never modified.

Fail-closed authoring: the build refuses to emit a world unless
  - world/v20/content.py's arithmetic validators all pass;
  - every pinned assertion string is present in the oracle reference output;
  - every fabrication-trap string is absent from the oracle reference output;
  - every read-anchor lands inside the 4,000-char trace observation window;
  - every walk tool exists in the product contracts;
  - no seeded id or task id collides with the base world.

Run:  python3 world/v20/build.py
      [--base world/blobfish/world-v19.json]
      [--out world/blobfish/world-v20-draft.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from world.v20 import content as C                      # noqa: E402
from world.v20.docs_a import family_a_docs              # noqa: E402
from world.v20.docs_a2 import family_a2_docs            # noqa: E402
from world.v20.docs_b import family_b_docs              # noqa: E402
from world.v20.tasks import build_specs                 # noqa: E402
from world.v20.verifiers import compile_vcode           # noqa: E402

DEFAULT_BASE = ROOT / "world" / "blobfish" / "world-v19.json"
DEFAULT_OUT = ROOT / "world" / "blobfish" / "world-v20-draft.json"
DEFAULT_REPORT = ROOT / "world" / "v20" / "realworld-build-report.json"
PACKS_DIR = ROOT / "world" / "expansion" / "packs-realworld"
RETAIL_LANE = ROOT / "world" / "v20" / "retail_lane.json"
RETAIL_CONTRACT = ROOT / "mcp" / "v4" / "contracts" / "retail-compliance.json"
RETAIL_SEEDS = ROOT / "research" / "retail-price-accuracy" / "seed-data.json"
CONTRACTS_DIR = ROOT / "mcp" / "v4" / "contracts"   # v4 = v3 systems + RetailGuard
HARVEY_PIN = "7be41d57fd5a"

DOC_ID_BASE = 200101
MATTER_IDS = {"delgado": 200001, "consent": 200002, "arl": 200003,
              "fees": 200004, "bipa": 200005, "breach": 200006}
WS_IDS = {"delgado": 21, "consent": 22, "arl": 23, "fees": 24, "bipa": 25, "breach": 26}
FOLDER_IDS = {"delgado": 41, "consent": 42, "arl": 43, "fees": 44, "bipa": 45, "breach": 46}
NOW = "2026-08-10T12:00:00Z"

MATTER_META = {
    "delgado": ("Halvorsen Market Group - Delgado Settlement Compliance (SIMULATED)",
                "20250-Delgado", "Post-settlement 51-jurisdiction pricing-law survey and remediation."),
    "consent": ("Halvorsen Market Group - San Bernal Consent Judgment (SIMULATED)",
                "20251-SanBernal", "Quarterly price-verification audit program under CIVSB-2024-118822."),
    "arl": ("Cobalt Peak Media - FCB Consent Order & ARL Sweep (SIMULATED)",
            "20252-PeakStream", "Auto-renewal 51-jurisdiction sweep and enrollment/cancel remediation."),
    "fees": ("Bluewater Lodge & Resorts - AG CID / Fee Remediation (SIMULATED)",
             "20253-Bluewater", "Drip-pricing CID response and all-in pricing remediation."),
    "bipa": ("Prairie Grill Holdings - Suarez Biometric Settlement (SIMULATED)",
             "20254-Suarez", "Biometric destruction schedule, consent remediation, vendor amendment."),
    "breach": ("Harborline Outfitters - Credential-Stuffing Breach Response (SIMULATED)",
               "20255-Harborline", "51-jurisdiction breach notification grid and resident letters."),
}

FAMILY_OF_TASK = lambda tid: ("consumer-protection-compliance" if "_cp_" in tid
                              else "consumer-protection-privacy")


def load_contract_tools() -> set[str]:
    names: set[str] = set()
    for path in CONTRACTS_DIR.glob("*.json"):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text("utf-8"))
        for tool in (data.get("tools") or data):
            if isinstance(tool, dict) and tool.get("name"):
                names.add(tool["name"])
    return names


def build_documents() -> tuple[list[dict], dict[str, dict]]:
    docs = family_a_docs() + family_a2_docs() + family_b_docs()
    by_key: dict[str, dict] = {}
    for offset, doc in enumerate(docs):
        doc["id"] = DOC_ID_BASE + offset
        mk = doc["matter_key"]
        doc["workspace_id"] = WS_IDS[mk]
        doc["folder_id"] = FOLDER_IDS[mk]
        if doc["key"] in by_key:
            raise SystemExit(f"duplicate document key {doc['key']}")
        by_key[doc["key"]] = doc
    return docs, by_key


def compile_task(spec: dict, docs_by_key: dict[str, dict]) -> tuple[dict, dict, list[str]]:
    problems: list[str] = []
    walk: list[str] = ["documents_search_fulltext"]
    args: list[dict] = [{"query": spec["search_query"], "limit": 20}]
    for key in spec["reads"]:
        doc = docs_by_key[key]
        walk.append("documents_download")
        args.append({"id": doc["id"]})
    for tool, targs in spec["writes"]:
        walk.append(tool)
        args.append(targs)

    assertions: list[dict] = []
    for key in spec["reads"]:
        doc = docs_by_key[key]
        if doc["anchor"] not in doc["body"]:
            problems.append(f"{spec['task_id']}: anchor missing from body of {key}")
        elif doc["body"].index(doc["anchor"]) > 3600:
            problems.append(f"{spec['task_id']}: anchor too deep in {key}")
        assertions.append({"kind": "tool_observation_contains", "name": f"read_{key}",
                           "tool": "documents_download", "anchors": [doc["anchor"]]})
    assertions.extend(spec["assertions"])

    # --- reference-output consistency (fail closed) ---
    write_texts: dict[str, str] = {}
    all_text_parts: list[str] = []
    for tool, targs in spec["writes"]:
        blob = json.dumps(targs, ensure_ascii=False)
        all_text_parts.append(blob)
        if tool == "documents_create":
            write_texts[f"doc::{targs['name']}"] = targs["body"]
        elif tool == "notes_create":
            write_texts[f"note::{targs['subject']}"] = targs["detail"]
    all_text = "\n".join(all_text_parts)

    for a in spec["assertions"]:
        m = a.get("matches") or {}
        if a["kind"] == "new_row":
            if a["table"] == "dm_documents":
                body = write_texts.get(f"doc::{m.get('name')}")
                needle = (m.get("body") or {}).get("contains")
                if body is None:
                    problems.append(f"{spec['task_id']}:{a['name']}: pin targets unknown doc {m.get('name')}")
                elif needle and needle not in body:
                    problems.append(f"{spec['task_id']}:{a['name']}: pin not in reference body: {needle!r}")
            elif a["table"] == "pm_notes":
                detail = write_texts.get(f"note::{m.get('subject')}")
                needle = (m.get("detail") or {}).get("contains")
                if detail is None:
                    problems.append(f"{spec['task_id']}:{a['name']}: pin targets unknown note {m.get('subject')}")
                elif needle and needle not in detail:
                    problems.append(f"{spec['task_id']}:{a['name']}: pin not in reference detail: {needle!r}")
            elif a["table"] == "pm_calendar_entries":
                date = (m.get("start_at") or {}).get("startswith", "")
                summary = (m.get("summary") or {}).get("contains", "")
                hit = any(t == "calendar_entries_create"
                          and ta["start_at"].startswith(date)
                          and summary in ta["summary"]
                          for t, ta in spec["writes"])
                if not hit:
                    problems.append(f"{spec['task_id']}:{a['name']}: no reference calendar write matches")
        elif a["kind"] == "absent_new_row":
            needle = None
            for field in ("body", "detail", "start_at", "summary"):
                v = m.get(field)
                if isinstance(v, dict):
                    needle = v.get("contains") or v.get("startswith")
                    if needle:
                        break
            # Scope the haystack the way the runtime scopes the check: per table.
            if a["table"] == "pm_calendar_entries":
                hay = "\n".join(ta["start_at"] + " " + ta["summary"]
                                for t, ta in spec["writes"] if t == "calendar_entries_create")
            elif a["table"] == "pm_notes":
                hay = "\n".join(b for k, b in write_texts.items() if k.startswith("note::"))
            else:
                scope_name = m.get("name")
                if isinstance(scope_name, dict):
                    hay = "\n".join(b for k, b in write_texts.items()
                                    if k.startswith("doc::") and scope_name.get("contains", "") in k)
                else:
                    hay = "\n".join(b for k, b in write_texts.items() if k.startswith("doc::"))
            if needle and needle in hay:
                problems.append(f"{spec['task_id']}:{a['name']}: TRAP string present in reference output: {needle!r}")

    complexity = {"medium": "medium", "high": "high"}[spec["difficulty"]]
    task = {
        "task_id": spec["task_id"],
        "outcome_class": "eligible_action",
        "prompt": spec["prompt"],
        "goal": spec["slug"].replace("-", " "),
        "required_tools": sorted(set(walk)),
        "walk": walk,
        "reference_args": args,
        "method": "v20_realworld_consumer_protection",
        "complexity": complexity,
        "steps": ["Locate the matter documents", "Read every required document in full",
                  "Apply the seeded in-world law and compute pinned values",
                  "File the deliverables in the exact pinned formats"],
        "tables_affected": spec["tables"],
        "effects": [{"table": t, "op": "insert"} for t in spec["tables"]],
        "provenance": {
            "family": FAMILY_OF_TASK(spec["task_id"]),
            "shaped_by": "research/realworld-tasks/RESEARCH.md",
            "synthetic": True,
        },
        "capability": spec["capability"],
        "difficulty_tier": "pending_triage",
        "acceptance_label": "admitted_deterministic_workflow",
    }
    verifier = {
        "task_id": spec["task_id"],
        "assertions": [a.get("name") or a["kind"] for a in assertions],
        "vcode": compile_vcode(spec["task_id"], walk, assertions,
                               allowed_tables=spec["tables"],
                               min_success_calls=len(walk)),
        "generated_by": "world/v20/build.py",
    }
    return task, verifier, problems


def seed_tables(world: dict, docs: list[dict]) -> dict[str, int]:
    tables = {t["name"]: t for t in world["tables"]}
    added = {"pm_matters": 0, "dm_workspaces": 0, "dm_folders": 0, "dm_documents": 0}

    existing_matter_ids = {r["id"] for r in tables["pm_matters"]["sample_rows"]}
    for key, mid in MATTER_IDS.items():
        if mid in existing_matter_ids:
            raise SystemExit(f"matter id collision: {mid}")
        display, number, desc = MATTER_META[key]
        tables["pm_matters"]["sample_rows"].append({
            "id": mid, "display_name": display, "number": number, "description": desc,
            "client_id": 1, "status": "open", "billing_method": "hourly",
            "open_date": "2025-09-20", "close_date": None,
            "practice_area_id": 2, "originating_attorney_id": 1,
            "responsible_attorney_id": 2, "updated_at": NOW,
        })
        added["pm_matters"] += 1

    existing_ws = {r["id"] for r in tables["dm_workspaces"]["sample_rows"]}
    for key, wid in WS_IDS.items():
        if wid in existing_ws:
            raise SystemExit(f"workspace id collision: {wid}")
        display, number, _ = MATTER_META[key]
        tables["dm_workspaces"]["sample_rows"].append({
            "id": wid, "name": display, "matter_number": number,
            "owner": "Consumer Protection Group",
        })
        added["dm_workspaces"] += 1

    existing_folders = {r["id"] for r in tables["dm_folders"]["sample_rows"]}
    for key, fid in FOLDER_IDS.items():
        if fid in existing_folders:
            raise SystemExit(f"folder id collision: {fid}")
        tables["dm_folders"]["sample_rows"].append({
            "id": fid, "name": "Compliance and Remediation", "workspace_id": WS_IDS[key],
        })
        added["dm_folders"] += 1

    existing_docs = {r["id"] for r in tables["dm_documents"]["sample_rows"]}
    for doc in docs:
        if doc["id"] in existing_docs:
            raise SystemExit(f"document id collision: {doc['id']}")
        tables["dm_documents"]["sample_rows"].append({
            "id": doc["id"], "name": doc["name"], "doc_class": doc["doc_class"],
            "folder_id": doc["folder_id"], "workspace_id": doc["workspace_id"],
            "author": "records@simulated-firm.example", "body": doc["body"],
            "edit_date": "2025-09-20", "latest_version": 1, "checked_out_by": None,
        })
        added["dm_documents"] += 1
    return added


def emit_packs(docs: list[dict], specs: list[dict], tasks: list[dict]) -> list[str]:
    PACKS_DIR.mkdir(parents=True, exist_ok=True)
    task_by_id = {t["task_id"]: t for t in tasks}
    out_paths = []
    for family, anchor in (
        ("consumer-protection-compliance",
         "Kukorinis v. Walmart / CA DA consent judgments / FTC v. Amazon (ARL) / "
         "FTC Fees Rule + state junk-fee laws - synthetic transforms"),
        ("consumer-protection-privacy",
         "Cothron v. White Castle + SB 2979 (BIPA) / Equifax multistate + 51-jurisdiction "
         "breach-notification variance - synthetic transforms"),
    ):
        fam_specs = [s for s in specs if FAMILY_OF_TASK(s["task_id"]) == family]
        fam_matter_keys = {s["matter_key"] for s in fam_specs}
        pack = {
            "family": family,
            "anchor": anchor,
            "provenance": {
                "research": "research/realworld-tasks/RESEARCH.md",
                "designs": "research/realworld-tasks/task-designs.json",
                "simulation_only": True,
                "compiled_by": "world/v20/build.py",
            },
            "documents": [
                {"title": d["name"], "doc_type": d["doc_class"].lower(),
                 "dm_document_id": d["id"], "trap": bool(d.get("trap")),
                 "body": d["body"]}
                for d in docs if d["matter_key"] in fam_matter_keys
            ],
            "tasks": [
                {"task_id": s["task_id"], "slug": s["slug"],
                 "capability": s["capability"], "difficulty": s["difficulty"],
                 "prompt": s["prompt"],
                 "reads": [x for x in s["reads"]],
                 "writes": [{"tool": t, "args": a} for t, a in s["writes"]],
                 "assertions": s["assertions"],
                 "walk": task_by_id[s["task_id"]]["walk"]}
                for s in fam_specs
            ],
        }
        path = PACKS_DIR / f"{family}.json"
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=1) + "\n", "utf-8")
        out_paths.append(str(path.relative_to(ROOT)))
    return out_paths


def build(base: Path, out: Path, report_path: Path) -> dict[str, Any]:
    content_errors = C.validate()
    if content_errors:
        for e in content_errors:
            print(f"CONTENT ERROR: {e}", file=sys.stderr)
        raise SystemExit(f"{len(content_errors)} content validation error(s)")

    docs, docs_by_key = build_documents()
    for doc in docs:
        if len(doc["body"]) > 3900:
            raise SystemExit(f"document {doc['key']} body too long ({len(doc['body'])} chars) "
                             "for the 4,000-char observation window")

    contract_tools = load_contract_tools()
    folders = {k: (FOLDER_IDS[k], WS_IDS[k]) for k in MATTER_IDS}
    specs = build_specs(MATTER_IDS, folders)

    raw = json.loads(base.read_text("utf-8"))
    world = raw.get("world", raw)
    existing_ids = {t["task_id"] for t in world["tasks"]}
    existing_tasks_by_id = {t["task_id"]: t for t in world["tasks"]}
    existing_verifiers_by_id = {v["task_id"]: v for v in world["verifiers"]}

    tasks, verifiers, problems = [], [], []
    for spec in specs:
        if spec["task_id"] in existing_ids:
            problems.append(f"duplicate task id {spec['task_id']}")
            continue
        task, verifier, task_problems = compile_task(spec, docs_by_key)
        problems.extend(task_problems)
        for tool in task["walk"]:
            if tool not in contract_tools:
                problems.append(f"{spec['task_id']}: walk tool not in contracts: {tool}")
        tasks.append(task)
        verifiers.append(verifier)

    # ------------------------------------------------------------------
    # Retail / harvey-recovery lane (extracted source: world/v20/retail_lane.json;
    # tables regenerated from the RetailGuard contract + committed seed data).
    # ------------------------------------------------------------------
    lane = json.loads(RETAIL_LANE.read_text("utf-8"))
    lane_verifier_by_id = {v["task_id"]: v for v in lane["verifiers"]}
    seen_ids = existing_ids | {t["task_id"] for t in tasks}
    lane_tasks, lane_verifiers = [], []
    for task in lane["tasks"]:
        if task["task_id"] in seen_ids:
            # Canonical v20 already contains this lane. Accept it only when
            # both the task and verifier are byte-for-byte equivalent.
            if existing_tasks_by_id.get(task["task_id"]) != task:
                problems.append(f"lane task conflicts with base: {task['task_id']}")
            if existing_verifiers_by_id.get(task["task_id"]) != lane_verifier_by_id.get(task["task_id"]):
                problems.append(f"lane verifier conflicts with base: {task['task_id']}")
            continue
        missing = [t for t in task.get("required_tools") or [] if t not in contract_tools]
        if missing:
            problems.append(f"{task['task_id']}: lane tools not in v4 contracts: {missing}")
        if task["task_id"] not in lane_verifier_by_id:
            problems.append(f"{task['task_id']}: lane verifier missing")
        lane_tasks.append(task)
        lane_verifiers.append(lane_verifier_by_id[task["task_id"]])
        seen_ids.add(task["task_id"])

    if problems:
        for p in problems:
            print(f"BUILD ERROR: {p}", file=sys.stderr)
        raise SystemExit(f"{len(problems)} build error(s); world not written")

    added = seed_tables(world, docs)

    retail_contract = json.loads(RETAIL_CONTRACT.read_text("utf-8"))
    retail_seeds = json.loads(RETAIL_SEEDS.read_text("utf-8"))["tables"]
    existing_table_names = {t["name"] for t in world["tables"]}
    existing_tables_by_name = {t["name"]: t for t in world["tables"]}
    retail_rows = 0
    retail_tables_added = 0
    for source in retail_contract["tables"]:
        name = source["name"]
        if name in existing_table_names:
            expected = {"name": name, "columns": source["columns"],
                        "sample_rows": retail_seeds[name]}
            if existing_tables_by_name[name] != expected:
                raise SystemExit(f"retail table conflicts with base: {name}")
            continue
        world["tables"].append({"name": name, "columns": source["columns"],
                                "sample_rows": retail_seeds[name]})
        retail_rows += len(retail_seeds[name])
        retail_tables_added += 1
    added["retail_tables"] = retail_tables_added
    added["retail_rows"] = retail_rows

    world["tasks"].extend(tasks)
    world["verifiers"].extend(verifiers)
    world["tasks"].extend(lane_tasks)
    world["verifiers"].extend(lane_verifiers)
    world["lab_practice_recovery"] = lane["world_keys"]["lab_practice_recovery"]
    world["version"] = 20
    world["world_id"] = "legal-agent-simulation-world-v20-draft"
    world["lineage"] = {
        "base": str(base.relative_to(ROOT)) if base.is_relative_to(ROOT) else str(base),
        "compiler": "world/v20/build.py",
        "families_added": ["consumer-protection-compliance", "consumer-protection-privacy"],
        "capabilities_added": ["complete-harvey-lab-adapter-coverage", "retail-price-accuracy",
                                "51-jurisdiction-research-gating",
                                "checkpointed-national-remediation"],
        "retail_lane_source": "world/v20/retail_lane.json",
        "research_provenance": ["research/realworld-tasks/RESEARCH.md",
                                 "research/retail-price-accuracy/SOURCES.md"],
    }

    # Harvey hosting arithmetic (fail closed): the recovery task must take
    # practice hosting to 1,760 unique sources; with the 250 firm-knowledge
    # tasks that is 2,010/2,010.
    practice_sources = {
        (t.get("file_lane") or {}).get("source_task")
        for t in world["tasks"]
        if (t.get("file_lane") or {}).get("source_commit") == HARVEY_PIN
    }
    practice_sources.discard(None)
    firm_sources = {
        (t.get("provenance") or {}).get("path")
        for t in world["tasks"]
        if t.get("method") == "harvey_lab_firm_knowledge_deterministic"
    }
    firm_sources.discard(None)
    hosted = len(practice_sources) + len(firm_sources)
    if len(practice_sources) != 1760 or len(firm_sources) != 250:
        raise SystemExit(f"harvey hosting drifted: practice={len(practice_sources)} "
                         f"firm={len(firm_sources)} (expected 1760/250)")

    payload = json.dumps(raw, ensure_ascii=False, separators=(",", ":")) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(payload, "utf-8")
    temporary.replace(out)

    pack_paths = emit_packs(docs, specs, tasks)

    report = {
        "schema_version": 2,
        "base": str(base.name),
        "base_tasks": len(world["tasks"]) - len(tasks) - len(lane_tasks),
        "added_tasks": len(tasks) + len(lane_tasks),
        "added_realworld_tasks": len(tasks),
        "added_retail_tasks": sum(1 for t in lane_tasks
                                  if t["task_id"].startswith("task_v20_retail_")),
        "added_harvey_recovery_tasks": sum(1 for t in lane_tasks
                                           if t["task_id"].startswith("labp_")),
        "added_documents": added["dm_documents"],
        "added_matters": added["pm_matters"],
        "retail_tables": added["retail_tables"],
        "retail_seed_rows": added["retail_rows"],
        "harvey_lab_source_tasks": 2010,
        "harvey_lab_tasks_hosted": hosted,
        "families": {
            "consumer-protection-compliance": sum(1 for t in tasks if "_cp_" in t["task_id"]),
            "consumer-protection-privacy": sum(1 for t in tasks if "_pp_" in t["task_id"]),
            "retail-price-accuracy": sum(1 for t in lane_tasks
                                         if t["task_id"].startswith("task_v20_retail_")),
            "harvey-lab-recovery": sum(1 for t in lane_tasks
                                       if t["task_id"].startswith("labp_")),
        },
        "assertion_counts": {v["task_id"]: len(v["assertions"]) for v in verifiers},
        "trap_documents": sorted(d["name"] for d in docs if d.get("trap")),
        "packs": pack_paths,
        "retail_lane_source": "world/v20/retail_lane.json",
        "total_tasks": len(world["tasks"]),
        "world_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    arguments = parser.parse_args()
    report = build(arguments.base, arguments.out, arguments.report)
    print(json.dumps({k: report[k] for k in
                      ("added_tasks", "added_documents", "total_tasks", "world_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
