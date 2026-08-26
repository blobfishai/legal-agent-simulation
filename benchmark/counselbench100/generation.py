"""Deterministic seeded-evidence generation for CounselBench-100."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
from datetime import date, timedelta
from pathlib import PurePosixPath
from typing import Any

from catalog import FAMILY_SETTINGS, Matter


FIXED_FILE_TIMESTAMP = "2026-08-25T12:00:00.000Z"
DOCUMENT_COUNT = 96
FINDING_COUNT = 16
MINIMUM_TOOL_CALLS = 109
DOCUMENT_ROOT = "/workspace/documents"
OUTPUT_ROOT = "/workspace/output"


PEOPLE = [
    "Maya Ellison", "Rafael Okafor", "Nora Chen", "Dominic Alvarez",
    "Priya Raman", "Elliot Mercer", "Talia Brooks", "Jonas Feld",
    "Mei Whitaker", "Caleb Hassan", "Leona Park", "Isaac Romero",
    "Sofia Bennett", "Adrian Mensah", "Willa Novak", "Theo Laurent",
    "Amara Patel", "Henry Cho", "Nadine Flores", "Micah Sullivan",
    "Farah Ibrahim", "Owen Delgado", "Lena Varga", "Samuel Kim",
]

RECORD_KINDS = [
    "control_register", "executed_instrument", "correspondence", "ledger_export",
    "review_memorandum", "formal_notice", "officer_certificate", "status_report",
]

EXTENSIONS = ["md", "txt", "eml", "csv", "json", "xml", "html", "md"]

OPENERS = [
    "The partner responsible for this matter needs a defensible decision record before the next client call.",
    "A late document production changed the factual picture, and the matter team needs the entire record reconciled from first principles.",
    "The client has asked for a board-ready risk assessment supported by a source-level tracker rather than a narrative-only summary.",
    "Several workstreams have maintained separate versions of the truth; your assignment is to produce one auditable legal view.",
    "Outside counsel inherited this file after turnover on the client team and must validate every operative record before advising.",
    "The upcoming deadline leaves no room for unsupported assumptions, so every conclusion must trace to the supplied production.",
    "A counterparty challenged the client's internal summary, making cross-document reconciliation and precise citations essential.",
    "The supervising attorney wants an exception-focused review that still demonstrates complete coverage of the data room.",
    "This matter will be reviewed by legal, finance, and compliance stakeholders who need a single source-grounded output.",
    "The record contains amendments, exports, and correspondence from different custodians; reconcile them into an actionable counsel work product.",
]

LENSES = [
    "Prioritize conflicts between signed instruments and later operational records.",
    "Separate confirmed exceptions from items that merely require follow-up.",
    "Treat dates, notice mechanics, approval evidence, and numerical reconciliations as independent controls.",
    "Distinguish a missing document from an affirmative contradiction in the documents that are present.",
    "Evaluate both legal consequence and the practical owner needed to cure each exception.",
    "Give controlling documents precedence only when the record supports that hierarchy.",
    "Flag cross-folder dependencies that would be invisible in a single-document review.",
    "Preserve the difference between the client's position, the counterparty's position, and an objective record conflict.",
    "Use the production as of the stated deadline; do not assume facts outside the supplied files.",
    "Write for a supervising lawyer who will spot-check source paths and exact values.",
]

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

RECORD_PURPOSES = {
    "control_register": "maintain the matter team's issue population, source lineage, review status, and accountable owner",
    "executed_instrument": "preserve the operative language, execution history, defined terms, and signature authority",
    "correspondence": "capture custodian communications, escalation history, instructions, and contemporaneous business understanding",
    "ledger_export": "reconcile system-of-record entries against the signed or approved source and expose population-level variance",
    "review_memorandum": "record the reviewer’s analysis, assumptions, unresolved questions, and recommended disposition",
    "formal_notice": "document the asserted obligation, notice mechanics, delivery evidence, cure period, and requested response",
    "officer_certificate": "state the certifying person’s knowledge, supporting review, exceptions, and reliance limitations",
    "status_report": "summarize milestones, dependencies, risk status, decision owners, and the next reporting cycle",
}

SECTION_VARIANTS = {
    "lineage": (
        "The producing team exported this record from {source_system} and retained the native identifier {record_id}. {custodian} confirmed the export boundary, while {reviewer} performed the legal-control review. The file has not been normalized to resolve differences with {cross_reference}.",
        "This copy was collected from {source_system} under matter hold {matter_number}. Its lineage runs from {custodian}, as producing custodian, to {reviewer}, as reviewing lawyer. The related record {cross_reference} remains a separate source of truth and was not merged into this document.",
        "Matter operations catalogued the record in {source_system} using identifier {record_id}. The chain of custody identifies {custodian} as source owner and {reviewer} as the most recent reviewer. Any inconsistency with {cross_reference} must be reconciled rather than silently overwritten.",
    ),
    "workstream": (
        "The {workstream} workstream sits within {workflow}. The team is tracking {related_issues} because decisions in this file may affect the deadline and the position taken with {counterparty}. {narrative}",
        "For this {workstream} review, legal and business stakeholders are using the record to evaluate {related_issues}. The file is part of {workflow} and should be read against the stated decision deadline. {narrative}",
        "The operational context is the {workstream} portion of {workflow}. Reviewers identified dependencies involving {related_issues}; those dependencies matter to the client’s position concerning {counterparty}. {narrative}",
    ),
    "review": (
        "The reviewer tested internal consistency, execution or approval evidence, status history, and the cited cross-reference. The review did not assume that a later system entry controls an earlier signed record. Open points remain assigned through the action register below.",
        "Review procedures included source identification, a comparison to the folder index, validation of the accountable owner, and a check for later amendments or operational entries. The conclusion is deliberately bounded to the produced record and its stated cross-reference.",
        "The legal-control check compared the record’s native value with the matter index and the identified related file. Conflicting custodial accounts, amendments outside the production, and post-date events were not resolved by inference and remain subject to documented follow-up.",
    ),
    "limitations": (
        "This record is one component of the production and should not be treated as a complete statement of the governing agreement, policy, ledger, or law. Dates reflect the fixed synthetic matter timeline; references to approval or closure describe the source record rather than an independent legal conclusion.",
        "The file is responsive evidence, not a standalone legal opinion. It does not establish facts held only by other custodians, waive the need to review amendments, or determine priority among competing instruments. The complete production remains necessary to reach a final conclusion.",
        "Reliance is limited to the document as produced. The record does not incorporate unproduced attachments, oral explanations, or later events, and its administrative status should not be confused with a legal determination about the underlying obligation.",
    ),
}

ROLE_TITLES = (
    "matter lead", "business owner", "records custodian", "finance reviewer",
    "compliance reviewer", "outside counsel liaison", "operations lead", "control owner",
)

ACTION_STATUSES = ("open", "in review", "awaiting evidence", "owner confirmed", "escalated")


def stable_int(*parts: object, digits: int = 12) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(digest[:digits], 16)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def severity_for(issue_index: int) -> str:
    return ("critical", "high", "high", "medium", "medium", "low")[issue_index % 6]


def issue_values(matter: Matter, task_index: int, issue_index: int, topic: str) -> dict[str, Any]:
    seed = stable_int(matter.slug, topic, issue_index)
    base_date = date(2025, 1, 3) + timedelta(days=(seed % 420))
    later_date = base_date + timedelta(days=7 + seed % 41)
    amount_a = 175_000 + (seed % 7_400_000)
    amount_b = amount_a + 11_500 + (seed % 310_000)
    pct_a = 2 + seed % 14
    pct_b = pct_a + 2 + seed % 6
    person_a = PEOPLE[(task_index + issue_index * 3) % len(PEOPLE)]
    person_b = PEOPLE[(task_index * 2 + issue_index * 5 + 7) % len(PEOPLE)]
    reference_a = f"{matter.matter_number}-{chr(65 + issue_index % 26)}{100 + seed % 900}"
    reference_b = f"{matter.matter_number}-{chr(65 + (issue_index + 9) % 26)}{100 + (seed // 13) % 900}"
    dimension = issue_index % 8
    if dimension == 0:
        primary = f"the operative date is {base_date.isoformat()} under control reference {reference_a}"
        secondary = f"the acknowledged date is {later_date.isoformat()} under response reference {reference_b}"
        fact_anchors = [base_date.isoformat(), reference_a, later_date.isoformat(), reference_b]
    elif dimension == 1:
        primary = f"the controlling amount is ${amount_a:,.2f}"
        secondary = f"the reconciliation and counterparty record use ${amount_b:,.2f}"
        fact_anchors = [f"${amount_a:,.2f}", f"${amount_b:,.2f}"]
    elif dimension == 2:
        primary = f"approval is attributed to {person_a} as the sole authorized reviewer"
        secondary = f"the approval log names {person_b} and contains no entry for {person_a}"
        fact_anchors = [person_a, person_b]
    elif dimension == 3:
        primary = f"the item is recorded as closed without exception in {reference_a}"
        secondary = f"the later status register marks it open and escalated in {reference_b}"
        fact_anchors = ["closed without exception", reference_a, "open and escalated", reference_b]
    elif dimension == 4:
        primary = f"the applicable location is {matter.venue}"
        secondary = f"the implementation record assigns the obligation to {matter.jurisdiction} operations outside {matter.venue}"
        fact_anchors = [matter.venue, matter.jurisdiction]
    elif dimension == 5:
        primary = f"the threshold is {pct_a}% with no stated tolerance"
        secondary = f"the applied threshold is {pct_b}% and produced a different exception result"
        fact_anchors = [f"{pct_a}%", f"{pct_b}%"]
    elif dimension == 6:
        required_address = f"notices-{slugify(matter.client)}@example.test"
        delivery_address = f"archive-{slugify(matter.counterparty)}@example.test"
        primary = f"formal notice must use {required_address}"
        secondary = f"the only delivery record was sent to {delivery_address}"
        fact_anchors = [required_address, delivery_address]
    else:
        primary_count = 48 + seed % 140
        secondary_count = 35 + seed % 41
        primary = f"the governed population contains {primary_count} records through {base_date.isoformat()}"
        secondary = f"the certification covers {secondary_count} records through {later_date.isoformat()}"
        fact_anchors = [
            f"{primary_count} records", base_date.isoformat(),
            f"{secondary_count} records", later_date.isoformat(),
        ]
    determination = (
        f"The records do not reconcile for {topic}: one source states {primary}, while the "
        f"corroborating source states {secondary}."
    )
    action_verbs = [
        "obtain a signed ratification and update the controlling register",
        "recalculate the exposure and preserve the supporting ledger",
        "secure written consent from the authorized decision-maker",
        "issue a corrective notice using the contractually operative method",
        "escalate the conflict to the responsible legal and business owners",
        "document the governing interpretation before the deadline",
        "place the affected population on hold pending reconciliation",
        "amend the closing or response checklist with a dated cure item",
    ]
    owner = PEOPLE[(task_index + issue_index + 11) % len(PEOPLE)]
    recommendation = (
        f"Before {matter.deadline}, {action_verbs[issue_index % len(action_verbs)]}; "
        f"owner: {owner}."
    )
    return {
        "finding_id": f"F-{issue_index + 1:02d}",
        "issue": topic,
        "severity": severity_for(issue_index),
        "owner": owner,
        "response_due": matter.deadline,
        "primary_statement": primary,
        "secondary_statement": secondary,
        "fact_anchors": fact_anchors,
        "action_anchors": [matter.deadline, owner],
        "determination": determination,
        "recommendation": recommendation,
    }


def document_paths(matter: Matter) -> list[str]:
    settings = FAMILY_SETTINGS[matter.family]
    folders = list(settings["folders"])
    paths: list[str] = []
    sequence = 0
    for folder in folders:
        for slot in range(8):
            sequence += 1
            kind = RECORD_KINDS[slot]
            extension = EXTENSIONS[slot]
            filename = f"{sequence:03d}_{slugify(folder.split('_', 1)[-1])}_{kind}.{extension}"
            paths.append(str(PurePosixPath(DOCUMENT_ROOT, folder, filename)))
    if len(paths) != DOCUMENT_COUNT:
        raise AssertionError(paths)
    return paths


def _issue_assignments() -> tuple[dict[int, int], dict[int, int]]:
    primary = {issue_index * 3: issue_index for issue_index in range(FINDING_COUNT)}
    corroborating = {48 + issue_index * 3: issue_index for issue_index in range(FINDING_COUNT)}
    return primary, corroborating


def _record_prose(
    matter: Matter,
    task_index: int,
    document_index: int,
    path: str,
    finding_context: dict[str, Any] | None,
    side: str | None,
) -> dict[str, Any]:
    settings = FAMILY_SETTINGS[matter.family]
    folder = PurePosixPath(path).parent.name
    workstream = folder.split("_", 1)[-1].replace("_", " ")
    kind = RECORD_KINDS[document_index % 8]
    seed = stable_int(matter.slug, document_index)
    custodian = PEOPLE[(task_index * 3 + document_index) % len(PEOPLE)]
    reviewer = PEOPLE[(task_index + document_index * 7 + 5) % len(PEOPLE)]
    record_date = date(2024, 3, 1) + timedelta(days=seed % 720)
    deadline = date.fromisoformat(matter.deadline)
    cross_index = (document_index * 17 + task_index * 11 + 9) % DOCUMENT_COUNT
    cross_ref = f"CB-DOC-{task_index + 1:03d}-{cross_index + 1:03d}"
    record_id = f"CB-DOC-{task_index + 1:03d}-{document_index + 1:03d}"
    source_systems = SOURCE_SYSTEMS[matter.family]
    source_system = source_systems[(document_index + task_index) % len(source_systems)]
    related_topics = [
        str(settings["issues"][(document_index + step * 5 + task_index) % FINDING_COUNT])
        for step in range(3)
    ]
    signal = None
    if finding_context:
        signal = (
            finding_context["primary_statement"]
            if side == "primary"
            else finding_context["secondary_statement"]
        )
    else:
        controls = [
            "No variance was recorded after the named reviewer compared the source ledger to the signed control record.",
            "The custodian confirmed that this export is complete for the stated period, subject to the cross-reference below.",
            "The operative record and its implementation evidence use the same identifier, date, and responsible owner.",
            "This file documents ordinary-course activity and does not supersede a signed instrument elsewhere in the production.",
            "The status remained unchanged through the review date, and no exception notice appears in this record.",
            "A second-level reviewer closed the control after matching the population total to the underlying entries.",
            "The record preserves the original value and separately identifies the later administrative annotation.",
            "The file is responsive background material; it supplies context but does not create an independent obligation.",
        ]
        signal = controls[document_index % len(controls)]
    unique_metric = 10_000 + seed % 890_000
    review_question = finding_context["issue"] if finding_context else "context only"
    finding_id = finding_context["finding_id"] if finding_context else "none"
    record_role = side if side else "context"
    control_severity = finding_context["severity"] if finding_context else "none"
    remediation_owner = finding_context["owner"] if finding_context else "none"
    response_due = finding_context["response_due"] if finding_context else "none"
    record_status = (
        "reviewed — source conflict identified"
        if side == "primary"
        else "reviewed — variance confirmed"
        if side == "corroborating"
        else ("reviewed — no independent exception" if document_index % 2 else "indexed — responsive context")
    )
    confidentiality = (
        "Attorney work product",
        "Confidential — legal review",
        "Confidential — matter team",
        "Restricted — need to know",
    )[(seed // 17) % 4]
    purpose = RECORD_PURPOSES[kind]
    related_issue_text = ", ".join(related_topics[:-1]) + f", and {related_topics[-1]}"
    template_values = {
        "source_system": source_system,
        "record_id": record_id,
        "custodian": custodian,
        "reviewer": reviewer,
        "cross_reference": cross_ref,
        "matter_number": matter.matter_number,
        "workstream": workstream,
        "workflow": settings["label"],
        "related_issues": related_issue_text,
        "counterparty": matter.counterparty,
        "narrative": matter.narrative,
    }
    lineage = SECTION_VARIANTS["lineage"][seed % 3].format(**template_values)
    workstream_context = SECTION_VARIANTS["workstream"][(seed // 3) % 3].format(
        **template_values
    )
    review_text = SECTION_VARIANTS["review"][(seed // 7) % 3].format(**template_values)
    limitations = SECTION_VARIANTS["limitations"][(seed // 11) % 3]
    classification_text = (
        f"The record-control overlay classifies this as the {side} source for {finding_id} "
        f"({review_question}) at {control_severity} severity. The assigned remediation owner is "
        f"{remediation_owner}, with response due {response_due}."
        if finding_context
        else "The record-control overlay classifies this file as context only. It may explain the matter history or test a cross-reference, but it is not an independent finding."
    )
    analysis_sections = [
        {
            "heading": "Purpose and audience",
            "text": (
                f"This {kind.replace('_', ' ')} supports the {workstream} workstream for "
                f"{matter.client}. Its purpose is to {purpose}. The intended audience is the "
                f"{settings['label']} matter team, including legal, finance, compliance, and the "
                "business owner responsible for the next decision."
            ),
        },
        {"heading": "Record lineage and custody", "text": lineage},
        {"heading": "Matter and workstream context", "text": workstream_context},
        {
            "heading": "Operative content",
            "text": (
                f"The operative entry states that {signal}. {classification_text} The entry is "
                "preserved as written because the benchmark requires reconciliation between sources, "
                "not silent correction of a document that appears incomplete or inconsistent."
            ),
        },
        {
            "heading": "Reviewer analysis",
            "text": (
                f"{review_text} Reviewer {reviewer} recorded status “{record_status}” and linked the "
                f"file to {cross_ref}. The control metric {unique_metric} is an administrative "
                "population identifier, not a damages estimate or a statement of materiality."
            ),
        },
        {
            "heading": "Dependencies and reliance limits",
            "text": (
                f"The record should be read with the {related_issue_text} materials and the files in "
                f"the adjacent workstreams. {limitations}"
            ),
        },
    ]

    chronology_dates = [
        record_date - timedelta(days=35 + seed % 17),
        record_date - timedelta(days=16 + seed % 9),
        record_date - timedelta(days=4 + seed % 5),
        record_date,
        min(deadline, record_date + timedelta(days=21 + seed % 18)),
    ]
    chronology_events = (
        "Source population opened for collection",
        "Custodian confirmed system and date boundary",
        "Matter team completed first-level comparison",
        "Legal reviewer recorded the current disposition",
        "Assigned owner scheduled the next control response",
    )
    chronology = [
        {
            "date": event_date.isoformat(),
            "event": chronology_events[index],
            "actor": PEOPLE[(task_index + document_index + index * 3) % len(PEOPLE)],
            "evidence": record_id if index in (0, 3) else cross_ref,
        }
        for index, event_date in enumerate(chronology_dates)
    ]
    participants = [
        {
            "name": PEOPLE[(task_index * 2 + document_index + index * 5) % len(PEOPLE)],
            "role": ROLE_TITLES[(document_index + index) % len(ROLE_TITLES)],
            "responsibility": (
                "source completeness", "business interpretation", "legal review", "remediation tracking"
            )[index],
        }
        for index in range(4)
    ]
    related_records = [
        {
            "record_id": f"CB-DOC-{task_index + 1:03d}-{((document_index + offset) % DOCUMENT_COUNT) + 1:03d}",
            "relationship": relationship,
            "workstream": str(settings["folders"][((document_index + offset) % DOCUMENT_COUNT) // 8]).split("_", 1)[-1].replace("_", " "),
        }
        for offset, relationship in (
            (7, "same-cycle source"), (19, "implementation evidence"),
            (37, "independent control record"), (53, "later reconciliation record"),
        )
    ]
    action_dates = [deadline - timedelta(days=14), deadline - timedelta(days=7), deadline]
    action_texts = [
        (
            finding_context["recommendation"]
            if finding_context
            else f"Confirm that {cross_ref} does not change the context-only classification."
        ),
        f"Preserve the native {source_system} export and document any replacement record.",
        f"Report the disposition to the {workstream} workstream lead before the matter deadline.",
    ]
    action_register = [
        {
            "action_id": f"A-{document_index + 1:03d}-{index + 1}",
            "action": action,
            "owner": (
                remediation_owner if finding_context and index == 0
                else PEOPLE[(task_index + document_index + index * 7 + 9) % len(PEOPLE)]
            ),
            "due_date": action_dates[index].isoformat(),
            "status": ACTION_STATUSES[(document_index + index + task_index) % len(ACTION_STATUSES)],
        }
        for index, action in enumerate(action_texts)
    ]
    data_rows = []
    for row_index in range(12):
        row_seed = stable_int(matter.slug, document_index, row_index)
        data_rows.append(
            {
                "line_id": f"{record_id}-L{row_index + 1:02d}",
                "category": related_topics[row_index % len(related_topics)],
                "description": (
                    signal if row_index == 0
                    else f"{workstream.title()} control observation {row_index + 1}; retained for reconciliation with {cross_ref}."
                ),
                "effective_date": (record_date - timedelta(days=row_index * 3 + row_seed % 4)).isoformat(),
                "owner": PEOPLE[(task_index + document_index + row_index * 2) % len(PEOPLE)],
                "status": ACTION_STATUSES[(row_seed // 13) % len(ACTION_STATUSES)],
                "metric": f"${25_000 + row_seed % 875_000:,.2f}" if row_index % 3 == 0 else f"{1 + row_seed % 24}%",
                "evidence_reference": record_id if row_index % 2 == 0 else cross_ref,
            }
        )
    return {
        "record_id": record_id,
        "matter_number": matter.matter_number,
        "matter_title": matter.title,
        "client": matter.client,
        "counterparty": matter.counterparty,
        "jurisdiction": matter.jurisdiction,
        "venue": matter.venue,
        "deadline": matter.deadline,
        "practice_workflow": settings["label"],
        "folder": folder,
        "workstream": workstream,
        "record_type": kind.replace("_", " "),
        "source_system": source_system,
        "native_version": f"{1 + seed % 4}.{seed // 29 % 10}",
        "record_status": record_status,
        "confidentiality": confidentiality,
        "custodian": custodian,
        "reviewer": reviewer,
        "record_date": record_date.isoformat(),
        "cross_reference": cross_ref,
        "control_metric": unique_metric,
        "review_question": review_question,
        "finding_id": finding_id,
        "record_role": record_role,
        "control_severity": control_severity,
        "remediation_owner": remediation_owner,
        "response_due": response_due,
        "operative_text": signal,
        "background": (
            f"This {kind.replace('_', ' ')} was maintained for {matter.client} in connection "
            f"with {matter.title}. {matter.narrative} The {workstream} team used the record to "
            f"{purpose}. Producing custodian {custodian} identified it as an ordinary-course "
            f"record from {source_system}; reviewer {reviewer} preserved the source wording and "
            "separately recorded the legal-control disposition."
        ),
        "scope": (
            f"The record covers activity in {matter.jurisdiction} through {record_date.isoformat()} "
            f"and should be evaluated with {cross_ref}, the four related records listed below, "
            f"and the complete {workstream} folder. It is not a complete statement of law or a "
            "substitute for the other folders in production."
        ),
        "control_note": (
            f"Reviewer {reviewer} compared identifier {unique_metric} against the folder index, "
            f"the native {source_system} entry, and {cross_ref}. The comparison preserved each "
            "source independently and did not infer facts held by other custodians, unproduced "
            "amendments, oral explanations, or records generated after the document date."
        ),
        "analysis_sections": analysis_sections,
        "chronology": chronology,
        "participants": participants,
        "related_records": related_records,
        "action_register": action_register,
        "data_rows": data_rows,
        "provenance": (
            "Synthetic CounselBench-100 benchmark evidence; all entities, people, addresses, "
            "amounts, and events are fictitious and are not legal advice."
        ),
    }


def _render_document(values: dict[str, Any], extension: str) -> str:
    control_keys = (
        "record_id", "matter_number", "record_date", "record_type", "folder",
        "workstream", "source_system", "native_version", "record_status",
        "confidentiality", "custodian", "reviewer", "cross_reference",
        "control_metric", "review_question", "finding_id", "record_role",
        "control_severity", "remediation_owner", "response_due",
    )
    matter_keys = (
        "matter_title", "client", "counterparty", "jurisdiction", "venue",
        "deadline", "practice_workflow",
    )

    def plain_sections() -> str:
        return "\n\n".join(
            f"{index}. {section['heading'].upper()}\n{section['text']}"
            for index, section in enumerate(values["analysis_sections"], 1)
        )

    def plain_chronology() -> str:
        return "\n".join(
            f"- {row['date']} | {row['event']} | {row['actor']} | {row['evidence']}"
            for row in values["chronology"]
        )

    def plain_actions() -> str:
        return "\n".join(
            f"- {row['action_id']} | {row['status']} | {row['owner']} | {row['due_date']} | {row['action']}"
            for row in values["action_register"]
        )

    if extension == "json":
        return json.dumps(
            {
                "document_control": {key: values[key] for key in control_keys},
                "matter": {key: values[key] for key in matter_keys},
                "record": {
                    "background": values["background"], "operative_text": values["operative_text"],
                    "scope": values["scope"], "control_note": values["control_note"],
                    "analysis_sections": values["analysis_sections"],
                },
                "chronology": values["chronology"],
                "participants": values["participants"],
                "related_records": values["related_records"],
                "action_register": values["action_register"],
                "supporting_rows": values["data_rows"],
                "provenance": values["provenance"],
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n"
    if extension == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        columns = [
            "record_id", "matter_number", "record_date", "row_type", "section",
            "key", "value", "owner", "status", "reference",
        ]
        writer.writerow(columns)
        for key in (*control_keys, *matter_keys, "background", "operative_text", "scope", "control_note"):
            writer.writerow([
                values["record_id"], values["matter_number"], values["record_date"],
                "metadata", "document_control", key, values[key], "", "", values["cross_reference"],
            ])
        for index, section in enumerate(values["analysis_sections"], 1):
            writer.writerow([
                values["record_id"], values["matter_number"], values["record_date"],
                "analysis", f"section_{index}", section["heading"], section["text"],
                values["reviewer"], values["record_status"], values["cross_reference"],
            ])
        for row in values["data_rows"]:
            writer.writerow([
                values["record_id"], values["matter_number"], row["effective_date"],
                "ledger_entry", row["category"], row["line_id"],
                f"{row['description']} Metric: {row['metric']}", row["owner"], row["status"],
                row["evidence_reference"],
            ])
        for row in values["chronology"]:
            writer.writerow([
                values["record_id"], values["matter_number"], row["date"],
                "chronology", values["workstream"], row["event"], row["event"],
                row["actor"], "recorded", row["evidence"],
            ])
        for row in values["action_register"]:
            writer.writerow([
                values["record_id"], values["matter_number"], row["due_date"],
                "action", values["workstream"], row["action_id"], row["action"],
                row["owner"], row["status"], values["cross_reference"],
            ])
        writer.writerow([
            values["record_id"], values["matter_number"], values["record_date"],
            "provenance", "release", "synthetic_notice", values["provenance"],
            values["reviewer"], "final", values["record_id"],
        ])
        return stream.getvalue()
    if extension == "xml":
        control = "\n".join(
            f"    <{key}>{html.escape(str(values[key]), quote=True)}</{key}>"
            for key in control_keys
        )
        matter = "\n".join(
            f"    <{key}>{html.escape(str(values[key]), quote=True)}</{key}>"
            for key in matter_keys
        )
        sections = "\n".join(
            "    <section index=\"{index}\" heading=\"{heading}\">{text}</section>".format(
                index=index,
                heading=html.escape(section["heading"], quote=True),
                text=html.escape(section["text"]),
            )
            for index, section in enumerate(values["analysis_sections"], 1)
        )
        chronology = "\n".join(
            "    <event date=\"{date}\" actor=\"{actor}\" evidence=\"{evidence}\">{event}</event>".format(
                **{key: html.escape(str(value), quote=True) for key, value in row.items()}
            )
            for row in values["chronology"]
        )
        actions = "\n".join(
            "    <action id=\"{action_id}\" owner=\"{owner}\" due=\"{due_date}\" status=\"{status}\">{action}</action>".format(
                **{key: html.escape(str(value), quote=True) for key, value in row.items()}
            )
            for row in values["action_register"]
        )
        return (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<legal-record schema-version=\"1.1\">\n"
            f"  <document-control>\n{control}\n  </document-control>\n"
            f"  <matter>\n{matter}\n  </matter>\n"
            f"  <background>{html.escape(values['background'])}</background>\n"
            f"  <operative-record>{html.escape(values['operative_text'])}</operative-record>\n"
            f"  <analysis>\n{sections}\n  </analysis>\n"
            f"  <chronology>\n{chronology}\n  </chronology>\n"
            f"  <action-register>\n{actions}\n  </action-register>\n"
            f"  <scope>{html.escape(values['scope'])}</scope>\n"
            f"  <control-note>{html.escape(values['control_note'])}</control-note>\n"
            f"  <provenance>{html.escape(values['provenance'])}</provenance>\n"
            "</legal-record>\n"
        )
    if extension == "html":
        control_rows = "\n".join(
            f"<tr><th>{html.escape(key.replace('_', ' ').title())}</th>"
            f"<td>{html.escape(str(values[key]))}</td></tr>"
            for key in (*control_keys, *matter_keys)
        )
        sections = "\n".join(
            f"<section><h2>{index}. {html.escape(section['heading'])}</h2>"
            f"<p>{html.escape(section['text'])}</p></section>"
            for index, section in enumerate(values["analysis_sections"], 1)
        )
        chronology_rows = "\n".join(
            f"<tr><td>{html.escape(row['date'])}</td><td>{html.escape(row['event'])}</td>"
            f"<td>{html.escape(row['actor'])}</td><td>{html.escape(row['evidence'])}</td></tr>"
            for row in values["chronology"]
        )
        action_rows = "\n".join(
            f"<tr><td>{html.escape(row['action_id'])}</td><td>{html.escape(row['action'])}</td>"
            f"<td>{html.escape(row['owner'])}</td><td>{html.escape(row['due_date'])}</td>"
            f"<td>{html.escape(row['status'])}</td></tr>"
            for row in values["action_register"]
        )
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(values['record_id'])}</title>"
            "<style>body{font-family:Georgia,serif;max-width:960px;margin:40px auto;line-height:1.5;color:#17242a}"
            "table{width:100%;border-collapse:collapse;margin:18px 0 30px}th,td{border:1px solid #aeb8bc;padding:8px;vertical-align:top}"
            "th{text-align:left;background:#eef2f2}header{border-bottom:3px solid #183b46;margin-bottom:28px}.notice{padding:12px;background:#f4eee4}</style>"
            "</head><body>"
            f"<header><p>{html.escape(values['confidentiality'])}</p><h1>{html.escape(values['matter_title'])}</h1>"
            f"<p>{html.escape(values['record_type'].title())} · {html.escape(values['record_id'])}</p></header>"
            f"<p class=\"notice\"><strong>Operative content:</strong> {html.escape(values['operative_text'])}</p>"
            f"<table><tbody>{control_rows}</tbody></table>{sections}"
            "<h2>Chronology</h2><table><thead><tr><th>Date</th><th>Event</th><th>Actor</th><th>Evidence</th></tr></thead>"
            f"<tbody>{chronology_rows}</tbody></table>"
            "<h2>Action register</h2><table><thead><tr><th>ID</th><th>Action</th><th>Owner</th><th>Due</th><th>Status</th></tr></thead>"
            f"<tbody>{action_rows}</tbody></table>"
            f"<h2>Scope</h2><p>{html.escape(values['scope'])}</p>"
            f"<h2>Certification note</h2><p>{html.escape(values['control_note'])}</p>"
            f"<footer><p>{html.escape(values['provenance'])}</p></footer></body></html>\n"
        )
    if extension == "eml":
        participants = ", ".join(row["name"] for row in values["participants"][1:])
        return (
            f"From: {slugify(values['custodian']).replace('_', '.')}@example.test\n"
            f"To: {slugify(values['reviewer']).replace('_', '.')}@example.test\n"
            f"Cc: matter-team-{slugify(values['client'])}@example.test\n"
            f"Date: {values['record_date']} 09:30:00 -0700\n"
            f"Message-ID: <{values['record_id'].casefold()}@example.test>\n"
            f"In-Reply-To: <{values['cross_reference'].casefold()}@example.test>\n"
            f"Subject: {values['matter_number']} — {values['record_type']} / {values['folder']}\n"
            f"X-Source-System: {values['source_system']}\n"
            f"X-Record-Status: {values['record_status']}\n"
            f"X-Confidentiality: {values['confidentiality']}\n"
            f"X-Review-Question: {values['review_question']}\n"
            f"X-Finding-ID: {values['finding_id']}\n"
            f"X-Record-Role: {values['record_role']}\n"
            f"X-Control-Severity: {values['control_severity']}\n"
            f"X-Remediation-Owner: {values['remediation_owner']}\n"
            f"X-Response-Due: {values['response_due']}\n"
            "MIME-Version: 1.0\nContent-Type: text/plain; charset=UTF-8\n\n"
            f"{values['reviewer'].split()[0]},\n\n"
            f"I completed the {values['workstream']} review for {values['matter_title']}. "
            f"The working group ({participants}) should use the record-control block below when updating the matter tracker.\n\n"
            f"{values['background']}\n\nOPERATIVE RECORD\n{values['operative_text']}\n\n"
            f"{plain_sections()}\n\nCHRONOLOGY\n{plain_chronology()}\n\nACTION REGISTER\n{plain_actions()}\n\n"
            f"SCOPE AND CROSS-REFERENCE\n{values['scope']}\n\nCONTROL NOTE\n{values['control_note']}\n\n"
            f"Regards,\n{values['custodian']}\n{values['workstream'].title()} records custodian\n\n"
            "-----Original Message-----\n"
            f"From: {slugify(values['reviewer']).replace('_', '.')}@example.test\n"
            f"Sent: {values['chronology'][1]['date']} 16:10:00 -0700\n"
            f"To: {slugify(values['custodian']).replace('_', '.')}@example.test\n"
            f"Subject: RE: {values['matter_number']} / {values['cross_reference']}\n\n"
            f"Please preserve the native {values['source_system']} entry, confirm the date boundary, and do not resolve any difference with {values['cross_reference']} outside the written matter record.\n\n"
            f"{values['provenance']}\n"
        )
    if extension == "txt":
        return (
            f"{values['confidentiality'].upper()}\n\n"
            f"{values['record_type'].upper()}\n{values['matter_title'].upper()}\n\n"
            f"DOCUMENT CONTROL: {values['record_id']}\nMATTER: {values['matter_number']} | {values['matter_title']}\n"
            f"RECORD TYPE: {values['record_type']}\nDATE: {values['record_date']}\nSOURCE SYSTEM: {values['source_system']}\n"
            f"NATIVE VERSION: {values['native_version']}\nSTATUS: {values['record_status']}\n"
            f"CUSTODIAN: {values['custodian']}\nREVIEWER: {values['reviewer']}\n"
            f"CROSS-REFERENCE: {values['cross_reference']}\nCONTROL METRIC: {values['control_metric']}\n\n"
            f"REVIEW QUESTION: {values['review_question']}\nFINDING ID: {values['finding_id']}\n"
            f"RECORD ROLE: {values['record_role']}\nCONTROL SEVERITY: {values['control_severity']}\n"
            f"REMEDIATION OWNER: {values['remediation_owner']}\nRESPONSE DUE: {values['response_due']}\n\n"
            f"RECITALS\n\nA. {values['background']}\n\n"
            f"B. The parties and matter team intend to preserve the source hierarchy and the decision record for {values['matter_number']}.\n\n"
            f"OPERATIVE RECORD\n{values['operative_text']}\n\n{plain_sections()}\n\n"
            f"SCHEDULE 1 — RECORD CHRONOLOGY\n{plain_chronology()}\n\n"
            f"SCHEDULE 2 — ACTION REGISTER\n{plain_actions()}\n\n"
            f"SCOPE\n{values['scope']}\n\nCONTROL NOTE\n{values['control_note']}\n\n"
            f"ACKNOWLEDGED FOR RECORD-CONTROL PURPOSES\n\nBy: {values['custodian']}\nRole: Producing custodian\n"
            f"Reviewed by: {values['reviewer']}\nRecord date: {values['record_date']}\n\n"
            f"PROVENANCE\n{values['provenance']}\n"
        )
    chronology_rows = "\n".join(
        f"| {row['date']} | {row['event']} | {row['actor']} | {row['evidence']} |"
        for row in values["chronology"]
    )
    participant_rows = "\n".join(
        f"| {row['name']} | {row['role']} | {row['responsibility']} |"
        for row in values["participants"]
    )
    action_rows = "\n".join(
        f"| {row['action_id']} | {row['action']} | {row['owner']} | {row['due_date']} | {row['status']} |"
        for row in values["action_register"]
    )
    analysis = "\n\n".join(
        f"## {index}. {section['heading']}\n\n{section['text']}"
        for index, section in enumerate(values["analysis_sections"], 1)
    )
    related = "\n".join(
        f"- `{row['record_id']}` — {row['relationship']} ({row['workstream']})"
        for row in values["related_records"]
    )
    return (
        f"# {values['record_type'].title()} — {values['record_id']}\n\n"
        f"> {values['confidentiality']} · {values['record_status']} · native version {values['native_version']}\n\n"
        f"| Control field | Value |\n|---|---|\n"
        f"| Matter | {values['matter_number']} — {values['matter_title']} |\n"
        f"| Client | {values['client']} |\n| Other party | {values['counterparty']} |\n"
        f"| Record date | {values['record_date']} |\n| Custodian | {values['custodian']} |\n"
        f"| Reviewer | {values['reviewer']} |\n| Cross-reference | {values['cross_reference']} |\n"
        f"| Source system | {values['source_system']} |\n| Workstream | {values['workstream']} |\n"
        f"| Control metric | {values['control_metric']} |\n"
        f"| Review question | {values['review_question']} |\n| Finding ID | {values['finding_id']} |\n"
        f"| Record role | {values['record_role']} |\n| Control severity | {values['control_severity']} |\n"
        f"| Remediation owner | {values['remediation_owner']} |\n| Response due | {values['response_due']} |\n\n"
        f"## Executive record summary\n\n{values['background']}\n\n"
        f"> **Operative record:** {values['operative_text']}\n\n{analysis}\n\n"
        "## Chronology\n\n| Date | Event | Actor | Evidence |\n|---|---|---|---|\n"
        f"{chronology_rows}\n\n## Participants\n\n| Name | Role | Responsibility |\n|---|---|---|\n"
        f"{participant_rows}\n\n## Related records\n\n{related}\n\n"
        "## Action register\n\n| ID | Action | Owner | Due | Status |\n|---|---|---|---|---|\n"
        f"{action_rows}\n\n## Scope and cross-reference\n\n{values['scope']}\n\n"
        f"## Control note\n\n{values['control_note']}\n\n## Provenance\n\n{values['provenance']}\n"
    )


def build_material(matter: Matter, task_index: int) -> dict[str, Any]:
    settings = FAMILY_SETTINGS[matter.family]
    topics = list(settings["issues"])
    paths = document_paths(matter)
    primary_assignment, corroborating_assignment = _issue_assignments()
    issue_details = [
        issue_values(matter, task_index, issue_index, topic)
        for issue_index, topic in enumerate(topics)
    ]
    documents: dict[str, str] = {}
    document_values: dict[str, dict[str, Any]] = {}
    for document_index, absolute_path in enumerate(paths):
        side = None
        detail = None
        if document_index in primary_assignment:
            side = "primary"
            detail = issue_details[primary_assignment[document_index]]
        elif document_index in corroborating_assignment:
            side = "corroborating"
            detail = issue_details[corroborating_assignment[document_index]]
        values = _record_prose(
            matter, task_index, document_index, absolute_path, detail, side
        )
        document_values[absolute_path] = values
        documents[absolute_path] = _render_document(values, PurePosixPath(absolute_path).suffix[1:])

    findings: list[dict[str, str]] = []
    for issue_index, (topic, detail) in enumerate(zip(topics, issue_details, strict=True)):
        primary_path = paths[issue_index * 3]
        corroborating_path = paths[48 + issue_index * 3]
        findings.append(
            {
                "id": f"F-{issue_index + 1:02d}",
                "severity": severity_for(issue_index),
                "issue": topic,
                "primary_source": primary_path,
                "corroborating_source": corroborating_path,
                "determination": detail["determination"],
                "recommended_action": detail["recommendation"],
            }
        )

    scoring_findings: list[dict[str, Any]] = []
    for finding, detail in zip(findings, issue_details, strict=True):
        allowed_fact_text = json.dumps(
            [
                document_values[finding["primary_source"]],
                document_values[finding["corroborating_source"]],
            ],
            ensure_ascii=False,
            sort_keys=True,
        )
        scoring_findings.append(
            {
                **finding,
                "fact_anchors": detail["fact_anchors"],
                "action_anchors": detail["action_anchors"],
                "allowed_fact_text": allowed_fact_text,
            }
        )

    task_id = f"cb100-{task_index + 1:03d}-{matter.slug}"
    expected_findings = {
        "schema_version": "1.0",
        "task_id": task_id,
        "matter_number": matter.matter_number,
        "prepared_for": matter.client,
        "as_of": matter.deadline,
        "findings": findings,
    }
    memo = render_memo(matter, task_id, findings)
    prompt = render_prompt(matter, task_index, task_id, paths, topics)
    return {
        "task_id": task_id,
        "documents": documents,
        "required_document_paths": paths,
        "metadata_check_paths": [paths[index * 3] for index in range(8)],
        "expected_findings": expected_findings,
        "scoring_findings": scoring_findings,
        "expected_findings_text": json.dumps(expected_findings, indent=2, ensure_ascii=False) + "\n",
        "expected_memo": memo,
        "instruction": prompt,
        "topics": topics,
    }


def render_memo(matter: Matter, task_id: str, findings: list[dict[str, str]]) -> str:
    lines = [
        f"# Counsel advice — {matter.title}", "",
        "## Executive assessment", "",
        f"For {matter.client} matter {matter.matter_number}, the review identified "
        f"{len(findings)} source-supported exceptions requiring action before {matter.deadline}. "
        f"The assessment concerns {matter.counterparty} and the supplied record for {matter.jurisdiction}.", "",
        "## Method and record coverage", "",
        f"The review inventoried and read all {DOCUMENT_COUNT} production files, searched the email exports, "
        "and checked metadata for the designated chain-of-custody sample. Conclusions are limited to the "
        "synthetic production supplied for this benchmark matter.", "",
        "## Findings", "",
    ]
    for finding in findings:
        lines.extend(
            [
                f"### {finding['id']} — {finding['issue']} ({finding['severity']})", "",
                finding["determination"], "",
                f"Primary source: `{finding['primary_source']}`", "",
                f"Corroborating source: `{finding['corroborating_source']}`", "",
                f"Recommended action: {finding['recommended_action']}", "",
            ]
        )
    lines.extend(
        [
            "## Recommended next actions", "",
            "Sequence the critical and high findings first, assign the named owners, preserve the cited records, "
            "and document any resolution in the controlling matter register before the stated deadline.", "",
            "## Assumptions and limitations", "",
            f"This analysis is confined to task {task_id} and the supplied synthetic evidence. It does not rely "
            "on external facts, does not resolve disputed law, and is not legal advice for a real person or entity.", "",
        ]
    )
    return "\n".join(lines)


def render_prompt(
    matter: Matter,
    task_index: int,
    task_id: str,
    paths: list[str],
    topics: list[str],
) -> str:
    settings = FAMILY_SETTINGS[matter.family]
    metadata_paths = [paths[index * 3] for index in range(8)]
    topic_lines = "\n".join(f"- {topic}" for topic in topics)
    metadata_lines = "\n".join(f"- `{path}`" for path in metadata_paths)
    return f"""# {matter.title}

