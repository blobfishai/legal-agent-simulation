"""Task specifications for the v20 real-world consumer-protection families.

Each spec is declarative; world/v20/build.py compiles it into a world task
(walk + reference_args) and a VCode verifier.  Reference deliverable bodies
are built from world/v20/content.py so every pinned assertion string is
present in the oracle's reference output by construction (build-time checked).
"""
from __future__ import annotations

from world.v20 import content as C

AUTHOR = "consumer-protection@simulated-firm.example"


# ---------------------------------------------------------------------------
# assertion helpers (compiled verbatim into v19-dialect assertions)
# ---------------------------------------------------------------------------

def doc_pin(name: str, doc_name: str, needle: str) -> dict:
    return {"kind": "new_row", "name": name, "table": "dm_documents", "count": 1,
            "matches": {"name": doc_name, "body": {"contains": needle}}}


def doc_absent(name: str, needle: str, doc_name_contains: str | None = None) -> dict:
    matches: dict = {"body": {"contains": needle}}
    if doc_name_contains:
        matches["name"] = {"contains": doc_name_contains}
    return {"kind": "absent_new_row", "name": name, "table": "dm_documents",
            "matches": matches}


def note_pin(name: str, subject: str, needle: str) -> dict:
    return {"kind": "new_row", "name": name, "table": "pm_notes", "count": 1,
            "matches": {"subject": subject, "detail": {"contains": needle}}}


def note_absent(name: str, needle: str) -> dict:
    return {"kind": "absent_new_row", "name": name, "table": "pm_notes",
            "matches": {"detail": {"contains": needle}}}


def cal_pin(name: str, date: str, summary_contains: str) -> dict:
    return {"kind": "new_row", "name": name, "table": "pm_calendar_entries", "count": 1,
            "matches": {"kind": "deadline", "start_at": {"startswith": date},
                        "summary": {"contains": summary_contains}}}


def cal_absent(name: str, date: str) -> dict:
    return {"kind": "absent_new_row", "name": name, "table": "pm_calendar_entries",
            "matches": {"start_at": {"startswith": date}}}


def _matrix_row(j: str) -> str:
    if j in C.ITEM_PRICING:
        e = C.ITEM_PRICING[j]
        return (f"{j} | statute=YES | cite={e['cite']} | remedy={e['remedy_phrase']} "
                f"| action=in-store remediation required")
    return (f"{j} | statute=NO | cite=none | remedy={C.UDAP_ROW_PHRASE} "
            f"| action=receipt footer update only")


def _cal_args(matter_id: int, summary: str, date: str) -> dict:
    return {"matter_id": matter_id, "summary": summary, "kind": "deadline",
            "start_at": f"{date}T17:00:00Z", "end_at": f"{date}T17:30:00Z"}


def _note_args(matter_id: int, subject: str, detail: str) -> dict:
    return {"matter_id": matter_id, "author_user_id": 1, "subject": subject,
            "detail": detail}


def _doc_args(folder_id: int, workspace_id: int, name: str, doc_class: str, body: str) -> dict:
    return {"folder_id": folder_id, "workspace_id": workspace_id, "name": name,
            "doc_class": doc_class, "author": AUTHOR, "body": body}


ROW_GRAMMAR = ("one line per jurisdiction, exactly: "
               "XX | statute=YES/NO | cite=<cite or none> | remedy=<remedy_phrase "
               "copied verbatim from the memo pack> | action=<required action>")


