"""Content model for the v20 real-world consumer-protection task families.

Single source of truth: every pinned figure lives here once and flows into
(a) the seeded document bodies, (b) the task prompts, (c) the oracle
reference deliverables, and (d) the verifier assertions.  ``validate()``
re-derives every date and every sum and fails the build on any drift.

Simulation only: every company, person, court, statute, and figure below is
synthetic test data.  Real cases (Kukorinis v. Walmart, the CA DA consent
judgments, FTC v. Amazon, Cothron v. White Castle, the Equifax multistate
settlement) supplied task SHAPES only — see research/realworld-tasks/RESEARCH.md.
"""
from __future__ import annotations

if not __debug__:
    raise RuntimeError("validation requires assertions; Python optimization is unsupported")

import datetime as _dt

# ---------------------------------------------------------------------------
# Jurisdictions
# ---------------------------------------------------------------------------

JURISDICTIONS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
]
assert len(JURISDICTIONS) == 51

REGION_SLICES = [(0, 9), (9, 18), (18, 27), (27, 36), (36, 45), (45, 51)]
REGIONS = [JURISDICTIONS[a:b] for a, b in REGION_SLICES]

JUR_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# ---------------------------------------------------------------------------
# Family A1 — Halvorsen Market Group / Delgado settlement (price accuracy)
# ---------------------------------------------------------------------------

CLIENT_A = "Halvorsen Market Group, Inc."
CASE_A = "Delgado v. Halvorsen Market Group, Inc., No. 8:24-cv-03117 (M.D. Fla.) (SIMULATED)"
EFFECTIVE_DATE = "2025-09-15"
SURVEY_DUE = "2025-11-14"           # Effective Date + 60 (Friday, no roll)
S75_RAW_DUE = "2025-12-14"          # Effective Date + 90 (Sunday)
S75_DUE = "2025-12-15"              # rolled per Section 7.6
FUND_A = "$42,500,000"

FOOTER_SENTENCE = ("If an item rings up higher than the lowest posted or "
                   "advertised price, you are entitled to the lower price at the register.")
OFFENDING_SENTENCE = ("In the event of any discrepancy, the price charged at "
                      "the point of sale shall control.")
REPLACEMENT_PHRASE = "the lowest posted, advertised, or shelf price"
RECEIPT_LINE_FORMAT = "NET WT {weight} LB @ ${unit_price}/LB"
CHICKEN_EXAMPLE = "CHKN BRST FAM PK  NET WT 3.12 LB @ $4.75/LB  $14.82"

# Canonical matrix row grammar (stated in the prompt; phrases copied verbatim
# from the memo pack's remedy_phrase / duty_phrase fields).
ITEM_PRICING = {
    "MI": {
        "cite": "Halloran Consumer Sales Act SS 445.11-445.24 (SIMULATED)",
        "remedy_phrase": ("refund plus a bonus of 10x the difference, "
                          "minimum $1.00, maximum $5.00"),
        "duty_phrase": "post the price-accuracy notice at every register",
    },
    "MA": {
        "cite": "Gen. Laws ch. 94A SS 184B-184E (SIMULATED)",
        "remedy_phrase": ("sell at the lowest of the item, shelf, or advertised "
                          "price; scope: food stores and food departments only"),
        "duty_phrase": "scanner-waiver annual fee $250 / $500 / $1,000 by store size",
    },
    "CT": {
        "cite": "Consumer Pricing Act S 21b-79 (SIMULATED)",
        "remedy_phrase": "item free on demand when the scanned price exceeds the posted price",
        "duty_phrase": "electronic-shelf-label exemption available on registration",
    },
    "CA": {
        "cite": "Bus. & Prof. Code S 12024.9 (SIMULATED)",
        "remedy_phrase": ("civil penalty up to $1,000 per violation; county "
                          "weights-and-measures enforcement; private bounty = NO"),
        "duty_phrase": "honor the lowest posted or advertised price at the register",
    },
    "NH": {
        "cite": "Rev. Stat. S 358-Q:4 (SIMULATED)",
        "remedy_phrase": "refund of the difference plus a $2.00 accuracy credit",
        "duty_phrase": "quarterly scanner-accuracy self-audit filed with the state",
    },
    "RI": {
        "cite": "Gen. Laws S 6-13.2-5 (SIMULATED)",
        "remedy_phrase": "item free up to a $10.00 maximum when overscanned",
        "duty_phrase": "item pricing required unless a scanner-waiver decal is displayed",
    },
}
STATUTE_STATES = sorted(ITEM_PRICING)          # CA, CT, MA, MI, NH, RI
UDAP_ROW_PHRASE = "no item-pricing or scanner statute - general UDAP only"
WY_TRAP_NOTE = ("the oft-cited Wyoming Retail Price Accuracy Act died in "
                "committee in 2019 and was never enacted")
