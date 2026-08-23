#!/usr/bin/env python3
"""Build world-v19: five checkpointed capstones and thirty multi-turn tasks."""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from world.v19.verifiers import compile_vcode  # noqa: E402


DEFAULT_BASE = ROOT / "world" / "blobfish" / "world-v18.json"
DEFAULT_OUT = ROOT / "world" / "blobfish" / "world-v19.json"
DEFAULT_REPORT = ROOT / "world" / "v19" / "build-report.json"

CAPABILITY_TYPES = {
    1: "extraction_and_determination",
    2: "rule_application",
    3: "computation",
    4: "retrieval_and_review_at_scale",
    5: "grounded_drafting_and_redlining",
    6: "workflow_execution",
    7: "abstention_and_escalation",
    8: "operational_robustness",
    9: "multi_turn_and_interruption",
    10: "long_horizon_composite_matters",
}

PACK_CAPABILITY = {
    # determinate extraction / review
    "acord-clause-retrieval.json": 1,
    "arbitration-clause-review.json": 1,
    "banking-finance-covenants.json": 1,
    "cuad-clause-extraction.json": 1,
    "maud-deal-points.json": 1,
    "spa-deal-extraction.json": 1,
    # rule application / categorical legal determination
    "appeal-outcome.json": 2,
    "bankruptcy-claim-classification.json": 2,
    "kyc-aml-screening.json": 2,
    "legalbench-rule-application.json": 2,
    "obliqa-regulatory-obligations.json": 2,
    "violation-screening.json": 2,
    # exact arithmetic / dates
    "covenant-portfolio-sweep.json": 3,
    "damages-computation.json": 3,
    "deadline-computation.json": 3,
    "hsr-merger-notification.json": 3,
    "lab-employment-compensation-escalation.json": 3,
    "multi-hop-damages.json": 3,
    # all-and-only corpus retrieval
    "discovery-retrieval.json": 4,
    "ethical-wall-screening.json": 4,
    "posture-dependent-chronology.json": 4,
    "production-gap-disclosure.json": 4,
    # grounded work product
    "deep-drafting.json": 5,
    "engagement-letters.json": 5,
    "grounded-drafting.json": 5,
    # executable processes
    "closing-binder.json": 6,
    "court-efiling.json": 6,
    "deposition-management.json": 6,
    "expert-witness-management.json": 6,
    "lawflow-entity-formation.json": 6,
    "settlement-authority.json": 6,
    # unsupported-answer traps
    "citation-audit.json": 7,
    "hallucination-traps.json": 7,
    # async submit/poll/retrieve is the primary load-bearing capability
    "async-privilege-screen.json": 8,
}

METHOD_CAPABILITY = {
    "graph_walk_exact_state": 6,
    "v3_workflow": 6,
    "m3_deadline_workflow": 3,
    "m3_efiling_workflow": 6,
    "m3_esign_closing_workflow": 6,
    "m6_native_multiturn": 9,
    "m6_checkpointed_capstone": 10,
}


def assign_capability(task: dict[str, Any]) -> None:
    """Give every task one primary §0B capability, without difficulty claims."""
    if task.get("capability_type") is None:
        method = task.get("method")
        pack = (task.get("expansion") or {}).get("pack")
        capability = METHOD_CAPABILITY.get(method) or PACK_CAPABILITY.get(pack)
        if capability is None:
            raise RuntimeError(f"no capability mapping for {task['task_id']} ({method=}, {pack=})")
        task["capability_type"] = capability
    capability = int(task["capability_type"])
    if capability not in CAPABILITY_TYPES:
        raise RuntimeError(f"invalid capability type {capability} on {task['task_id']}")
    task["capability_name"] = CAPABILITY_TYPES[capability]


def _phase(name: str, instruction: str, calls: list[tuple[str, dict]],
           assertions: list[dict]) -> dict[str, Any]:
    return {
        "name": name,
        "instruction": instruction,
        "walk": [tool for tool, _ in calls],
        "reference_args": [args for _, args in calls],
        "assertions": assertions,
        "min_reward": 1.0,
    }


def _gmail_raw(sender: str, recipient: str, subject: str, body: str) -> str:
    message = (f"From: {sender}\r\nTo: {recipient}\r\nSubject: {subject}\r\n"
               "Content-Type: text/plain; charset=utf-8\r\n\r\n" + body)
    return base64.urlsafe_b64encode(message.encode()).decode().rstrip("=")


