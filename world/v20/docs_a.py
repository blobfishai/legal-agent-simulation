"""Seeded documents for family A (consumer-protection-compliance).

Every document is synthetic simulation content.  Bodies stay under 3,900
characters so the distinctive anchor strings land inside the trace
observation window.  ``trap=True`` marks deliberately wrong/superseded
material a competent agent must refuse to rely on.
"""
from __future__ import annotations

from world.v20 import content as C


def _pricing_state_line(j: str) -> str:
    name = C.JUR_NAME[j]
    if j in C.ITEM_PRICING:
        e = C.ITEM_PRICING[j]
        return (f"{j} ({name}): statute=YES. cite={e['cite']}. "
                f"remedy_phrase=\"{e['remedy_phrase']}\". "
                f"duty_phrase=\"{e['duty_phrase']}\".")
    if j == "WY":
        return (f"{j} ({name}): statute=NO - {C.WY_TRAP_NOTE}. "
                f"remedy_phrase=\"{C.UDAP_ROW_PHRASE}\".")
    if j == "NY":
        return (f"{j} ({name}): statute=NO - {C.NY_TRAP_NOTE}. "
                f"remedy_phrase=\"{C.UDAP_ROW_PHRASE}\".")
    return f"{j} ({name}): statute=NO. remedy_phrase=\"{C.UDAP_ROW_PHRASE}\"."


def _pricing_region_doc(idx: int, states: list[str]) -> dict:
    lines = "\n".join(_pricing_state_line(j) for j in states)
    rng = f"{states[0]}-{states[-1]}"
    return {
        "key": f"pricing_memo_r{idx}",
        "name": f"state-pricing-law-memo-pack-region-{idx}.docx",
        "doc_class": "MEMO",
        "matter_key": "delgado",
        "anchor": f"STATE PRICING-LAW MEMO PACK - REGION {idx} ({rng})",
        "body": (
            f"STATE PRICING-LAW MEMO PACK - REGION {idx} ({rng}) - DELGADO SURVEY (SIMULATED)\n"
            f"Prepared for {C.CLIENT_A} under {C.CASE_A}.\n"
            "This pack IS the controlling in-world law for the Section 7.3 survey. "
            "Copy each remedy_phrase verbatim into the compliance matrix.\n\n"
            f"{lines}\n\n"
            "END OF REGION MEMO. The survey covers 50 states plus the District of "
            "Columbia (51 jurisdictions). Puerto Rico is expressly out of survey scope."
        ),
    }