NY_TRAP_NOTE = ("the statewide item-pricing law sunset in 2012; only three "
                "county ordinances survive, so the statewide answer is NO")

STORE_COUNTS = {"MI": 61, "MA": 38, "CT": 27, "NH": 11, "RI": 8, "CA": 172}
PR_STORES = 23
TOTAL_STORES = 1684
REMEDIATION_STORES = sum(STORE_COUNTS.values())            # 317
_filler_states = [j for j in JURISDICTIONS if j not in STORE_COUNTS]
_filler_total = TOTAL_STORES - REMEDIATION_STORES - PR_STORES  # 1,344 over 45
STORE_FILLER = {}
for _i, _j in enumerate(_filler_states):
    STORE_FILLER[_j] = 29 + (1 if _i < (_filler_total - 29 * len(_filler_states)) else 0)

# ---------------------------------------------------------------------------
# Family A2 — Halvorsen consent-judgment audit (San Bernal County)
# ---------------------------------------------------------------------------

JUDGMENT_NO = "San Bernal County Superior Court No. CIVSB-2024-118822 (SIMULATED)"
AUDIT_DONE = "2025-09-24"
REAUDIT_DUE = "2025-10-24"          # +30
QUARTER_CLOSE = "2025-09-30"
REPORT_DUE = "2025-10-30"           # +30
PENALTY_PER_STORE = 2500
GUARANTEE_SENTENCE = ("If we charge more than the lowest posted or advertised "
                      "price, you will receive $3.00 off the correct price. "
                      "If the item costs $3.00 or less, it is free.")
STALE_SIGN_AMOUNT = "$2.00 off"
AUDIT_ROWS = {  # store: (overcharges, undercharges) out of 100 items
    "0417": (4, 1),   # FAIL — Verdera
    "0233": (2, 0),   # PASS boundary (fail requires MORE than 2 overcharges)
    "0781": (3, 0),   # FAIL — Sandoval
    "0522": (0, 6),   # PASS (undercharges never fail a store)
}
FAILING_STORES = ["0417", "0781"]
WATCHLIST = ["0417", "0522", "0781"]           # total errors > 2
TOTAL_PENALTIES = PENALTY_PER_STORE * len(FAILING_STORES)  # $5,000
RIDER_STATES = ["CT", "MI"]                    # $3 guarantee cannot displace these
SUFFICIENT_AS_IS = 51 - len(RIDER_STATES)      # 49

# ---------------------------------------------------------------------------
# Family A3 — claims administration calendar (Delgado)
# ---------------------------------------------------------------------------

PRELIM_ORDER = "2025-10-06"
NOTICE_DATE = "2025-11-05"          # +30
CLAIMS_DEADLINE = "2026-02-03"      # notice +90 (Tuesday)
OPTOUT_RAW = "2026-01-04"           # notice +60 (Sunday)
OPTOUT_FINAL = "2026-01-05"         # rolled
CAFA_SERVICE = "2025-10-10"
HEARING_FLOOR = "2026-01-08"        # +90
HEARING_DATE = "2026-02-24"
CLAIM_TIERS = "1-50 items = $10; 51-75 = $15; 76-100 = $20; 101 or more = $25"
CLAIMS = {
    # id: (kind, amount_or_items, postmark, expected)
    "C-0011": ("receipts", 18400.00, "2026-01-20", "APPROVED | $368.00"),
    "C-0027": ("receipts", 31250.00, "2026-01-28", "APPROVED | $500.00"),
    "C-0042": ("attest", 88, "2026-02-02", "APPROVED | $20.00"),
    "C-0058": ("attest", 40, "2026-01-15", "APPROVED | $10.00"),
    "C-0063": ("attest", 60, "2026-02-04", "REJECTED | late"),
    "C-0075": ("attest", 120, "2026-01-30", "APPROVED | $25.00"),
}
TOTAL_APPROVED = "923.00"
OPTOUTS = {"O-004": ("2026-01-05", "TIMELY"), "O-007": ("2026-01-09", "LATE")}

# ---------------------------------------------------------------------------
# Family A4 — Cobalt Peak Media auto-renewal sweep
# ---------------------------------------------------------------------------

