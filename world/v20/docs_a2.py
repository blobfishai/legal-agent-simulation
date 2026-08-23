"""Seeded documents for family A, continued: ARL sweep and junk-fee matters."""
from __future__ import annotations

from world.v20 import content as C

GENERIC_ARL_PHRASE = ("clear-and-conspicuous ARL disclosure, affirmative consent, "
                      "renewal reminder, online cancellation")


def _arl_state_line(j: str) -> str:
    name = C.JUR_NAME[j]
    if j in C.ARL_PINS:
        return f"{j} ({name}): statute=YES. obligations=\"{C.ARL_PINS[j]}\"."
    if j == "FL":
        return f"{j} ({name}): statute=NO - {C.FL_ARL_TRAP}."
    if j in C.ARL_YES:
        return f"{j} ({name}): statute=YES. obligations=\"{GENERIC_ARL_PHRASE}\"."
    return f"{j} ({name}): statute=NO - general UDAP only."


def _arl_region_doc(idx: int, states: list[str]) -> dict:
    rng = f"{states[0]}-{states[-1]}"
    return {
        "key": f"arl_memo_r{idx}",
        "name": f"state-arl-memo-pack-region-{idx}.docx",
        "doc_class": "MEMO",
        "matter_key": "arl",
        "anchor": f"STATE AUTO-RENEWAL MEMO PACK - REGION {idx} ({rng})",
        "body": (
            f"STATE AUTO-RENEWAL MEMO PACK - REGION {idx} ({rng}) (SIMULATED)\n"
            f"Prepared for {C.CLIENT_ARL}. This pack IS the controlling in-world law "
            "for the 51-jurisdiction sweep.\n\n"
            + "\n".join(_arl_state_line(j) for j in states)
            + "\n\nEND OF REGION MEMO."
        ),
    }


