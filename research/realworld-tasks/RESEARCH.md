# Real-World Case Research for Synthetic Benchmark Task Design

> **Provenance file.** This document records REAL cases, statutes, settlement terms, and regulatory
> frameworks (with real names, figures, and URLs) that anchor the synthetic task designs in
> `task-designs.json`. Everything seeded into the simulated world is synthetic; this file exists so
> every synthetic number/shape can be traced to a realistic original. Researched 2026-08-22 via web
> search (~20 queries). Facts marked *[knowledge, verify]* come from model knowledge without a
> fetched source and should be re-verified before being quoted externally (they are only shape
> inputs for synthetic seeding, so precision is not load-bearing).

---

## 1. Anchor: Retail price-scanning / overcharge litigation (the "Walmart shape")

### 1.1 Kukorinis v. Wal-Mart Inc. — the nationwide weighted-goods class settlement

- **Case**: *Vassilios Kukorinis, et al. v. Walmart, Inc.*, No. 8:22-cv-02402 (M.D. Fla.).
  (The task brief's "Vasquez/Kukorinis" appears to conflate this case with the separate
  California DA scanner action in §1.2 — no distinct "Vasquez v. Walmart" scanner class action
  surfaced in searches.)
- **Claims asserted**: FDUTPA (Florida Deceptive and Unfair Trade Practices Act) and unjust
  enrichment — register/label price exceeding the lowest in-store advertised unit price.
- **Alleged mechanics**: POS "inflated" weights on variable-weight meat/poultry/pork/seafood
  ("Weighted Goods," Walmart Department 93, price-embedded barcodes) and on "Bagged Citrus"
  (oranges, grapefruit, tangerines, navels in mesh/plastic bags); clearance/"Rollback"-stickered
  items rang above the sticker unit price.
- **Settlement**: **$45,000,000** common fund; **final approval June 28, 2024**.
- **Class period**: purchases in-person at U.S./Puerto Rico Walmart stores **Oct 19, 2018 –
  Jan 19, 2024**.
- **Claims structure** (the key reusable shape):
  - With receipts/proof of purchase: **2% of substantiated purchases, capped at $500**.
  - Without documentation: attestation tiers up to **$25** (tiering by attested purchase volume,
    $10/$15/$20/$25 style *[knowledge, verify exact tier bounds]*), all subject to pro-rata
    increase/decrease.
- **Admin**: settlement website (walmartweightedgroceriessettlement.com), Angeion administrator,
  claim deadline / opt-out / objection dates set in preliminary approval order.
- Sources:
  - https://news.bloomberglaw.com/litigation/court-approves-45-million-settlement-in-walmart-mispricing-suit
  - https://chimicles.com/walmart-grocery-overcharge-class-action-litigation/
  - https://www.classaction.org/settlements/walmart-weighted-groceries
  - https://topclassactions.com/lawsuit-settlements/closed-settlements/walmart-weighted-groceries-45m-class-action-settlement/
  - https://angeion-public.s3.amazonaws.com/www.walmartweightedgroceriessettlement.com/docs/Summary%20Notice.pdf

### 1.2 California district attorneys v. Walmart — weights-and-measures consent judgments

- **History**: Dec 2005 investigation (CA AG + San Diego DA); random price-checking found **164
  Walmart stores in 30 counties** with scanner errors → **Stipulated Final Judgment Nov 24,
  2008**; continued violations found by 11 county Weights & Measures departments starting Nov
  2010 → **Modified Final Judgment Mar 21, 2012 + $2.1M penalties**; a further coalition action
  (Santa Clara, Sonoma, San Diego DAs et al.) settled **Aug 2025 for $5.6M** (scanner overcharges
  + short-weight/false advertising), superseding the earlier judgments.
- **Injunctive relief — the "$3 guarantee" program (2008 judgment)**: a customer overcharged at
  the register immediately receives **$3 off the lowest advertised price; if the item costs less
  than $3, it is free**. This is the canonical price-verification injunctive program.
- **2025 judgment adds**: designated employees in each California store responsible for keeping
  shelf tags, POS prices, and item weights aligned (esp. variable-weight goods).