CLIENT_ARL = "Cobalt Peak Media, LLC (PeakStream+) (SIMULATED)"
FCB_ORDER_DATE = "2025-06-20"
FCB_PENALTY = "$18,000,000"
ARL_REMEDIATION_DUE = "2025-09-18"  # +90 (Thursday)
FED_VACATUR_DATE = "2025-07-08"
FED_TRAP_EFFECTIVE = "2025-07-14"   # the stale draft's wrong claim
MONTHLY_PRICE = "$11.99"
ANNUAL_PRICE = "$119.99"
TRIAL_DAYS = 45
ARL_YES = [
    "CA", "NY", "VT", "IL", "DC", "CO", "CT", "DE", "GA", "HI", "ID", "IA",
    "LA", "ME", "MD", "MA", "MN", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NC", "ND", "OR", "SC", "TN", "TX",
]
ARL_NO = [j for j in JURISDICTIONS if j not in ARL_YES]   # 21 incl. FL
ARL_PINS = {
    "CA": ("separate affirmative consent; annual renewal reminder; annual-plan "
           "renewal notice 15-45 days before renewal; trials longer than 31 days "
           "get a reminder 3-21 days before trial end; cancel in the same medium; "
           "consent records kept 3 years or 1 year after termination, whichever is longer"),
    "NY": ("clear-and-conspicuous offer terms; post-purchase acknowledgment with "
           "cancellation instructions; online cancellation required"),
    "VT": ("auto-renewal term accepted by a separate affirmative opt-in; applies "
           "only to initial terms of one year or longer, so monthly plan = out of scope"),
    "IL": ("renewal notice 30-60 days before the cancellation deadline for "
           "12-month contracts renewing 12+ months; annual plan only"),
    "DC": ("renewal notice 30-60 days before renewal for 12-month+ terms; "
           "affirmative consent for free-trial conversions of one month or longer"),
}
FL_ARL_TRAP = ("the statute covers only defined tangible service contracts and "
               "expressly excludes digital subscription streaming, so FL = NO / UDAP-only")
CANCEL_LABEL = "Cancel Subscription"
RENEW_PHRASE = "will automatically renew on"
CHECKOUT_PHRASE = "cancel anytime online"
RETENTION_RULE = "at most one retention offer"
TWO_CLICK_RULE = "no more than 2 clicks from the account page"

# ---------------------------------------------------------------------------
# Family A5 — Bluewater Lodge & Resorts junk-fee remediation
# ---------------------------------------------------------------------------

CLIENT_FEE = "Bluewater Lodge & Resorts Co. (SIMULATED)"
CID_SERVED = "2025-07-21"
CID_DUE = "2025-09-04"              # +45 (Thursday)
FED_FEE_EFFECTIVE = "2025-05-12"
FED_FEE_PENALTY = "$51,744"
ROOM_BASE = "$189.00"
AMENITY_FEE = "$39.95"
PROCESSING_FEE = "$12.00"
ALLIN_NIGHTLY = "$228.95"           # 189.00 + 39.95
THREE_NIGHT_TOTAL = "$698.85"       # 3 x 228.95 + 12.00
AD_STRING = "$228.95 per night (total before taxes)"
OCC_TAX = "11.5%"
SERVICE_CHARGE = "18%"
BESPOKE_FEE_STATES = 3              # CA-style, MN-style, MA-style memos
FEE_EFFECTIVES = {"CA-style": "2024-07-01", "MN-style": "2025-01-01", "MA-style": "2025-09-02"}

# ---------------------------------------------------------------------------
# Family B1 — Prairie Grill biometric (Suarez) remediation
# ---------------------------------------------------------------------------

