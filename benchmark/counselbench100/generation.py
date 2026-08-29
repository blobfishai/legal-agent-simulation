"""Deterministic, causally grounded evidence generation for CounselBench-100."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import textwrap
import zipfile
from datetime import date, timedelta
from pathlib import PurePosixPath
from typing import Any

try:
    from .catalog import FAMILY_SETTINGS, MATTERS, Matter
    from .decision_specs import DECISION_RULES, DecisionRule, validate_decision_rules
except ImportError:  # pragma: no cover - flat import in release builder
    from catalog import FAMILY_SETTINGS, MATTERS, Matter
    from decision_specs import DECISION_RULES, DecisionRule, validate_decision_rules


FIXED_FILE_TIMESTAMP = "2026-08-29T12:00:00.000Z"
RELEASE_VERSION = "3.1.0"
DOCUMENT_COUNT = 96
AGENT_VISIBLE_FILE_COUNT = DOCUMENT_COUNT + 1
PORTFOLIO_COUNT = 12
FINDING_COUNT = PORTFOLIO_COUNT  # Backward-compatible public constant.
REQUIRED_EVIDENCE_READS = 49  # Release-wide lower bound; each task varies.
MINIMUM_TOOL_CALLS = 59  # Release-wide lower bound; each task varies.
DOCUMENT_ROOT = "/workspace/documents"
OUTPUT_ROOT = "/workspace/output"


PEOPLE = (
    "Maya Ellison", "Rafael Okafor", "Nora Chen", "Dominic Alvarez",
    "Priya Raman", "Elliot Mercer", "Talia Brooks", "Jonas Feld",
    "Mei Whitaker", "Caleb Hassan", "Leona Park", "Isaac Romero",
    "Sofia Bennett", "Adrian Mensah", "Willa Novak", "Theo Laurent",
    "Amara Patel", "Henry Cho", "Nadine Flores", "Micah Sullivan",
    "Farah Ibrahim", "Owen Delgado", "Lena Varga", "Samuel Kim",
)

EVIDENCE_ROLES = (
    "identity_crosswalk",
    "operative_authority",
    "current_operations",
    "approval_and_capacity",
    "correspondence",
    "financial_or_population_support",
    "chronology_and_custody",
    "independent_counterrecord",
)

EXTENSIONS = ("md", "txt", "eml", "csv", "json", "xml", "html", "pdf")

SOURCE_SYSTEMS: dict[str, tuple[str, ...]] = {
    "corporate-ma": (
        "Intralinks VDR", "Carta capitalization ledger", "Ironclad CLM",
        "NetSuite close workbook", "Jira integration tracker", "Workday HRIS",
    ),
    "commercial-contracts": (
        "Ironclad CLM", "Salesforce contract object", "Zuora billing export",
        "ServiceNow SLA register", "Coupa supplier record", "Google Vault",
    ),
    "internal-investigations": (
        "EthicsPoint intake", "Microsoft Purview", "Concur expense ledger",
        "Okta system log", "Workday case file", "BoardVantage materials",
    ),
    "litigation-discovery": (
        "Relativity workspace", "Microsoft Purview", "Legal hold console",
        "iManage matter file", "court docket mirror", "Everlaw production log",
    ),
    "restructuring": (
        "Stretto claims register", "KERP vendor ledger", "NetSuite AP",
        "DIP budget workbook", "court docket mirror", "balloting portal",
    ),
    "real-estate": (
        "MRI lease administration", "Yardi property ledger", "title plant export",
        "Procore project file", "environmental data room", "lender portal",
    ),
    "privacy-regulatory": (
        "OneTrust data map", "ServiceNow privacy queue", "BigID deletion log",
        "Vanta control register", "vendor risk portal", "regulatory response room",
    ),
    "employment": (
        "Workday HRIS", "ADP payroll export", "EthicsPoint intake",
        "leave administration portal", "LMS completion ledger", "agency response room",
    ),
    "ip-technology": (
        "Anaqua IP register", "GitHub Enterprise audit log", "Black Duck inventory",
        "domain registrar console", "DocuSign assignment room", "lender UCC file",
    ),
    "public-company": (
        "Diligent Boards", "Workiva disclosure binder", "EDGAR filing room",
        "Equity Edge ledger", "Nasdaq compliance portal", "certification console",
    ),
}

REQUEST_OPENERS = (
    "I need a straight answer before the next partner call.",
    "The business team is asking whether it can move, and I do not want to answer from the summary deck.",
    "A late record changed the picture this morning.",
    "The client wants a decision, not another document inventory.",
    "We inherited inconsistent versions of this matter and need to settle the operating position.",
    "I am about to brief the decision makers and need the source record reconciled first.",
    "The other side has challenged our internal account of the facts.",
    "There is enough noise in this file that a name match or newest-document shortcut will be dangerous.",
    "Please take ownership of the open question before the deadline.",
    "I need to know what is proven, what we can do about it, and what is still only an evidence gap.",
)

REQUEST_CLOSES = (
    "Put the supported calls into the matter register and leave me a short note I can use with the partner.",
    "Update the matter record only where the evidence supports it, and give me the practical options for the client.",
    "Leave the defensible result in the matter workspace, including any item that must stay on hold for better evidence.",
    "I need the recommendation and the real blockers recorded before the team acts.",
    "Document the scoped result for the team and separate genuine exceptions from unresolved identity or revision questions.",
    "Give me a decision-ready note and make the corresponding matter-register entries, without guessing through missing records.",
    "Record the outcome the source hierarchy supports and explain the alternatives we should not take.",
    "Make the matter record usable by operations after your review, but do not turn ambiguity into an accusation or obligation.",
    "Capture the supported action and the remaining holds so the next reviewer can reproduce the call.",
    "Leave a concise decision record with exact source references and an owner for each supported next step.",
)


def stable_int(*parts: object, digits: int = 12) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(digest[:digits], 16)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def severity_for(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 62:
        return "high"
    if score >= 38:
        return "medium"
    return "low"


def document_paths(matter: Matter) -> list[str]:
    paths: list[str] = []
    sequence = 0
    for folder in FAMILY_SETTINGS[matter.family]["folders"]:
        for slot in range(8):
            sequence += 1
            extension = EXTENSIONS[slot]
            filename = (
                f"{sequence:03d}_{slugify(str(folder).split('_', 1)[-1])}_"
                f"source_export.{extension}"
            )
            paths.append(str(PurePosixPath(DOCUMENT_ROOT, str(folder), filename)))
    if len(paths) != DOCUMENT_COUNT:
        raise AssertionError(f"expected {DOCUMENT_COUNT} document paths")
    return paths


def _target_slots(matter: Matter, task_index: int) -> set[int]:
    count = 5 + stable_int(matter.slug, "supported-action-count") % 5
    ranked = sorted(
        range(PORTFOLIO_COUNT),
        key=lambda slot: stable_int(matter.slug, task_index, "action-rank", slot),
    )
    return set(ranked[:count])


def _dimension_facts(
    matter: Matter,
    topic: str,
    task_index: int,
    slot: int,
    *,
    trigger_met: bool,
) -> dict[str, Any]:
    seed = stable_int(matter.slug, topic, slot)
    base = date(2025, 1, 6) + timedelta(days=seed % 480)
    later = base + timedelta(days=9 + seed % 37)
    amount = 95_000 + seed % 7_800_000
    threshold = max(25_000, amount - (13_000 + seed % 240_000))
    pct = 3 + seed % 14
    observed_pct = pct + (2 + seed % 7) if trigger_met else max(0, pct - 1)
    required_person = PEOPLE[(task_index + slot * 3) % len(PEOPLE)]
    observed_person = (
        PEOPLE[(task_index + slot * 5 + 7) % len(PEOPLE)]
        if trigger_met
        else required_person
    )
    reference = f"{matter.matter_number}-R{100 + seed % 900}"
    event_reference = f"{matter.matter_number}-E{100 + (seed // 17) % 900}"
    dimension = (task_index + slot * 5) % 8

    if dimension == 0:
        observed_date = later if trigger_met else base - timedelta(days=2)
        governing = f"completion is required by {base.isoformat()} under {reference}"
        observed = f"the current event record shows completion on {observed_date.isoformat()} under {event_reference}"
        anchors = [base.isoformat(), observed_date.isoformat(), reference, event_reference]
    elif dimension == 1:
        observed_amount = amount if trigger_met else max(0, threshold - 5_000)
        governing = f"the operative cap is ${threshold:,.2f} under {reference}"
        observed = f"the matched ledger population totals ${observed_amount:,.2f} under {event_reference}"
        anchors = [f"${threshold:,.2f}", f"${observed_amount:,.2f}", reference, event_reference]
    elif dimension == 2:
        governing = f"approval must come from {required_person} under {reference}"
        observed = f"the effective approval record names {observed_person} under {event_reference}"
        anchors = [required_person, observed_person, reference, event_reference]
    elif dimension == 3:
        observed_status = "open and unresolved" if trigger_met else "closed with completion evidence"
        governing = f"an open exception blocks completion under {reference}"
        observed = f"the current status is {observed_status} under {event_reference}"
        anchors = ["open exception", observed_status, reference, event_reference]
    elif dimension == 4:
        observed_location = matter.jurisdiction if trigger_met else matter.venue
        governing = f"the permission is limited to {matter.venue} under {reference}"
        observed = f"the matched activity occurred in {observed_location} under {event_reference}"
        anchors = [matter.venue, observed_location, reference, event_reference]
    elif dimension == 5:
        governing = f"the controlling threshold is {pct}% under {reference}"
        observed = f"the independently calculated result is {observed_pct}% under {event_reference}"
        anchors = [f"{pct}%", f"{observed_pct}%", reference, event_reference]
    elif dimension == 6:
        required_address = f"notices-{slugify(matter.client)}@example.test"
        delivered_address = (
            f"archive-{slugify(matter.counterparty)}@example.test"
            if trigger_met
            else required_address
        )
        governing = f"delivery must use {required_address} under {reference}"
        observed = f"the only matched receipt used {delivered_address} under {event_reference}"
        anchors = [required_address, delivered_address, reference, event_reference]
    else:
        required_count = 72 + seed % 170
        observed_count = required_count - (9 + seed % 31) if trigger_met else required_count
        governing = f"the controlled population contains {required_count} records under {reference}"
        observed = f"the certification covers {observed_count} records under {event_reference}"
        anchors = [f"{required_count} records", f"{observed_count} records", reference, event_reference]
    return {
        "dimension": dimension,
        "governing_statement": governing,
        "observed_statement": observed,
        "fact_anchors": anchors,
        "reference": reference,
        "event_reference": event_reference,
    }


def _build_case(
    matter: Matter,
    rule: DecisionRule,
    task_index: int,
    slot: int,
    paths_by_role: dict[str, str],
    actionable_slots: set[int],
) -> dict[str, Any]:
    topics = list(FAMILY_SETTINGS[matter.family]["issues"])
    topic = str(topics[(task_index + slot * 5) % len(topics)])
    supported = slot in actionable_slots
    failure_modes = (
        "identity_ambiguous", "trigger_not_met", "authority_pending", "revision_stale"
    )
    failure_mode = None if supported else failure_modes[(task_index + slot) % 4]
    identity_exact = failure_mode != "identity_ambiguous"
    trigger_met = failure_mode != "trigger_not_met"
    authority_effective = failure_mode != "authority_pending"
    revision_current = failure_mode != "revision_stale"
    facts = _dimension_facts(matter, topic, task_index, slot, trigger_met=trigger_met)
    portfolio_key = f"CBP-{task_index + 1:03d}-{slot + 1:02d}"
    entity_id = f"ENT-{task_index + 1:03d}-{1000 + slot}"
    alternate_id = f"ENT-{task_index + 1:03d}-{2000 + slot}"
    current_revision = f"REV-{2025 + (task_index % 2)}.{1 + slot % 7}"
    referenced_revision = (
        current_revision if revision_current else f"REV-{2024 + (task_index % 2)}.{slot % 7}"
    )
    owner = PEOPLE[(task_index * 3 + slot * 7 + 5) % len(PEOPLE)]
    owner_active = authority_effective
    remaining_capacity = 1 + stable_int(matter.slug, slot, "capacity") % 6 if owner_active else 0
    due_date = (date.fromisoformat(matter.deadline) - timedelta(days=1 + slot % 9)).isoformat()
    impact_score = 30 + stable_int(matter.slug, slot, "impact") % 70
    conditions = {
        "identity_exact": identity_exact,
        "trigger_met": trigger_met,
        "authority_effective": authority_effective,
        "revision_current": revision_current,
    }
    disposition = "action" if all(conditions.values()) else "evidence_hold"
    hold_reason = {
        "identity_ambiguous": "two source records share the display identity but not the immutable entity key",
        "trigger_not_met": "the current observation does not meet the operative trigger",
        "authority_pending": "the required approval or active owner capacity is not yet effective",
        "revision_stale": "the operational record relies on a superseded control revision",
        None: "",
    }[failure_mode]
    selected_roles = list(EVIDENCE_ROLES[:4])
    extra_count = stable_int(matter.slug, slot, "extra-evidence") % 3
    ranked_extras = sorted(
        EVIDENCE_ROLES[4:],
        key=lambda role: stable_int(matter.slug, slot, "extra-rank", role),
    )
    selected_roles.extend(ranked_extras[:extra_count])
    return {
        "slot": slot,
        "portfolio_key": portfolio_key,
        "topic": topic,
        "entity_id": entity_id,
        "alternate_id": alternate_id,
        "legal_name": f"{matter.client} — {topic.title()} record {slot + 1}",
        "current_revision": current_revision,
        "referenced_revision": referenced_revision,
        "owner": owner,
        "owner_active": owner_active,
        "remaining_capacity": remaining_capacity,
        "due_date": due_date,
        "impact_score": impact_score,
        "severity": severity_for(impact_score),
        "conditions": conditions,
        "failure_mode": failure_mode,
        "hold_reason": hold_reason,
        "disposition": disposition,
        "paths_by_role": paths_by_role,
        "required_roles": selected_roles,
        "required_paths": [paths_by_role[role] for role in selected_roles],
        **facts,
    }


def derive_disposition(case: dict[str, Any]) -> str:
    conditions = case["conditions"]
    return "action" if all(bool(conditions[key]) for key in (
        "identity_exact", "trigger_met", "authority_effective", "revision_current"
    )) else "evidence_hold"


def _role_body(case: dict[str, Any], role: str, matter: Matter, rule: DecisionRule) -> str:
    if role == "identity_crosswalk":
        if case["conditions"]["identity_exact"]:
            return (
                f"Crosswalk revision {case['current_revision']} maps portfolio key {case['portfolio_key']} "
                f"and legal name {case['legal_name']} to immutable entity {case['entity_id']}. "
                "The domain, legal entity, and native system key agree; the nearby alias is excluded."
            )
        return (
            f"Portfolio key {case['portfolio_key']} is associated with both {case['entity_id']} and "
            f"{case['alternate_id']}. The display name is shared, while the domain and legal-entity "
            "fields disagree. No approved crosswalk revision resolves the collision."
        )
    if role == "operative_authority":
        revision_note = (
            f"The referenced and current revision are both {case['current_revision']}."
            if case["conditions"]["revision_current"]
            else f"Operations cites {case['referenced_revision']}, but {case['current_revision']} is the later effective revision."
        )
        return (
            f"For {case['topic']}, {case['governing_statement']}. {revision_note} "
            f"The matter-level control is: {rule.authority}"
        )
    if role == "current_operations":
        return (
            f"For immutable entity {case['entity_id']}, {case['observed_statement']}. "
            f"The operating extract cites revision {case['referenced_revision']} and portfolio key "
            f"{case['portfolio_key']}; it does not state a legal disposition."
        )
    if role == "approval_and_capacity":
        status = "active" if case["owner_active"] else "pending approval and inactive"
        return (
            f"The current responsibility roster names {case['owner']} for {case['portfolio_key']}. "
            f"Status is {status}; remaining matter capacity is {case['remaining_capacity']}. "
            f"The next internal control date is {case['due_date']}."
        )
    if role == "correspondence":
        return (
            f"The business owner asks whether {case['observed_statement']}. The counterparty points to "
            f"{case['governing_statement']}. Neither message resolves entity identity, revision priority, "
            "or approval authority; the source records must be reconciled."
        )
    if role == "financial_or_population_support":
        return (
            f"The supporting population for {case['portfolio_key']} was exported under "
            f"{case['event_reference']}. The population uses immutable entity {case['entity_id']} and "
            f"records impact-control score {case['impact_score']}; this score is an input, not a disposition."
        )
    if role == "chronology_and_custody":
        return (
            f"Custody history shows collection from {case['paths_by_role']['current_operations']} after "
            f"the operative record was fixed at {case['paths_by_role']['operative_authority']}. "
            f"Reviewer handoff preserved both versions and the identity record for {case['portfolio_key']}."
        )
    return (
        f"An independent source repeats portfolio key {case['portfolio_key']} and immutable entity "
        f"{case['entity_id']} but uses reference {case['event_reference']}. It confirms raw activity only; "
        "it neither selects a decision option nor assigns a legal consequence."
    )


def _supporting_rows(
    matter: Matter,
    case: dict[str, Any],
    role: str,
    task_index: int,
    document_index: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    start = date(2024, 4, 1) + timedelta(days=stable_int(matter.slug, document_index) % 500)
    for row_index in range(18):
        row_seed = stable_int(matter.slug, document_index, row_index)
        rows.append(
            {
                "line_id": f"{case['portfolio_key']}-{role[:3].upper()}-{row_index + 1:02d}",
                "effective_date": (start + timedelta(days=row_index * 3)).isoformat(),
                "entity_key": case["entity_id"] if row_index != 7 else case["alternate_id"],
                "revision": case["referenced_revision"] if row_index % 5 == 0 else case["current_revision"],
                "actor": PEOPLE[(task_index + document_index + row_index * 3) % len(PEOPLE)],
                "status": ("recorded", "confirmed", "pending", "superseded")[row_seed % 4],
                "metric": (
                    f"${25_000 + row_seed % 975_000:,.2f}"
                    if row_index % 3 == 0
                    else f"{1 + row_seed % 27}%"
                ),
                "note": (
                    f"{role.replace('_', ' ').title()} support row {row_index + 1} for "
                    f"{case['topic']}; retained from the native system so the reviewer can distinguish "
                    f"the exact {case['portfolio_key']} population from similarly named records."
                ),
            }
        )
    return rows


def _record_payload(
    matter: Matter,
    rule: DecisionRule,
    case: dict[str, Any],
    role: str,
    task_index: int,
    document_index: int,
    path: str,
) -> dict[str, Any]:
    seed = stable_int(matter.slug, document_index, role)
    source_systems = SOURCE_SYSTEMS[matter.family]
    source_system = source_systems[(task_index + document_index) % len(source_systems)]
    record_id = f"CB-DOC-{task_index + 1:03d}-{document_index + 1:03d}"
    record_date = date(2024, 5, 1) + timedelta(days=seed % 680)
    reviewer = PEOPLE[(task_index + document_index * 7 + 3) % len(PEOPLE)]
    custodian = PEOPLE[(task_index * 5 + document_index + 9) % len(PEOPLE)]
    body = _role_body(case, role, matter, rule)
    rows = _supporting_rows(matter, case, role, task_index, document_index)
    sections = [
        {
            "heading": "Source lineage",
            "text": (
                f"{source_system} produced native record {record_id} for {matter.matter_number}. "
                f"{custodian} owns the source population and {reviewer} recorded the collection review. "
                "The export remains separate from later legal analysis."
            ),
        },
        {
            "heading": "Business context",
            "text": (
                f"This record concerns {case['topic']} within {matter.title}. {matter.narrative} "
                f"The record addresses one part of the broader question: {rule.observation}"
            ),
        },
        {"heading": "Native record", "text": body},
        {
            "heading": "Reliance limits",
            "text": (
                f"This file supplies {role.replace('_', ' ')} evidence for {case['portfolio_key']}. "
                "It does not decide legal effect, select among candidate responses, resolve another "
                "system's entity identity, or establish that its cited revision is controlling."
            ),
        },
    ]
    chronology = [
        {
            "date": (record_date - timedelta(days=35 - step * 6)).isoformat(),
            "event": (
                "native population opened", "custodian boundary confirmed",
                "export created", "cross-system identifier checked",
                "revision retained", "matter copy collected",
            )[step],
            "actor": PEOPLE[(task_index + document_index + step * 4) % len(PEOPLE)],
            "reference": record_id if step % 2 == 0 else case["portfolio_key"],
        }
        for step in range(6)
    ]
    return {
        "record_id": record_id,
        "matter_number": matter.matter_number,
        "matter_title": matter.title,
        "client": matter.client,
        "counterparty": matter.counterparty,
        "source_system": source_system,
        "native_version": f"{1 + seed % 5}.{seed // 17 % 10}",
        "record_date": record_date.isoformat(),
        "custodian": custodian,
        "reviewer": reviewer,
        "confidentiality": (
            "Attorney work product", "Confidential legal review",
            "Restricted matter team", "Confidential source record",
        )[seed % 4],
        "portfolio_key": case["portfolio_key"],
        "subject": case["topic"],
        "evidence_role": role,
        "immutable_entity_key": case["entity_id"],
        "referenced_revision": case["referenced_revision"],
        "current_revision": case["current_revision"],
        "body": body,
        "sections": sections,
        "chronology": chronology,
        "rows": rows,
        "related_records": [
            f"CB-DOC-{task_index + 1:03d}-{((document_index + offset) % DOCUMENT_COUNT) + 1:03d}"
            for offset in (11, 29, 47, 71)
        ],
        "source_path": path,
        "provenance": (
            "Synthetic CounselBench-100 source record. All people, entities, events, amounts, "
            "and addresses are fictitious; the record is not legal advice."
        ),
    }


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _render_pdf(value: dict[str, Any]) -> str:
    """Create a deterministic, uncompressed PDF that remains text-readable via MCP.

    The official filesystem MCP exposes text reads but no PDF extraction tool.  An
    ASCII, uncompressed PDF preserves the native file contract while still letting
    the agent inspect every source line through the pinned upstream tool.
    """

    logical_lines = [
        "COUNSELBENCH SOURCE RECORD",
        f"Record: {value['record_id']}",
        f"Matter: {value['matter_number']} - {value['matter_title']}",
        f"Portfolio key: {value['portfolio_key']}",
        f"Source system: {value['source_system']}",
        f"Evidence role: {value['evidence_role']}",
        f"Immutable entity: {value['immutable_entity_key']}",
        f"Referenced revision: {value['referenced_revision']}",
        f"Current revision: {value['current_revision']}",
        f"Custodian: {value['custodian']}",
        f"Reviewer: {value['reviewer']}",
        "",
        "NATIVE RECORD",
        value["body"],
    ]
    for section in value["sections"]:
        logical_lines.extend(("", str(section["heading"]).upper(), str(section["text"])))
    logical_lines.extend(("", "NATIVE ROWS"))
    logical_lines.extend(
        " | ".join(
            str(row[key])
            for key in (
                "line_id", "effective_date", "entity_key", "revision",
                "actor", "status", "metric", "note",
            )
        )
        for row in value["rows"]
    )
    logical_lines.extend(("", "CHRONOLOGY"))
    logical_lines.extend(
        " | ".join(str(row[key]) for key in ("date", "event", "actor", "reference"))
        for row in value["chronology"]
    )
    logical_lines.extend(("", "RELATED NATIVE RECORDS", *value["related_records"], "", value["provenance"]))

    lines: list[str] = []
    for logical_line in logical_lines:
        ascii_line = str(logical_line).encode("ascii", "replace").decode("ascii")
        lines.extend(textwrap.wrap(ascii_line, width=105, replace_whitespace=False) or [""])
    pages = [lines[index : index + 62] for index in range(0, len(lines), 62)]
    font_id = 3 + len(pages) * 2
    objects: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {len(pages)} /Kids "
            f"[{' '.join(f'{3 + index * 2} 0 R' for index in range(len(pages)))}] >>"
        ),
        font_id: "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    }
    for page_index, page_lines in enumerate(pages):
        page_id = 3 + page_index * 2
        content_id = page_id + 1
        stream = "BT\n/F1 7 Tf\n36 756 Td\n9 TL\n" + "".join(
            f"({_pdf_escape(line)}) Tj\nT*\n" for line in page_lines
        ) + "ET\n"
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        objects[content_id] = f"<< /Length {len(stream.encode('ascii'))} >>\nstream\n{stream}endstream"

    output = "%PDF-1.4\n% CounselBench deterministic native source\n"
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(output.encode("ascii"))
        output += f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n"
    xref_offset = len(output.encode("ascii"))
    output += f"xref\n0 {font_id + 1}\n0000000000 65535 f \n"
    output += "".join(f"{offsets[object_id]:010d} 00000 n \n" for object_id in range(1, font_id + 1))
    output += f"trailer\n<< /Size {font_id + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    return output


def _render_xlsx_workbook(matter: Matter, cases: list[dict[str, Any]]) -> bytes:
    """Create a deterministic, parser-valid OOXML workbook without build dependencies.

    The workbook is stored without ZIP compression.  This keeps its native spreadsheet
    structure while allowing the pinned filesystem MCP's extension-agnostic text read to
    surface the underlying XML rows.  It deliberately contains only impact-population
    facts; identity, authority, current operations, and approval still have to be joined
    from independent records.
    """

    headers = (
        "portfolio_key",
        "immutable_entity",
        "impact_control_score",
        "event_reference",
        "source_revision",
        "source_population_status",
        "matter_number",
    )
    data_rows = [
        (
            case["portfolio_key"],
            case["entity_id"],
            str(case["impact_score"]),
            case["event_reference"],
            case["referenced_revision"],
            "retained source population; not a legal disposition",
            matter.matter_number,
        )
        for case in cases
    ]

    def cell(reference: str, value: str) -> str:
        return (
            f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">'
            f"{html.escape(value)}"
            "</t></is></c>"
        )

    worksheet_rows = []
    for row_number, values in enumerate((headers, *data_rows), start=1):
        cells = "".join(
            cell(f"{chr(65 + column)}{row_number}", str(value))
            for column, value in enumerate(values)
        )
        worksheet_rows.append(f'<row r="{row_number}">{cells}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:G13"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/><sheetData>'
        + "".join(worksheet_rows)
        + '</sheetData></worksheet>'
    )
    entries = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Impact population" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": worksheet,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, content.encode("utf-8"))
    return output.getvalue()


def _render_document(value: dict[str, Any], extension: str) -> str:
    if extension == "pdf":
        return _render_pdf(value)
    if extension == "json":
        return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    if extension == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["record_id", "matter_number", "portfolio_key", "row_type", "date", "key", "value", "actor", "status", "reference"]
        )
        for key in (
            "matter_title", "client", "counterparty", "source_system", "native_version",
            "record_date", "custodian", "reviewer", "subject", "evidence_role",
            "immutable_entity_key", "referenced_revision", "current_revision", "body",
        ):
            writer.writerow([
                value["record_id"], value["matter_number"], value["portfolio_key"],
                "metadata", value["record_date"], key, value[key], value["reviewer"],
                "recorded", value["record_id"],
            ])
        for row in value["rows"]:
            writer.writerow([
                value["record_id"], value["matter_number"], value["portfolio_key"],
                "source_row", row["effective_date"], row["line_id"],
                f"{row['note']} Metric {row['metric']}; revision {row['revision']}",
                row["actor"], row["status"], row["entity_key"],
            ])
        for row in value["chronology"]:
            writer.writerow([
                value["record_id"], value["matter_number"], value["portfolio_key"],
                "chronology", row["date"], row["event"], row["event"], row["actor"],
                "recorded", row["reference"],
            ])
        return stream.getvalue()

    if extension == "xml":
        sections = "\n".join(
            f"    <section heading=\"{html.escape(section['heading'], quote=True)}\">{html.escape(section['text'])}</section>"
            for section in value["sections"]
        )
        rows = "\n".join(
            "    <row id=\"{line_id}\" date=\"{effective_date}\" entity=\"{entity_key}\" revision=\"{revision}\" actor=\"{actor}\" status=\"{status}\" metric=\"{metric}\">{note}</row>".format(
                **{key: html.escape(str(item), quote=True) for key, item in row.items()}
            )
            for row in value["rows"]
        )
        chronology = "\n".join(
            "    <event date=\"{date}\" actor=\"{actor}\" reference=\"{reference}\">{event}</event>".format(
                **{key: html.escape(str(item), quote=True) for key, item in row.items()}
            )
            for row in value["chronology"]
        )
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<counsel-source-record schema-version=\"3.1\">\n"
            f"  <record-id>{html.escape(value['record_id'])}</record-id>\n"
            f"  <matter-number>{html.escape(value['matter_number'])}</matter-number>\n"
            f"  <portfolio-key>{html.escape(value['portfolio_key'])}</portfolio-key>\n"
            f"  <source-system>{html.escape(value['source_system'])}</source-system>\n"
            f"  <evidence-role>{html.escape(value['evidence_role'])}</evidence-role>\n"
            f"  <immutable-entity-key>{html.escape(value['immutable_entity_key'])}</immutable-entity-key>\n"
            f"  <referenced-revision>{html.escape(value['referenced_revision'])}</referenced-revision>\n"
            f"  <current-revision>{html.escape(value['current_revision'])}</current-revision>\n"
            f"  <native-record>{html.escape(value['body'])}</native-record>\n"
            f"  <analysis>\n{sections}\n  </analysis>\n"
            f"  <supporting-rows>\n{rows}\n  </supporting-rows>\n"
            f"  <chronology>\n{chronology}\n  </chronology>\n"
            f"  <provenance>{html.escape(value['provenance'])}</provenance>\n"
            "</counsel-source-record>\n"
        )

    row_lines = "\n".join(
        f"{row['line_id']} | {row['effective_date']} | {row['entity_key']} | {row['revision']} | "
        f"{row['actor']} | {row['status']} | {row['metric']} | {row['note']}"
        for row in value["rows"]
    )
    chronology_lines = "\n".join(
        f"{row['date']} | {row['event']} | {row['actor']} | {row['reference']}"
        for row in value["chronology"]
    )
    section_text = "\n\n".join(
        f"{section['heading'].upper()}\n{section['text']}" for section in value["sections"]
    )

    if extension == "eml":
        thread = "\n\n".join(
            (
                f"-----Original Message-----\nFrom: {row['actor']} <{slugify(row['actor'])}@example.test>\n"
                f"Sent: {row['effective_date']} 09:00:00 -0700\n"
                f"To: {value['reviewer']} <{slugify(value['reviewer'])}@example.test>\n"
                f"Subject: {value['portfolio_key']} source row {row['line_id']}\n\n"
                f"{row['note']} The native status is {row['status']} and the recorded metric is {row['metric']}."
            )
            for row in value["rows"][:8]
        )
        return (
            f"From: {value['custodian']} <{slugify(value['custodian'])}@example.test>\n"
            f"To: {value['reviewer']} <{slugify(value['reviewer'])}@example.test>\n"
            f"Date: {value['record_date']} 08:30:00 -0700\n"
            f"Message-ID: <{value['record_id'].lower()}@example.test>\n"
            f"Subject: {value['matter_number']} — {value['subject']} source export\n"
            f"X-Matter-Number: {value['matter_number']}\n"
            f"X-Portfolio-Key: {value['portfolio_key']}\n"
            f"X-Source-System: {value['source_system']}\n"
            "MIME-Version: 1.0\nContent-Type: text/plain; charset=utf-8\n\n"
            f"{value['body']}\n\n{section_text}\n\nSOURCE THREAD\n{thread}\n\n"
            f"CHRONOLOGY\n{chronology_lines}\n\n{value['provenance']}\n"
        )

    if extension == "html":
        sections = "".join(
            f"<section><h2>{html.escape(section['heading'])}</h2><p>{html.escape(section['text'])}</p></section>"
            for section in value["sections"]
        )
        rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                *(html.escape(str(row[key])) for key in (
                    "line_id", "effective_date", "entity_key", "revision", "actor", "status", "metric", "note"
                ))
            )
            for row in value["rows"]
        )
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(value['record_id'])}</title></head><body>"
            f"<h1>{html.escape(value['subject'])}</h1><dl>"
            f"<dt>Record</dt><dd>{html.escape(value['record_id'])}</dd>"
            f"<dt>Matter</dt><dd>{html.escape(value['matter_number'])}</dd>"
            f"<dt>Portfolio key</dt><dd>{html.escape(value['portfolio_key'])}</dd>"
            f"<dt>Source system</dt><dd>{html.escape(value['source_system'])}</dd>"
            f"<dt>Evidence role</dt><dd>{html.escape(value['evidence_role'])}</dd>"
            f"<dt>Entity</dt><dd>{html.escape(value['immutable_entity_key'])}</dd>"
            f"<dt>Revision</dt><dd>{html.escape(value['referenced_revision'])}</dd></dl>"
            f"<p>{html.escape(value['body'])}</p>{sections}"
            "<h2>Native rows</h2><table><thead><tr><th>ID</th><th>Date</th><th>Entity</th>"
            "<th>Revision</th><th>Actor</th><th>Status</th><th>Metric</th><th>Note</th></tr></thead>"
            f"<tbody>{rows}</tbody></table><p>{html.escape(value['provenance'])}</p></body></html>\n"
        )

    if extension == "txt":
        return (
            f"{value['confidentiality'].upper()}\n\n{value['subject'].upper()}\n"
            f"RECORD: {value['record_id']}\nMATTER: {value['matter_number']}\n"
            f"PORTFOLIO KEY: {value['portfolio_key']}\nSOURCE SYSTEM: {value['source_system']}\n"
            f"EVIDENCE ROLE: {value['evidence_role']}\nENTITY KEY: {value['immutable_entity_key']}\n"
            f"REFERENCED REVISION: {value['referenced_revision']}\nCURRENT REVISION: {value['current_revision']}\n"
            f"CUSTODIAN: {value['custodian']}\nREVIEWER: {value['reviewer']}\n\n"
            f"NATIVE RECORD\n{value['body']}\n\n{section_text}\n\n"
            f"SCHEDULE 1 — NATIVE ROWS\n{row_lines}\n\n"
            f"SCHEDULE 2 — CHRONOLOGY\n{chronology_lines}\n\nPROVENANCE\n{value['provenance']}\n"
        )

    sections = "\n\n".join(
        f"## {section['heading']}\n\n{section['text']}" for section in value["sections"]
    )
    rows = "\n".join(
        f"| {row['line_id']} | {row['effective_date']} | {row['entity_key']} | {row['revision']} | "
        f"{row['actor']} | {row['status']} | {row['metric']} | {row['note']} |"
        for row in value["rows"]
    )
    chronology = "\n".join(
        f"| {row['date']} | {row['event']} | {row['actor']} | {row['reference']} |"
        for row in value["chronology"]
    )
    return (
        f"# {value['subject'].title()} — {value['record_id']}\n\n"
        f"> {value['confidentiality']} · {value['source_system']} · native version {value['native_version']}\n\n"
        "| Control field | Value |\n|---|---|\n"
        f"| Matter | {value['matter_number']} — {value['matter_title']} |\n"
        f"| Portfolio key | {value['portfolio_key']} |\n| Evidence role | {value['evidence_role']} |\n"
        f"| Immutable entity | {value['immutable_entity_key']} |\n"
        f"| Referenced revision | {value['referenced_revision']} |\n"
        f"| Current revision | {value['current_revision']} |\n"
        f"| Custodian | {value['custodian']} |\n| Reviewer | {value['reviewer']} |\n\n"
        f"> {value['body']}\n\n{sections}\n\n"
        "## Native rows\n\n| ID | Date | Entity | Revision | Actor | Status | Metric | Note |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"{rows}\n\n## Chronology\n\n| Date | Event | Actor | Reference |\n|---|---|---|---|\n"
        f"{chronology}\n\n## Related native records\n\n"
        + "\n".join(f"- `{record}`" for record in value["related_records"])
        + f"\n\n## Provenance\n\n{value['provenance']}\n"
    )


def decision_options(matter: Matter, task_index: int) -> list[dict[str, Any]]:
    rule = DECISION_RULES[matter.slug]
    options = [
        {
            "id": f"{matter.slug}:scoped-evidence",
            "label": rule.recommended,
            "approach": (
                f"Apply the exact identity, current-state, authority, and revision test. {rule.register_action}"
            ),
            "selected": True,
        },
        {
            "id": f"{matter.slug}:shortcut",
            "label": rule.unsafe_shortcut,
            "approach": "Use a plausible summary or one source without completing the controlling joins.",
            "selected": False,
        },
        {
            "id": f"{matter.slug}:blanket-hold",
            "label": "Freeze the entire matter population",
            "approach": "Treat supported actions and genuinely ambiguous records as if they were equally unresolved.",
            "selected": False,
        },
    ]
    rotation = task_index % len(options)
    return options[rotation:] + options[:rotation]


def _action_row(case: dict[str, Any], rule: DecisionRule) -> dict[str, Any]:
    return {
        "id": f"ACT-{case['portfolio_key']}",
        "portfolio_key": case["portfolio_key"],
        "issue": case["topic"],
        "severity": case["severity"],
        "identity_id": case["entity_id"],
        "determination": (
            f"{case['governing_statement']}; {case['observed_statement']}. Identity resolves to "
            f"{case['entity_id']}, revision {case['current_revision']} is current, and {case['owner']} "
            f"is active with capacity {case['remaining_capacity']}."
        ),
        "recommended_action": f"{rule.register_action} Owner: {case['owner']}; due {case['due_date']}.",
        "owner": case["owner"],
        "due_date": case["due_date"],
        "source_paths": list(case["required_paths"]),
    }


def _hold_row(case: dict[str, Any]) -> dict[str, Any]:
    missing = {
        "identity_ambiguous": "an approved immutable entity crosswalk",
        "trigger_not_met": "a current observation that satisfies the operative trigger",
        "authority_pending": "effective approval and an active owner with remaining capacity",
        "revision_stale": "an operational record using the current effective revision",
    }[case["failure_mode"]]
    return {
        "id": f"HOLD-{case['portfolio_key']}",
        "portfolio_key": case["portfolio_key"],
        "issue": case["topic"],
        "reason": case["hold_reason"],
        "required_next_evidence": missing,
        "source_paths": list(case["required_paths"]),
    }


def _expected_outputs(
    matter: Matter,
    task_id: str,
    rule: DecisionRule,
    options: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    actions = [_action_row(case, rule) for case in cases if derive_disposition(case) == "action"]
    holds = [_hold_row(case) for case in cases if derive_disposition(case) == "evidence_hold"]
    selected = next(option for option in options if option["selected"])
    alternatives = [option["id"] for option in options if not option["selected"]]
    decision = {
        "schema_version": "counselbench.decision.v3",
        "task_id": task_id,
        "matter_number": matter.matter_number,
        "prepared_for": matter.client,
        "as_of": matter.deadline,
        "decision": {
            "question": rule.question,
            "selected_option_id": selected["id"],
            "recommendation": rule.recommended,
            "rationale": (
                f"The four-part causal test supports {len(actions)} scoped actions and leaves "
                f"{len(holds)} records on evidence hold. {rule.authority}"
            ),
            "alternatives_considered": alternatives,
        },
        "actions": actions,
        "holds": holds,
    }
    register_rows: list[dict[str, Any]] = []
    action_by_key = {row["portfolio_key"]: row for row in actions}
    hold_by_key = {row["portfolio_key"]: row for row in holds}
    for case in cases:
        common = {
            "row_id": f"REG-{case['portfolio_key']}",
            "matter_number": matter.matter_number,
            "portfolio_key": case["portfolio_key"],
            "issue": case["topic"],
            "decision_option_id": selected["id"],
        }
        if derive_disposition(case) == "action":
            action = action_by_key[case["portfolio_key"]]
            register_rows.append(
                {
                    **common,
                    "disposition": "open_action",
                    "owner": action["owner"],
                    "due_date": action["due_date"],
                    "source_paths": action["source_paths"],
                }
            )
        else:
            hold = hold_by_key[case["portfolio_key"]]
            register_rows.append(
                {
                    **common,
                    "disposition": "evidence_hold",
                    "owner": None,
                    "due_date": None,
                    "hold_reason": hold["reason"],
                    "source_paths": hold["source_paths"],
                }
            )
    register = {
        "schema_version": "counselbench.matter-register.v3",
        "task_id": task_id,
        "matter_number": matter.matter_number,
        "rows": register_rows,
    }
    lines = [
        f"# Decision note — {matter.title}", "",
        "## Recommendation", "",
        f"{rule.recommended} The reconciled record supports {len(actions)} scoped actions and "
        f"leaves {len(holds)} items on evidence hold.", "",
        f"Selected option: `{selected['id']}`.", "",
        "## Why this is the supported option", "",
        f"{rule.observation} {rule.authority}", "",
        "## Supported actions", "",
    ]
    for row in actions:
        lines.extend(
            [
                f"### {row['portfolio_key']} — {row['issue']} ({row['severity']})", "",
                row["determination"], "",
                f"Action: {row['recommended_action']}", "",
                "Sources: " + ", ".join(f"`{path}`" for path in row["source_paths"]), "",
            ]
        )
    lines.extend(["## Evidence holds", ""])
    for row in holds:
        lines.extend(
            [
                f"- **{row['portfolio_key']} — {row['issue']}**: {row['reason']}. "
                f"Next evidence: {row['required_next_evidence']}. Sources: "
                + ", ".join(f"`{path}`" for path in row["source_paths"]),
                "",
            ]
        )
    lines.extend(
        [
            "## Alternatives considered", "",
            *[
                f"- `{option['id']}` — {option['label']}: {option['approach']}"
                for option in options if not option["selected"]
            ],
            "", "## Assumptions and limits", "",
            f"This decision is limited to {task_id}, the supplied synthetic records, and the "
            f"matter state as of {matter.deadline}. Similar names, stale revisions, and pending "
            "authority are not treated as proof.", "",
        ]
    )
    return decision, register, "\n".join(lines)


def render_prompt(matter: Matter, task_index: int) -> str:
    rule = DECISION_RULES[matter.slug]
    return (
        f"{REQUEST_OPENERS[task_index % len(REQUEST_OPENERS)]} {rule.question} "
        f"{matter.narrative} The team needs the call by {matter.deadline}. "
        f"{REQUEST_CLOSES[(task_index * 3 + 1) % len(REQUEST_CLOSES)]}"
    )


def render_work_product_control(
    matter: Matter,
    task_id: str,
    options: list[dict[str, Any]],
) -> str:
    option_rows = "\n".join(
        f"- `{option['id']}` — {option['label']}: {option['approach']}"
        for option in options
    )
    return f"""