def build_specs(matters: dict, folders: dict) -> list[dict]:
    """matters: matter_key -> matter_id; folders: matter_key -> (folder_id, ws_id)."""
    specs: list[dict] = []

    def M(k: str) -> int:
        return matters[k]

    def F(k: str) -> tuple[int, int]:
        return folders[k]

    # ------------------------------------------------------------------ 001
    fid, wid = F("delgado")
    matrix_body = (
        "51-JURISDICTION PRICE-ACCURACY COMPLIANCE MATRIX - DELGADO SECTION 7.3 (SIMULATED)\n"
        f"Client: {C.CLIENT_A}. Source: executed settlement + region memo pack (the "
        "superseded draft matrix v1 was disregarded).\n\n"
        + "\n".join(_matrix_row(j) for j in C.JURISDICTIONS)
        + f"\n\nJurisdiction rows: 51 (50 states + DC). Puerto Rico excluded per Section 7.3."
    )
    summary_detail = ("statute_yes_count=6; statute_jurisdictions=CA, CT, MA, MI, NH, RI; "
                      f"survey_due={C.SURVEY_DUE}; jurisdiction_rows=51; puerto_rico_included=NO")
    specs.append({
        "task_id": "task_v20_cp_001",
        "slug": "delgado-51-jurisdiction-survey-matrix",
        "capability": "rule_application",
        "difficulty": "high",
        "matter_key": "delgado",
        "search_query": "state-pricing-law-memo-pack",
        "reads": ["settlement_a", "partner_instructions", "pricing_memo_r1",
                  "pricing_memo_r2", "pricing_memo_r3", "pricing_memo_r4",
                  "pricing_memo_r5", "pricing_memo_r6", "draft_matrix_trap"],
        "writes": [
            ("documents_create", _doc_args(fid, wid,
             "delgado-51-jurisdiction-compliance-matrix.docx", "MATRIX", matrix_body)),
            ("notes_create", _note_args(M("delgado"), "delgado-survey-summary", summary_detail)),
        ],
        "assertions": [
            doc_pin("mi_row_and_statute", "delgado-51-jurisdiction-compliance-matrix.docx", "MI | statute=YES"),
            doc_pin("mi_bounty_capped_at_5", "delgado-51-jurisdiction-compliance-matrix.docx", C.ITEM_PRICING["MI"]["remedy_phrase"]),
            doc_pin("ma_scope_food_only", "delgado-51-jurisdiction-compliance-matrix.docx", "food stores and food departments only"),
            doc_pin("ct_free_item_remedy", "delgado-51-jurisdiction-compliance-matrix.docx", C.ITEM_PRICING["CT"]["remedy_phrase"]),
            doc_pin("ca_no_private_bounty", "delgado-51-jurisdiction-compliance-matrix.docx", "private bounty = NO"),
            doc_pin("wy_no_statute", "delgado-51-jurisdiction-compliance-matrix.docx", "WY | statute=NO"),
            doc_pin("ny_statewide_no", "delgado-51-jurisdiction-compliance-matrix.docx", "NY | statute=NO"),
            note_pin("summary_six_statute_states", "delgado-survey-summary", "statute_yes_count=6"),
            note_pin("summary_survey_due", "delgado-survey-summary", f"survey_due={C.SURVEY_DUE}"),
            note_pin("summary_row_count", "delgado-survey-summary", "jurisdiction_rows=51"),
            note_pin("summary_pr_excluded", "delgado-survey-summary", "puerto_rico_included=NO"),
            doc_absent("trap_wy_not_yes", "WY | statute=YES"),
            doc_absent("trap_mi_not_10_dollar", "maximum $10.00"),
            doc_absent("trap_ma_not_all_retail", "all retail stores"),
        ],
        "tables": ["dm_documents", "pm_notes"],
        "prompt": (
            f"Matter: Halvorsen Market Group - Delgado Settlement Compliance (matter {M('delgado')}). "
            "Complete the Section 7.3 pricing-law survey. Locate and read IN FULL, via "
            "MatterVault full-text search and download: the executed settlement agreement, "
            "the partner instructions, all six region memo packs "
            "(state-pricing-law-memo-pack-region-1 through -6), and the superseded draft "
            "matrix v1 (so you know what it got wrong - it must not be relied on). Then "
            f"file the compliance matrix as a new MatterVault document named exactly "
            f"'delgado-51-jurisdiction-compliance-matrix.docx' (folder_id {fid}, "
            f"workspace_id {wid}, doc_class MATRIX): {ROW_GRAMMAR}. Cover all 50 states "
            "plus DC - exactly 51 rows, and NO Puerto Rico row. Copy every remedy_phrase "
            "verbatim from the memo pack; correct the draft's errors from the memos, "
            "never the reverse. Finally record a matter note with subject exactly "
            "'delgado-survey-summary' and detail exactly in the form "
            f"'{summary_detail.replace(C.SURVEY_DUE, '<computed Section 7.3 due date YYYY-MM-DD>')}' "
            "- compute the due date yourself from the settlement's Effective Date and "
            "Section 7.6 counting rule."
        ),
    })

    # ------------------------------------------------------------------ 002
    rollout_detail = (f"remediation_stores=317; puerto_rico_stores_excluded={C.PR_STORES}; "
                      "statute_jurisdictions=CA, CT, MA, MI, NH, RI")
    specs.append({
        "task_id": "task_v20_cp_002",
        "slug": "delgado-remediation-rollout-and-deadline",
        "capability": "computation",
        "difficulty": "medium",
        "matter_key": "delgado",
        "search_query": "store-footprint-by-state",
        "reads": ["settlement_a", "store_footprint", "pricing_memo_r1",
                  "pricing_memo_r3", "pricing_memo_r4", "pricing_memo_r5"],
        "writes": [
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Section 7.3 survey and remediation plan due - Delgado settlement", C.SURVEY_DUE)),
            ("notes_create", _note_args(M("delgado"), "delgado-remediation-rollout", rollout_detail)),
        ],
        "assertions": [
            cal_pin("survey_deadline_calendared", C.SURVEY_DUE, "Section 7.3"),
            note_pin("rollout_store_count", "delgado-remediation-rollout", "remediation_stores=317"),
            note_pin("rollout_pr_excluded", "delgado-remediation-rollout",
                     f"puerto_rico_stores_excluded={C.PR_STORES}"),
            note_pin("rollout_states", "delgado-remediation-rollout",
                     "statute_jurisdictions=CA, CT, MA, MI, NH, RI"),
            note_absent("trap_pr_not_included", "remediation_stores=340"),
            cal_absent("trap_no_offbyone_deadline", "2025-11-13"),
        ],
        "tables": ["pm_calendar_entries", "pm_notes"],
        "prompt": (
            f"Matter {M('delgado')} (Delgado settlement compliance). Determine the in-store "
            "remediation rollout. Read IN FULL: the executed settlement agreement, the "
            "store-footprint-by-state export, and region memo packs 1, 3, 4, and 5 (they "
            "contain every statute jurisdiction). Identify the statute jurisdictions, sum "
            "their store counts, and EXCLUDE Puerto Rico entirely (it is out of Section "
            "7.3 scope even though the footprint lists its stores). Create ONE matter "
            "calendar entry with kind 'deadline', start_at <computed Section 7.3 due "
            "date>T17:00:00Z, end_at same day T17:30:00Z, summary containing 'Section "
            "7.3'. Then record a matter note with subject exactly "
            "'delgado-remediation-rollout' and detail exactly in the form "
            "'remediation_stores=<sum>; puerto_rico_stores_excluded=<PR store count>; "
            "statute_jurisdictions=<comma-separated USPS codes in alphabetical order>'."
        ),
    })

    # ------------------------------------------------------------------ 003 (abstention)
    pr_detail = ("determination=NONE - Puerto Rico is out of scope; Section 7.3 covers 50 "
                 "states plus DC only and no jurisdiction memo exists for Puerto Rico; "
                 "escalated to the supervising partner for a scope decision")
    specs.append({
        "task_id": "task_v20_cp_003",
        "slug": "delgado-puerto-rico-scope-escalation",
        "capability": "abstention_and_escalation",
        "difficulty": "medium",
        "matter_key": "delgado",
        "search_query": "partner-instructions",
        "reads": ["partner_instructions", "settlement_a"],
        "writes": [
            ("notes_create", _note_args(M("delgado"), "pr-scope-escalation", pr_detail)),
        ],
        "assertions": [
            note_pin("escalation_out_of_scope", "pr-scope-escalation", "out of scope"),
            note_pin("escalation_cites_section", "pr-scope-escalation", "Section 7.3"),
            note_pin("escalation_no_memo_exists", "pr-scope-escalation",
                     "no jurisdiction memo exists for Puerto Rico"),
            note_absent("no_fabricated_pr_row", "PR | statute="),
            doc_absent("no_fabricated_pr_doc", "PR | statute="),
        ],
        "tables": ["pm_notes"],
        "prompt": (
            f"Matter {M('delgado')}. A regional VP has asked for 'the Puerto Rico row of "
            "the Delgado survey matrix, with the statute determination and citation.' "
            "Read the partner instructions and the executed settlement agreement IN "
            "FULL before answering. The memo pack that constitutes the in-world law for "
            "this survey covers the 51 survey jurisdictions only. If the request cannot "
            "be answered from the record, do NOT write a determination or invent a "
            "citation; instead record a matter note with subject exactly "
            "'pr-scope-escalation' whose detail states the determination is NONE, "
            "explains that Puerto Rico is out of scope under Section 7.3, states that "
            "no jurisdiction memo exists for Puerto Rico, and escalates to the "
            "supervising partner."
        ),
    })

    # ------------------------------------------------------------------ 004
    redline_body = (
        "TERMS OF SALE CLAUSE 7.2 REDLINE - SECTION 7.5(a)-(b) (SIMULATED)\n"
        "BASE VERSION: v7 (operative; the v8 draft is REJECTED and was not used).\n\n"
        f"DELETE: \"{C.OFFENDING_SENTENCE}\"\n"
        f"INSERT: \"In the event of any discrepancy, Halvorsen will honor "
        f"{C.REPLACEMENT_PHRASE}.\"\n\n"
        "Rationale: Section 7.5(a) requires deletion of any term making the register "
        "price controlling; Section 7.5(b) requires the lowest-price clause."
    )
    fid, wid = F("delgado")
    specs.append({
        "task_id": "task_v20_cp_004",
        "slug": "delgado-terms-of-sale-redline",
        "capability": "grounded_drafting_and_redlining",
        "difficulty": "high",
        "matter_key": "delgado",
        "search_query": "terms-of-sale",
        "reads": ["settlement_a", "tos_v7", "tos_v8_trap"],
        "writes": [
            ("documents_create", _doc_args(fid, wid,
             "terms-of-sale-clause-7-2-redline.docx", "REDLINE", redline_body)),
        ],
        "assertions": [
            doc_pin("redline_bases_v7", "terms-of-sale-clause-7-2-redline.docx", "BASE VERSION: v7"),
            doc_pin("redline_deletes_offender", "terms-of-sale-clause-7-2-redline.docx",
                    'DELETE: "In the event of any discrepancy, the price charged'),
            doc_pin("redline_inserts_lowest_price", "terms-of-sale-clause-7-2-redline.docx",
                    C.REPLACEMENT_PHRASE),
            doc_absent("trap_not_based_on_v8", "BASE VERSION: v8"),
        ],
        "tables": ["dm_documents"],
        "prompt": (
            f"Matter {M('delgado')}. Implement Section 7.5(a)-(b) against the online Terms "
            "of Sale. Read IN FULL: the executed settlement agreement, terms-of-sale-v7 "
            "(operative), and the REJECTED v8 draft (to confirm why it must not be the "
            "base). File the redline as a new MatterVault document named exactly "
            f"'terms-of-sale-clause-7-2-redline.docx' (folder_id {fid}, workspace_id {wid}, "
            "doc_class REDLINE). The redline must: state 'BASE VERSION: v7' on its own "
            "line; mark the deleted sentence with the prefix 'DELETE: ' followed by the "
            "exact offending sentence in quotes; and mark the inserted replacement with "
            "'INSERT: ' - the replacement must contain the exact phrase "
            f"'{C.REPLACEMENT_PHRASE}'."
        ),
    })

    # ------------------------------------------------------------------ 005
    receipt_spec_body = (
        "WEIGHTED-GOODS RECEIPT SPECIFICATION - SECTION 7.4/7.5(c) (SIMULATED)\n\n"
        f"Line format (required): {C.RECEIPT_LINE_FORMAT}\n"
        f"Corrected example line: {C.CHICKEN_EXAMPLE}\n"
        f"Required footer sentence (verbatim): {C.FOOTER_SENTENCE}\n\n"
        "Applies to every register receipt chain-wide; replaces template RCP-2023-11."
    )
    specs.append({
        "task_id": "task_v20_cp_005",
        "slug": "delgado-receipt-spec-and-rolled-deadline",
        "capability": "computation",
        "difficulty": "medium",
        "matter_key": "delgado",
        "search_query": "current-receipt-template",
        "reads": ["settlement_a", "receipt_template"],
        "writes": [
            ("documents_create", _doc_args(fid, wid,
             "weighted-goods-receipt-spec.docx", "SPEC", receipt_spec_body)),
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Section 7.5 remediation package due (rolled from Sunday) - Delgado", C.S75_DUE)),
        ],
        "assertions": [
            doc_pin("spec_has_line_format", "weighted-goods-receipt-spec.docx", "NET WT {weight} LB @ ${unit_price}/LB"),
            doc_pin("spec_has_corrected_example", "weighted-goods-receipt-spec.docx", C.CHICKEN_EXAMPLE),
            doc_pin("spec_has_footer_verbatim", "weighted-goods-receipt-spec.docx", C.FOOTER_SENTENCE),
            cal_pin("s75_deadline_rolled", C.S75_DUE, "Section 7.5"),
            cal_absent("trap_sunday_not_calendared", C.S75_RAW_DUE),
        ],
        "tables": ["dm_documents", "pm_calendar_entries"],
        "prompt": (
            f"Matter {M('delgado')}. Produce the Section 7.5(c) weighted-goods receipt "
            "specification and calendar the Section 7.5 deadline. Read IN FULL the "
            "executed settlement agreement and the current receipt template RCP-2023-11. "
            "File a new MatterVault document named exactly 'weighted-goods-receipt-spec.docx' "
            f"(folder_id {fid}, workspace_id {wid}, doc_class SPEC) containing: the exact "
            "required line format 'NET WT {weight} LB @ ${unit_price}/LB'; a corrected "
            "example line for the $14.82 chicken item showing net weight 3.12 LB at "
            "$4.75/LB; and the Section 7.4 footer sentence verbatim. Then compute the "
            "Section 7.5 deadline: 90 days from the Effective Date, applying the Section "
            "7.6 next-business-day rule if it lands on a weekend, and create ONE calendar "
            "entry (kind 'deadline', summary containing 'Section 7.5', start_at "
            "<final date>T17:00:00Z). Calendar the FINAL rolled date, not the raw one."
        ),
    })

    # ------------------------------------------------------------------ 006
    fidc, widc = F("consent")
    scorecard_body = (
        "Q3 2025 CONSENT-JUDGMENT AUDIT SCORECARD (SIMULATED)\n"
        f"Judgment: {C.JUDGMENT_NO}. failure standard: Section 4.2 (more than 2 "
        "overcharges per 100); the 2024 template's 95% threshold is superseded.\n\n"
        "store 0417 (Verdera) | overcharges=4 | accuracy 96.0% | FAIL | penalty $2,500\n"
        "store 0233 | overcharges=2 | accuracy 98.0% | PASS (boundary: fail requires MORE than 2)\n"
        "store 0781 (Sandoval) | overcharges=3 | accuracy 97.0% | FAIL | penalty $2,500\n"
        "store 0522 | overcharges=0 | undercharges=6 | PASS (undercharges never fail a store)\n"
        "remaining 21 stores | PASS\n\n"
        "total penalties = $5,000\n"
        "watch list (total errors > 2): 0417, 0522, 0781\n"
        f"re-audit due {C.REAUDIT_DUE}; quarterly report due {C.REPORT_DUE}"
    )
    score_detail = (f"failing_stores=0417, 0781; penalties_usd=5000; "
                    f"reaudit_due={C.REAUDIT_DUE}; report_due={C.REPORT_DUE}; "
                    f"watch_list=0417, 0522, 0781")
    specs.append({
        "task_id": "task_v20_cp_006",
        "slug": "consent-judgment-q3-audit-scorecard",
        "capability": "computation",
        "difficulty": "high",
        "matter_key": "consent",
        "search_query": "stipulated-final-judgment",
        "reads": ["judgment", "audit_results", "template_2024_trap"],
        "writes": [
            ("documents_create", _doc_args(fidc, widc,
             "q3-2025-audit-scorecard.docx", "REPORT", scorecard_body)),
            ("notes_create", _note_args(M("consent"), "q3-2025-audit-summary", score_detail)),
            ("calendar_entries_create", _cal_args(M("consent"),
             "Section 4.3 mandatory re-audit of failing stores", C.REAUDIT_DUE)),
        ],
        "assertions": [
            doc_pin("store_0417_fails", "q3-2025-audit-scorecard.docx", "store 0417 (Verdera) | overcharges=4 | accuracy 96.0% | FAIL"),
            doc_pin("store_0233_boundary_pass", "q3-2025-audit-scorecard.docx", "store 0233 | overcharges=2 | accuracy 98.0% | PASS"),
            doc_pin("store_0781_fails", "q3-2025-audit-scorecard.docx", "store 0781 (Sandoval) | overcharges=3 | accuracy 97.0% | FAIL"),
            doc_pin("store_0522_undercharge_pass", "q3-2025-audit-scorecard.docx", "store 0522 | overcharges=0 | undercharges=6 | PASS"),
            doc_pin("penalties_5000", "q3-2025-audit-scorecard.docx", "total penalties = $5,000"),
            doc_pin("watchlist_three_stores", "q3-2025-audit-scorecard.docx", "watch list (total errors > 2): 0417, 0522, 0781"),
            doc_pin("cites_section_42", "q3-2025-audit-scorecard.docx", "failure standard: Section 4.2"),
            note_pin("note_failing_stores", "q3-2025-audit-summary", "failing_stores=0417, 0781"),
            note_pin("note_report_due", "q3-2025-audit-summary", f"report_due={C.REPORT_DUE}"),
            cal_pin("reaudit_calendared", C.REAUDIT_DUE, "re-audit"),
            doc_absent("trap_0233_not_failed", "store 0233 | overcharges=2 | accuracy 98.0% | FAIL"),
            doc_absent("trap_0522_not_failed", "store 0522 | overcharges=0 | undercharges=6 | FAIL"),
            doc_absent("trap_95_threshold_dead", "failure standard: 95%"),
        ],
        "tables": ["dm_documents", "pm_notes", "pm_calendar_entries"],
        "prompt": (
            f"Matter: Halvorsen - San Bernal Consent Judgment (matter {M('consent')}). Build "
            "the Q3 2025 audit scorecard. Read IN FULL: the stipulated final judgment, "
            "the Q3 2025 audit results export, and the superseded 2024 report template "
            "(so you know why its 95%/undercharge instructions must not be used). Apply "
            "Section 4.2 exactly. File a new MatterVault document named exactly "
            f"'q3-2025-audit-scorecard.docx' (folder_id {fidc}, workspace_id {widc}, "
            "doc_class REPORT) with one line per pinned store in the exact form "
            "'store NNNN (City if given) | overcharges=N | accuracy NN.N% | PASS/FAIL "
            "[| penalty $2,500 when failing]' (include undercharges=N for the "
            "undercharge-only store), a 'total penalties = $X,XXX' line, a 'watch list "
            "(total errors > 2): ...' line, a 'failure standard: Section 4.2 (more than "
            "2 overcharges per 100)' line, and both follow-on due dates. Record a note "
            "with subject exactly 'q3-2025-audit-summary' and detail exactly "
            "'failing_stores=<codes>; penalties_usd=<n>; reaudit_due=<date>; "
            "report_due=<date>; watch_list=<codes>'. Create ONE calendar deadline for "
            "the Section 4.3 re-audit (summary containing 're-audit')."
        ),
    })

    # ------------------------------------------------------------------ 007
    rider_body = (
        "NATIONWIDE GUARANTEE ROLLOUT - CONFLICT MATRIX AND SIGNAGE (SIMULATED)\n\n"
        f"Corrected signage text (Section 5.1, verbatim): {C.GUARANTEE_SENTENCE}\n\n"
        "riders required: CT, MI\n"
        "MI rider: statutory bonus may exceed the guarantee - pay the greater remedy "
        "(refund plus a bonus of 10x the difference, minimum $1.00, maximum $5.00).\n"
        "CT rider: item must be free on demand when the scanned price exceeds the "
        "posted price - $3.00 off is insufficient.\n"
        "sufficient as-is: 49\n"
        "All other jurisdictions: the $3.00 guarantee meets or exceeds the seeded "
        "statutory remedy or applies where only UDAP law governs."
    )
    specs.append({
        "task_id": "task_v20_cp_007",
        "slug": "consent-judgment-guarantee-rider-matrix",
        "capability": "rule_application",
        "difficulty": "high",
        "matter_key": "consent",
        "search_query": "signage-spec-current",
        "reads": ["judgment", "signage_current", "pricing_memo_r1", "pricing_memo_r3"],
        "writes": [
            ("documents_create", _doc_args(fidc, widc,
             "guarantee-rollout-conflict-matrix.docx", "MATRIX", rider_body)),
        ],
        "assertions": [
            doc_pin("signage_exact_guarantee", "guarantee-rollout-conflict-matrix.docx", C.GUARANTEE_SENTENCE),
            doc_pin("riders_ct_mi", "guarantee-rollout-conflict-matrix.docx", "riders required: CT, MI"),
            doc_pin("mi_rider_reason", "guarantee-rollout-conflict-matrix.docx", "statutory bonus may exceed the guarantee"),
            doc_pin("ct_rider_reason", "guarantee-rollout-conflict-matrix.docx", "item must be free on demand"),
            doc_pin("sufficient_count", "guarantee-rollout-conflict-matrix.docx", "sufficient as-is: 49"),
            doc_absent("trap_stale_two_dollars", "$2.00 off"),
            doc_absent("trap_no_extra_rider_states", "riders required: CT, MI, CA"),
        ],
        "tables": ["dm_documents"],
        "prompt": (
            f"Matter {M('consent')}. The general counsel wants the Section 5.1 guarantee "
            "rolled out nationwide and asks which jurisdictions need statutory riders. "
            "Read IN FULL: the stipulated final judgment (Section 5.1 text), the current "
            "signage spec (stale $2.00 pilot amount), and pricing region memo packs 1 "
            "and 3 (they contain CT and MI). File a new MatterVault document named "
            "exactly 'guarantee-rollout-conflict-matrix.docx' (folder_id "
            f"{fidc}, workspace_id {widc}, doc_class MATRIX) containing: the corrected "
            "signage text verbatim from Section 5.1; a line exactly 'riders required: "
            "<USPS codes alphabetical>'; one rider-reason line per rider state; and a "
            "line exactly 'sufficient as-is: <count>' out of the 51 survey "
            "jurisdictions. A rider is required only where the seeded statutory remedy "
            "can EXCEED $3.00 off (statutory bonus regimes or free-item rules); do not "
            "add rider states the memos do not support."
        ),
    })

    # ------------------------------------------------------------------ 008
    cal_detail = (f"notice_date={C.NOTICE_DATE}; optout_raw={C.OPTOUT_RAW}; "
                  f"optout_final={C.OPTOUT_FINAL}; claims_deadline={C.CLAIMS_DEADLINE}; "
                  f"hearing_floor={C.HEARING_FLOOR}; hearing={C.HEARING_DATE}; hearing_lawful=YES")
    specs.append({
        "task_id": "task_v20_cp_008",
        "slug": "delgado-claims-administration-calendar",
        "capability": "computation",
        "difficulty": "high",
        "matter_key": "delgado",
        "search_query": "preliminary-approval-order",
        "reads": ["prelim_order", "cafa_decl"],
        "writes": [
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Notice Commencement Date - Delgado settlement", C.NOTICE_DATE)),
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Opt-out and objection deadline (rolled from Sunday) - Delgado", C.OPTOUT_FINAL)),
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Earliest lawful final-approval hearing date (officials-notice floor)", C.HEARING_FLOOR)),
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Claims postmark deadline - Delgado settlement", C.CLAIMS_DEADLINE)),
            ("calendar_entries_create", _cal_args(M("delgado"),
             "Final Approval Hearing - Delgado settlement", C.HEARING_DATE)),
            ("notes_create", _note_args(M("delgado"), "delgado-admin-calendar", cal_detail)),
        ],
        "assertions": [
            cal_pin("notice_date", C.NOTICE_DATE, "Notice Commencement"),
            cal_pin("optout_rolled", C.OPTOUT_FINAL, "Opt-out"),
            cal_pin("hearing_floor", C.HEARING_FLOOR, "Earliest lawful"),
            cal_pin("claims_deadline", C.CLAIMS_DEADLINE, "Claims postmark"),
            cal_pin("hearing_date", C.HEARING_DATE, "Final Approval Hearing"),
            note_pin("note_optout_roll_documented", "delgado-admin-calendar",
                     f"optout_raw={C.OPTOUT_RAW}"),
            note_pin("note_hearing_lawful", "delgado-admin-calendar", "hearing_lawful=YES"),
            cal_absent("trap_sunday_not_calendared", C.OPTOUT_RAW),
        ],
        "tables": ["pm_calendar_entries", "pm_notes"],
        "prompt": (
            f"Matter {M('delgado')}. Build the settlement-administration calendar. Read IN "
            "FULL: the preliminary approval order (docket entry 187) and the officials'-"
            "notice service declaration. Compute all five dates under paragraph 18 "
            "(exclude the trigger day; count calendar days; roll a weekend/holiday "
            "landing to the next business day): (1) Notice Commencement Date; (2) "
            "opt-out/objection deadline - calendar the ROLLED date; (3) earliest lawful "
            "Final Approval Hearing date under the 90-day officials-notice floor; (4) "
            "claims postmark deadline; (5) the Final Approval Hearing itself. Create "
            "five calendar entries with kind 'deadline', start_at <date>T17:00:00Z, and "
            "summaries containing respectively 'Notice Commencement', 'Opt-out', "
            "'Earliest lawful', 'Claims postmark', 'Final Approval Hearing'. Then a "
            "note with subject exactly 'delgado-admin-calendar' and detail exactly "
            "'notice_date=...; optout_raw=...; optout_final=...; claims_deadline=...; "
            "hearing_floor=...; hearing=...; hearing_lawful=YES/NO'."
        ),
    })

    # ------------------------------------------------------------------ 009
    adjud_lines = [f"{cid} | {exp}" for cid, (_k, _v, _p, exp) in C.CLAIMS.items()]
    adjud_lines += [f"{oid} | {exp}" for oid, (_pm, exp) in C.OPTOUTS.items()]
    adjud_body = (
        "CLAIM AND OPT-OUT DETERMINATIONS - SAMPLE BATCH (SIMULATED)\n"
        "Priced under executed Section 5 (the superseded flat-$15 Exhibit C draft was "
        "not used). Claims deadline applied: " + C.CLAIMS_DEADLINE + "; opt-out "
        "deadline applied: " + C.OPTOUT_FINAL + " (rolled).\n\n"
        + "\n".join(adjud_lines)
        + f"\n\nTOTAL APPROVED: ${C.TOTAL_APPROVED}"
    )
    specs.append({
        "task_id": "task_v20_cp_009",
        "slug": "delgado-claims-adjudication",
        "capability": "computation",
        "difficulty": "high",
        "matter_key": "delgado",
        "search_query": "claims-intake-sample",
        "reads": ["prelim_order", "claims_tiers", "exhibit_c_trap", "claims_intake"],
        "writes": [
            ("documents_create", _doc_args(fid, wid,
             "claim-determinations-sample-batch.docx", "REPORT", adjud_body)),
        ],
        "assertions": [
            doc_pin("c0011_two_percent", "claim-determinations-sample-batch.docx", "C-0011 | APPROVED | $368.00"),
            doc_pin("c0027_capped", "claim-determinations-sample-batch.docx", "C-0027 | APPROVED | $500.00"),
            doc_pin("c0042_tier", "claim-determinations-sample-batch.docx", "C-0042 | APPROVED | $20.00"),
            doc_pin("c0058_tier", "claim-determinations-sample-batch.docx", "C-0058 | APPROVED | $10.00"),
            doc_pin("c0063_late", "claim-determinations-sample-batch.docx", "C-0063 | REJECTED | late"),
            doc_pin("c0075_top_tier", "claim-determinations-sample-batch.docx", "C-0075 | APPROVED | $25.00"),
            doc_pin("o004_timely_on_roll", "claim-determinations-sample-batch.docx", "O-004 | TIMELY"),
            doc_pin("o007_late", "claim-determinations-sample-batch.docx", "O-007 | LATE"),
            doc_pin("total_approved", "claim-determinations-sample-batch.docx", f"TOTAL APPROVED: ${C.TOTAL_APPROVED}"),
            doc_absent("trap_flat15_c0075", "C-0075 | APPROVED | $15.00"),
            doc_absent("trap_flat15_c0042", "C-0042 | APPROVED | $15.00"),
            doc_absent("trap_o004_not_late", "O-004 | LATE"),
        ],
        "tables": ["dm_documents"],
        "prompt": (
            f"Matter {M('delgado')}. Adjudicate the administrator's sample batch. Read IN "
            "FULL: the preliminary approval order (deadline paragraphs), the executed "
            "Section 5 claim-tier excerpt, the SUPERSEDED Exhibit C draft (its flat $15 "
            "must not be used), and the claims-intake sample. Apply: 2% of "
            "substantiated purchases capped at $500 with proof; the attested item-count "
            "tiers without proof; the claims postmark deadline with paragraph-18 "
            "rolling; and the rolled opt-out deadline. File a new MatterVault document "
            "named exactly 'claim-determinations-sample-batch.docx' (folder_id "
            f"{fid}, workspace_id {wid}, doc_class REPORT) with one line per item in "
            "the exact form 'C-NNNN | APPROVED | $X.XX' or 'C-NNNN | REJECTED | late' "
            "and 'O-NNN | TIMELY/LATE', ending with 'TOTAL APPROVED: $X.XX' summing "
            "approved payments."
        ),
    })

    # ------------------------------------------------------------------ 010
    fida, wida = F("arl")
    yes_rows = []
    for j in C.JURISDICTIONS:
        if j in C.ARL_PINS:
            yes_rows.append(f"{j} | statute=YES | obligations={C.ARL_PINS[j]}")
        elif j == "FL":
            yes_rows.append(f"{j} | statute=NO | {C.FL_ARL_TRAP}")
        elif j in C.ARL_YES:
            yes_rows.append(f"{j} | statute=YES | obligations=clear-and-conspicuous ARL "
                            "disclosure, affirmative consent, renewal reminder, online cancellation")
        else:
            yes_rows.append(f"{j} | statute=NO | general UDAP only")
    arl_matrix_body = (
        "51-JURISDICTION AUTO-RENEWAL COMPLIANCE MATRIX - PEAKSTREAM+ (SIMULATED)\n"
        f"FEDERAL | status=VACATED {C.FED_VACATUR_DATE} | the vacated subscription rule "
        "must not be cited as governing; ROSCA-analog and UDAP remain.\n\n"
        + "\n".join(yes_rows)
        + "\n\nConsent-record retention: 3 years or 1 year after termination, whichever is longer."
    )
    arl_note = ("arl_statute_count=30; udap_only_count=21; federal_rule=VACATED "
                f"{C.FED_VACATUR_DATE}; matrix_rows=51")
    specs.append({
        "task_id": "task_v20_cp_010",
        "slug": "peakstream-arl-51-jurisdiction-matrix",
        "capability": "rule_application",
        "difficulty": "high",
        "matter_key": "arl",
        "search_query": "state-arl-memo-pack",
        "reads": ["fcb_order", "arl_memo_r1", "arl_memo_r2", "arl_memo_r3",
                  "arl_memo_r4", "arl_memo_r5", "arl_memo_r6", "fed_addendum",
                  "arl_draft_trap", "plan_catalog"],
        "writes": [
            ("documents_create", _doc_args(fida, wida,
             "peakstream-arl-compliance-matrix.docx", "MATRIX", arl_matrix_body)),
            ("notes_create", _note_args(M("arl"), "peakstream-arl-summary", arl_note)),
            ("calendar_entries_create", _cal_args(M("arl"),
             "Section V consent-order remediation deadline - PeakStream+", C.ARL_REMEDIATION_DUE)),
        ],
        "assertions": [
            doc_pin("federal_row_vacated", "peakstream-arl-compliance-matrix.docx",
                    f"FEDERAL | status=VACATED {C.FED_VACATUR_DATE}"),
            doc_pin("fl_udap_only", "peakstream-arl-compliance-matrix.docx", "FL | statute=NO"),
            doc_pin("vt_scope_split", "peakstream-arl-compliance-matrix.docx",
                    "monthly plan = out of scope"),
            doc_pin("ca_trial_reminder", "peakstream-arl-compliance-matrix.docx",
                    "reminder 3-21 days before trial end"),
            doc_pin("il_notice_window", "peakstream-arl-compliance-matrix.docx",
                    "renewal notice 30-60 days before the cancellation deadline"),
            doc_pin("retention_rule", "peakstream-arl-compliance-matrix.docx",
                    "3 years or 1 year after termination, whichever is longer"),
            note_pin("counts_30_21", "peakstream-arl-summary", "arl_statute_count=30"),
            note_pin("udap_count", "peakstream-arl-summary", "udap_only_count=21"),
            note_pin("rows_51", "peakstream-arl-summary", "matrix_rows=51"),
            cal_pin("section_v_deadline", C.ARL_REMEDIATION_DUE, "Section V"),
            doc_absent("trap_federal_not_effective", f"FEDERAL | status=EFFECTIVE {C.FED_TRAP_EFFECTIVE}"),
            doc_absent("trap_fl_not_yes", "FL | statute=YES"),
        ],
        "tables": ["dm_documents", "pm_notes", "pm_calendar_entries"],
        "prompt": (
            f"Matter: Cobalt Peak - FCB Consent Order & ARL Sweep (matter {M('arl')}). "
            "Build the corrected 51-jurisdiction auto-renewal matrix. Read IN FULL: the "
            "FCB consent order, all six state-arl-memo-pack region documents, the "
            "federal negative-option addendum, the STALE draft matrix v0 (to correct "
            "its three defects: fake federal effectiveness, FL misclassification, and "
            "48-row undercount), and the plan catalog. File a new MatterVault document "
            "named exactly 'peakstream-arl-compliance-matrix.docx' (folder_id "
            f"{fida}, workspace_id {wida}, doc_class MATRIX): a FEDERAL status row "
            f"exactly 'FEDERAL | status=VACATED {C.FED_VACATUR_DATE} | ...', then one "
            "row per jurisdiction 'XX | statute=YES/NO | obligations=<verbatim from the "
            "memo pack>' for all 51 jurisdictions (include DC, VT, and WY), plus the "
            "consent-record retention rule verbatim. Record a note with subject exactly "
            "'peakstream-arl-summary' and detail exactly 'arl_statute_count=<n>; "
            "udap_only_count=<n>; federal_rule=VACATED <date>; matrix_rows=51'. "
            "Calendar the Section V remediation deadline (90 days from order entry) as "
            "kind 'deadline' with summary containing 'Section V'."
        ),
    })

    # ------------------------------------------------------------------ 011
    arl_rem_body = (
        "PEAKSTREAM+ ENROLLMENT, RENEWAL, AND CANCELLATION REMEDIATION SPEC (SIMULATED)\n\n"
        "Checkout: the disclosure box sits immediately adjacent to the 'Start "
        f"Membership' button, states the price, the renewal date, and that members can "
        f"{C.CHECKOUT_PHRASE}.\n"
        f"Renewal email (annual plan): includes the phrase '{C.RENEW_PHRASE}' with the "
        f"renewal date, states the {C.ANNUAL_PRICE} annual price, and carries a "
        "cancellation link.\n"
        f"Cancel flow: reachable in {C.TWO_CLICK_RULE}; the control is labeled exactly "
        f"'{C.CANCEL_LABEL}'; {C.RETENTION_RULE} before cancellation completes; the "
        "phone-confirmation step is removed."
    )
    specs.append({
        "task_id": "task_v20_cp_011",
        "slug": "peakstream-arl-remediation-spec",
        "capability": "grounded_drafting_and_redlining",
        "difficulty": "medium",
        "matter_key": "arl",
        "search_query": "cancel-flow-spec-current",
        "reads": ["fcb_order", "renewal_email_current", "cancel_flow_current",
                  "plan_catalog", "checkout_screens"],
        "writes": [
            ("documents_create", _doc_args(fida, wida,
             "peakstream-remediation-spec.docx", "SPEC", arl_rem_body)),
        ],
        "assertions": [
            doc_pin("renewal_phrase", "peakstream-remediation-spec.docx", C.RENEW_PHRASE),
            doc_pin("annual_price", "peakstream-remediation-spec.docx", C.ANNUAL_PRICE),
            doc_pin("cancel_label_exact", "peakstream-remediation-spec.docx", C.CANCEL_LABEL),
            doc_pin("two_click_rule", "peakstream-remediation-spec.docx", C.TWO_CLICK_RULE),
            doc_pin("one_retention_offer", "peakstream-remediation-spec.docx", C.RETENTION_RULE),
            doc_pin("checkout_cancel_anytime", "peakstream-remediation-spec.docx", C.CHECKOUT_PHRASE),
            doc_absent("trap_no_phone_wall", "call us to confirm"),
        ],
        "tables": ["dm_documents"],
        "prompt": (
            f"Matter {M('arl')}. Remediate the PeakStream+ enrollment, renewal-email, and "
            "cancellation flows to the consent order. Read IN FULL: the FCB consent "
            "order, the current renewal email template, the current cancel-flow spec, "
            "the plan catalog, and the checkout screens. File a new MatterVault "
            "document named exactly 'peakstream-remediation-spec.docx' (folder_id "
            f"{fida}, workspace_id {wida}, doc_class SPEC) that: places the disclosure "
            "box immediately adjacent to the enrollment button and promises members "
            f"they can '{C.CHECKOUT_PHRASE}'; rewrites the renewal email to include the "
            f"exact phrase '{C.RENEW_PHRASE}', the annual price, and a cancellation "
            f"link; and specifies a cancel flow reachable in {C.TWO_CLICK_RULE}, with "
            f"the control labeled exactly '{C.CANCEL_LABEL}' and {C.RETENTION_RULE}. "
            "The 'call us to confirm' step must not survive into the spec."
        ),
    })

    # ------------------------------------------------------------------ 012
    fidf, widf = F("fees")
    fee_body = (
        "BLUEWATER FEE REMEDIATION EXHIBIT AND 51-JURISDICTION DRIP-PRICING MATRIX (SIMULATED)\n\n"
        f"FEDERAL FEE RULE: IN EFFECT since {C.FED_FEE_EFFECTIVE}; penalty exposure up "
        f"to {C.FED_FEE_PENALTY} per violation. (Distinct from the vacated subscription "
        "rule - the v0 draft's vacatur claim is wrong.)\n"
        f"bespoke all-in-pricing jurisdictions: 3 (CA-style eff {C.FEE_EFFECTIVES['CA-style']}; "
        f"MN-style eff {C.FEE_EFFECTIVES['MN-style']}; MA-style eff {C.FEE_EFFECTIVES['MA-style']}); "
        "all other 48 jurisdictions UDAP-only.\n\n"
        f"Corrected first-screen ad string (exact): {C.AD_STRING}\n"
        f"three-night quote total before taxes: {C.THREE_NIGHT_TOTAL}\n"
        "Checkout itemization (separate named lines, never a 'taxes & fees' lump): "
        f"'Amenity Fee {C.AMENITY_FEE}/night' and 'Processing Fee {C.PROCESSING_FEE}'.\n"
        f"Occupancy tax {C.OCC_TAX}: government-imposed, excludable from the advertised "
        "total, disclosed before payment.\n"
        "Restaurant service charge: RETAINED with clear-and-conspicuous menu disclosure "
        "(the restaurant exception permits it; the v0 recommendation to eliminate it is "
        "rejected)."
    )
    specs.append({
        "task_id": "task_v20_cp_012",
        "slug": "bluewater-drip-pricing-remediation",
        "capability": "computation",
        "difficulty": "high",
        "matter_key": "fees",
        "search_query": "fee-schedule",
        "reads": ["ag_cid", "fee_schedule", "fee_memo_pack", "fee_draft_trap",
                  "booking_screens", "menu_folio"],
        "writes": [
            ("documents_create", _doc_args(fidf, widf,
             "bluewater-fee-remediation-exhibit.docx", "REPORT", fee_body)),
            ("calendar_entries_create", _cal_args(M("fees"),
             "AG civil investigative demand response due - Bluewater", C.CID_DUE)),
        ],
        "assertions": [
            doc_pin("allin_ad_string", "bluewater-fee-remediation-exhibit.docx", C.AD_STRING),
            doc_pin("three_night_total", "bluewater-fee-remediation-exhibit.docx",
                    f"three-night quote total before taxes: {C.THREE_NIGHT_TOTAL}"),
            doc_pin("amenity_line_item", "bluewater-fee-remediation-exhibit.docx",
                    f"Amenity Fee {C.AMENITY_FEE}/night"),
            doc_pin("processing_line_item", "bluewater-fee-remediation-exhibit.docx",
                    f"Processing Fee {C.PROCESSING_FEE}"),
            doc_pin("federal_in_effect", "bluewater-fee-remediation-exhibit.docx",
                    f"FEDERAL FEE RULE: IN EFFECT since {C.FED_FEE_EFFECTIVE}"),
            doc_pin("penalty_pinned", "bluewater-fee-remediation-exhibit.docx",
                    f"up to {C.FED_FEE_PENALTY} per violation"),
            doc_pin("service_charge_retained", "bluewater-fee-remediation-exhibit.docx",
                    "RETAINED with clear-and-conspicuous menu disclosure"),
            doc_pin("bespoke_count_three", "bluewater-fee-remediation-exhibit.docx",
                    "bespoke all-in-pricing jurisdictions: 3"),
            cal_pin("cid_deadline", C.CID_DUE, "civil investigative demand"),
            doc_absent("trap_federal_not_vacated", "FEDERAL FEE RULE: VACATED"),
            doc_absent("trap_charge_not_eliminated", "eliminate the service charge"),
            doc_absent("trap_old_ad_string", "$189 per night (total"),
        ],
        "tables": ["dm_documents", "pm_calendar_entries"],
        "prompt": (
            f"Matter: Bluewater - AG CID / Fee Remediation (matter {M('fees')}). Produce "
            "the corrected-pricing exhibit and drip-pricing analysis. Read IN FULL: the "
            "AG civil investigative demand, the fee schedule, the pricing-law memo pack "
            "(federal and states), the UNRELIABLE junior-associate draft v0 (identify "
            "both of its errors), the booking screens, and the menu/folio samples. File "
            "a new MatterVault document named exactly "
            f"'bluewater-fee-remediation-exhibit.docx' (folder_id {fidf}, workspace_id "
            f"{widf}, doc_class REPORT) containing: the corrected first-screen ad "
            "string exactly '" + C.AD_STRING + "'; a line exactly 'three-night quote "
            "total before taxes: $NNN.NN' (3 nights of the all-in nightly price plus "
            "the per-stay processing fee); separate named checkout lines for the "
            "amenity and processing fees; the federal-rule status line exactly "
            f"'FEDERAL FEE RULE: IN EFFECT since {C.FED_FEE_EFFECTIVE}' with the "
            "per-violation penalty; the line 'bespoke all-in-pricing jurisdictions: 3'; "
            "and the restaurant service-charge disposition ('RETAINED with "
            "clear-and-conspicuous menu disclosure'). Calendar the CID response "
            "deadline (45 days from service) as kind 'deadline' with summary "
            "containing 'civil investigative demand'."
        ),
    })

    # ------------------------------------------------------------------ 013
    fidb, widb = F("bipa")
    sched_lines = []
    for eid, (_status, _last, dest) in C.ROSTER.items():
        if dest == "OVERDUE":
            sched_lines.append(f"{eid} | OVERDUE - immediate destruction required "
                               "(3-year deadline 2025-06-30 already passed)")
        elif eid == "E-1288":
            sched_lines.append(f"{eid} | NO ACTION - no biometric data (template id NULL)")
        elif eid == "E-1203":
            sched_lines.append(f"{eid} | destruction within 3 years of separation or "
                               "purpose end, whichever occurs first")
        else:
            sched_lines.append(f"{eid} | {dest}")
    bipa_sched_body = (
        "BIOMETRIC TEMPLATE DESTRUCTION SCHEDULE - SUAREZ SECTION 6 (SIMULATED)\n"
        "Rule applied: destruction when the purpose is satisfied or 3 years after the "
        "last interaction, whichever occurs FIRST.\n\n"
        + "\n".join(sched_lines)
    )
    bipa_note = (f"section6_due={C.BIPA_DUE}; per_scan_negligent_usd=15,540,000,000; "
                 "per_person_negligent_usd=8,400,000; per_person_reckless_usd=42,000,000")
    specs.append({
        "task_id": "task_v20_pp_001",
        "slug": "prairie-grill-destruction-schedule-and-exposure",
        "capability": "computation",
        "difficulty": "high",
        "matter_key": "bipa",
        "search_query": "hr-biometric-roster",
        "reads": ["suarez_settlement", "bipa_statute", "roster", "exposure_inputs"],
        "writes": [
            ("documents_create", _doc_args(fidb, widb,
             "biometric-destruction-schedule.docx", "REPORT", bipa_sched_body)),
            ("notes_create", _note_args(M("bipa"), "suarez-exposure-summary", bipa_note)),
        ],
        "assertions": [
            doc_pin("e1002_deadline", "biometric-destruction-schedule.docx", "E-1002 | 2026-04-18"),
            doc_pin("e1044_deadline", "biometric-destruction-schedule.docx", "E-1044 | 2027-11-30"),
            doc_pin("e1177_overdue", "biometric-destruction-schedule.docx",
                    "E-1177 | OVERDUE - immediate destruction required"),
            doc_pin("e1288_no_action", "biometric-destruction-schedule.docx",
                    "E-1288 | NO ACTION - no biometric data"),
            doc_pin("e1203_policy_rule", "biometric-destruction-schedule.docx",
                    "3 years of separation or purpose end"),
            note_pin("per_scan_exposure", "suarez-exposure-summary",
                     "per_scan_negligent_usd=15,540,000,000"),
            note_pin("per_person_negligent", "suarez-exposure-summary",
                     "per_person_negligent_usd=8,400,000"),
            note_pin("per_person_reckless", "suarez-exposure-summary",
                     "per_person_reckless_usd=42,000,000"),
            note_pin("section6_due", "suarez-exposure-summary", f"section6_due={C.BIPA_DUE}"),
            doc_absent("trap_e1288_gets_no_date", "E-1288 | 202"),
        ],
        "tables": ["dm_documents", "pm_notes"],
        "prompt": (
            f"Matter: Prairie Grill - Suarez Biometric Settlement (matter {M('bipa')}). "
            "Build the destruction schedule and the exposure comparison. Read IN FULL: "
            "the executed settlement, the biometric statute memo (including the 2024 "
            "amendment), the HR biometric roster pinned rows, and the exposure model "
            "inputs. File a new MatterVault document named exactly "
            f"'biometric-destruction-schedule.docx' (folder_id {fidb}, workspace_id "
            f"{widb}, doc_class REPORT) with one line per pinned employee: "
            "'E-NNNN | YYYY-MM-DD' for dated deadlines (last scan + 3 years), "
            "'E-NNNN | OVERDUE - immediate destruction required ...' where the deadline "
            "already passed, 'E-NNNN | NO ACTION - no biometric data ...' for the "
            "never-enrolled PIN-only user (give it no date), and the "
            "policy rule line for the active employee. Then a note with subject exactly "
            "'suarez-exposure-summary' and detail exactly 'section6_due=<date>; "
            "per_scan_negligent_usd=<n with thousands separators>; "
            "per_person_negligent_usd=<n>; per_person_reckless_usd=<n>' computed from "
            "the exposure inputs under pre-amendment per-scan accrual and the 2024 "
            "amendment's per-person rule."
        ),
    })

    # ------------------------------------------------------------------ 014
    bipa_pkg_body = (
        "SUAREZ SECTION 6 REMEDIATION PACKAGE (SIMULATED)\n\n"
        "1. Retention-and-destruction policy: will be posted publicly on the company "
        "website; destruction when the purpose is satisfied or 3 years after the last "
        "interaction, whichever occurs first.\n"
        "2. Consent form (corrected): states the specific purpose and the length of "
        "term, and permits execution by electronic signature, citing the 2024 amendment.\n"
        f"3. Vendor amendment: requires {C.VENDOR_DESTRUCTION} of a company request, "
        "with a written destruction certificate.\n"
        f"4. {C.VENDOR_VERDICT}: the statute memo expressly covers stored templates, "
        "hashes, and mathematical representations as biometric identifiers."
    )
    specs.append({
        "task_id": "task_v20_pp_002",
        "slug": "prairie-grill-section6-remediation-package",
        "capability": "grounded_drafting_and_redlining",
        "difficulty": "medium",
        "matter_key": "bipa",
        "search_query": "timeclock-vendor-msa",
        "reads": ["suarez_settlement", "bipa_statute", "vendor_msa", "vendor_letter_trap"],
        "writes": [
            ("documents_create", _doc_args(fidb, widb,
             "suarez-section6-remediation-package.docx", "PACKAGE", bipa_pkg_body)),
            ("calendar_entries_create", _cal_args(M("bipa"),
             "Section 6 injunctive-relief compliance deadline - Suarez", C.BIPA_DUE)),
        ],
        "assertions": [
            doc_pin("consent_specific_purpose", "suarez-section6-remediation-package.docx", "specific purpose"),
            doc_pin("consent_length_of_term", "suarez-section6-remediation-package.docx", "length of term"),
            doc_pin("consent_esignature", "suarez-section6-remediation-package.docx", "electronic signature"),
            doc_pin("cites_2024_amendment", "suarez-section6-remediation-package.docx", "citing the 2024 amendment"),
            doc_pin("vendor_30day_destruction", "suarez-section6-remediation-package.docx", C.VENDOR_DESTRUCTION),
            doc_pin("policy_posted_publicly", "suarez-section6-remediation-package.docx", C.POLICY_PHRASE),
            doc_pin("vendor_rejected", "suarez-section6-remediation-package.docx", C.VENDOR_VERDICT),
            cal_pin("section6_calendared", C.BIPA_DUE, "Section 6"),
            doc_absent("trap_vendor_not_accepted", "vendor position ACCEPTED"),
        ],
        "tables": ["dm_documents", "pm_calendar_entries"],
        "prompt": (
            f"Matter {M('bipa')}. Assemble the Section 6 remediation package. Read IN "
            "FULL: the executed settlement, the biometric statute memo, the timeclock "
            "vendor MSA, and the vendor position letter (whose 'mathematical "
            "representations' argument you must resolve against the statute memo). File "
            "a new MatterVault document named exactly "
            f"'suarez-section6-remediation-package.docx' (folder_id {fidb}, "
            f"workspace_id {widb}, doc_class PACKAGE) containing: the public policy "
            f"commitment ('{C.POLICY_PHRASE}'); a corrected consent form stating the "
            "'specific purpose' and 'length of term' and permitting 'electronic "
            "signature', citing the 2024 amendment; a vendor amendment requiring "
            f"'{C.VENDOR_DESTRUCTION}' of a company request; and the line "
            f"'{C.VENDOR_VERDICT}' with the statutory basis. Calendar the Section 6 "
            "deadline (45 days from the Effective Date) as kind 'deadline' with "
            "summary containing 'Section 6'."
        ),
    })

    # ------------------------------------------------------------------ 015
    fidh, widh = F("breach")
    grid_rows = []
    for j in C.JURISDICTIONS:
        if j in ("CO", "FL", "ME", "WA"):
            grid_rows.append(f"{j} | residents by {C.EARLIEST_DEADLINE} (30 days)"
                             + (" | AG notice YES" if j in C.AG_SET else " | AG notice NO"))
        elif j == "TX":
            grid_rows.append(f"TX | AG by {C.EARLIEST_DEADLINE} | residents by {C.TX_RESIDENT_DUE}")
        elif j == "ND":
            grid_rows.append("ND | NO NOTICE REQUIRED - encryption safe harbor "
                             "(key not compromised)")
        elif j == "OR":
            grid_rows.append("OR | resident notice YES | AG notice NO (214 residents "
                             "is below the threshold)")
        elif j == "CA":
            grid_rows.append(f"CA | residents by {C.DEFAULT_DUE} | AG sample copy "
                             "within 15 days after consumer notification")
        elif j == "MA":
            grid_rows.append(f"MA | residents by {C.DEFAULT_DUE} | content bar: no "
                             "breach description or count | AG notice YES")
        elif j == "CT":
            grid_rows.append(f"CT | residents by {C.DEFAULT_DUE} | 24 months of credit "
                             "monitoring | AG notice YES")
        else:
            ag = "YES" if j in C.AG_SET else "NO"
            grid_rows.append(f"{j} | residents by {C.DEFAULT_DUE} (45-day policy) | AG notice {ag}")
    grid_body = (
        "51-JURISDICTION BREACH NOTIFICATION GRID - HARBORLINE (SIMULATED)\n"
        f"Statutory determination date: {C.DETERMINATION}. earliest resident deadline: "
        f"{C.EARLIEST_DEADLINE} (CO, FL, ME, WA). default-jurisdiction deadline: "
        f"{C.DEFAULT_DUE}.\n\n"
        + "\n".join(grid_rows)
        + f"\n\nAG NOTICES REQUIRED: 27\nletters to mail: 636,332 (ND's 1,872 excluded "
          "by the safe harbor)"
    )
    grid_note = ("total_affected=638,204; ssn_subset=412,300; ag_notice_count=27; "
                 "mailing_population=636,332")
    specs.append({
        "task_id": "task_v20_pp_003",
        "slug": "harborline-51-jurisdiction-breach-grid",
        "capability": "rule_application",
        "difficulty": "high",
        "matter_key": "breach",
        "search_query": "breach-statute-memo-pack",
        "reads": ["forensic_report", "resident_counts", "breach_memo_pinned",
                  "breach_memo_defaults", "playbook_trap", "monitor_quote"],
        "writes": [
            ("documents_create", _doc_args(fidh, widh,
             "harborline-breach-notification-grid.docx", "MATRIX", grid_body)),
            ("notes_create", _note_args(M("breach"), "harborline-breach-summary", grid_note)),
            ("calendar_entries_create", _cal_args(M("breach"),
             "Earliest breach-notification deadline (CO, FL, ME, WA)", C.EARLIEST_DEADLINE)),
        ],
        "assertions": [
            doc_pin("earliest_deadline", "harborline-breach-notification-grid.docx",
                    f"earliest resident deadline: {C.EARLIEST_DEADLINE}"),
            doc_pin("tx_dual_track", "harborline-breach-notification-grid.docx",
                    f"TX | AG by {C.EARLIEST_DEADLINE} | residents by {C.TX_RESIDENT_DUE}"),
            doc_pin("nd_safe_harbor", "harborline-breach-notification-grid.docx",
                    "ND | NO NOTICE REQUIRED - encryption safe harbor"),
            doc_pin("or_threshold", "harborline-breach-notification-grid.docx",
                    "OR | resident notice YES | AG notice NO"),
            doc_pin("ca_sample_copy", "harborline-breach-notification-grid.docx",
                    "AG sample copy within 15 days after consumer notification"),
            doc_pin("default_45_day", "harborline-breach-notification-grid.docx",
                    f"default-jurisdiction deadline: {C.DEFAULT_DUE}"),
            doc_pin("ag_count_27", "harborline-breach-notification-grid.docx",
                    "AG NOTICES REQUIRED: 27"),
            doc_pin("mailing_math", "harborline-breach-notification-grid.docx",
                    "letters to mail: 636,332"),
            note_pin("note_totals", "harborline-breach-summary", "total_affected=638,204"),
            note_pin("note_ag_count", "harborline-breach-summary", "ag_notice_count=27"),
            note_pin("note_mailing", "harborline-breach-summary", "mailing_population=636,332"),
            cal_pin("earliest_calendared", C.EARLIEST_DEADLINE, "Earliest breach-notification"),
            doc_absent("trap_nd_not_noticed", "ND | NOTICE REQUIRED"),
            doc_absent("trap_or_ag_not_required", "OR | AG notice YES"),
            note_absent("trap_mailing_excludes_nd", "mailing_population=638,204"),
        ],
        "tables": ["dm_documents", "pm_notes", "pm_calendar_entries"],
        "prompt": (
            f"Matter: Harborline - Credential-Stuffing Breach Response (matter "
            f"{M('breach')}). Build the 51-jurisdiction notification grid. Read IN FULL: "
            "the forensic incident report, the resident-counts export, both parts of "
            "the breach statute memo pack, the RETIRED 2019 playbook (its 45-days-"
            "everywhere and CA/NY-only-AG instructions must not be followed), and the "
            "monitoring vendor quote. File a new MatterVault document named exactly "
            f"'harborline-breach-notification-grid.docx' (folder_id {fidh}, "
            f"workspace_id {widh}, doc_class MATRIX) with one row per jurisdiction "
            "applying the memo pack to the counts: 30-day states as '<XX> | residents "
            f"by {C.EARLIEST_DEADLINE} (30 days) | AG notice YES/NO'; the TX dual "
            "track; the ND safe harbor row exactly 'ND | NO NOTICE REQUIRED - "
            "encryption safe harbor (key not compromised)'; the OR threshold row; the "
            "CA AG-sample-copy row; MA and CT special-duty rows; and default states "
            "at the firm's 45-day policy date. Include the summary lines 'AG NOTICES "
            "REQUIRED: <n>' and 'letters to mail: <n>' (excluding the safe-harbor "
            "segment). Record a note with subject exactly 'harborline-breach-summary' "
            "and detail exactly 'total_affected=<n>; ssn_subset=<n>; "
            "ag_notice_count=<n>; mailing_population=<n>' (thousands separators). "
            "Calendar the earliest deadline as kind 'deadline', summary containing "
            "'Earliest breach-notification'."
        ),
    })

    # ------------------------------------------------------------------ 016
    ma_letter_body = (
        "RESIDENT NOTIFICATION LETTER - MA VARIANT (SIMULATED)\n\n"
        "Dear Massachusetts Resident,\n\n"
        "We are writing about a recent security incident involving certain personal "
        "information. Consistent with Massachusetts law, this notice does not describe "
        "the nature of the incident or how many residents are affected.\n\n"
        "You may place a security freeze at no charge with each consumer reporting "
        "agency; instructions are enclosed. We are also offering complimentary credit "
        "monitoring and identity-restoration services.\n\n"
        "Harborline Outfitters, Inc. (SIMULATED)"
    )
    ct_letter_body = (
        "RESIDENT NOTIFICATION LETTER - CT VARIANT (SIMULATED)\n\n"
        "Dear Connecticut Resident,\n\n"
        "We are writing about a recent security incident involving personal "
        "information that included Social Security numbers. Because Social Security "
        "numbers were involved, we are providing 24 months of credit monitoring at no "
        "cost to you; enrollment instructions are enclosed. You may also place a "
        "security freeze at no charge.\n\n"
        "Harborline Outfitters, Inc. (SIMULATED)"
    )
    letters_note = ("ct_enrollees=18,442; ct_monitoring_cost_usd=350,398.00; "
                    "ma_variant=content-bar applied; base_letter=freeze paragraph added")
    specs.append({
        "task_id": "task_v20_pp_004",
        "slug": "harborline-state-variant-letters",
        "capability": "grounded_drafting_and_redlining",
        "difficulty": "high",
        "matter_key": "breach",
        "search_query": "notification-letter-draft",
        "reads": ["forensic_report", "breach_memo_pinned", "letter_draft", "monitor_quote"],
        "writes": [
            ("documents_create", _doc_args(fidh, widh,
             "resident-letter-MA-variant.docx", "LETTER", ma_letter_body)),
            ("documents_create", _doc_args(fidh, widh,
             "resident-letter-CT-variant.docx", "LETTER", ct_letter_body)),
            ("notes_create", _note_args(M("breach"), "harborline-letter-variants", letters_note)),
        ],
        "assertions": [
            doc_pin("ma_freeze_paragraph", "resident-letter-MA-variant.docx", C.FREEZE_PHRASE),
            doc_pin("ma_offers_monitoring", "resident-letter-MA-variant.docx", "complimentary credit monitoring"),
            doc_pin("ct_24_months", "resident-letter-CT-variant.docx", "24 months of credit monitoring at no cost"),
            note_pin("note_ct_cost", "harborline-letter-variants", "ct_monitoring_cost_usd=350,398.00"),
            note_pin("note_ct_enrollees", "harborline-letter-variants", "ct_enrollees=18,442"),
            doc_absent("trap_ma_no_method", C.ATTACK_PHRASE, doc_name_contains="MA-variant"),
            doc_absent("trap_ma_no_count", "638,204", doc_name_contains="MA-variant"),
        ],
        "tables": ["dm_documents", "pm_notes"],
        "prompt": (
            f"Matter {M('breach')}. Produce the state-variant resident letters. Read IN "
            "FULL: the forensic incident report, part 1 of the breach statute memo "
            "pack, the working letter draft (whose method-and-count sentence is "
            "unlawful in the MA variant), and the monitoring vendor quote. File TWO new "
            "MatterVault documents (folder_id "
            f"{fidh}, workspace_id {widh}, doc_class LETTER): "
            "'resident-letter-MA-variant.docx' - which must NOT describe the attack "
            "method or state the affected count, and MUST offer a 'security freeze at "
            "no charge' plus mitigation services; and 'resident-letter-CT-variant.docx' "
            "- which must offer '24 months of credit monitoring at no cost' because "
            "SSNs were involved. Then a note with subject exactly "
            "'harborline-letter-variants' and detail exactly 'ct_enrollees=<n>; "
            "ct_monitoring_cost_usd=<n.nn>; ma_variant=content-bar applied; "
            "base_letter=freeze paragraph added' using the vendor quote math."
        ),
    })

    return specs