- **Statutory hook**: Cal. Bus. & Prof. Code § 12024.2 (charging more than the posted/advertised
  price; county sealer/DA enforcement, civil penalties) plus UCL/FAL (§§ 17200/17500)
  *[knowledge, verify section]*.
- Sources:
  - https://da.santaclaracounty.gov/walmart-overcharged-customers-will-pay-56-million-settle-consumer-protection-lawsuit
  - https://da.sonomacounty.ca.gov/walmart-settles-consumer-protection-case-for-scanner-price-overcharges-and-false-advertising
  - https://www.kiplinger.com/personal-finance/shopping/walmart-price-weight-settlement-california

### 1.3 Dollar General — the state-AG price-accuracy enforcement wave (injunctive program examples)

- **Pennsylvania (AG Dave Sunday)**: **$1.55M** settlement; investigation found Dollar General
  stores failed **more than 40% of pricing-accuracy inspections 2019–2023**; injunctive terms:
  employee training, sufficient staffing, improved practices.
- **Colorado (AG Weiser)**: **$400,000** fine for register price > shelf price.
- **Vermont (Agency of Agriculture)**: **$1.75M**; must implement a **"Pricing Accuracy Policy"**
  ensuring consumers are charged the shelf price.
- **Missouri (AG Bailey)**: suit for deceptive pricing — investigators price-checked 5,000+ items;
  **average overcharge $2.71, up to $6.50/item**.
- **Private class**: $8.5M Dollar General price-overcharge class settlement (cash payments to
  class members).
- Reusable injunctive-program elements: periodic price audits, accuracy percentage thresholds,
  training, staffing minimums, honor-lowest-price policies, reporting to the AG.
- Sources:
  - https://www.attorneygeneral.gov/taking-action/attorney-general-dave-sunday-obtains-1-55-million-settlement-with-dollar-general-for-allegedly-overcharging-consumers/
  - https://coag.gov/2025/400k-settlement-with-dollar-general-for-overcharging-customers/
  - https://agriculture.vermont.gov/vt-receive-175-million-dollar-general-pricing-inaccuracies
  - https://ago.mo.gov/attorney-general-bailey-files-suit-against-dollar-general-for-deceptive-pricing/
  - https://topclassactions.com/lawsuit-settlements/closed-settlements/8-5m-dollar-general-price-overcharge-class-action-settlement/

### 1.4 The NIST Handbook 130 price-verification inspection standard

- **Examination Procedure for Price Verification (EPPV)**, NIST Handbook 130: randomized/
  stratified samples; **a store passes at ≥98% accuracy** (max 2 errors on a 100-item sample).
- **Adopted by 42 states** — this is the de facto national scanner-accuracy standard where no
  item-pricing statute exists.
- **Key nuance (great trap material)**: the **total error rate (over- + undercharges)** drives
  re-inspection frequency, but **fines/penalties are based only on overcharges**.
- Sources:
  - https://www.nist.gov/system/files/documents/2021/12/01/2022-HB130-V-FINAL.pdf
  - https://nist.gov/pml/owm/faqs-examination-procedure-price-verification
  - https://koronapos.com/blog/scanner-accuracy-laws/

### 1.5 State item-pricing / scanner-accuracy statutory variance (the survey backbone)