def family_a_docs() -> list[dict]:
    docs: list[dict] = []

    docs.append({
        "key": "settlement_a",
        "name": "delgado-settlement-agreement-executed.docx",
        "doc_class": "AGREEMENT",
        "matter_key": "delgado",
        "anchor": "EXECUTED SETTLEMENT AGREEMENT - DELGADO v. HALVORSEN MARKET GROUP",
        "body": (
            "EXECUTED SETTLEMENT AGREEMENT - DELGADO v. HALVORSEN MARKET GROUP, INC. (SIMULATED)\n"
            f"{C.CASE_A}\n\n"
            f"Settlement fund: {C.FUND_A}. Class period: 2019-03-01 through 2025-01-31. "
            f"The Effective Date is stipulated as {C.EFFECTIVE_DATE}.\n\n"
            "Section 7.3 (Survey and Remediation). Within 60 days of the Effective Date, "
            "Halvorsen shall complete a pricing-law compliance survey covering all 50 "
            "states and the District of Columbia (51 jurisdictions) and adopt a "
            "remediation plan. Puerto Rico is expressly EXCLUDED from the survey and "
            "from every remediation count under this Agreement.\n\n"
            "Section 7.4 (Receipt Disclosure). Every register receipt shall add the "
            f"exact footer sentence: \"{C.FOOTER_SENTENCE}\"\n\n"
            "Section 7.5 (Terms, Receipt Specification, Signage). Within 90 days of the "
            "Effective Date, Halvorsen shall (a) delete from its online Terms of Sale "
            "any term making the register price controlling, (b) insert a clause "
            f"honoring \"{C.REPLACEMENT_PHRASE}\", (c) publish a weighted-goods receipt "
            "specification whose line format is "
            f"\"{C.RECEIPT_LINE_FORMAT}\", and (d) post lowest-price signage in every "
            "store located in a statute jurisdiction.\n\n"
            "Section 7.6 (Computation). Periods run in calendar days from (and "
            "excluding) the Effective Date. If a deadline falls on a Saturday, Sunday, "
            "or legal holiday, it extends to the next business day."
        ),
    })

    for i, states in enumerate(C.REGIONS, 1):
        docs.append(_pricing_region_doc(i, states))

    docs.append({
        "key": "draft_matrix_trap",
        "name": "draft-compliance-matrix-v1-SUPERSEDED.docx",
        "doc_class": "DRAFT",
        "matter_key": "delgado",
        "trap": True,
        "anchor": "DRAFT COMPLIANCE MATRIX v1 - DO NOT CIRCULATE",
        "body": (
            "DRAFT COMPLIANCE MATRIX v1 - DO NOT CIRCULATE, unverified paralegal draft (SIMULATED)\n\n"
            "Selected rows as drafted (KNOWN TO CONTAIN ERRORS):\n"
            "MI: statute YES; maximum bonus $10.00.\n"
            "MA: statute YES; applies to all retail stores.\n"
            "WY: statute YES; Wyoming Retail Price Accuracy Act.\n"
            "NY: statute YES statewide.\n\n"
            "Cell note: v1 - unverified; the memo pack controls. This draft was "
            "superseded before circulation and must not be relied on."
        ),
    })

    docs.append({
        "key": "receipt_template",
        "name": "current-receipt-template-RCP-2023-11.docx",
        "doc_class": "TEMPLATE",
        "matter_key": "delgado",
        "anchor": "RECEIPT TEMPLATE RCP-2023-11",
        "body": (
            "RECEIPT TEMPLATE RCP-2023-11 (CURRENT, PRE-SETTLEMENT) (SIMULATED)\n\n"
            "HALVORSEN MARKET  STORE #NNNN\nLine-item block:\n"
            "  CHKN BRST FAM PK  $14.82   <- weighted item printed WITHOUT net weight or unit price\n"
            "  2% MILK 1GAL      $3.49\n"
            "Footer: return policy text only. There is NO lowest-price footer sentence "
            "in this version. Weighted-goods lines show only the extended price."
        ),
    })

    docs.append({
        "key": "partner_instructions",
        "name": "partner-instructions.eml",
        "doc_class": "CORRESPONDENCE",
        "matter_key": "delgado",
        "anchor": "PARTNER INSTRUCTIONS - DELGADO SURVEY DELIVERABLES",
        "body": (
            "PARTNER INSTRUCTIONS - DELGADO SURVEY DELIVERABLES (SIMULATED EMAIL)\n"
            "From: supervising.partner@simulated-firm.example\n\n"
            "1) Compliance matrix: one row per jurisdiction, 50 states plus DC, exactly "
            "51 rows, no Puerto Rico row. Canonical row grammar, one line per row:\n"
            "   XX | statute=YES/NO | cite=<cite or none> | remedy=<remedy_phrase verbatim "
            "from the memo pack> | action=<required action>\n"
            "2) Report the computed Section 7.3 survey due date.\n"
            "3) Report how many stores need in-store remediation across the statute "
            "jurisdictions, excluding Puerto Rico entirely.\n"
            "4) The paralegal draft matrix v1 is superseded and wrong in at least three "
            "rows; work only from the executed agreement and the region memo pack.\n"
            "If asked for any jurisdiction outside the 51 (for example Puerto Rico), do "
            "not guess: escalate with a note instead of writing a determination."
        ),
    })

    footprint_lines = []
    for j in C.JURISDICTIONS:
        n = C.STORE_COUNTS.get(j, C.STORE_FILLER.get(j))
        footprint_lines.append(f"{j}: {n}")
    docs.append({
        "key": "store_footprint",
        "name": "store-footprint-by-state.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "delgado",
        "anchor": "STORE FOOTPRINT BY JURISDICTION",
        "body": (
            "STORE FOOTPRINT BY JURISDICTION (SIMULATED DATA EXPORT)\n"
            f"Network total including Puerto Rico: {C.TOTAL_STORES} stores.\n"
            f"PR (Puerto Rico): {C.PR_STORES}  <- territory row; out of Section 7.3 scope\n"
            + "\n".join(footprint_lines)
        ),
    })

    docs.append({
        "key": "tos_v7",
        "name": "terms-of-sale-v7-OPERATIVE.docx",
        "doc_class": "AGREEMENT",
        "matter_key": "delgado",
        "anchor": "TERMS OF SALE v7 - OPERATIVE",
        "body": (
            "TERMS OF SALE v7 - OPERATIVE (SIMULATED)\n"
            "DMS profile: version 7; EFFECTIVE 2024-05-01; status=operative.\n\n"
            "Clause 7.2 (Pricing). Prices are displayed on shelf tags and in "
            f"advertisements. {C.OFFENDING_SENTENCE}\n\n"
            "Clause 7.3 (Payment). Payment is due at the point of sale."
        ),
    })

    docs.append({
        "key": "tos_v8_trap",
        "name": "terms-of-sale-v8-draft-REJECTED.docx",
        "doc_class": "DRAFT",
        "matter_key": "delgado",
        "trap": True,
        "anchor": "TERMS OF SALE v8 DRAFT - REJECTED",
        "body": (
            "TERMS OF SALE v8 DRAFT - REJECTED (SIMULATED)\n"
            "DMS profile: version 8 DRAFT; status=REJECTED 2025-07-22; comment: "
            "\"Legal: does not satisfy Section 7.5 - do not use.\"\n\n"
            f"Clause 7.2 (Pricing) as drafted: {C.OFFENDING_SENTENCE} except where "
            "prohibited by law.\n\n"
            "This draft keeps the register-price-controls sentence behind a disclaimer "
            "and was rejected for exactly that reason."
        ),
    })

    docs.append({
        "key": "judgment",
        "name": "stipulated-final-judgment-CIVSB-2024-118822.docx",
        "doc_class": "ORDER",
        "matter_key": "consent",
        "anchor": "STIPULATED FINAL JUDGMENT - CIVSB-2024-118822",
        "body": (
            "STIPULATED FINAL JUDGMENT - CIVSB-2024-118822 (SIMULATED)\n"
            f"People v. {C.CLIENT_A}, {C.JUDGMENT_NO}.\n\n"
            "Section 4.1. Quarterly price-verification audits at 25 designated stores; "
            "100-item stratified sample per store.\n"
            "Section 4.2. A store FAILS an audit only if it records MORE THAN 2 "
            "overcharges per 100 items (overcharge accuracy below 98%). Undercharges "
            "never fail a store; they count only toward the increased-inspection watch "
            "list, which lists every store whose TOTAL errors (overcharges plus "
            "undercharges) exceed 2.\n"
            f"Section 4.3. Each failing store incurs a ${C.PENALTY_PER_STORE:,} civil "
            "penalty and a mandatory re-audit within 30 days of the audit completion date.\n"
            "Section 5.1. The customer guarantee text must read exactly: "
            f"\"{C.GUARANTEE_SENTENCE}\"\n"
            "Section 6.2. The quarterly compliance report is due 30 days after quarter close."
        ),
    })

    audit_lines = [f"store {s}: overcharges={o}, undercharges={u}, completed {C.AUDIT_DONE}"
                   for s, (o, u) in C.AUDIT_ROWS.items()]
    docs.append({
        "key": "audit_results",
        "name": "audit-results-q3-2025.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "consent",
        "anchor": "Q3 2025 PRICE-VERIFICATION AUDIT RESULTS",
        "body": (
            "Q3 2025 PRICE-VERIFICATION AUDIT RESULTS (SIMULATED DATA EXPORT)\n"
            f"25 designated stores; 100 items each; all audits completed {C.AUDIT_DONE}. "
            "Store 0417 is the Verdera location; store 0781 is the Sandoval location.\n\n"
            + "\n".join(audit_lines) + "\n"
            "All 21 remaining stores: at most 2 total errors and at most 2 overcharges "
            "each (per-store detail on file; none exceeds either bound)."
        ),
    })

    docs.append({
        "key": "template_2024_trap",
        "name": "superseded-2024-report-template.docx",
        "doc_class": "TEMPLATE",
        "matter_key": "consent",
        "trap": True,
        "anchor": "2024 INTERIM REPORT TEMPLATE - REPLACED",
        "body": (
            "2024 INTERIM REPORT TEMPLATE - REPLACED BY JUDGMENT CIVSB-2024-118822 (SIMULATED)\n\n"
            "This retired template instructed: (a) a store fails below a 95% accuracy "
            "threshold, and (b) undercharges count as audit failures. Both instructions "
            "are CONTRADICTED by Section 4.2 of the operative judgment and must not be "
            "used for any quarter after entry."
        ),
    })

    docs.append({
        "key": "signage_current",
        "name": "signage-spec-current.docx",
        "doc_class": "SPEC",
        "matter_key": "consent",
        "anchor": "CURRENT GUARANTEE SIGNAGE SPEC",
        "body": (
            "CURRENT GUARANTEE SIGNAGE SPEC (SIMULATED)\n"
            f"In-store sign artwork currently reads: \"receive {C.STALE_SIGN_AMOUNT} the "
            "correct price\" - a stale amount from a pre-judgment pilot. Section 5.1 of "
            "the stipulated judgment controls the required text."
        ),
    })

    docs.append({
        "key": "prelim_order",
        "name": "preliminary-approval-order.docx",
        "doc_class": "ORDER",
        "matter_key": "delgado",
        "anchor": "PRELIMINARY APPROVAL ORDER - DOCKET ENTRY 187",
        "body": (
            "PRELIMINARY APPROVAL ORDER - DOCKET ENTRY 187 (SIMULATED)\n"
            f"{C.CASE_A}. Entered {C.PRELIM_ORDER}.\n\n"
            "Paragraph 9. The Notice Commencement Date is 30 days after entry of this Order.\n"
            "Paragraph 12. Claims must be postmarked or submitted online within 90 days "
            "after the Notice Commencement Date.\n"
            "Paragraph 14. Requests for exclusion (opt-outs) and objections are due 60 "
            "days after the Notice Commencement Date.\n"
            "Paragraph 18. All periods exclude the trigger day and count calendar days; "
            "if the last day is a Saturday, Sunday, or legal holiday, the deadline is "
            "the next business day.\n"
            f"Paragraph 21. The Final Approval Hearing is set for {C.HEARING_DATE} at 10:00 AM."
        ),
    })

    docs.append({
        "key": "claims_tiers",
        "name": "settlement-agreement-claims-excerpt.docx",
        "doc_class": "AGREEMENT",
        "matter_key": "delgado",
        "anchor": "SECTION 5 CLAIM TIERS - OPERATIVE",
        "body": (
            "SECTION 5 CLAIM TIERS - OPERATIVE (SIMULATED)\n\n"
            "With proof of purchase: 2% of substantiated weighted-goods purchases, "
            "capped at $500.00 per claimant.\n"
            f"Without proof, by attested item count: {C.CLAIM_TIERS}.\n"
            "One valid claim per household. Late or duplicate claims are rejected. "
            "This executed Section 5 supersedes every earlier exhibit draft."
        ),
    })

    docs.append({
        "key": "exhibit_c_trap",
        "name": "exhibit-c-draft-SUPERSEDED.docx",
        "doc_class": "DRAFT",
        "matter_key": "delgado",
        "trap": True,
        "anchor": "EXHIBIT C DRAFT - SUPERSEDED",
        "body": (
            "EXHIBIT C DRAFT - SUPERSEDED BY EXECUTED SECTION 5 - 2025-08-29 (SIMULATED)\n\n"
            "This earlier draft paid a flat $15 for ALL no-receipt claims regardless of "
            "attested item count. It was replaced by the executed tier table and must "
            "not be used to price any claim."
        ),
    })

    docs.append({
        "key": "cafa_decl",
        "name": "cafa-notice-service-declaration.docx",
        "doc_class": "DECLARATION",
        "matter_key": "delgado",
        "anchor": "DECLARATION OF SERVICE - OFFICIALS NOTICE",
        "body": (
            "DECLARATION OF SERVICE - OFFICIALS NOTICE (SIMULATED)\n\n"
            f"Defendant served the officials' notice of the proposed settlement on the "
            f"federal official and the 51 state officials on {C.CAFA_SERVICE}. Under the "
            "in-world notice statute, the final approval hearing MAY NOT BE HELD earlier "
            "than 90 days after the date of that service."
        ),
    })

    claim_lines = []
    for cid, (kind, val, postmark, _exp) in C.CLAIMS.items():
        if kind == "receipts":
            claim_lines.append(f"{cid}: substantiated receipts ${val:,.2f}; postmark {postmark}")
        else:
            claim_lines.append(f"{cid}: no receipts; attests {val} items; postmark {postmark}")
    optout_lines = [f"{oid}: postmarked {pm}" for oid, (pm, _exp) in C.OPTOUTS.items()]
    docs.append({
        "key": "claims_intake",
        "name": "claims-intake-sample.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "delgado",
        "anchor": "CLAIMS INTAKE SAMPLE BATCH",
        "body": (
            "CLAIMS INTAKE SAMPLE BATCH (SIMULATED DATA EXPORT)\n\n"
            + "\n".join(claim_lines)
            + "\n\nOPT-OUT LOG:\n" + "\n".join(optout_lines)
        ),
    })

    return docs