def family_a2_docs() -> list[dict]:
    docs: list[dict] = []

    docs.append({
        "key": "fcb_order",
        "name": "fcb-consent-order.docx",
        "doc_class": "ORDER",
        "matter_key": "arl",
        "anchor": "FEDERAL CONSUMER BUREAU CONSENT ORDER - COBALT PEAK",
        "body": (
            "FEDERAL CONSUMER BUREAU CONSENT ORDER - COBALT PEAK MEDIA, LLC (SIMULATED)\n"
            f"Entered {C.FCB_ORDER_DATE}. Civil penalty: {C.FCB_PENALTY}.\n\n"
            "Section III (Injunctive Terms). (a) Material terms - price, renewal date, "
            "and cancellation method - must be disclosed immediately adjacent to the "
            "enrollment button. (b) An online cancellation path reachable in "
            f"{C.TWO_CLICK_RULE}, with the control labeled exactly "
            f"\"{C.CANCEL_LABEL}\". (c) {C.RETENTION_RULE} before cancellation completes.\n\n"
            "Section V (Deadline). All remediation must be complete within 90 days of entry."
        ),
    })

    for i, states in enumerate(C.REGIONS, 1):
        docs.append(_arl_region_doc(i, states))

    docs.append({
        "key": "fed_addendum",
        "name": "federal-negative-option-addendum.docx",
        "doc_class": "MEMO",
        "matter_key": "arl",
        "anchor": "FEDERAL ADDENDUM - NEGATIVE-OPTION RULE STATUS",
        "body": (
            "FEDERAL ADDENDUM - NEGATIVE-OPTION RULE STATUS (SIMULATED)\n\n"
            "The federal negative-option (subscription) rule was VACATED in full by the "
            f"court of appeals on {C.FED_VACATUR_DATE}, before its compliance date. It is "
            "NOT in effect and must not be cited as governing law. The ROSCA-analog "
            "statute and general UDAP law remain fully applicable. Any matrix row for "
            "the federal layer must carry status=VACATED with that date."
        ),
    })

    docs.append({
        "key": "arl_draft_trap",
        "name": "draft-arl-matrix-v0-STALE.docx",
        "doc_class": "DRAFT",
        "matter_key": "arl",
        "trap": True,
        "anchor": "DRAFT ARL MATRIX v0 - STALE",
        "body": (
            "DRAFT ARL MATRIX v0 - STALE, DO NOT USE (SIMULATED)\n\n"
            "Known defects: (1) a federal row citing the vacated subscription rule as "
            f"\"effective {C.FED_TRAP_EFFECTIVE} - controls nationwide\"; (2) FL marked "
            "statute=YES with the streaming plan in scope; (3) only 48 state rows - "
            "DC, VT, and WY are missing entirely, so the row count is wrong."
        ),
    })

    docs.append({
        "key": "renewal_email_current",
        "name": "renewal-email-template-current.docx",
        "doc_class": "TEMPLATE",
        "matter_key": "arl",
        "anchor": "CURRENT RENEWAL EMAIL TEMPLATE",
        "body": (
            "CURRENT RENEWAL EMAIL TEMPLATE (SIMULATED)\n\n"
            "Subject: Thanks for being a member!\nBody: \"Thanks for being a member!\" "
            "The template contains NO renewal date, NO price, and NO cancellation link. "
            "It must be rewritten for the annual plan."
        ),
    })

    docs.append({
        "key": "cancel_flow_current",
        "name": "cancel-flow-spec-current.docx",
        "doc_class": "SPEC",
        "matter_key": "arl",
        "anchor": "CURRENT CANCEL FLOW SPEC",
        "body": (
            "CURRENT CANCEL FLOW SPEC (SIMULATED)\n\n"
            "Six steps from the account page, including three sequential retention "
            "offers and a final \"call us to confirm\" step. This violates Section "
            "III(b)-(c) of the consent order and is the before-state for remediation."
        ),
    })

    docs.append({
        "key": "plan_catalog",
        "name": "plan-catalog.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "arl",
        "anchor": "PEAKSTREAM+ PLAN CATALOG",
        "body": (
            "PEAKSTREAM+ PLAN CATALOG (SIMULATED DATA EXPORT)\n\n"
            f"Monthly plan: {C.MONTHLY_PRICE} per month; initial term 1 month; no trial.\n"
            f"Annual plan: {C.ANNUAL_PRICE} per year; initial term 12 months; free trial "
            f"{C.TRIAL_DAYS} days.\n"
            "Use this table to determine which state rules attach to which plan."
        ),
    })

    docs.append({
        "key": "checkout_screens",
        "name": "checkout-flow-screens.docx",
        "doc_class": "SPEC",
        "matter_key": "arl",
        "anchor": "CURRENT ENROLLMENT CHECKOUT SCREENS",
        "body": (
            "CURRENT ENROLLMENT CHECKOUT SCREENS (SIMULATED)\n\n"
            "Price appears only on a prior page; renewal terms sit in a footnote below "
            "the fold; the button is labeled \"Start Membership\" with no adjacent "
            "disclosure box. Before-state for the Section III(a) remediation."
        ),
    })

    docs.append({
        "key": "ag_cid",
        "name": "ag-civil-investigative-demand.docx",
        "doc_class": "DEMAND",
        "matter_key": "fees",
        "anchor": "CIVIL INVESTIGATIVE DEMAND - DRIP PRICING",
        "body": (
            "CIVIL INVESTIGATIVE DEMAND - DRIP PRICING (SIMULATED)\n\n"
            f"Served on {C.CLIENT_FEE} on {C.CID_SERVED}, citing the state UDAP act and "
            "the in-world federal lodging-fee rule. Demands the fee schedule, booking "
            "screens, and a remediation plan within 45 days of service."
        ),
    })

    docs.append({
        "key": "fee_schedule",
        "name": "fee-schedule.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "fees",
        "anchor": "PROPERTY FEE SCHEDULE - HARBOR KING",
        "body": (
            "PROPERTY FEE SCHEDULE - HARBOR KING PINNED ROW (SIMULATED DATA EXPORT)\n\n"
            f"Harbor King room: base {C.ROOM_BASE} per night; MANDATORY amenity fee "
            f"{C.AMENITY_FEE} per night; processing fee {C.PROCESSING_FEE} per stay; "
            f"occupancy tax {C.OCC_TAX} (government-imposed).\n"
            f"Restaurant tab: {C.SERVICE_CHARGE} service charge at 9 of 27 properties.\n"
            "All 27 properties carry the same mandatory amenity-fee structure."
        ),
    })

    docs.append({
        "key": "fee_memo_pack",
        "name": "pricing-law-memo-pack-federal-and-states.docx",
        "doc_class": "MEMO",
        "matter_key": "fees",
        "anchor": "PRICING-LAW MEMO PACK - FEDERAL AND STATES (FEES)",
        "body": (
            "PRICING-LAW MEMO PACK - FEDERAL AND STATES (FEES) (SIMULATED)\n\n"
            "FEDERAL LODGING-FEE RULE: IN EFFECT since "
            f"{C.FED_FEE_EFFECTIVE}. Total price including all known mandatory fees must "
            "be disclosed up front; government-imposed taxes and shipping are excludable "
            "if disclosed before payment. Civil penalty: up to "
            f"{C.FED_FEE_PENALTY} per violation. NOTE: this rule is DISTINCT from the "
            f"subscription negative-option rule vacated {C.FED_VACATUR_DATE}; do not "
            "confuse them.\n\n"
            f"CA-style all-in pricing statute: effective {C.FEE_EFFECTIVES['CA-style']}; "
            "restaurant exception - mandatory food-service charges are lawful IF clearly "
            "and conspicuously displayed wherever prices are shown.\n"
            f"MN-style all-in pricing statute: effective {C.FEE_EFFECTIVES['MN-style']}.\n"
            f"MA-style regulation: effective {C.FEE_EFFECTIVES['MA-style']}; total price "
            "at first presentation; opt-out instructions for optional fees.\n\n"
            "All other 48 jurisdictions: general UDAP only. Exactly 3 jurisdictions "
            "carry bespoke all-in-pricing statutes or regulations."
        ),
    })

    docs.append({
        "key": "fee_draft_trap",
        "name": "draft-matrix-and-memo-v0-TRAP.docx",
        "doc_class": "DRAFT",
        "matter_key": "fees",
        "trap": True,
        "anchor": "JUNIOR ASSOCIATE DRAFT v0 - UNRELIABLE",
        "body": (
            "JUNIOR ASSOCIATE DRAFT v0 - UNRELIABLE (SIMULATED)\n\n"
            "This draft asserts: \"the federal fee rule was vacated by the court of "
            "appeals in July 2025, so only state law applies\" and recommends "
            "\"eliminate the 18% restaurant service charge entirely.\" Both statements "
            "are contradicted by the operative memo pack (the vacated rule was the "
            "SUBSCRIPTION rule; the fee rule is in effect, and the restaurant exception "
            "permits a clearly disclosed service charge)."
        ),
    })

    docs.append({
        "key": "booking_screens",
        "name": "booking-flow-screens.docx",
        "doc_class": "SPEC",
        "matter_key": "fees",
        "anchor": "CURRENT BOOKING FLOW SCREENS",
        "body": (
            "CURRENT BOOKING FLOW SCREENS (SIMULATED)\n\n"
            f"Step 1 advertises \"Harbor King - {C.ROOM_BASE.rstrip('0').rstrip('.') if False else '$189'}/night\". "
            f"Step 3 first reveals \"Amenity Fee {C.AMENITY_FEE}/night\" and \"Processing "
            f"Fee {C.PROCESSING_FEE}/stay\" inside a collapsed \"taxes & fees\" lump with "
            f"the {C.OCC_TAX} occupancy tax. Before-state for remediation."
        ),
    })

    docs.append({
        "key": "menu_folio",
        "name": "menu-and-folio-samples.docx",
        "doc_class": "SPEC",
        "matter_key": "fees",
        "anchor": "MENU AND FOLIO SAMPLES",
        "body": (
            "MENU AND FOLIO SAMPLES (SIMULATED)\n\n"
            "The restaurant menu contains NO service-charge disclosure anywhere; the "
            f"guest folio shows the {C.SERVICE_CHARGE} charge appearing only at checkout. "
            "Remediation must add a clear-and-conspicuous menu disclosure line without "
            "abolishing the charge."
        ),
    })

    return docs