| Jurisdiction | Regime | Key pinned facts (real) |
|---|---|---|
| **Michigan** | Shopping Reform and Modernization Act, 2011 PA 15, **MCL 445.311–445.324** ("Scanner Law") | Overcharge remedy: notify seller within **30 days**; seller refunds the difference **plus a bonus of 10× the difference, min $1.00, max $5.00**, payable within **2 days** of notice. If seller refuses: suit for the greater of actual damages or **$250**, plus attorney fees up to **$300**. (Replaced the 1976 Item Pricing Act; general item-sticker requirement repealed 2011, bounty kept.) |
| **Massachusetts** | M.G.L. c. 94, **§§ 184B–184E** (food store item pricing); AG reg **940 CMR 3.13**; **202 CMR 7.00** | **Food stores/food departments only** must item-price most items AND sell at the **lowest** price on the item/sign/ad. **Scanner waiver program**: stores may drop stickers if they run consumer scanners etc.; annual waiver fee **$250 (<15,000 sq ft) / $500 (15,000–30,000) / $1,000 (>30,000)**; no waiver while item-pricing fines outstanding. Fines per missing shelf tag. |
| **Connecticut** | Conn. Gen. Stat. **§ 21a-79** | UPC-scanned "consumer commodities" must be price-marked, with exemptions (incl. electronic shelf labels). If the **electronic (scanned) price is higher than the posted price, the customer gets the item free on demand**. Commissioner of Consumer Protection enforcement; § 21a-79a alternative-system test-audit program. |
| **California** | Bus. & Prof. Code § 12024.2 + UCL/FAL; county Weights & Measures/DA enforcement | No statewide item-sticker law, but overcharging vs. posted/advertised price is independently unlawful; civil penalties; DA consent judgments impose programs like the **$3-or-free guarantee** (§1.2). |
| **New York** | Statewide item-pricing law lapsed (~2012); **county ordinances** (e.g., Suffolk, Nassau, Westchester) survive *[knowledge, verify counties]* | Survey answer is "no statewide statute — county-level only + GBL 349 UDAP." |
| **~44 other states + DC** | No item-pricing/bounty statute | General UDAP statutes only + NIST HB130 inspection programs (42 states adopt EPPV). |

This asymmetry (2–6 "statute states" with bespoke remedies vs. a UDAP-only default, plus a
county-only oddball and states where a rumored statute never passed) is exactly what makes a
51-jurisdiction survey non-trivial and verifiable.

---

## 2. The post-settlement "50-state survey → remediation" workflow (what firms actually deliver)

Observed deliverables across the settlements above (Walmart CA judgments, Dollar General AG
settlements, Marriott AVC, Equifax):

1. **Compliance matrix by jurisdiction** (statute Y/N, citation, remedy, disclosure duty, action
   required) — 50 states + DC = 51 rows.
2. **Revised receipt language / receipt spec** (unit-price lines for weighted goods, lowest-price
   guarantee footer).