You are acting as {settings['role']} for {matter.client}. {OPENERS[task_index % 10]}

Matter: {matter.matter_number}
Other party or authority: {matter.counterparty}
Jurisdiction: {matter.jurisdiction}
Venue or forum: {matter.venue}
Decision deadline: {matter.deadline}

## Assignment

{matter.narrative} {LENSES[task_index % 10]}

Reconcile the complete seeded production and prepare an exception tracker plus a concise counsel memo. The data room contains {DOCUMENT_COUNT} text-native legal and business records in 12 folders. Some facts can be evaluated only by comparing a primary record in one folder with a later or independently maintained record elsewhere. Do not rely on filenames alone, do not assume that a later record controls, and do not use facts outside this production.

Finding-bearing records identify the review question, stable finding ID, record role, severity, remediation owner, and response due date in their record-control metadata. Preserve those values exactly. Records labeled `context only` are responsive background, not independent findings.

Your review scope includes these independently tested legal and control questions:

{topic_lines}

## Required review procedure

Use the `io.github.modelcontextprotocol/server-filesystem` MCP tools exposed by the environment.

1. Call `list_allowed_directories` and confirm the available roots.
2. Call `directory_tree` on `{DOCUMENT_ROOT}` to inventory the complete production.
3. Call `search_files` on `{DOCUMENT_ROOT}` with pattern `**/*.eml`.
4. Call `read_text_file` separately, without `head` or `tail`, for every one of the {DOCUMENT_COUNT} files. Bulk reads are intentionally unavailable because the work product must have file-level provenance.
5. Call `get_file_info` for each of these eight chain-of-custody sample records:

