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


def stable_int(*parts: object, digits: int = 12) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(digest[:digits], 16)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def severity_for(issue_index: int) -> str:
    return ("critical", "high", "high", "medium", "medium", "low")[issue_index % 6]


def issue_values(matter: Matter, task_index: int, issue_index: int, topic: str) -> dict[str, str]:
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
    elif dimension == 1:
        primary = f"the controlling amount is ${amount_a:,.2f}"
        secondary = f"the reconciliation and counterparty record use ${amount_b:,.2f}"
    elif dimension == 2:
        primary = f"approval is attributed to {person_a} as the sole authorized reviewer"
        secondary = f"the approval log names {person_b} and contains no entry for {person_a}"
    elif dimension == 3:
        primary = f"the item is recorded as closed without exception in {reference_a}"
        secondary = f"the later status register marks it open and escalated in {reference_b}"
    elif dimension == 4:
        primary = f"the applicable location is {matter.venue}"
        secondary = f"the implementation record assigns the obligation to {matter.jurisdiction} operations outside {matter.venue}"
    elif dimension == 5:
        primary = f"the threshold is {pct_a}% with no stated tolerance"
        secondary = f"the applied threshold is {pct_b}% and produced a different exception result"
    elif dimension == 6:
        primary = f"formal notice must use notices-{slugify(matter.client)}@example.test"
        secondary = f"the only delivery record was sent to archive-{slugify(matter.counterparty)}@example.test"
    else:
        primary = f"the governed population contains {48 + seed % 140} records through {base_date.isoformat()}"
        secondary = f"the certification covers {35 + seed % 41} records through {later_date.isoformat()}"
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
    recommendation = (
        f"Before {matter.deadline}, {action_verbs[issue_index % len(action_verbs)]}; "
        f"owner: {PEOPLE[(task_index + issue_index + 11) % len(PEOPLE)]}."
    )
    return {
        "primary_statement": primary,
        "secondary_statement": secondary,
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
    finding_context: dict[str, str] | None,
    side: str | None,
) -> dict[str, Any]:
    settings = FAMILY_SETTINGS[matter.family]
    folder = PurePosixPath(path).parent.name
    kind = RECORD_KINDS[document_index % 8]
    seed = stable_int(matter.slug, document_index)
    custodian = PEOPLE[(task_index * 3 + document_index) % len(PEOPLE)]
    reviewer = PEOPLE[(task_index + document_index * 7 + 5) % len(PEOPLE)]
    record_date = date(2024, 3, 1) + timedelta(days=seed % 720)
    cross_index = (document_index * 17 + task_index * 11 + 9) % DOCUMENT_COUNT
    cross_ref = f"CB-DOC-{task_index + 1:03d}-{cross_index + 1:03d}"
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
    return {
        "record_id": f"CB-DOC-{task_index + 1:03d}-{document_index + 1:03d}",
        "matter_number": matter.matter_number,
        "matter_title": matter.title,
        "client": matter.client,
        "counterparty": matter.counterparty,
        "jurisdiction": matter.jurisdiction,
        "venue": matter.venue,
        "deadline": matter.deadline,
        "practice_workflow": settings["label"],
        "folder": folder,
        "record_type": kind.replace("_", " "),
        "custodian": custodian,
        "reviewer": reviewer,
        "record_date": record_date.isoformat(),
        "cross_reference": cross_ref,
        "control_metric": unique_metric,
        "operative_text": signal,
        "background": (
            f"This {kind.replace('_', ' ')} was maintained for {matter.client} in connection "
            f"with {matter.title}. It concerns {matter.narrative} The producing custodian, "
            f"{custodian}, identified it as an ordinary-course record used by the "
            f"{settings['label']} team."
        ),
        "scope": (
            f"The record covers activity in {matter.jurisdiction} through {record_date.isoformat()} "
            f"and should be evaluated with {cross_ref}. It is not a complete statement of law "
            f"or a substitute for the other folders in production."
        ),
        "control_note": (
            f"Reviewer {reviewer} compared identifier {unique_metric} against the folder index. "
            f"The comparison did not evaluate facts held by other custodians, later amendments, "
            f"or records generated after the document date."
        ),
        "provenance": (
            "Synthetic CounselBench-100 benchmark evidence; all entities, people, addresses, "
            "amounts, and events are fictitious and are not legal advice."
        ),
    }