# Matter work-product protocol

Matter operations needs one decision across the twelve portfolio keys in `{task_id}`. For
each key, reconcile the immutable identity, operative authority, current operations, and
effective approval/revision before choosing a disposition. A supported action requires all
four controls. Otherwise preserve an evidence hold and state the missing control; do not
turn a similar name, a superseded revision, or a pending owner into proof.

Candidate approaches (the production does not identify the selected one):

{option_rows}

Leave exactly `/workspace/output/decision.json`, `/workspace/output/matter-register.json`,
and `/workspace/output/advice.md` through the approved filesystem tools. `decision.json`
contains the matter identity, one selected option, considered alternatives, supported
actions, and evidence holds. `matter-register.json` contains one row per portfolio key with
the matching disposition and exact source paths. `advice.md` explains the recommendation,
supported actions, holds, alternatives, and limits. Read each completed file back before
finishing. The matter date is {matter.deadline}; no external facts may be assumed.
"""


def _search_patterns(matter: Matter, rule: DecisionRule, task_index: int) -> list[str]:
    """Return the case-specific native-format discovery plan.

    The PDF search is invariant because the eighth record in every production folder is
    a native PDF source.  The remaining searches are derived from the authored matter and
    decision rule, rather than a benchmark-wide modulo template.  They are public verifier
    requirements: an agent must actually perform these searches before it can earn the
    procedure reward.
    """

    mandatory_patterns = ["**/*.pdf", "**/*.xlsx"]
    choices = (
        "**/*.eml",
        "**/*.csv",
        "**/*.json",
        "**/*.xml",
        "**/*.html",
        "**/*.txt",
        "**/*.md",
    )
    count = 4 + stable_int(
        matter.slug, rule.question, rule.authority, "native-format-search-count"
    ) % 6
    start = stable_int(matter.slug, rule.observation, "native-format-search-start") % len(choices)
    stride = (1, 2, 3, 4, 5, 6)[
        stable_int(rule.register_action, task_index, "native-format-search-stride") % 6
    ]
    ordered: list[str] = []
    cursor = start
    while len(ordered) < count - len(mandatory_patterns):
        candidate = choices[cursor % len(choices)]
        if candidate not in ordered:
            ordered.append(candidate)
        cursor += stride
        if len(ordered) < count - len(mandatory_patterns) and cursor % len(choices) == start:
            cursor += 1
    for pattern in mandatory_patterns:
        insertion = stable_int(matter.slug, pattern, "native-search-position") % (len(ordered) + 1)
        ordered.insert(insertion, pattern)
    return ordered


def reference_calls(
    task_index: int,
    required_paths: list[str],
    metadata_paths: list[str],
    search_patterns: list[str],
    path_roles: dict[str, tuple[str, str]],
    decision_text: str,
    register_text: str,
    advice_text: str,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = [
        {"name": "list_allowed_directories", "arguments": {}, "phase": "discovery"},
        {
            "name": "directory_tree",
            "arguments": {"path": DOCUMENT_ROOT, "excludePatterns": []},
            "phase": "discovery",
        },
    ]
    investigation: list[dict[str, Any]] = []
    for path in required_paths:
        portfolio_key, role = path_roles[path]
        investigation.append(
            {
                "name": "read_text_file",
                "arguments": {"path": path},
                "phase": f"evidence:{role}",
                "portfolio_key": portfolio_key,
            }
        )
    for path in metadata_paths:
        portfolio_key, role = path_roles[path]
        investigation.append(
            {
                "name": "get_file_info",
                "arguments": {"path": path},
                "phase": f"custody:{role}",
                "portfolio_key": portfolio_key,
            }
        )
    for pattern in search_patterns:
        investigation.append(
            {
                "name": "search_files",
                "arguments": {"path": DOCUMENT_ROOT, "pattern": pattern, "excludePatterns": []},
                "phase": f"targeted-search:{pattern}",
            }
        )
    investigation.sort(
        key=lambda call: stable_int(
            "counsel-reference", task_index, call["phase"],
            call["arguments"].get("path", ""), call["arguments"].get("pattern", ""),
        )
    )
    calls.extend(investigation)
    writes = [
        {
            "name": "write_file",
            "arguments": {"path": f"{OUTPUT_ROOT}/decision.json", "content": decision_text},
            "phase": "state-transition:decision",
        },
        {
            "name": "write_file",
            "arguments": {"path": f"{OUTPUT_ROOT}/matter-register.json", "content": register_text},
            "phase": "state-transition:matter-register",
        },
        {
            "name": "write_file",
            "arguments": {"path": f"{OUTPUT_ROOT}/advice.md", "content": advice_text},
            "phase": "state-transition:advice",
        },
    ]
    rotation = task_index % 3
    writes = writes[rotation:] + writes[:rotation]
    calls.extend(writes)
    readback_order = list(reversed(writes)) if task_index % 2 else list(writes)
    calls.extend(
        {
            "name": "read_text_file",
            "arguments": {"path": call["arguments"]["path"]},
            "phase": call["phase"].replace("state-transition", "postwrite-readback"),
        }
        for call in readback_order
    )
    return calls


def rubric_criteria(material: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(category: str, identifier: str, description: str) -> None:
        rows.append({"id": f"{category}.{identifier}", "category": category, "description": description})

    add("investigation", "discover_production", "Inventory the production and use targeted searches to locate records across native formats.")
    add("investigation", "read_before_write", "Complete every task-specific identity, authority, operations, and approval read before the first state transition.")
    add("investigation", "custody_before_write", "Inspect designated source metadata before relying on those records.")
    add("decision", "selected_option", f"Select the supported option {material['expected_decision']['decision']['selected_option_id']!r} after applying the four-part test.")
    add("decision", "alternatives", "Identify both rejected approaches and explain why a one-source shortcut and a blanket hold are wrong.")
    for case in material["cases"]:
        key = case["portfolio_key"]
        paths = case["paths_by_role"]
        add("investigation", f"{key}.identity", f"Resolve {key} using the immutable identity record {paths['identity_crosswalk']} rather than its display name.")
        add("investigation", f"{key}.authority", f"Read the operative rule and revision in {paths['operative_authority']} for {case['topic']}.")
        add("investigation", f"{key}.operations", f"Compare the current observation in {paths['current_operations']} to the operative trigger.")
        add("investigation", f"{key}.approval", f"Verify effective approval, owner status, and capacity in {paths['approval_and_capacity']}.")
        add(
            "decision",
            f"{key}.branch",
            f"After joining those records, classify {key} as {case['disposition']!r}; the controlling branch is "
            + ("all four conditions are satisfied." if case["disposition"] == "action" else f"{case['hold_reason']}.")
        )
        add("state", f"{key}.register", f"Create the exact task-scoped matter-register row for {key} and do not change another portfolio key.")
    add("state", "exact_decision", "Write the exact selected option, supported action population, evidence-hold population, facts, owners, deadlines, and citations.")
    add("state", "exact_register", "Create one exact register row per portfolio key with no extra, missing, or modified row.")
    add("state", "write_scope_containment", "Leave only the three approved deliverables and perform no extra state-changing write.")
    add("state", "postwrite_readback", "Read back decision.json, matter-register.json, and advice.md after their final writes.")
    add("answer", "decision_note", "Explain the selected recommendation, supported actions, holds, alternatives, and limitations with exact source anchors.")
    return rows


def _material_quality(
    cases: list[dict[str, Any]],
    documents: dict[str, str],
    expected: dict[str, Any],
) -> dict[str, bool]:
    joined = "\n".join(documents.values()).casefold()
    answer_phrases = [
        *[row["determination"].casefold() for row in expected["actions"]],
        *[row["recommended_action"].casefold() for row in expected["actions"]],
        *[row["reason"].casefold() for row in expected["holds"]],
    ]
    forbidden_schema = (
        "finding_id", "record_role", "control_severity", "remediation_owner",
        '"selected_option_id"', '"disposition": "open_action"',
        '"disposition": "evidence_hold"',
    )
    return {
        "causality_recomputed": all(derive_disposition(case) == case["disposition"] for case in cases),
        "action_and_hold_mix": bool(expected["actions"]) and bool(expected["holds"]),
        "no_answer_shaped_schema_in_evidence": not any(token in joined for token in forbidden_schema),
        "no_precomputed_outcome_text_in_evidence": not any(phrase and phrase in joined for phrase in answer_phrases),
        "all_four_core_roles_split": all(
            len({case["paths_by_role"][role] for role in EVIDENCE_ROLES[:4]}) == 4
            for case in cases
        ),
        "every_case_has_independent_evidence": all(len(case["required_paths"]) >= 4 for case in cases),
    }


def build_material(matter: Matter, task_index: int) -> dict[str, Any]:
    validate_decision_rules({item.slug for item in MATTERS})
    rule = DECISION_RULES[matter.slug]
    paths = document_paths(matter)
    task_id = f"cb100-{task_index + 1:03d}-{matter.slug}"
    paths_by_slot: dict[int, dict[str, str]] = {slot: {} for slot in range(PORTFOLIO_COUNT)}
    path_roles: dict[str, tuple[str, str]] = {}
    for document_index, path in enumerate(paths):
        slot = document_index % PORTFOLIO_COUNT
        role = EVIDENCE_ROLES[document_index // PORTFOLIO_COUNT]
        paths_by_slot[slot][role] = path
    actionable_slots = _target_slots(matter, task_index)
    cases = [
        _build_case(matter, rule, task_index, slot, paths_by_slot[slot], actionable_slots)
        for slot in range(PORTFOLIO_COUNT)
    ]
    for case in cases:
        for role, path in case["paths_by_role"].items():
            path_roles[path] = (case["portfolio_key"], role)

    workbook_folder = str(FAMILY_SETTINGS[matter.family]["folders"][-1])
    workbook_path = str(
        PurePosixPath(
            DOCUMENT_ROOT,
            workbook_folder,
            f"097_{slugify(matter.slug)}_impact_population.xlsx",
        )
    )
    path_roles[workbook_path] = ("portfolio", "financial_or_population_support")
    for case in cases:
        case["required_roles"].append("portfolio_impact_workbook")
        case["required_paths"].append(workbook_path)

    documents: dict[str, str] = {}
    for document_index, path in enumerate(paths):
        slot = document_index % PORTFOLIO_COUNT
        role = EVIDENCE_ROLES[document_index // PORTFOLIO_COUNT]
        payload = _record_payload(
            matter, rule, cases[slot], role, task_index, document_index, path
        )
        documents[path] = _render_document(payload, PurePosixPath(path).suffix[1:])
    binary_documents = {workbook_path: _render_xlsx_workbook(matter, cases)}

    options = decision_options(matter, task_index)
    protocol_path = next(
        path for path in reversed(paths) if PurePosixPath(path).suffix == ".md"
    )
    documents[protocol_path] += render_work_product_control(matter, task_id, options)
    expected_decision, expected_register, advice = _expected_outputs(
        matter, task_id, rule, options, cases
    )
    decision_text = json.dumps(expected_decision, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    register_text = json.dumps(expected_register, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    required_paths = sorted(
        {protocol_path, *(path for case in cases for path in case["required_paths"])}
    )
    metadata_count = 4 + stable_int(
        matter.slug, rule.observation, rule.authority, "custody-check-count"
    ) % 9
    metadata_paths = [workbook_path, *sorted(
        (path for path in required_paths if path != workbook_path),
        key=lambda path: (
            0 if PurePosixPath(path).suffix == ".pdf" else 1,
            0 if path_roles[path][1] in {"operative_authority", "approval_and_capacity"} else 1,
            stable_int(matter.slug, rule.register_action, "metadata", path),
        ),
    )][:metadata_count]
    search_patterns = _search_patterns(matter, rule, task_index)
    calls = reference_calls(
        task_index, required_paths, metadata_paths, search_patterns, path_roles,
        decision_text, register_text, advice,
    )
    material: dict[str, Any] = {
        "task_id": task_id,
        "documents": documents,
        "binary_documents": binary_documents,
        "all_document_paths": [*paths, workbook_path],
        "required_document_paths": required_paths,
        "metadata_check_paths": metadata_paths,
        "search_patterns": search_patterns,
        "path_roles": path_roles,
        "cases": cases,
        "expected_decision": expected_decision,
        "expected_register": expected_register,
        "expected_advice": advice,
        "decision_text": decision_text,
        "register_text": register_text,
        "instruction": render_prompt(matter, task_index),
        "decision_options": options,
        "decision_rule": {
            "question": rule.question,
            "observation": rule.observation,
            "authority": rule.authority,
            "register_action": rule.register_action,
        },
        "reference_calls": calls,
        "minimum_tool_calls": len(calls),
        "action_count": len(expected_decision["actions"]),
        "hold_count": len(expected_decision["holds"]),
        "semantic_signature": [
            f"{call['phase']}:{call.get('portfolio_key', '')}" for call in calls
        ],
    }
    material["quality_gates"] = _material_quality(cases, documents, expected_decision)
    material["rubric_criteria"] = rubric_criteria(material)
    if not all(material["quality_gates"].values()):
        failed = sorted(name for name, passed in material["quality_gates"].items() if not passed)
        raise AssertionError(f"{task_id} material quality gates failed: {failed}")
    if len(required_paths) < REQUIRED_EVIDENCE_READS:
        raise AssertionError(f"{task_id} has only {len(required_paths)} required evidence reads")
    if len(calls) < MINIMUM_TOOL_CALLS:
        raise AssertionError(f"{task_id} has only {len(calls)} reference calls")
    return material