CLIENT_BIPA = "Prairie Grill Holdings, Inc. (SIMULATED)"
BIPA_FUND = "$9,750,000"
BIPA_CLASS = 8400
BIPA_ED = "2025-08-01"
BIPA_DUE = "2025-09-15"             # +45 (Monday)
SCANS_PER_MEMBER = 1850
NEGLIGENT_RATE = 1000
RECKLESS_RATE = 5000
PER_SCAN_NEGLIGENT = BIPA_CLASS * SCANS_PER_MEMBER * NEGLIGENT_RATE   # 15,540,000,000
PER_PERSON_NEGLIGENT = BIPA_CLASS * NEGLIGENT_RATE                    # 8,400,000
PER_PERSON_RECKLESS = BIPA_CLASS * RECKLESS_RATE                      # 42,000,000
ROSTER = {
    "E-1002": ("terminated", "2023-04-18", "2026-04-18"),
    "E-1044": ("terminated", "2024-11-30", "2027-11-30"),
    "E-1177": ("terminated", "2022-06-30", "OVERDUE"),    # 2025-06-30 already passed
    "E-1203": ("active", None, "3 years of separation or purpose end"),
    "E-1288": ("pin-only", None, "NO ACTION - no biometric data"),
}
VENDOR_DESTRUCTION = "certified destruction within 30 days"
CONSENT_PHRASES = ["specific purpose", "length of term", "electronic signature"]
POLICY_PHRASE = "posted publicly on the company website"
VENDOR_VERDICT = "vendor position REJECTED"

# ---------------------------------------------------------------------------
# Family B2 — Harborline Outfitters breach notification grid
# ---------------------------------------------------------------------------