CAPSTONES = [
    ("northstar", 1, "answer_to_complaint", "Northstar Answer", "complaint_and_summons_served",
     "personal", "2026-08-14", "2026-09-04", "410 U.S. 113"),
    ("aurelius", 2, "motion", "Aurelius Motion", "interrogatories_served",
     "electronic", "2026-08-12", "2026-09-11", "347 U.S. 483"),
    ("lumos", 3, "notice", "Lumos Notice", "interrogatories_served",
     "mail", "2026-08-12", "2026-09-14", "410 U.S. 113"),
    ("dunmore", 1, "stipulation", "Dunmore Stipulation", "requests_for_production_served",
     "electronic", "2026-08-14", "2026-09-14", "347 U.S. 483"),
    ("quorum", 2, "response", "Quorum Response", "requests_for_production_served",
     "mail", "2026-08-14", "2026-09-16", "410 U.S. 113"),
]


def _capstone(index: int, values: tuple[str | int, ...]) -> tuple[dict, dict]:
    slug, case_id, event_type, label, trigger, service, trigger_date, due, citation = values
    assert isinstance(case_id, int)
    task_id = f"task_v19_capstone_{index:03d}"
    document_name = f"{slug}-capstone-filing.pdf"
    final_summary = f"{label} deadline — superseding instruction"
    original_summary = f"{label} deadline — initial instruction"
    task_name = f"Complete {label} response"
    original_task_name = f"Prepare {label} response"
    bill_number = "INV-15123"
    ledger_invoice_id = [3, 6, 7, 8, 2][index - 1]
    record_name = f"{slug}-matter-closeout.md"

    phase1_calls = (
        [("contacts_list", {"limit": 20})] * 4
        + [("matters_list", {})] * 3
        + [("documents_search", {"anywhere": str(slug), "limit": 20, "offset": 0})] * 3
    )
    phase2_calls = (
        [("opinions_search", {"q": str(slug)})] * 4
        + [("citation_lookup", {"text": str(citation)})] * 4
        + [("documents_search", {"anywhere": "litigation", "limit": 20, "offset": 0})] * 2
    )
    filing_args = {
        "case_id": case_id,
        "event_type": event_type,
        "document_name": document_name,
        "document_mime_type": "application/pdf",
        "document_sha256": hashlib.sha256(document_name.encode()).hexdigest(),
        "description": label,
    }
    phase3_calls = [
        ("efiling_cases_get", {"case_id": case_id}),
        ("efiling_cases_get", {"case_id": case_id}),
        ("efiling_filings_create", filing_args),
        *[("efiling_nef_notices_list", {"case_id": case_id, "status": "sent", "limit": 20}) for _ in range(3)],
        *[("efiling_docket_entries_list", {"case_id": case_id, "limit": 20}) for _ in range(4)],
    ]
    deadline_args = {"trigger_event": trigger, "jurisdiction": "US-FEDERAL-CIVIL",
                     "service_method": service, "trigger_date": trigger_date}
    calendar_list = {"calendarId": "docketing@simulated-firm.example",
                     "timeMin": f"{due}T00:00:00Z", "timeMax": f"{due}T23:59:59Z",
                     "maxResults": 20}
    calendar_create = {
        "calendarId": "docketing@simulated-firm.example", "summary": final_summary,
        "start_at": f"{due}T17:00:00Z", "end_at": f"{due}T17:30:00Z",
        "attendees": "docketing@simulated-firm.example",
    }
    task_create = {"body": {"data": {
        "assignee": {"id": 1, "type": "User"}, "description": "Verified from DeadlineRules",
        "due_at": due, "matter": {"id": 1}, "name": task_name, "priority": "high",
    }}}
    phase4_calls = (
        [("deadlines_compute", deadline_args)] * 3
        + [("calendar_events_list", calendar_list)] * 2
        + [("calendar_events_insert", calendar_create)]
        + [("tasks_list", {"matter_id": 1, "limit": 20})] * 2
        + [("tasks_create", task_create), ("calendar_events_list", calendar_list)]
    )
    time_create = {"body": {"data": {
        "type": "TimeEntry", "date": "2026-08-12", "matter": {"id": 1},
        "user": {"id": 1}, "quantity": 1.0 + index / 10, "price": 500,
        "note": f"Capstone closeout for {label}",
        "activity_description": {"utbms_task_id": "L110"}, "non_billable": False,
    }}}
    communication = {"body": {"data": {
        "matter": {"id": 1}, "type": "Email", "subject": f"{label} completed",
        "body": f"Filed {document_name}; deadline {due}; bill {bill_number} prepared.",
        "senders": "associate@simulated-firm.example",
        "receivers": "client@simulated.example", "received_at": "2026-08-12T18:00:00Z",
    }}}
    email_subject = f"{label} matter closeout"
    phase5_calls = [
        ("time_entries_create", time_create),
        ("time_entries_list", {"matter_id": 1, "limit": 20}),
        ("bills_get", {"id": 9}),
        ("bills_update", {"id": 9, "body": {"data": {"state": "awaiting_approval"}}}),
        ("bills_get", {"id": 9}),
        ("invoices_submit", {"id": ledger_invoice_id}),
        ("documents_create", {"folder_id": 1, "workspace_id": 1, "name": record_name,
                              "doc_class": "MATTER_CLOSEOUT", "author": "associate@simulated-firm.example",
                              "body": f"{label}: {document_name} filed; deadline {due}; {bill_number}; "
                                      f"Ledger invoice {ledger_invoice_id} submitted."}),
        ("documents_search", {"anywhere": record_name, "limit": 20, "offset": 0}),
        ("communications_create", communication),
        ("gmail_messages_send", {"userId": "me", "body": {"raw": _gmail_raw(
            "associate@simulated-firm.example", "client@simulated.example", email_subject,
            f"Filed {document_name}; deadline {due}; {bill_number} advanced; Ledger invoice submitted.")}}),
    ]

    phases = [
        _phase("01-intake-conflicts",
               f"Review contacts, open matters, and DMS records for {label}. The working deadline label is "
               f"`{original_summary}`; do not create records yet.", phase1_calls,
               [{"kind": "tool_min_calls", "name": "contacts_reviewed", "tool": "contacts_list", "minimum": 4},
                {"kind": "tool_min_calls", "name": "matter_reviewed", "tool": "matters_list", "minimum": 3}]),
        _phase("02-authority",
               f"Research and cite-check authority for {label}; resolve citation {citation}. Do not fabricate authority.",
               phase2_calls,
               [{"kind": "tool_min_calls", "name": "citation_checked", "tool": "citation_lookup", "minimum": 4}]),
        _phase("03-file-and-confirm",
               f"File `{document_name}` in CourtFile as `{event_type}` and confirm both the NEF and docket entry.",
               phase3_calls,
               [{"kind": "new_row", "name": "filing_created", "table": "ef_filings",
                 "matches": {"case_id": case_id, "event_type": event_type, "document_name": document_name}},
                {"kind": "new_row", "name": "nef_created", "table": "ef_nef_notices", "matches": {"status": "sent"}}]),
        _phase("04-superseding-deadline",
               f"Superseding instruction: discard the earlier label `{original_summary}`. Compute the deadline from "
               f"{trigger_date}, then use exactly `{final_summary}` and task `{task_name}`, both due {due}.",
               phase4_calls,
               [{"kind": "new_row", "name": "corrected_calendar_event", "table": "ws_events",
                 "matches": {"summary": final_summary, "start_at": {"startswith": due}}},
                {"kind": "new_row", "name": "corrected_tickler", "table": "pm_tasks",
                 "matches": {"name": task_name, "due_at": {"startswith": due}}},
                {"kind": "absent_new_row", "name": "superseded_label_absent", "table": "ws_events",
                 "matches": {"summary": original_summary}}]),
        _phase("05-closeout-billing",
               f"Record time, move prebill {bill_number} to awaiting approval, submit Ledger invoice "
               f"{ledger_invoice_id}, file `{record_name}`, verify it, and send/log the client communication.",
               phase5_calls,
               [{"kind": "new_row", "name": "time_recorded", "table": "pm_time_entries",
                 "matches": {"description": f"Capstone closeout for {label}"}},
                {"kind": "changed_row", "name": "prebill_advanced", "table": "pm_bills", "id": 9,
                 "before": {"state": "draft"}, "matches": {"state": "awaiting_approval"}},
                {"kind": "changed_row", "name": "ledes_invoice_submitted", "table": "eb_invoices",
                 "id": ledger_invoice_id, "matches": {"status": "submitted"}},
                {"kind": "new_row", "name": "closeout_filed", "table": "dm_documents", "matches": {"name": record_name}},
                {"kind": "new_row", "name": "communication_logged", "table": "pm_communications",
                 "matches": {"subject": f"{label} completed"}},
                {"kind": "new_row", "name": "client_email_sent", "table": "ws_messages",
                 "matches": {"subject": email_subject}}]),
    ]
    walk = [tool for phase in phases for tool in phase["walk"]]
    reference_args = [args for phase in phases for args in phase["reference_args"]]
    all_assertions = [item for phase in phases for item in phase["assertions"]]
    allowed = ["ef_filings", "ef_docket_entries", "ef_nef_notices", "cl_docket_entries",
               "ws_events", "pm_tasks", "pm_time_entries", "pm_bills", "eb_invoices",
               "dm_documents", "pm_communications", "ws_messages"]
    phase_vcodes = {
        phase["name"]: compile_vcode(task_id, phase["walk"], phase["assertions"])
        for phase in phases[:-1]
    }
    # The final checkpoint is also the cumulative verifier.  Earlier phase
    # passes cannot mask later collateral damage or rollback.
    phase_vcodes[phases[-1]["name"]] = compile_vcode(
        task_id, walk, all_assertions, allowed_tables=allowed, min_success_calls=50)

    pre_args = copy.deepcopy(reference_args)
    calendar_index = walk.index("calendar_events_insert")
    task_index = walk.index("tasks_create")
    pre_args[calendar_index]["summary"] = original_summary
    pre_args[task_index]["body"]["data"]["name"] = original_task_name
    task = {
        "task_id": task_id,
        "outcome_class": "eligible_action",
        "prompt": f"Run the checkpointed {label} matter from conflict review through filing, deadline, and billing.",
        "goal": f"Complete one {label} matter end to end",
        "required_tools": sorted(set(walk)),
        "walk": walk,
        "reference_args": reference_args,
        "pre_correction_walk": walk,
        "pre_correction_reference_args": pre_args,
        "method": "m6_checkpointed_capstone",
        "complexity": "very_high",
        "multi_step": {"reward_strategy": "mean", "phases": phases},
        "session": [{"turn": 4, "user_text": phases[3]["instruction"], "kind": "superseding_instruction"}],
        "tables_affected": allowed,
        "provenance": {"source": "manifest-first canonical workflow 12", "synthetic": True},
        "difficulty_tier": "pending_triage",
        "acceptance_label": "admitted_long_horizon_composite",
        "capability_type": 10,
    }
    verifier = {
        "task_id": task_id,
        "assertions": [a["name"] for a in all_assertions] + ["minimum_successful_calls", "no_collateral_damage"],
        "vcode": compile_vcode(task_id, walk, all_assertions, allowed_tables=allowed, min_success_calls=50),
        "phase_vcodes": phase_vcodes,
        "generated_by": "world/v19/build.py",
    }
    return task, verifier