3. **Revised terms & conditions / terms of sale** (pricing-discrepancy clause: "register price
   controls" language is exactly what settlements kill).
4. **POS disclosures & signage** (e.g., the CA "$3 or free" guarantee sign; item-pricing waiver
   scanner signage in MA).
5. **Training memos + staffing minimums** (Dollar General PA).
6. **Auditor/monitor artifacts**: periodic price-verification audits against the 98% EPPV
   standard, quarterly compliance reports to DAs/AGs, re-audit schedules (Walmart CA 2012 — the
   $2.1M was for failing to comply with the 2008 program; Marriott was fined **$225,000** in 2023
   for missing its 2021 disclosure-implementation deadline after extensions to Feb 15, 2023).
7. **Claims-administration calendar** (notice date, opt-out/objection deadlines, claims deadline,
   CAFA 90-day floor before final approval, distribution windows).

Real example of a compliance program with teeth: the 2008/2012/2025 Walmart California judgments
(§1.2) — audits by county sealers, a customer-facing guarantee, designated per-store compliance
employees, escalating penalties for noncompliance.

---

## 3. Pattern A — Automatic-renewal / subscription compliance sweeps

### 3.1 Federal layer

- **ROSCA**, 15 U.S.C. §§ 8401–8405: negative-option online sales require clear disclosure,
  express informed consent, and simple cancellation mechanisms.
- **FTC "Click-to-Cancel" / Negative Option Rule — VACATED**: the Eighth Circuit vacated the
  entire rule on **July 8, 2025**, six days before its full compliance date of **July 14, 2025**
  (initial effective date had been May 14, 2025, then delayed). Ground: FTC skipped the
  **preliminary regulatory analysis** required by FTC Act § 22 for rules with >$100M annual
  economic impact. ROSCA, FTC Act § 5, and state ARLs remain fully enforceable. (Perfect
  "superseded/vacated authority" trap: a rule that was final, published, and partially effective
  — then erased.)
- **FTC v. Amazon.com, Inc. (Prime)**, No. 2:23-cv-0932 (W.D. Wash.): settled **Sept 25, 2025**
  for up to **$2.5B** — **$1.0B civil penalty** (largest ever for an FTC rule violation) +
  **$1.5B consumer redress** to ~**35M** consumers (automatic payments up to **$51** within 90
  days). Covered enrollments **June 23, 2019 – June 23, 2025** via "challenged flows" (incl.
  people who used ≤3 Prime benefits in a 12-month window, or who tried and failed to cancel).
  Injunctive: no misrepresentation of terms; **cancellation must be easy** (no more steps than
  enrollment); clause providing that a future re-issued Click-to-Cancel rule supersedes the
  order's conduct terms.
- Sources:
  - https://www.lw.com/en/insights/eighth-circuit-vacates-ftc-click-to-cancel-rule-days-before-compliance-deadline
  - https://www.mayerbrown.com/en/insights/publications/2025/07/click-to-cancelled-eighth-circuit-vacates-federal-trade-commissions-revised-negative-option-rule
  - https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-secures-historic-25-billion-settlement-against-amazon
  - https://www.alston.com/en/insights/publications/2025/10/ftc-settlement-prime-subscription-practices
  - https://www.cnbc.com/2025/09/25/amazon-ftc-prime-settlement.html

### 3.2 State ARL variance (survey backbone)

| State | Statute | Distinctive requirement |
|---|---|---|
| **California** | Bus. & Prof. Code §§ 17600–17606, amended by **AB 390** (eff. 7/1/2022) and **AB 2863** (eff. **July 1, 2025**, applies to contracts entered/amended/extended on or after) | Express affirmative consent to ARL terms as a separate item; **annual renewal reminders** (terms, renewal date, cancel instructions); free-to-paid conversions covered; **"click to quit"** — cancel in the same medium as signup; consent records kept **3 years or 1 year after termination, whichever is longer**; notice of material price/service changes. |
| **New York** | GBL **§ 527-a** (eff. **Feb 9, 2021**) | CA-model: clear-and-conspicuous offer terms (defined typographically), affirmative consent, post-sale **acknowledgment** with cancel policy, **online cancellation** for online signups; AG enforcement. |
| **Vermont** | 9 V.S.A. § 2454a *[knowledge, verify cite]* | **Double opt-in**: auto-renewal provision must be accepted by a **separate affirmative action** distinct from accepting the contract; applies to contracts with initial term ≥1 year renewing >1 month. Monthly plans typically out of scope — classic scope trap. |
| **Illinois** | Automatic Contract Renewal Act, 815 ILCS 601 *[knowledge, verify]* | Written renewal notice **30–60 days before the cancellation deadline** for 12-month+ contracts that renew for 12+ months. |
| **D.C.** | D.C. Code § 28A-203 *[knowledge, verify]* | Renewal notice window for 12-month+ terms; affirmative consent for free-trial conversions ≥1 month. |
| **~25 more states** | ARL-type statutes of varying scope (FL limited to defined "service contracts," GA 12-month thresholds, etc.) | Roughly 30 jurisdictions have some ARL statute; the remainder are UDAP-only. |

Concrete lawyer deliverables: enrollment-flow disclosure audit, checkout screen redlines, renewal
reminder email templates with per-state timing windows, cancel-flow click-count spec,
consent-record retention schedule, 51-row matrix.

---

## 4. Pattern B — Illinois BIPA biometric class actions

- **Statute**: 740 ILCS 14 (BIPA). § 15(a): public written retention-and-destruction policy;
  destroy identifiers when the initial purpose is satisfied **or within 3 years of the
  individual's last interaction, whichever occurs first**. § 15(b): written notice + specific
  purpose and length of term + **written release** before collection. § 20: **$1,000 per
  negligent violation / $5,000 per reckless-or-intentional violation**, or actual damages, plus
  fees.
- **Rosenbach v. Six Flags**, 2019 IL 123186: no actual injury required — statutory violation
  alone confers standing to sue. *[knowledge, verify cite]*
- **Cothron v. White Castle System, Inc.**, Ill. Sup. Ct. 2023: a claim accrues **on every scan**
  (each collection/disclosure), not just the first — producing a potential **~$17B** exposure for
  a fingerprint timeclock (the dissent's "absurd result"). Case then settled: **$9.39M final
  approval** for **~9,000+ current/former employees** (fingerprint timekeeping without consent).
- **SB 2979** (signed **Aug 2, 2024**): (1) a private entity commits **a single violation per
  person per method of collection** regardless of scan count — legislatively reversing Cothron's
  damages math; (2) "written release" expressly includes an **electronic signature**. The Seventh
  Circuit has since held the amendment applies **retroactively** (2026).
- **Benchmarks settlements**: *In re Facebook Biometric Info. Privacy Litig.* (N.D. Cal.) —
  **$650M**, ~1.38M valid claims, first-round checks **$397**, second round **$30.61** (Tag
  Suggestions). *Rivera v. Google* (Cook Cty.) — **$100M**, **687,484** claimants, ~**$95.38**
  each (Google Photos Face Grouping).
- Lawyer deliverables that fall out of these settlements: public retention/destruction policy,
  per-employee destruction-date schedule (3-year rule), § 15(b)-compliant consent forms
  (electronic signature OK post-amendment), vendor contract amendments (deletion/certification
  clauses; "mathematical representations are not biometrics" is a rejected argument), exposure
  models comparing per-scan vs. per-person accrual.
- Sources:
  - https://topclassactions.com/lawsuit-settlements/privacy/bipa/judge-set-to-approve-9-4m-settlement-over-white-castles-biometric-timekeeping-practices/
  - https://www.classaction.org/media/cothron-v-white-castle-system-inc-et-al-settlement-agreement.pdf
  - https://www.gtlaw.com/en/insights/2024/8/bipa-update-illinois-limits-liability-and-clarifies-electronic-consent-for-biometric-data-collection
  - https://www.insideprivacy.com/data-privacy/illinois-enacts-bipa-amendment-limiting-violation-accrual/
  - https://www.paulhastings.com/insights/ph-privacy/7th-circuit-confirms-bipa-amendment-has-retroactive-application
  - https://topclassactions.com/lawsuit-settlements/closed-settlements/illinois-facebook-biometric-privacy-class-action-settlement/
  - https://topclassactions.com/lawsuit-settlements/closed-settlements/google-photos-face-recognition-privacy-100m-class-action-settlement/

---

## 5. Pattern C — Data-breach notification 50-state+DC survey

- All 50 states + DC (+ territories) have breach-notification statutes; the variance is in
  deadlines, AG-notice triggers, content rules, and remedies:
  - **Hard 30-day consumer deadlines**: **Colorado, Florida, Maine, Washington**.
  - **Texas**: individuals within **60 days**; **AG within 30 days when ≥250 Texas residents**
    affected (post-2023 amendment; online AG portal).
  - **AG/regulator notice thresholds** elsewhere cluster at 250–1,000 residents (e.g., WA >500,
    FL ≥500, OR >250 *[knowledge, verify OR]*); **36 states** require some AG/agency notice; NY
    requires AG + Dept. of State + State Police for any number *[knowledge, verify]*.
  - **Massachusetts** (M.G.L. c. 93H § 3): notice to residents **may NOT describe the nature of
    the breach or the number of residents affected** (anti-roadmap rule); must include security
    freeze rights (free), police-report rights, and mitigation services; AG + OCABR notified
    regardless of count; **18 months of credit monitoring** if SSN involved (42 months for
    consumer reporting agencies) *[knowledge, verify months]*.
  - **Connecticut**: breaches involving **SSNs require 24 months of free credit monitoring**
    (eff. Oct 1, 2018; raised from 12).
  - **California**: Civ. Code § 1798.82 — if **>500 CA residents**, submit a **sample copy of the
    notice (PII excluded) to the AG electronically**; **SB 446** adds a 30-day consumer deadline
    and a 15-calendar-day AG-sample deadline effective 2026.
  - **Encryption safe harbors** in nearly all states (no notice if data encrypted and key not
    compromised) — a clean "correct answer is NO notice" trap.
- **Equifax (2017 breach) global settlement (2019)** — the remediation anchor: **Consumer
  Restitution Fund up to $425M** ($300M + up to $125M contingent), **$175M to 48+2 states**,
  $100M CFPB penalty *[knowledge, verify]*; up to **10 years** of credit monitoring; injunctive:
  comprehensive information-security program, third-party assessments, easier freezes/disputes,
  dedicated ID-theft staffing.
- Lawyer deliverables: 51-row notification chart (deadline, AG trigger, content constraints,
  monitoring duty), per-state resident letters (with the MA content carve-out), AG cover letters,
  credit-monitoring procurement, notification-timeline computation from the "determination" date.
- Sources:
  - https://iapp.org/resources/article/state-data-breach-notification-chart
  - https://coggno.com/blog/data-breach-notification-laws-state-reporting-timelines-employers/
  - https://databreachcost.com/breach-notification-laws/texas
  - https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXV/Chapter93H/Section3
  - https://www.hunton.com/privacy-and-cybersecurity-law-blog/connecticut-requires-24-months-credit-monitoring-certain-security-breaches
  - https://oag.ca.gov/privacy/databreach/reporting
  - https://oag.dc.gov/release/50-attorneys-general-secure-600-million-equifax
  - https://riag.ri.gov/press-releases/us-consumers-receive-425-million-equifax-data-breach-settlement

---

## 6. Pattern D — Junk fees / drip pricing

- **FTC Rule on Unfair or Deceptive Fees**, 16 C.F.R. Part 464 — **effective May 12, 2025**;
  covers **live-event tickets and short-term lodging**; total price (all known mandatory fees)
  must be disclosed clearly/conspicuously/prominently up front; government taxes and shipping
  excludable but must be disclosed before payment; civil penalties **up to $51,744 per
  violation**. NOTE: this rule is **in effect** — it is the *subscription* (click-to-cancel) rule
  that was vacated. The near-miss confusion between the two 2025 FTC rules is a deliberately
  seeded trap in the designs.
- **California SB 478** ("Honest Pricing"/hidden-fees law, CLRA § 1770(a)(29)) — **eff. July 1,
  2024**: advertised/displayed price must include all mandatory fees except government
  taxes/fees and reasonable shipping. **SB 1524** (signed June 29, 2024): restaurant/bar/food
  service exception — mandatory service fees allowed if **clearly and conspicuously displayed**
  wherever prices are shown. CA AG FAQ published May 2024.
- **Minnesota**: junk-fee ban (DTPA amendment) — **eff. Jan 1, 2025**; advertised price must
  include all mandatory non-avoidable fees.
- **Massachusetts**: AG "junk fee" regs **940 CMR 38.00** — enforcement from **Sept 2, 2025**;
  total price at **first presentation**; optional/waivable fees must be explained with opt-out
  instructions; also regulates trial/auto-renewal offers.
- **Marriott resort-fee AVC (Pennsylvania AG, Nov 2021)**: total stay price including resort/
  amenity fees on the **first page** of booking results; 9-month nationwide implementation
  window; repeated extensions to Feb 15, 2023; **$225,000 fine (2023)** for noncompliance; final
  compliance by May 15, 2023. (The multistate hotel-fee effort also touched Hilton/Omni/other
  chains *[knowledge]*.)
- Lawyer deliverables: booking-flow fee audit, corrected "total price" ad copy, checkout screen
  itemization spec, 51-row drip-pricing matrix (3 bespoke statute/reg states + federal
  sector rule + UDAP default), AG response letters, compliance-deadline calendar.
- Sources:
  - https://www.ftc.gov/news-events/news/press-releases/2025/05/ftc-rule-unfair-or-deceptive-fees-take-effect-may-12-2025
  - https://www.ftc.gov/business-guidance/resources/rule-unfair-or-deceptive-fees-frequently-asked-questions
  - https://oag.ca.gov/hiddenfees
  - https://www.gtlaw.com/en/insights/2024/7/california-junk-fee-bill-sb-1524-becomes-law-what-it-means-for-restaurants
  - https://www.claconnect.com/en/resources/blogs/new-junk-fees-law-taking-effect-in-mn-effective-january-1-2025
  - https://www.mass.gov/doc/junk-fee-regulations-940-cmr-3800-0/download
  - https://www.cbsnews.com/pittsburgh/news/marriott-disclose-hidden-resort-fees-settlement-pennsylvania/
  - https://www.forbes.com/sites/suzannerowankelleher/2021/11/22/marriott-disclose-resort-fees/

---

## 7. Pattern E (brief) — TCPA text-marketing *[knowledge-based, not separately searched]*

- 47 U.S.C. § 227: **$500 per call/text, $1,500 willful**; *Facebook v. Duguid* (2021) narrowed
  ATDS; DNC-registry claims still drive text-marketing classes; FCC one-to-one consent rule was
  vacated by the Eleventh Circuit (Jan 2025) — another live "vacated rule" trap; FCC revocation
  rule (honor opt-outs within 10 business days, any reasonable means) effective April 2025.
- Classic settlements: Capital One ~$75.5M (2014); Caribbean Cruise Line ~$76M.
- Not used as a primary design anchor (the four patterns above are richer for document-heavy
  survey work), but $500/$1,500 per-message damages math and quiet-hours/consent-log audits are
  a good future expansion.

---

## 8. Mapping: research → task designs (see task-designs.json)

| Design id | Shape | Real anchors |
|---|---|---|
| `mm-price-accuracy-51-matrix` | Walmart-shape 51-jurisdiction survey + receipt remediation | Kukorinis; MI/MA/CT/CA variance; NIST 42-state default |
| `mm-consent-judgment-audit-scorecard` | Walmart-shape consent-judgment audit + 51-row guarantee-conflict matrix | Walmart CA 2008/2012/2025 judgments; $3-or-free program; NIST 98% EPPV; Dollar General AG terms |
| `mm-receipt-tnc-remediation` | Walmart-shape T&C redline + receipt spec + signage rollout | Kukorinis injunctive posture; MA lowest-price rule; Marriott first-page disclosure discipline |
| `mm-claims-admin-calendar` | Class-settlement administration/deadlines | Kukorinis claim tiers (2%/$500 cap; $10–$25 attestation); Rule 23(e)/CAFA 90-day; Rule 6(a) weekend roll |
| `cp-arl-51-sweep` | Subscription auto-renewal 51-jurisdiction sweep | FTC v. Amazon Prime ($1B/$1.5B); vacated click-to-cancel rule; CA AB 2863; NY 527-a; VT double opt-in |
| `pg-biometric-timeclock-remediation` | BIPA post-settlement remediation | Cothron/White Castle $9.39M; $17B per-scan math; SB 2979; Facebook $650M |
| `ho-breach-51-notification-grid` | Breach-notification 51-jurisdiction grid + letters | CO/FL/ME/WA 30-day; TX 60/30@250; MA content ban; CT 24-month monitoring; CA >500 AG sample; Equifax |
| `bw-resort-fee-remediation` | Junk-fee audit + 51-row drip-pricing matrix | FTC 16 CFR 464 (in effect); CA SB 478/SB 1524; MN 1/1/25; MA 940 CMR 38; Marriott AVC |

Seeding conventions used by the designs:

- All companies, courts, case captions, agencies, and dollar figures in the designs are
  **synthetic** ("Meridian Mart Stores, Inc.," "Delgado v. Meridian Mart," the "Federal Consumer
  Bureau," etc.); real state names are retained but **in-world state law is whatever the seeded
  memo pack says** (modeled on the real variance above; where the design needs a 6th statute
  state, NH/RI are seeded with MA/CT-style synthetic regimes and flagged as such in
  `state_variance_basis`).
- Every deterministic check is derivable from the input-document specs alone; each design carries
  2–3 deliberate traps (superseded drafts, vacated-rule citations, absent-statute jurisdictions,
  boundary values at the 98%/threshold lines, weekend deadline rolls).