CLIENT_BREACH = "Harborline Outfitters, Inc. (SIMULATED)"
DETERMINATION = "2025-06-02"
EARLIEST_DEADLINE = "2025-07-02"    # +30 (CO, FL, ME, WA)
TX_RESIDENT_DUE = "2025-08-01"      # +60
DEFAULT_DUE = "2025-07-17"          # firm policy 45 days
TOTAL_AFFECTED = 638204
SSN_SUBSET = 412300
RESIDENT_PINNED = {
    "CA": 88412, "TX": 54003, "FL": 41220, "MA": 22150, "CT": 18442,
    "WA": 12876, "CO": 9341, "ME": 3004, "ND": 1872, "OR": 214, "WY": 302,
}
_r_filler_states = [j for j in JURISDICTIONS if j not in RESIDENT_PINNED]
_r_filler_total = TOTAL_AFFECTED - sum(RESIDENT_PINNED.values())
RESIDENT_FILLER = {}
for _i, _j in enumerate(_r_filler_states):
    RESIDENT_FILLER[_j] = (_r_filler_total // len(_r_filler_states)) + (
        1 if _i < (_r_filler_total - (_r_filler_total // len(_r_filler_states)) * len(_r_filler_states)) else 0)
MAILING_POPULATION = TOTAL_AFFECTED - RESIDENT_PINNED["ND"]   # 636,332 (ND safe harbor)
AG_SET = [
    "AL", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "IL", "IN", "IA",
    "LA", "ME", "MD", "MA", "MO", "MT", "NE", "NH", "NM", "NY", "NC", "SC",
    "TX", "VA", "WA",
]                                    # exactly 27; OR out (214 < 250), ND out (safe harbor)
MONITOR_RATE = 9.50
CT_MONITOR_COST = "350,398.00"       # 18,442 x 2 years x $9.50
FREEZE_PHRASE = "security freeze at no charge"
ATTACK_PHRASE = "credential stuffing"

# ---------------------------------------------------------------------------
# Validation — the build refuses inconsistent content
# ---------------------------------------------------------------------------

def _d(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def validate() -> list[str]:
    errors: list[str] = []

    def chk(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    chk(sorted(sum(REGIONS, [])) == sorted(JURISDICTIONS), "region split loses jurisdictions")
    chk(len(set(JURISDICTIONS)) == 51, "jurisdiction list must be 51 unique entries")

    # Delgado dates
    chk(_d(SURVEY_DUE) == _d(EFFECTIVE_DATE) + _dt.timedelta(days=60), "survey due != ED+60")
    chk(_d(SURVEY_DUE).weekday() == 4, "survey due must be a Friday (no roll)")
    chk(_d(S75_RAW_DUE) == _d(EFFECTIVE_DATE) + _dt.timedelta(days=90), "7.5 raw != ED+90")
    chk(_d(S75_RAW_DUE).weekday() == 6, "7.5 raw due must be a Sunday (the trap)")
    chk(_d(S75_DUE) == _d(S75_RAW_DUE) + _dt.timedelta(days=1), "7.5 roll wrong")

    # Store counts
    chk(REMEDIATION_STORES == 317, "remediation store count must be 317")
    chk(sum(STORE_FILLER.values()) == TOTAL_STORES - REMEDIATION_STORES - PR_STORES,
        "store filler must sum to the remainder")
    chk(len(STORE_FILLER) == 45, "store filler must cover 45 jurisdictions")

    # Consent judgment
    chk(_d(REAUDIT_DUE) == _d(AUDIT_DONE) + _dt.timedelta(days=30), "re-audit != +30")
    chk(_d(REPORT_DUE) == _d(QUARTER_CLOSE) + _dt.timedelta(days=30), "report != +30")
    chk(TOTAL_PENALTIES == 5000, "penalties must be $5,000")
    fails = [s for s, (o, _u) in AUDIT_ROWS.items() if o > 2]
    chk(sorted(fails) == sorted(FAILING_STORES), "failing-store derivation drifted")
    watch = [s for s, (o, u) in AUDIT_ROWS.items() if o + u > 2]
    chk(sorted(watch) == sorted(WATCHLIST), "watchlist derivation drifted")

    # Claims
    chk(_d(NOTICE_DATE) == _d(PRELIM_ORDER) + _dt.timedelta(days=30), "notice != +30")
    chk(_d(CLAIMS_DEADLINE) == _d(NOTICE_DATE) + _dt.timedelta(days=90), "claims != +90")
    chk(_d(OPTOUT_RAW) == _d(NOTICE_DATE) + _dt.timedelta(days=60), "optout raw != +60")
    chk(_d(OPTOUT_RAW).weekday() == 6, "optout raw must be a Sunday")
    chk(_d(HEARING_FLOOR) == _d(CAFA_SERVICE) + _dt.timedelta(days=90), "floor != +90")
    chk(round(0.02 * 18400.00, 2) == 368.00, "C-0011 math")
    chk(min(round(0.02 * 31250.00, 2), 500.00) == 500.00, "C-0027 cap math")
    chk(368.00 + 500.00 + 20.00 + 10.00 + 25.00 == 923.00, "approved total math")
    chk(CLAIMS["C-0063"][2] > CLAIMS_DEADLINE, "C-0063 must be late")

    # ARL
    chk(len(ARL_YES) == 30 and len(ARL_NO) == 21, "ARL split must be 30/21")
    chk("FL" in ARL_NO, "FL must be UDAP-only (trap)")
    chk(len(set(ARL_YES)) == 30 and not (set(ARL_YES) - set(JURISDICTIONS)), "ARL_YES malformed")
    chk(_d(ARL_REMEDIATION_DUE) == _d(FCB_ORDER_DATE) + _dt.timedelta(days=90), "ARL due != +90")

    # Fees
    chk(round(189.00 + 39.95, 2) == 228.95, "all-in nightly math")
    chk(round(3 * 228.95 + 12.00, 2) == 698.85, "3-night quote math")
    chk(_d(CID_DUE) == _d(CID_SERVED) + _dt.timedelta(days=45), "CID due != +45")

    # BIPA
    chk(_d(BIPA_DUE) == _d(BIPA_ED) + _dt.timedelta(days=45), "BIPA due != +45")
    chk(PER_SCAN_NEGLIGENT == 15_540_000_000, "per-scan exposure math")
    chk(PER_PERSON_NEGLIGENT == 8_400_000 and PER_PERSON_RECKLESS == 42_000_000,
        "per-person exposure math")
    for eid, (_status, last, dest) in ROSTER.items():
        if last and dest not in ("OVERDUE",):
            want = _d(last).replace(year=_d(last).year + 3)
            chk(_d(dest) == want, f"{eid} destruction date != last scan + 3y")

    # Breach
    chk(_d(EARLIEST_DEADLINE) == _d(DETERMINATION) + _dt.timedelta(days=30), "30-day math")
    chk(_d(TX_RESIDENT_DUE) == _d(DETERMINATION) + _dt.timedelta(days=60), "60-day math")
    chk(_d(DEFAULT_DUE) == _d(DETERMINATION) + _dt.timedelta(days=45), "45-day math")
    total = sum(RESIDENT_PINNED.values()) + sum(RESIDENT_FILLER.values())
    chk(total == TOTAL_AFFECTED, "resident counts must sum to the affected total")
    chk(MAILING_POPULATION == 636332, "mailing population must be 636,332")
    chk(len(AG_SET) == 27, "AG set must have exactly 27 jurisdictions")
    chk("OR" not in AG_SET and "ND" not in AG_SET, "OR and ND must be outside the AG set")
    for must in ("TX", "CA", "MA", "CT"):
        chk(must in AG_SET, f"{must} must be in the AG set")
    chk(all(j in JURISDICTIONS for j in AG_SET), "AG set contains unknown jurisdiction")
    chk(round(18442 * 2 * MONITOR_RATE, 2) == 350398.00, "CT monitoring math")

    return errors