def _task_create(name: str, due: str, *, description: str = "Superseding instruction applied") -> dict:
    return {"body": {"data": {
        "assignee": {"id": 1, "type": "User"}, "description": description,
        "due_at": due, "matter": {"id": 1}, "name": name, "priority": "normal",
    }}}


def _multiturn(index: int) -> tuple[dict, dict]:
    task_id = f"task_v19_turn_{index:03d}"
    group = "fragment" if index <= 8 else "correction" if index <= 16 else "supersede" if index <= 23 else "withdrawal"
    ordinal = f"{index:02d}"
    read_calls: list[tuple[str, dict]]
    final_calls: list[tuple[str, dict]]
    pre_calls: list[tuple[str, dict]]
    final_assertions: list[dict]

    if group == "fragment":
        final_name = f"Selected candidate 1 — turn {ordinal}"
        read_calls = [("tasks_list", {"matter_id": 1, "limit": 20}),
                      ("contacts_list", {"limit": 20})]
        final_calls = [("tasks_create", _task_create(final_name, "2026-09-30"))]
        pre_calls = read_calls
        initial = "Review the candidate records for matter 1 and wait for my numbered selection. Do not write yet."
        followup = f"1 — proceed with candidate 1. Create task `{final_name}` due 2026-09-30."
        final_assertions = [{"kind": "new_row", "name": "selected_candidate_created",
                             "table": "pm_tasks", "matches": {"name": final_name, "due_at": {"startswith": "2026-09-30"}}}]
    elif group == "correction":
        name = f"Corrected deadline task {ordinal}"
        old_due = "2026-10-01"
        new_due = f"2026-10-{index - 3:02d}"
        read_calls = [("documents_search", {"anywhere": "deadline", "limit": 20, "offset": 0}),
                      ("tasks_list", {"matter_id": 1, "limit": 20})]
        final_calls = [("tasks_create", _task_create(name, new_due))]
        pre_calls = read_calls + [("tasks_create", _task_create(name, old_due, description="Original instruction"))]
        initial = f"Review the record, then create `{name}` due {old_due}. Wait in case docketing corrects the date."
        followup = f"Correction: {old_due} is superseded. The only valid due date is {new_due}; create exactly one task."
        final_assertions = [
            {"kind": "new_row", "name": "corrected_due_date", "table": "pm_tasks",
             "matches": {"name": name, "due_at": {"startswith": new_due}}},
            {"kind": "absent_new_row", "name": "old_due_date_absent", "table": "pm_tasks",
             "matches": {"name": name, "due_at": {"startswith": old_due}}},
            {"kind": "new_row_count", "name": "single_task_only", "table": "pm_tasks", "count": 1},
        ]
    elif group == "supersede":
        old_name = f"draft-instruction-{ordinal}.md"
        new_name = f"superseding-letter-{ordinal}.md"
        read_calls = [("documents_search", {"anywhere": "instruction", "limit": 20, "offset": 0}),
                      ("matters_list", {})]
        final_doc = {"folder_id": 1, "workspace_id": 1, "name": new_name,
                     "doc_class": "INSTRUCTION", "author": "partner@simulated-firm.example",
                     "body": f"Superseding instruction turn {ordinal}; prior draft withdrawn."}
        old_doc = {**final_doc, "name": old_name, "body": f"Original instruction turn {ordinal}."}
        final_calls = [("documents_create", final_doc)]
        pre_calls = read_calls + [("documents_create", old_doc)]
        initial = f"Review the matter and prepare to file `{old_name}` after confirmation."
        followup = f"Superseding letter: do not file `{old_name}`. File only `{new_name}` and state that the prior draft is withdrawn."
        final_assertions = [
            {"kind": "new_row", "name": "superseding_letter_filed", "table": "dm_documents",
             "matches": {"name": new_name, "body": {"contains": "prior draft withdrawn"}}},
            {"kind": "absent_new_row", "name": "superseded_draft_absent", "table": "dm_documents",
             "matches": {"name": old_name}},
            {"kind": "new_row_count", "name": "single_document_only", "table": "dm_documents", "count": 1},
        ]
    else:
        keep = f"Retained scope item {ordinal}"
        withdrawn = f"Withdrawn scope item {ordinal}"
        read_calls = [("tasks_list", {"matter_id": 1, "limit": 20}),
                      ("matters_list", {})]
        keep_call = ("tasks_create", _task_create(keep, "2026-11-01"))
        withdrawn_call = ("tasks_create", _task_create(withdrawn, "2026-11-02"))
        final_calls = [keep_call]
        pre_calls = read_calls + [keep_call, withdrawn_call]
        initial = f"Review the matter, then create tasks `{keep}` and `{withdrawn}` after final scope confirmation."
        followup = f"Scope withdrawal: skip `{withdrawn}` entirely. Create only `{keep}`."
        final_assertions = [
            {"kind": "new_row", "name": "retained_scope_created", "table": "pm_tasks", "matches": {"name": keep}},
            {"kind": "absent_new_row", "name": "withdrawn_scope_absent", "table": "pm_tasks", "matches": {"name": withdrawn}},
            {"kind": "new_row_count", "name": "single_scope_item", "table": "pm_tasks", "count": 1},
        ]

    phases = [
        _phase("01-initial-review", initial, read_calls,
               [{"kind": "tool_min_calls", "name": "initial_review_completed",
                 "tool": read_calls[0][0], "minimum": 1}]),
        _phase("02-user-followup", followup, final_calls, final_assertions),
    ]
    walk = [tool for phase in phases for tool in phase["walk"]]
    reference_args = [args for phase in phases for args in phase["reference_args"]]
    allowed = ["pm_tasks"] if group in {"fragment", "correction", "withdrawal"} else ["dm_documents"]
    final_vcode = compile_vcode(task_id, walk, final_assertions, allowed_tables=allowed)
    phase_vcodes = {
        phases[0]["name"]: compile_vcode(task_id, phases[0]["walk"], phases[0]["assertions"]),
        phases[1]["name"]: final_vcode,
    }
    verifier = {
        "task_id": task_id,
        "assertions": [a["name"] for a in final_assertions] + ["required_path", "no_collateral_damage"],
        "vcode": final_vcode,
        "phase_vcodes": phase_vcodes,
        "generated_by": "world/v19/build.py",
    }
    task = {
        "task_id": task_id,
        "outcome_class": "eligible_action",
        "prompt": initial,
        "goal": f"Apply a load-bearing {group} follow-up without stale writes",
        "required_tools": sorted(set(walk)),
        "walk": walk,
        "reference_args": reference_args,
        "pre_correction_walk": [tool for tool, _ in pre_calls],
        "pre_correction_reference_args": [args for _, args in pre_calls],
        "method": "m6_native_multiturn",
        "complexity": "medium",
        "multi_step": {"reward_strategy": "mean", "phases": phases},
        "session": [{"turn": 2, "user_text": followup, "kind": group}],
        "tables_affected": allowed,
        "provenance": {"source": "manifest-first multi-turn family", "synthetic": True},
        "difficulty_tier": "pending_triage",
        "acceptance_label": "admitted_multi_turn",
        "capability_type": 9,
    }
    return task, verifier


