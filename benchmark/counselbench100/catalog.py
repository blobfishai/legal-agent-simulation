"""Hand-authored matter catalog for CounselBench-100.

The catalog deliberately stores the factual spine of every matter rather than
deriving 100 cosmetic variants from one seed.  The builder adds deterministic
record-level details, but these titles, clients, adversaries, venues, deadlines,
and matter narratives are the human-authored source of task diversity.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Matter:
    family: str
    slug: str
    title: str
    client: str
    counterparty: str
    jurisdiction: str
    venue: str
    matter_number: str
    deadline: str
    narrative: str


FAMILY_SETTINGS: dict[str, dict[str, object]] = {
    "corporate-ma": {
        "label": "M&A data-room diligence",
        "role": "buyer-side transactions counsel",
        "folders": [
            "01_corporate", "02_capitalization", "03_material_contracts",
            "04_debt_security", "05_employment", "06_ip_technology",
            "07_privacy_security", "08_regulatory", "09_litigation",
            "10_real_property", "11_tax_insurance", "12_financials",
        ],
        "issues": [
            "charter authorization mismatch", "unrecorded option grant",
            "change-of-control consent", "anti-assignment restriction",
            "most-favored-customer exposure", "financial covenant breach",
            "key-person retention gap", "invention assignment defect",
            "open-source copyleft exposure", "unreported security incident",
            "permit transfer restriction", "threatened customer dispute",
            "facility title exception", "sales-tax nexus gap",
            "claims-made insurance tail", "revenue recognition exception",
        ],
    },
    "commercial-contracts": {
        "label": "commercial agreement portfolio reconciliation",
        "role": "commercial contracts counsel",
        "folders": [
            "01_master_agreements", "02_order_forms", "03_amendments",
            "04_statements_of_work", "05_pricing", "06_service_levels",
            "07_security_privacy", "08_notices", "09_invoices",
            "10_correspondence", "11_policies", "12_renewal_records",
        ],
        "issues": [
            "renewal date conflict", "pricing-escalator mismatch",
            "minimum-commit shortfall", "service-credit underpayment",
            "termination notice defect", "assignment consent requirement",
            "data-localization conflict", "subprocessor notice lapse",
            "insurance-limit deficiency", "audit-right deadline",
            "exclusivity carveout breach", "benchmarking right omission",
            "invoice currency discrepancy", "usage-report inconsistency",
            "order-form precedence conflict", "survival-clause ambiguity",
        ],
    },
    "internal-investigations": {
        "label": "internal investigation evidence synthesis",
        "role": "independent investigations counsel",
        "folders": [
            "01_intake", "02_preservation", "03_interviews",
            "04_email_exports", "05_chat_exports", "06_expenses",
            "07_access_logs", "08_vendor_files", "09_policies",
            "10_hr_records", "11_board_reporting", "12_remediation",
        ],
        "issues": [
            "preservation delay", "interview timeline conflict",
            "undisclosed related party", "split-purchase pattern",
            "approval override", "gift-policy threshold breach",
            "off-channel communication", "deleted-message anomaly",
            "badge-log inconsistency", "vendor due-diligence gap",
            "retaliation concern", "policy training lapse",
            "board-reporting omission", "hotline classification error",
            "expense support deficiency", "remediation ownership gap",
        ],
    },
    "litigation-discovery": {
        "label": "litigation discovery and privilege review",
        "role": "discovery counsel",
        "folders": [
            "01_pleadings", "02_orders", "03_requests_responses",
            "04_custodian_files", "05_email_families", "06_chat_exports",
            "07_privilege_material", "08_production_logs", "09_depositions",
            "10_expert_material", "11_third_party", "12_case_management",
        ],
        "issues": [
            "custodian omission", "legal-hold delivery gap",
            "collection-date inconsistency", "email-family separation",
            "privilege-log description defect", "common-interest support gap",
            "clawback deadline", "protective-order designation error",
            "request-response mismatch", "deposition exhibit omission",
            "expert draft segregation", "third-party subpoena deadline",
            "production gap", "metadata field loss", "Bates-range overlap",
            "meet-and-confer commitment",
        ],
    },
    "restructuring": {
        "label": "restructuring claims reconciliation",
        "role": "debtor-side restructuring counsel",
        "folders": [
            "01_petition_schedules", "02_claims_register", "03_proofs_of_claim",
            "04_contracts_leases", "05_cash_management", "06_financing",
            "07_critical_vendors", "08_tax", "09_litigation",
            "10_plan_disclosure", "11_notices_ballots", "12_reconciliations",
        ],
        "issues": [
            "scheduled-claim mismatch", "duplicate proof of claim",
            "secured-status defect", "priority classification error",
            "executory-contract cure dispute", "lease rejection deadline",
            "postpetition invoice", "critical-vendor overstatement",
            "setoff assertion", "guaranty overlap", "tax priority period",
            "DIP budget variance", "cash-collateral reporting gap",
            "ballot amount discrepancy", "notice-address defect",
            "reserve calculation error",
        ],
    },
    "real-estate": {
        "label": "real-estate portfolio and lease audit",
        "role": "real-estate transactions counsel",
        "folders": [
            "01_leases", "02_amendments", "03_estoppels",
            "04_title_survey", "05_environmental", "06_zoning_permits",
            "07_operating_expenses", "08_insurance", "09_notices",
            "10_construction", "11_financing", "12_property_management",
        ],
        "issues": [
            "rent schedule inconsistency", "renewal-option notice",
            "exclusive-use conflict", "assignment consent",
            "estoppel discrepancy", "survey encroachment",
            "title exception", "environmental recognized condition",
            "zoning nonconformity", "permit closeout gap",
            "CAM reconciliation error", "insurance endorsement deficiency",
            "casualty restoration deadline", "construction lien notice",
            "lender SNDA omission", "security-deposit mismatch",
        ],
    },
    "privacy-regulatory": {
        "label": "privacy and regulatory response audit",
        "role": "privacy and regulatory counsel",
        "folders": [
            "01_data_inventory", "02_processing_records", "03_vendor_reviews",
            "04_security_incidents", "05_consumer_requests", "06_notices_consents",
            "07_transfer_mechanisms", "08_retention_deletion", "09_training",
            "10_regulator_correspondence", "11_risk_assessments", "12_remediation",
        ],
        "issues": [
            "processing-purpose gap", "notice-practice mismatch",
            "consent-record deficiency", "processor-contract omission",
            "subprocessor inventory mismatch", "cross-border transfer gap",
            "retention schedule conflict", "deletion-job failure",
            "access-request deadline", "identity-verification inconsistency",
            "incident-notification clock", "risk-assessment omission",
            "sensitive-data classification", "minor-consent issue",
            "training completion gap", "regulator commitment overdue",
        ],
    },
    "employment": {
        "label": "employment compliance matter audit",
        "role": "employment counsel",
        "folders": [
            "01_handbooks_policies", "02_personnel_records", "03_payroll_time",
            "04_compensation_equity", "05_leave_accommodation", "06_complaints",
            "07_investigations", "08_performance_discipline", "09_separation",
            "10_contractors", "11_training", "12_agency_matters",
        ],
        "issues": [
            "classification inconsistency", "overtime calculation error",
            "meal-period premium gap", "pay-equity outlier",
            "leave designation delay", "interactive-process lapse",
            "complaint escalation gap", "investigation independence concern",
            "discipline comparator inconsistency", "retaliation timing",
            "separation pay discrepancy", "restrictive-covenant conflict",
            "contractor control evidence", "training completion gap",
            "personnel-file access deadline", "agency response commitment",
        ],
    },
    "ip-technology": {
        "label": "IP chain-of-title and technology audit",
        "role": "intellectual-property counsel",
        "folders": [
            "01_patents", "02_trademarks", "03_copyrights",
            "04_invention_assignments", "05_licenses_in", "06_licenses_out",
            "07_open_source", "08_domain_accounts", "09_development_records",
            "10_disputes", "11_maintenance", "12_security_interests",
        ],
        "issues": [
            "inventor assignment gap", "recorded-owner mismatch",
            "maintenance-fee deadline", "foreign-filing restriction",
            "trademark specimen issue", "coexistence restriction",
            "work-for-hire defect", "source-code ownership gap",
            "inbound-license field restriction", "outbound sublicense overreach",
            "copyleft distribution trigger", "notice-file omission",
            "domain registrant mismatch", "repository access anomaly",
            "cease-and-desist deadline", "security-interest release gap",
        ],
    },
    "public-company": {
        "label": "public-company disclosure and governance audit",
        "role": "securities and governance counsel",
        "folders": [
            "01_board_committees", "02_minutes_materials", "03_sec_filings",
            "04_disclosure_controls", "05_insider_trading", "06_related_parties",
            "07_equity_compensation", "08_earnings_guidance", "09_whistleblower",
            "10_stock_exchange", "11_debt_covenants", "12_certifications",
        ],
        "issues": [
            "committee-independence gap", "minutes-approval omission",
            "8-K deadline", "risk-factor inconsistency",
            "disclosure-control exception", "trading-window violation",
            "Section 16 filing delay", "related-party disclosure gap",
            "equity-plan share mismatch", "non-GAAP reconciliation issue",
            "guidance-control failure", "whistleblower escalation delay",
            "listing-standard notice", "debt-covenant disclosure",
            "officer certification exception", "board-matrix inconsistency",
        ],
    },
}


_ROWS = """
corporate-ma|helios-forge|Project Daybreak battery acquisition|Helios Forge, Inc.|BluePeak Battery Systems LLC|Delaware|Washoe County, Nevada|CB-MA-2401|2026-09-04|A carve-out manufacturer owns cathode tooling in Nevada while its largest automaker customer can terminate upon an indirect change of control.
corporate-ma|northstar-orbit|Project Sextant satellite software merger|Northstar Orbit plc|Aster Vale Navigation Corp.|Delaware|District of Colorado|CB-MA-2402|2026-09-08|The target licenses university navigation code, operates a classified support unit, and recently refinanced through a lender with blanket liens.
corporate-ma|lumen-health|Project Orchard clinic platform purchase|Lumen Health Partners|OrchardBridge Clinical Systems, Inc.|New York|Kings County, New York|CB-MA-2403|2026-09-11|A healthcare scheduling platform combines physician contracts, patient data, and a revenue-share channel relationship that the seller treats as nonexclusive.
corporate-ma|tamarack-foods|Project Copper Kettle food plant divestiture|Tamarack Foods Group|Copper Kettle Nutrition Co.|Illinois|Cook County, Illinois|CB-MA-2404|2026-09-15|The divested nutrition plant has private-label commitments, shared wastewater permits, a union successorship clause, and disputed promotional accruals.
corporate-ma|solace-mobility|Project Lantern fleet technology acquisition|Solace Mobility Holdings|Lantern Route Analytics, Inc.|California|Santa Clara County, California|CB-MA-2405|2026-09-18|The route-optimization target relies on contractor-created models, municipal fleet data, and a customer letter that changes the pricing floor after closing.
corporate-ma|meridian-water|Project Spillway treatment business acquisition|Meridian Water Infrastructure|Spillway Process Controls, LLC|Texas|Harris County, Texas|CB-MA-2406|2026-09-22|A process-controls business has municipal framework contracts, source-code escrow obligations, and a legacy explosion claim excluded from current insurance.
corporate-ma|bracken-home|Project Hearth consumer products merger|Bracken Home Brands|Hearth & Reed Appliances Corp.|Ohio|Franklin County, Ohio|CB-MA-2407|2026-09-25|A connected-appliance company changed component suppliers after a recall, pledged inventory under a revolver, and promised one retailer price parity.
corporate-ma|cobalt-learning|Project Chalkboard education platform purchase|Cobalt Learning Cooperative|Chalkboard Metrics PBC|Massachusetts|Suffolk County, Massachusetts|CB-MA-2408|2026-09-29|The target processes school records, sublicenses assessment content, and issued advisor warrants that never reached the formal capitalization schedule.
corporate-ma|silverline-logistics|Project Switchyard logistics roll-up|Silverline Logistics LP|Switchyard Freight Intelligence, LLC|Georgia|Fulton County, Georgia|CB-MA-2409|2026-10-02|A freight analytics add-on uses carrier fuel data, occupies a rail-adjacent facility, and disputes a customer offset against implementation invoices.
corporate-ma|verdant-grid|Project Canopy microgrid acquisition|Verdant Grid Holdings|Canopy Storage Works, Inc.|Delaware|Maricopa County, Arizona|CB-MA-2410|2026-10-06|The target assembles storage systems under state incentives, leases desert test acreage, and may have recognized milestone revenue before customer acceptance.
commercial-contracts|atlas-fiber|Atlas Fiber enterprise customer reset|Atlas Fiber Networks|Juniper Peak Retail Group|Colorado|Denver, Colorado|CB-CC-2501|2026-09-03|A five-year network agreement has three order forms, disputed uptime credits, and competing renewal dates created by a migration amendment.
commercial-contracts|banyan-payments|Banyan acquiring-bank portfolio review|Banyan Payments, Inc.|Red Harbor Bank, N.A.|New York|New York County, New York|CB-CC-2502|2026-09-07|Processing volume dropped below an annual floor while a security addendum and pricing schedule assign different consequences to the same shortfall.
commercial-contracts|cirrus-labs|Cirrus cloud-reseller reconciliation|Cirrus Laboratory Cloud LLC|Quartzline Resellers Ltd.|Washington|King County, Washington|CB-CC-2503|2026-09-10|A reseller claims exclusivity in public-sector accounts and relies on an unsigned order form that changed usage reporting and audit mechanics.
commercial-contracts|driftwood-media|Driftwood content-delivery renewal audit|Driftwood Media Studios|Palisade Stream Services, Inc.|California|Los Angeles County, California|CB-CC-2504|2026-09-14|Delivery charges, localization commitments, and service credits diverge across a master agreement, two amendments, and eighteen months of invoices.
commercial-contracts|ember-medical|Ember device-support contract triage|Ember Medical Devices|Keystone Field Support LLC|Minnesota|Hennepin County, Minnesota|CB-CC-2505|2026-09-17|A national maintenance vendor missed response targets and added subcontractors without completing required background or insurance documentation.
commercial-contracts|fathom-retail|Fathom marketplace vendor audit|Fathom Retail Markets|North Cove Merchandising Corp.|Illinois|Cook County, Illinois|CB-CC-2506|2026-09-21|Marketplace fees changed mid-quarter, returns data moved offshore, and the parties disagree whether an email modified the category exclusivity provision.
commercial-contracts|garnet-energy|Garnet offtake agreement review|Garnet Renewable Energy|Mesa Crown Utilities|Texas|Travis County, Texas|CB-CC-2507|2026-09-24|An energy offtake portfolio contains metering disputes, a change-in-law pass-through, and notice records sent to an address deleted by amendment.
commercial-contracts|harborlight-ai|Harborlight AI procurement reconciliation|Harborlight AI Systems|Westmere Insurance Cooperative|Connecticut|Hartford County, Connecticut|CB-CC-2508|2026-09-28|An AI services deal combines outcome benchmarks, model-training restrictions, and contradictory schedules for data deletion and incident notice.
commercial-contracts|ironwood-agri|Ironwood distribution portfolio review|Ironwood Agricultural Supply|Blue Fen Distribution, Inc.|Iowa|Polk County, Iowa|CB-CC-2509|2026-10-01|A regional distributor invokes price protection and territorial exclusivity despite dealer reports showing sales outside the assigned states.
commercial-contracts|juno-travel|Juno reservation platform exit analysis|Juno Travel Technologies|Crescent Hotel Consortium|Florida|Miami-Dade County, Florida|CB-CC-2510|2026-10-05|The customer seeks an early exit after repeated outages, but separate documents disagree about cure periods, transition services, and prepaid credits.
internal-investigations|alder-biotech|Alder clinical-vendor payment inquiry|Alder Biotherapeutics|Morrow Trial Services LLC|Massachusetts|Cambridge, Massachusetts|CB-IV-2601|2026-09-02|A hotline report alleges that a study manager split vendor invoices after accepting travel from a firm owned by a former colleague.
internal-investigations|beacon-mining|Beacon procurement integrity review|Beacon Mineral Resources|Red Mesa Hauling Co.|Arizona|Pima County, Arizona|CB-IV-2602|2026-09-06|Anonymous allegations connect emergency hauling awards to off-channel messages, badge visits, and an undeclared family relationship.
internal-investigations|cedar-finance|Cedar branch incentive investigation|Cedar Community Finance|Lakefront Referral Partners|Wisconsin|Milwaukee County, Wisconsin|CB-IV-2603|2026-09-09|A branch posted referral bonuses just below secondary-approval thresholds while employee interviews conflict with access and expense records.
internal-investigations|dovetail-aerospace|Dovetail export-controls inquiry|Dovetail Aerospace Components|Orion Bridge Consulting|Virginia|Fairfax County, Virginia|CB-IV-2604|2026-09-13|Engineering files may have been shared with an overseas consultant before screening, and preservation began after an account was deactivated.
internal-investigations|evergreen-charter|Evergreen enrollment complaint review|Evergreen Charter Network|Summit Enrollment Advisors|Oregon|Multnomah County, Oregon|CB-IV-2605|2026-09-16|A complaint alleges manipulated wait-list entries, consultant gifts, and retaliation against the registrar who questioned manual overrides.
internal-investigations|foxglove-pharma|Foxglove speaker-program investigation|Foxglove Pharmaceuticals|Clearwater Medical Events|New Jersey|Middlesex County, New Jersey|CB-IV-2606|2026-09-20|Attendance logs, meal receipts, and speaker agreements suggest repeat programs with missing educational content and incomplete escalation.
internal-investigations|granite-hospitality|Granite hotel renovation inquiry|Granite Hospitality Trust|Sable Ridge Interiors|Nevada|Clark County, Nevada|CB-IV-2607|2026-09-23|A renovation executive approved change orders for a related vendor while project chats and board reporting omit key ownership information.
internal-investigations|horizon-relief|Horizon grant-use investigation|Horizon Relief Foundation|Fieldstone Logistics NGO|District of Columbia|Washington, District of Columbia|CB-IV-2608|2026-09-27|Grant funds were rerouted through emergency vendors, with inconsistent delivery evidence and delayed reports to the audit committee.
internal-investigations|indigo-telecom|Indigo channel-rebate inquiry|Indigo Telecom Americas|Prairie Link Solutions|Texas|Dallas County, Texas|CB-IV-2609|2026-09-30|Quarter-end rebates were approved through overrides after unusual chats, duplicate support, and a vendor diligence file that omits beneficial ownership.
internal-investigations|jasper-university|Jasper research-fund inquiry|Jasper University Research Institute|Nova Bench Analytics|Pennsylvania|Allegheny County, Pennsylvania|CB-IV-2610|2026-10-04|A principal investigator directed purchases to a startup owned by a former student while training, disclosure, and expense records diverge.
litigation-discovery|aurora-antitrust|Aurora pricing MDL discovery audit|Aurora Home Supply Co.|In re Residential Fixture Pricing|Illinois|Northern District of Illinois|CB-LD-2701|2026-09-05|A multidistrict antitrust production must reconcile mobile chats, departed custodians, overlapping Bates ranges, and a pending privilege challenge.
litigation-discovery|bayfield-patent|Bayfield patent case production review|Bayfield Sensorics, Inc.|Kestrel Vision Systems LLC|Delaware|District of Delaware|CB-LD-2702|2026-09-09|Source-code collections and inventor communications were produced under a protective order, but family links and designation fields are inconsistent.
litigation-discovery|crown-employment|Crown wage action discovery check|Crown Kitchen Group|Martinez et al.|California|Central District of California|CB-LD-2703|2026-09-12|A wage class action involves manager texts, scheduling exports, late legal holds, and commitments made during two meet-and-confer sessions.
litigation-discovery|delta-products|Delta product-liability collection audit|Delta Infant Products|Reed v. Delta Infant Products|Georgia|Northern District of Georgia|CB-LD-2704|2026-09-16|Design-history files, overseas supplier emails, and expert materials have inconsistent collection dates and an unresolved third-party subpoena.
litigation-discovery|elm-river|Elm River trade-secret privilege audit|Elm River Robotics|Former engineers and Nacre Automation|Massachusetts|District of Massachusetts|CB-LD-2705|2026-09-19|The production mixes counsel-directed forensic reports with ordinary-course analyses and omits attachments from several high-value email families.
litigation-discovery|federal-basin|Federal Basin royalty dispute production|Federal Basin Resources|Osage Crest Minerals LLC|Oklahoma|Western District of Oklahoma|CB-LD-2706|2026-09-23|Lease-accounting exports, title opinions, and executive messages must be mapped to document requests before a court-ordered certification.
litigation-discovery|glacier-insurance|Glacier coverage action discovery review|Glacier Mutual Insurance|Moraine Data Centers, Inc.|New York|Southern District of New York|CB-LD-2707|2026-09-26|Claims files contain mixed business and legal communications, redaction inconsistencies, and a disputed clawback notice date.
litigation-discovery|highland-securities|Highland securities case hold audit|Highland Medical Analytics|Patel Securities Action|Tennessee|Middle District of Tennessee|CB-LD-2708|2026-09-30|A securities action requires collection from executives, messaging platforms, and board portals after an acquisition changed account ownership.
litigation-discovery|isotope-environmental|Isotope contamination case production check|Isotope Specialty Chemicals|County of Briar v. Isotope|Louisiana|Eastern District of Louisiana|CB-LD-2709|2026-10-03|Environmental sampling, consultant drafts, and regulator correspondence present designation, metadata, and expert-discovery questions.
litigation-discovery|juniper-franchise|Juniper franchise dispute discovery audit|Juniper Table Restaurants|Oak Street Franchisees Association|Florida|Middle District of Florida|CB-LD-2710|2026-10-07|A franchise production has custodian scope gaps, incomplete chat threads, and order-form attachments missing from key email families.
restructuring|anchor-marine|Anchor Marine chapter 11 claim review|Anchor Marine Fabrication, Inc.|Gulfline Steel Supply|Texas|Southern District of Texas Bankruptcy Court|CB-RS-2801|2026-09-04|A vessel fabricator must reconcile steel claims, lien assertions, postpetition deliveries, and disputed critical-vendor payments.
restructuring|birch-aviation|Birch Aviation lease reconciliation|Birch Regional Aviation LLC|Skyframe Aircraft Leasing|Virginia|Eastern District of Virginia Bankruptcy Court|CB-RS-2802|2026-09-08|Aircraft and gate leases carry cure disputes, guaranties, and notice addresses that changed shortly before the petition date.
restructuring|cascade-retail|Cascade Retail claims reserve audit|Cascade Outdoor Retail Corp.|Multiple merchandise vendors|Delaware|District of Delaware Bankruptcy Court|CB-RS-2803|2026-09-11|A retail debtor faces duplicate claims, returned-goods offsets, rejected store leases, and inconsistent ballot amounts.
restructuring|drummond-care|Drummond Care restructuring schedule check|Drummond Senior Care Group|Pinecrest Medical Staffing|New Jersey|District of New Jersey Bankruptcy Court|CB-RS-2804|2026-09-15|Healthcare staffing, tax, and landlord claims conflict with schedules while cash-collateral reports omit a disputed receivable reserve.
restructuring|equinox-solar|Equinox Solar project claim reconciliation|Equinox Solar Development|Mesa Array Contractors|Arizona|District of Arizona Bankruptcy Court|CB-RS-2805|2026-09-18|Construction claims assert secured and priority treatment across partially completed projects with overlapping guaranties.
restructuring|foundry-foods|Foundry Foods vendor claim audit|Foundry Prepared Foods, Inc.|Northland Cold Chain LLC|Minnesota|District of Minnesota Bankruptcy Court|CB-RS-2806|2026-09-22|Cold-storage invoices straddle the petition date, critical-vendor payments overlap claims, and cure schedules use stale balances.
restructuring|greenway-transit|Greenway Transit plan claim review|Greenway Transit Services|Metro Fleet Finance|Illinois|Northern District of Illinois Bankruptcy Court|CB-RS-2807|2026-09-25|Fleet liens, tax claims, rejection damages, and a DIP variance affect voting and reserve recommendations.
restructuring|harvest-paper|Harvest Paper mill restructuring audit|Harvest Paper Mills LLC|Timber Run Energy Cooperative|Maine|District of Maine Bankruptcy Court|CB-RS-2808|2026-09-29|Energy and timber contracts have contested cure amounts, setoff claims, and address defects in solicitation records.
restructuring|inlet-fitness|Inlet Fitness lease claims review|Inlet Fitness Studios|Urban Square Properties|California|Central District of California Bankruptcy Court|CB-RS-2809|2026-10-02|Studio leases, member refunds, and franchise obligations create duplicate and misclassified claims across the register.
restructuring|keystone-press|Keystone Press disclosure reconciliation|Keystone Regional Press|Commonwealth Newsprint Pension Trust|Pennsylvania|Eastern District of Pennsylvania Bankruptcy Court|CB-RS-2810|2026-10-06|Pension, newsprint, tax, and litigation claims must be reconciled before disclosure-statement and ballot deadlines.
real-estate|acorn-logistics|Acorn industrial portfolio lease audit|Acorn Logistics REIT|Redwood Fulfillment Services|California|San Bernardino County, California|CB-RE-2901|2026-09-03|Three warehouses have conflicting rent schedules, an unclosed solar permit, and an estoppel that excludes a disputed CAM credit.
real-estate|brookline-clinic|Brookline clinic acquisition property review|Brookline Care Partners|Elm Street Medical Properties|Massachusetts|Middlesex County, Massachusetts|CB-RE-2902|2026-09-07|A medical-office portfolio presents zoning, assignment, lender consent, and environmental records that do not align with seller certificates.
real-estate|canyon-grocery|Canyon grocery lease portfolio audit|Canyon Fresh Markets|Mesa Vista Shopping Centers|Arizona|Maricopa County, Arizona|CB-RE-2903|2026-09-10|Store leases contain exclusives, renewal options, and percentage-rent provisions that conflict with landlord statements and payment records.
real-estate|dockside-hotel|Dockside hotel financing property audit|Dockside Hospitality LLC|Harbor Quay Lending|Florida|Duval County, Florida|CB-RE-2904|2026-09-14|A waterfront hotel has a survey encroachment, restoration deadline, construction lien notice, and missing insurance endorsement.
real-estate|eastgate-labs|Eastgate laboratory campus diligence|Eastgate Life Sciences|Polymer Park Properties|North Carolina|Wake County, North Carolina|CB-RE-2905|2026-09-17|Wet-lab leases, hazardous-material records, and expansion permits differ across amendments, estoppels, and property-manager files.
real-estate|fairhaven-storage|Fairhaven self-storage portfolio review|Fairhaven Storage Partners|Cobalt Door Management|Texas|Bexar County, Texas|CB-RE-2906|2026-09-21|A storage portfolio has title exceptions, rent-roll discrepancies, security deposits, and management charges inconsistent with governing documents.
real-estate|glenridge-school|Glenridge charter campus lease review|Glenridge Education Network|Cedar Hall Development|Colorado|Arapahoe County, Colorado|CB-RE-2907|2026-09-24|A school campus faces use restrictions, renewal notices, accessibility work, and an SNDA missing from lender records.
real-estate|hemlock-manufacturing|Hemlock plant sale-leaseback audit|Hemlock Precision Works|Iron Gate Capital|Michigan|Oakland County, Michigan|CB-RE-2908|2026-09-28|A manufacturing sale-leaseback includes an environmental condition, equipment liens, roof obligations, and unresolved permit closeout.
real-estate|ivory-tower|Ivory Tower office sublease reconciliation|Ivory Tower Software|Metropolitan Workspace Holdings|New York|New York County, New York|CB-RE-2909|2026-10-01|A headquarters sublease has consent conditions, restoration obligations, rent abatements, and notices delivered under obsolete instructions.
real-estate|kestrel-farms|Kestrel agricultural land portfolio audit|Kestrel Farms Cooperative|Rainshadow Land Trust|Washington|Yakima County, Washington|CB-RE-2910|2026-10-05|Irrigated parcels carry water-right questions, access encroachments, crop leases, and insurance records inconsistent with loan covenants.
privacy-regulatory|arcadia-genomics|Arcadia genomic data response audit|Arcadia Genomics, Inc.|North Coast Sequencing Network|California|California Privacy Protection Agency|CB-PR-3001|2026-09-02|A consumer access request exposes inconsistencies among genomic-data notices, deletion jobs, vendors, and overseas research transfers.
privacy-regulatory|brightpath-kids|BrightPath child-privacy compliance review|BrightPath Learning Apps|Lighthouse School District|Connecticut|Connecticut Attorney General|CB-PR-3002|2026-09-06|An education app collected voice samples under school consent while subprocessor and deletion records lagged product changes.
privacy-regulatory|civic-route|CivicRoute location-data inquiry|CivicRoute Mobility|MetroPulse Advertising LLC|Colorado|Colorado Attorney General|CB-PR-3003|2026-09-09|A mobility app shared precise location segments through an advertising integration not reflected in its processing inventory or opt-out flow.
privacy-regulatory|deepwell-health|Deepwell breach-notice audit|Deepwell Health Services|Morrow Claims Clearinghouse|New York|New York Department of Financial Services|CB-PR-3004|2026-09-13|A credential incident moved through multiple vendors, creating disputed discovery dates and incomplete regulator commitments.
privacy-regulatory|everfield-market|Everfield loyalty-data assessment|Everfield Markets|Poppy Loyalty Cloud|Virginia|Virginia Attorney General|CB-PR-3005|2026-09-16|Loyalty profiles combine purchase and inferred health data with consent, retention, and processor terms that differ by system.
privacy-regulatory|fable-fintech|Fable automated-decision privacy review|Fable Financial Technologies|Northbridge Model Services|Illinois|Illinois Department of Financial and Professional Regulation|CB-PR-3006|2026-09-20|A credit prequalification workflow uses third-party model features while notices, assessments, deletion records, and complaint responses conflict.
privacy-regulatory|grove-hospitality|Grove guest-data transfer audit|Grove Hospitality Group|GlobalStay Reservation Services|Florida|Federal Trade Commission|CB-PR-3007|2026-09-23|Reservation data crosses regions through undocumented subprocessors and a failed retention job identified during a regulator response.
privacy-regulatory|highline-wearables|Highline biometric-data review|Highline Wearables, Inc.|MotionKey Analytics|Texas|Texas Attorney General|CB-PR-3008|2026-09-27|Wearable telemetry and voice features launched before updated consents, assessments, and vendor deletion controls were complete.
privacy-regulatory|inkwell-publishing|Inkwell subscriber request audit|Inkwell Digital Publishing|Blue Quill Audience Systems|Oregon|Oregon Attorney General|CB-PR-3009|2026-09-30|Subscriber access and deletion requests reveal identity-verification, advertising disclosure, and data-retention inconsistencies.
privacy-regulatory|jetstream-saas|Jetstream regulator commitment check|Jetstream Enterprise SaaS|Nimbus Hosting Europe GmbH|Utah|Utah Division of Consumer Protection|CB-PR-3010|2026-10-04|A prior assurance requires vendor reviews and training that do not match current transfer, incident, and completion records.
employment|alpine-delivery|Alpine courier classification audit|Alpine Same-Day Delivery|Mountain West Couriers Association|Colorado|Colorado Department of Labor and Employment|CB-EL-3101|2026-09-05|Courier contracts describe independence while routing, discipline, time, and equipment records show centralized control.
employment|bluebird-care|Bluebird caregiver wage review|Bluebird Home Care Services|Regional caregiver group|California|California Labor Commissioner|CB-EL-3102|2026-09-09|Payroll, visit logs, and policies conflict on travel time, meal premiums, and complaint escalation for mobile caregivers.
employment|copper-state|Copper State accommodation audit|Copper State Manufacturing|Former quality engineer|Arizona|Equal Employment Opportunity Commission|CB-EL-3103|2026-09-12|Leave and accommodation records show delayed follow-up, differing restrictions, comparator discipline, and close termination timing.
employment|daymark-bank|Daymark pay-equity privileged audit|Daymark Community Bank|Compensation review group|North Carolina|United States Department of Labor|CB-EL-3104|2026-09-16|Job architecture, bonuses, performance ratings, and manager messages reveal unexplained compensation outliers in two regions.
employment|elmwood-retail|Elmwood scheduling complaint review|Elmwood Specialty Retail|Store manager collective|Illinois|Illinois Department of Labor|CB-EL-3105|2026-09-19|Schedule-change records, time punches, policy acknowledgments, and discipline files conflict after a protected complaint.
employment|frontier-games|Frontier contractor and IP audit|Frontier Game Studios|Distributed art contributor group|Washington|Washington Department of Labor & Industries|CB-EL-3106|2026-09-23|Remote artists signed varying agreements while access, supervision, invoice, and source-file records support different classifications.
employment|goldleaf-hotels|Goldleaf harassment response audit|Goldleaf Hotels and Resorts|Former banquet supervisor|Nevada|Nevada Equal Rights Commission|CB-EL-3107|2026-09-26|A complaint moved among HR and operations while witness selection, schedule changes, training, and separation records diverged.
employment|harbor-transit|Harbor Transit leave compliance review|Harbor Regional Transit|Maintenance employee group|Oregon|Oregon Bureau of Labor and Industries|CB-EL-3108|2026-09-30|Intermittent leave, overtime, fitness-for-duty, and attendance points were administered inconsistently across systems.
employment|island-biologics|Island Biologics separation audit|Island Biologics Corp.|Former research director|Massachusetts|Massachusetts Commission Against Discrimination|CB-EL-3109|2026-10-03|A research director's complaint, comparator discipline, incentive payment, restrictive covenant, and separation documents require reconciliation.
employment|junction-foods|Junction Foods agency response check|Junction Prepared Foods|Packaging-line employee group|Iowa|Iowa Civil Rights Commission|CB-EL-3110|2026-10-07|Shift records, accommodations, training, payroll corrections, and agency commitments contain conflicting dates and owners.
ip-technology|aperture-robotics|Aperture robotics chain-of-title review|Aperture Robotics, Inc.|Founding engineer group|Delaware|United States Patent and Trademark Office|CB-IP-3201|2026-09-04|Robotics patents and source repositories include founder, contractor, university, and lender interests that are not consistently recorded.
ip-technology|blue-fern|Blue Fern brand portfolio audit|Blue Fern Beverages|Fern & Field Cooperative|California|Trademark Trial and Appeal Board|CB-IP-3202|2026-09-08|A beverage rebrand faces specimen, coexistence, domain, and distributor-license records with conflicting territorial limits.
ip-technology|crux-mapping|Crux geospatial license review|Crux Mapping Systems|National Terrain Archive|Virginia|Eastern District of Virginia|CB-IP-3203|2026-09-11|Mapping products combine government, university, and open-source inputs subject to attribution, field, and distribution restrictions.
ip-technology|drift-audio|Drift Audio catalog ownership audit|Drift Audio Labs|Silver Reed Composers LLC|Tennessee|Middle District of Tennessee|CB-IP-3204|2026-09-15|An audio-model training catalog includes commissioned recordings, performer releases, sample licenses, and takedown correspondence.
ip-technology|everglass-medical|Everglass patent license diligence|Everglass Medical Optics|Lakeshore Research University|Wisconsin|Western District of Wisconsin|CB-IP-3205|2026-09-18|University optical patents carry diligence milestones, sublicense economics, government rights, and maintenance obligations.
ip-technology|frostline-security|Frostline software provenance audit|Frostline Security Software|Open Harbor Foundation|Massachusetts|District of Massachusetts|CB-IP-3206|2026-09-22|A security appliance contains open-source packages, contractor modules, outbound licenses, and incomplete notice files.
ip-technology|goldfinch-media|Goldfinch content platform IP review|Goldfinch Media Network|Independent creator collective|New York|Southern District of New York|CB-IP-3207|2026-09-25|A creator platform has mismatched work-for-hire, moderation-tool, domain, and copyright registration records.
ip-technology|hinterland-agri|Hinterland seed technology title audit|Hinterland Agricultural Science|Prairie State University|Iowa|Southern District of Iowa|CB-IP-3208|2026-09-29|Seed-trait patents, research materials, grant obligations, field restrictions, and recorded security interests do not align.
ip-technology|ionwave-semi|IonWave semiconductor portfolio check|IonWave Semiconductor|Kiyomizu Design KK|Texas|Western District of Texas|CB-IP-3209|2026-10-02|Chip designs rely on foreign contractors, foundry licenses, export-controlled files, and patents with approaching maintenance dates.
ip-technology|jagged-cloud|Jagged Cloud acquisition IP audit|Jagged Cloud Infrastructure|Nimbus Fork Technologies|Washington|Western District of Washington|CB-IP-3210|2026-10-06|A cloud acquisition includes forked code, contributor agreements, patent assertions, registrant mismatches, and lender release questions.
public-company|alabaster-energy|Alabaster disclosure-controls review|Alabaster Energy Corp.|Audit Committee|Delaware|New York Stock Exchange|CB-PC-3301|2026-09-03|A production outage, covenant forecast, and insider trade moved through controls that did not produce consistent board or filing records.
public-company|brightstar-medical|Brightstar 8-K and governance audit|Brightstar Medical Systems|Nominating and Governance Committee|Minnesota|Nasdaq Stock Market|CB-PC-3302|2026-09-07|A director departure, customer loss, equity award, and committee vacancy create overlapping disclosure and listing obligations.
public-company|cypress-bank|Cypress related-party disclosure review|Cypress Community Bancorp|Related Party Transactions Committee|Florida|Nasdaq Stock Market|CB-PC-3303|2026-09-10|Vendor, loan, family relationship, board approval, and questionnaire records differ before the proxy filing date.
public-company|duneworks|Duneworks earnings-controls audit|Duneworks Software, Inc.|Disclosure Committee|California|New York Stock Exchange|CB-PC-3304|2026-09-14|Sales adjustments, non-GAAP metrics, guidance drafts, and certification exceptions were tracked differently across finance and legal files.
public-company|eastport-shipping|Eastport covenant disclosure check|Eastport Shipping Lines|Bondholder trustee|New York|New York Stock Exchange|CB-PC-3305|2026-09-17|Fleet impairment, covenant calculations, lender notices, and risk-factor drafts use conflicting assumptions and dates.
public-company|fieldstone-foods|Fieldstone whistleblower escalation audit|Fieldstone Foods plc|Audit Committee|Illinois|Nasdaq Stock Market|CB-PC-3306|2026-09-21|A revenue-recognition complaint reached management, the hotline vendor, and directors on different timelines before an earnings release.
public-company|granular-tech|Granular Section 16 filing review|Granular Technology Corp.|Executive officer group|Texas|Nasdaq Stock Market|CB-PC-3307|2026-09-24|Equity grants, broker confirmations, powers of attorney, and filing records reveal late or inconsistent insider reports.
public-company|highwater-utilities|Highwater board independence audit|Highwater Utilities, Inc.|Nominating Committee|Oregon|New York Stock Exchange|CB-PC-3308|2026-09-28|Consulting payments, family ties, committee appointments, and questionnaires affect director independence and board-matrix disclosures.
public-company|ironclad-logistics|Ironclad trading-window inquiry|Ironclad Logistics Corp.|Special Committee|Georgia|New York Stock Exchange|CB-PC-3309|2026-10-01|A repurchase update, acquisition talks, executive sale, and preclearance record raise control and disclosure timing questions.
public-company|juniper-photonics|Juniper Photonics filing readiness audit|Juniper Photonics, Inc.|Disclosure Committee|Delaware|Nasdaq Stock Market|CB-PC-3310|2026-10-05|Cybersecurity, customer concentration, equity-plan, committee, and certification records require reconciliation before a periodic report.
"""


def matters() -> list[Matter]:
    result: list[Matter] = []
    for raw in _ROWS.strip().splitlines():
        parts = [part.strip() for part in raw.split("|")]
        if len(parts) != 10:
            raise ValueError(f"catalog row has {len(parts)} fields: {raw}")
        result.append(Matter(*parts))
    if len(result) != 100:
        raise ValueError(f"expected 100 matters, found {len(result)}")
    if len({matter.slug for matter in result}) != 100:
        raise ValueError("matter slugs must be unique")
    if set(matter.family for matter in result) != set(FAMILY_SETTINGS):
        raise ValueError("every configured family must be represented")
    counts = {family: sum(m.family == family for m in result) for family in FAMILY_SETTINGS}
    if set(counts.values()) != {10}:
        raise ValueError(f"each family must have ten matters: {counts}")
    return result


MATTERS = tuple(matters())