{metadata_lines}

6. Use `write_file` to create both final deliverables under `{OUTPUT_ROOT}`.

An accepted trajectory therefore contains at least {MINIMUM_TOOL_CALLS} successful MCP tool calls. The verifier checks the call trace and final filesystem state; merely stating that records were reviewed is insufficient.

## Deliverables

Create exactly these two files and no others:

- `{OUTPUT_ROOT}/findings.json`
- `{OUTPUT_ROOT}/advice.md`

`findings.json` must be valid JSON with this exact top-level shape:

```json
{{
  "schema_version": "1.0",
  "task_id": "{task_id}",
  "matter_number": "{matter.matter_number}",
  "prepared_for": "{matter.client}",
  "as_of": "{matter.deadline}",
  "findings": [
    {{
      "id": "F-01",
      "severity": "critical|high|medium|low",
      "issue": "short issue label",
      "primary_source": "/workspace/documents/...",
      "corroborating_source": "/workspace/documents/...",
      "determination": "precise reconciliation of the conflicting facts",
      "recommended_action": "dated, owned next step"
    }}
  ]
}}
```

Use one row per confirmed exception, stable IDs beginning at `F-01`, exact absolute source paths, and exact dates, amounts, names, statuses, thresholds, or counts from the cited records.

`advice.md` must contain these headings: `Executive assessment`, `Method and record coverage`, `Findings`, `Recommended next actions`, and `Assumptions and limitations`. Address every JSON finding in the memo with its ID, issue, severity, both source paths, determination, and recommended action. Keep confirmed contradictions distinct from assumptions or unresolved legal questions.

All facts in this task are synthetic. The work product is benchmark output, not legal advice.
"""