def build(base: Path, out: Path, report_path: Path) -> dict[str, Any]:
    raw = json.loads(base.read_text("utf-8"))
    world = raw.get("world", raw)
    existing = {task["task_id"] for task in world["tasks"]}
    pairs = [*(_capstone(i, row) for i, row in enumerate(CAPSTONES, 1)),
             *(_multiturn(i) for i in range(1, 31))]
    for task, verifier in pairs:
        if task["task_id"] in existing:
            raise RuntimeError(f"duplicate task id {task['task_id']}")
        world["tasks"].append(task)
        world["verifiers"].append(verifier)
        existing.add(task["task_id"])
    for task in world["tasks"]:
        assign_capability(task)
    world["task_taxonomy"] = {
        "version": "LAB-Superset-0B-v1",
        "primary_capability_only": True,
        "types": {str(key): value for key, value in CAPABILITY_TYPES.items()},
        "assignment": "world/v19/build.py:assign_capability",
        "difficulty_is_separate": "tools/triage_world.py; never inferred from capability",
    }
    world["version"] = 19
    world["world_id"] = "legal-agent-simulation-world-v19"
    world["lineage"] = {
        "base": str(base.relative_to(ROOT)) if base.is_relative_to(ROOT) else str(base),
        "compiler": "world/v19/build.py",
        "capabilities_added": ["checkpointed-capstones", "native-multi-turn", "superseding-instructions"],
    }
    payload = json.dumps(raw, ensure_ascii=False, separators=(",", ":")) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = out.with_suffix(out.suffix + ".tmp")
    temporary.write_text(payload, "utf-8")
    temporary.replace(out)
    report = {
        "schema_version": 1,
        "base_tasks": len(world["tasks"]) - len(pairs),
        "added": {"capstones": 5, "multi_turn": 30},
        "capstone_calls": {task["task_id"]: len(task["walk"])
                            for task, _ in pairs if task["method"] == "m6_checkpointed_capstone"},
        "load_bearing_corrections": sum(bool(task.get("pre_correction_walk")) for task, _ in pairs),
        "total_tasks": len(world["tasks"]),
        "capability_counts": {
            str(capability): sum(task["capability_type"] == capability for task in world["tasks"])
            for capability in CAPABILITY_TYPES
        },
        "unclassified_capability_tasks": sum(task.get("capability_type") is None for task in world["tasks"]),
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
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.out, args.report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