def _render_document(values: dict[str, Any], extension: str) -> str:
    if extension == "json":
        return json.dumps(
            {
                "document_control": {key: values[key] for key in (
                    "record_id", "matter_number", "record_date", "custodian", "reviewer",
                    "record_type", "cross_reference", "control_metric",
                )},
                "matter": {
                    "title": values["matter_title"], "client": values["client"],
                    "counterparty": values["counterparty"], "jurisdiction": values["jurisdiction"],
                    "venue": values["venue"], "deadline": values["deadline"],
                },
                "record": {
                    "background": values["background"], "operative_text": values["operative_text"],
                    "scope": values["scope"], "control_note": values["control_note"],
                },
                "provenance": values["provenance"],
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n"
    if extension == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["field", "value", "record_id"])
        for key in (
            "matter_number", "matter_title", "client", "counterparty", "record_date",
            "custodian", "reviewer", "cross_reference", "control_metric", "background",
            "operative_text", "scope", "control_note", "provenance",
        ):
            writer.writerow([key, values[key], values["record_id"]])
        return stream.getvalue()
    if extension == "xml":
        fields = "\n".join(
            f"  <{key}>{html.escape(str(value), quote=True)}</{key}>"
            for key, value in values.items()
        )
        return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<legal-record>\n{fields}\n</legal-record>\n"
    if extension == "html":
        rows = "\n".join(
            f"<tr><th>{html.escape(key.replace('_', ' ').title())}</th>"
            f"<td>{html.escape(str(value))}</td></tr>"
            for key, value in values.items()
        )
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html.escape(values['record_id'])}</title></head><body>"
            f"<h1>{html.escape(values['matter_title'])}</h1><table>{rows}</table></body></html>\n"
        )
    if extension == "eml":
        return (
            f"From: {slugify(values['custodian']).replace('_', '.')}@example.test\n"
            f"To: {slugify(values['reviewer']).replace('_', '.')}@example.test\n"
            f"Date: {values['record_date']} 09:30:00 -0700\n"
            f"Message-ID: <{values['record_id'].casefold()}@example.test>\n"
            f"Subject: {values['matter_number']} — {values['record_type']} / {values['folder']}\n"
            "MIME-Version: 1.0\nContent-Type: text/plain; charset=UTF-8\n\n"
            f"{values['background']}\n\nOperative record\n{values['operative_text']}\n\n"
            f"Scope and cross-reference\n{values['scope']}\n\nControl note\n{values['control_note']}\n\n"
            f"{values['provenance']}\n"
        )
    if extension == "txt":
        return (
            f"DOCUMENT CONTROL: {values['record_id']}\nMATTER: {values['matter_number']} | {values['matter_title']}\n"
            f"RECORD TYPE: {values['record_type']}\nDATE: {values['record_date']}\n"
            f"CUSTODIAN: {values['custodian']}\nREVIEWER: {values['reviewer']}\n"
            f"CROSS-REFERENCE: {values['cross_reference']}\nCONTROL METRIC: {values['control_metric']}\n\n"
            f"BACKGROUND\n{values['background']}\n\nOPERATIVE RECORD\n{values['operative_text']}\n\n"
            f"SCOPE\n{values['scope']}\n\nCONTROL NOTE\n{values['control_note']}\n\n"
            f"PROVENANCE\n{values['provenance']}\n"
        )
    return (
        f"# {values['record_type'].title()} — {values['record_id']}\n\n"
        f"| Control field | Value |\n|---|---|\n"
        f"| Matter | {values['matter_number']} — {values['matter_title']} |\n"
        f"| Client | {values['client']} |\n| Other party | {values['counterparty']} |\n"
        f"| Record date | {values['record_date']} |\n| Custodian | {values['custodian']} |\n"
        f"| Reviewer | {values['reviewer']} |\n| Cross-reference | {values['cross_reference']} |\n"
        f"| Control metric | {values['control_metric']} |\n\n"
        f"## Background\n\n{values['background']}\n\n## Operative record\n\n"
        f"{values['operative_text']}\n\n## Scope and cross-reference\n\n{values['scope']}\n\n"
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
