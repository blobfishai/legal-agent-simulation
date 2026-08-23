"""Seeded documents for family B (consumer-protection-privacy)."""
from __future__ import annotations

from world.v20 import content as C


def family_b_docs() -> list[dict]:
    docs: list[dict] = []

    docs.append({
        "key": "suarez_settlement",
        "name": "suarez-settlement-agreement.docx",
        "doc_class": "AGREEMENT",
        "matter_key": "bipa",
        "anchor": "SUAREZ v. PRAIRIE GRILL HOLDINGS, INC. - EXECUTED SETTLEMENT",
        "body": (
            "SUAREZ v. PRAIRIE GRILL HOLDINGS, INC. - EXECUTED SETTLEMENT (SIMULATED)\n\n"
            f"Fund: {C.BIPA_FUND} covering {C.BIPA_CLASS:,} class members. Effective "
            f"Date: {C.BIPA_ED}.\n\n"
            "Section 6 (Injunctive Relief) - due within 45 days of the Effective Date:\n"
            "(a) a biometric retention-and-destruction policy posted publicly on the "
            "company website;\n"
            "(b) a statute-compliant written-release consent form for all active "
            "employees;\n"
            "(c) a vendor contract amendment requiring certified destruction of "
            "templates within 30 days of a company request."
        ),
    })

    docs.append({
        "key": "bipa_statute",
        "name": "biometric-statute-and-2024-amendment-memo.docx",
        "doc_class": "MEMO",
        "matter_key": "bipa",
        "anchor": "BIOMETRIC PRIVACY ACT MEMO AND 2024 AMENDMENT",
        "body": (
            "BIOMETRIC PRIVACY ACT MEMO AND 2024 AMENDMENT (SIMULATED IN-WORLD LAW)\n\n"
            "Destruction: required when the initial purpose is satisfied OR within 3 "
            "years of the individual's last interaction with the company, whichever "
            "occurs FIRST.\n"
            f"Liquidated damages: ${C.NEGLIGENT_RATE:,} per negligent violation; "
            f"${C.RECKLESS_RATE:,} per reckless violation.\n"
            "Consent: written notice stating the specific purpose and the length of "
            "term; a written release is required before collection.\n"
            "2024 amendment: (i) one violation per person per method of collection "
            "regardless of scan count; (ii) a written release MAY be executed by "
            "electronic signature.\n"
            "Coverage: stored templates, hashes, and \"mathematical representations\" of "
            "fingerprints ARE biometric identifiers under this Act. A vendor claim to "
            "the contrary is wrong as a matter of law."
        ),
    })

    roster_lines = []
    for eid, (status, last, _dest) in C.ROSTER.items():
        if status == "pin-only":
            roster_lines.append(f"{eid}: PIN-only user; template id NULL (never enrolled)")
        elif status == "active":
            roster_lines.append(f"{eid}: ACTIVE; timekeeping purpose ongoing")
        else:
            roster_lines.append(f"{eid}: terminated; last scan {last}")
    docs.append({
        "key": "roster",
        "name": "hr-biometric-roster.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "bipa",
        "anchor": "HR BIOMETRIC ROSTER - PINNED ROWS",
        "body": (
            "HR BIOMETRIC ROSTER - PINNED ROWS (SIMULATED DATA EXPORT)\n\n"
            + "\n".join(roster_lines)
            + "\nRemaining roster rows are not in scope for the pinned schedule."
        ),
    })

    docs.append({
        "key": "vendor_msa",
        "name": "timeclock-vendor-msa.docx",
        "doc_class": "AGREEMENT",
        "matter_key": "bipa",
        "anchor": "TIMECLOCK VENDOR MASTER SERVICES AGREEMENT",
        "body": (
            "TIMECLOCK VENDOR MASTER SERVICES AGREEMENT (SIMULATED)\n\n"
            "The MSA contains NO deletion, destruction-certification, or "
            "biometric-specific clause. Renewal date: 2026-01-31. Section 14: "
            "amendments require a written instrument signed by both parties."
        ),
    })

    docs.append({
        "key": "vendor_letter_trap",
        "name": "vendor-position-letter.docx",
        "doc_class": "CORRESPONDENCE",
        "matter_key": "bipa",
        "trap": True,
        "anchor": "VENDOR POSITION LETTER - CONTESTED",
        "body": (
            "VENDOR POSITION LETTER - CONTESTED (SIMULATED)\n\n"
            "The timeclock vendor asserts its system stores only \"irreversible "
            "mathematical representations,\" which it claims are not biometric "
            "identifiers and therefore need no consent, retention policy, or deletion "
            "obligations. This position is directly contradicted by the statute memo's "
            "express coverage of templates and hashes."
        ),
    })

    docs.append({
        "key": "exposure_inputs",
        "name": "exposure-model-inputs.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "bipa",
        "anchor": "EXPOSURE MODEL INPUTS",
        "body": (
            "EXPOSURE MODEL INPUTS (SIMULATED DATA EXPORT)\n\n"
            f"Class members: {C.BIPA_CLASS:,}. Average scans per member: "
            f"{C.SCANS_PER_MEMBER:,}. Negligent rate: ${C.NEGLIGENT_RATE:,}. Reckless "
            f"rate: ${C.RECKLESS_RATE:,}.\n"
            "Compute per-scan exposure (members x scans x rate) and post-amendment "
            "per-person exposure (members x rate) for the negotiation-history memo."
        ),
    })

    docs.append({
        "key": "forensic_report",
        "name": "forensic-incident-report.docx",
        "doc_class": "REPORT",
        "matter_key": "breach",
        "anchor": "FORENSIC INCIDENT REPORT - HARBORLINE",
        "body": (
            "FORENSIC INCIDENT REPORT - HARBORLINE OUTFITTERS (SIMULATED)\n\n"
            "Intrusion window 2025-04-14 to 2025-05-28; anomaly detected 2025-05-19; "
            "forensic DETERMINATION of unauthorized acquisition fixed at "
            f"{C.DETERMINATION} (the statutory trigger).\n"
            f"Affected residents: {C.TOTAL_AFFECTED:,} across all 50 states and DC. "
            f"Store-cardholders with SSNs exposed: {C.SSN_SUBSET:,} (including every "
            "affected CT resident).\n"
            "Attack method: credential stuffing against the loyalty API.\n"
            f"Encryption appendix: the ND-resident segment ({C.RESIDENT_PINNED['ND']:,} "
            "residents) lived on an encrypted volume whose key was NOT compromised."
        ),
    })

    count_lines = []
    for j in C.JURISDICTIONS:
        n = C.RESIDENT_PINNED.get(j, C.RESIDENT_FILLER.get(j))
        count_lines.append(f"{j}: {n:,}")
    docs.append({
        "key": "resident_counts",
        "name": "resident-counts-by-state.xlsx.txt",
        "doc_class": "DATA",
        "matter_key": "breach",
        "anchor": "AFFECTED RESIDENT COUNTS BY JURISDICTION",
        "body": (
            "AFFECTED RESIDENT COUNTS BY JURISDICTION (SIMULATED DATA EXPORT)\n"
            f"Total affected: {C.TOTAL_AFFECTED:,}.\n"
            + "\n".join(count_lines)
        ),
    })

    ag_list = ", ".join(C.AG_SET)
    docs.append({
        "key": "breach_memo_pinned",
        "name": "breach-statute-memo-pack-part-1-pinned-states.docx",
        "doc_class": "MEMO",
        "matter_key": "breach",
        "anchor": "BREACH STATUTE MEMO PACK - PART 1 (PINNED STATES)",
        "body": (
            "BREACH STATUTE MEMO PACK - PART 1 (PINNED STATES) (SIMULATED IN-WORLD LAW)\n\n"
            "CO, FL, ME, WA: resident notice within 30 days of determination.\n"
            "TX: residents within 60 days; AG within 30 days when 250 or more Texas "
            "residents are affected.\n"
            "CA: when more than 500 CA residents are affected, the AG receives a sample "
            "copy of the notice (personal information excluded) within 15 days after "
            "consumer notification.\n"
            "OR: AG notice only when MORE than 250 Oregon residents are affected.\n"
            "MA: the resident notice MUST NOT describe the nature of the breach or the "
            "number of residents affected; it MUST offer a security freeze at no charge "
            "and mitigation services; the AG is notified regardless of count.\n"
            "CT: 24 months of credit monitoring at no cost whenever SSNs are involved.\n"
            "ND: encryption safe harbor - NO notice required when the data was "
            "encrypted and the key was not compromised."
        ),
    })

    docs.append({
        "key": "breach_memo_defaults",
        "name": "breach-statute-memo-pack-part-2-defaults-and-ag-table.docx",
        "doc_class": "MEMO",
        "matter_key": "breach",
        "anchor": "BREACH STATUTE MEMO PACK - PART 2 (DEFAULTS AND AG TABLE)",
        "body": (
            "BREACH STATUTE MEMO PACK - PART 2 (DEFAULTS AND AG TABLE) (SIMULATED)\n\n"
            "All jurisdictions not pinned in Part 1: notice without unreasonable delay; "
            "firm policy calendars these at 45 days from determination.\n\n"
            "AG/REGULATOR SUMMARY TABLE: applying this pack's thresholds to the "
            "resident-counts workbook, AG or regulator notice is required in EXACTLY 27 "
            f"jurisdictions: {ag_list}. OR is excluded (214 residents is below its "
            "threshold); ND is excluded by the encryption safe harbor."
        ),
    })

    docs.append({
        "key": "letter_draft",
        "name": "notification-letter-draft.docx",
        "doc_class": "DRAFT",
        "matter_key": "breach",
        "anchor": "RESIDENT NOTIFICATION LETTER - WORKING DRAFT",
        "body": (
            "RESIDENT NOTIFICATION LETTER - WORKING DRAFT (SIMULATED)\n\n"
            "Current draft text says: \"attackers used credential stuffing against our "
            f"loyalty API, affecting {C.TOTAL_AFFECTED:,} customers.\" That language is "
            "unlawful in the MA variant and must be stripped there. The draft is also "
            "missing the security-freeze paragraph and the credit-monitoring offer."
        ),
    })

    docs.append({
        "key": "playbook_trap",
        "name": "legacy-ir-playbook-2019-RETIRED.docx",
        "doc_class": "TEMPLATE",
        "matter_key": "breach",
        "trap": True,
        "anchor": "2019 INCIDENT-RESPONSE PLAYBOOK - RETIRED",
        "body": (
            "2019 INCIDENT-RESPONSE PLAYBOOK - RETIRED 2024, RETAINED FOR RECORDS (SIMULATED)\n\n"
            "This retired playbook instructed \"45 days to notify in all states\" and "
            "\"AG letters only in California and New York.\" Both instructions are "
            "contradicted by the operative memo pack and must not be followed."
        ),
    })

    docs.append({
        "key": "monitor_quote",
        "name": "credit-monitoring-vendor-quote.docx",
        "doc_class": "QUOTE",
        "matter_key": "breach",
        "anchor": "CREDIT MONITORING VENDOR QUOTE",
        "body": (
            "CREDIT MONITORING VENDOR QUOTE (SIMULATED)\n\n"
            f"Price: ${C.MONITOR_RATE:.2f} per enrollee per year. CT obligation math: "
            f"{C.RESIDENT_PINNED['CT']:,} CT residents x 2 years x ${C.MONITOR_RATE:.2f} "
            f"= ${C.CT_MONITOR_COST}."
        ),
    })

    return docs
