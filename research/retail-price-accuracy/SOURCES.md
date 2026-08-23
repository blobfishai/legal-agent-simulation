# Primary-source research register

Verified for benchmark design on 2026-08-22. This is a source map, not legal
advice or an exhaustive 51-jurisdiction legal opinion. Current text,
applicability, exclusions, local overlays, remedies, effective dates, private
rights, and procedural requirements must be validated by qualified counsel.

## Walmart matters and enforcement

- **Rector v. Walmart Inc.**, No. 1:24-cv-00658-RC (D.D.C.). The official
  GovInfo opinion describes allegations that shelf prices were lower than
  register prices and stays the case under the first-filed rule. It is not a
  merits judgment or settlement:
  <https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_24-cv-00658/pdf/USCOURTS-dcd-1_24-cv-00658-1.pdf>
- **Kahn v. Walmart Inc.**, 107 F.4th 585 (7th Cir. 2024). The official court
  opinion addresses pleaded scanner-price discrepancies and consumer-law
  theories:
  <https://media.ca7.uscourts.gov/cgi-bin/OpinionsWeb/processWebInputExternal.pl?Path=Y2024%2FD07-03%2FC%3A23-1751%3AJ%3AHamilton%3Aaut%3AT%3AfnOp%3AN%3A3231141%3AS%3A0&Submit=Display>
- **Kukorinis v. Walmart Inc.**, No. 8:22-cv-02402 (M.D. Fla.). The $45 million
  settlement concerned weighted goods and bagged citrus, not a California
  self-checkout double-charge settlement. Walmart denied wrongdoing:
  <https://www.walmartweightedgroceriessettlement.com/> and
  <https://ecf.flmd.uscourts.gov/cgi-bin/show_public_doc?2022-02402-132-8-cv=>
- California Attorney General, 2012 checkout-overcharge enforcement release
  describing a $2.1 million resolution and price-accuracy obligations:
  <https://oag.ca.gov/node/30977>
- Santa Clara County District Attorney, 2025 price/weight enforcement release
  describing a $5.6 million California settlement:
  <https://da.santaclaracounty.gov/walmart-overcharged-customers-will-pay-56-million-settle-consumer-protection-lawsuit>

## Federal measurement and inspection references

- NIST, current Handbook 130 (uniform laws/regulations and examination
  procedures): <https://www.nist.gov/pml/owm/nist-handbook-130-current-edition>
- NIST, Price Verification FAQs. NIST expressly distinguishes the Examination
  Procedure for Price Verification from governing law:
  <https://www.nist.gov/pml/owm/faqs/price-verification-faqs>
- NIST, 2024 National Price Verification Survey announcement:
  <https://www.nist.gov/news-events/news/2024/01/2024-national-price-verification-survey>
- FTC, *Price Check II: A Report on the Accuracy of Checkout Scanner Prices*:
  <https://www.ftc.gov/sites/default/files/documents/reports/price-check-report-accuracy-checkout-scanners/scanners.pdf>

## Triaged jurisdiction authorities

- California Business and Professions Code § 12024.2:
  <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=12024.2>
- California Business and Professions Code § 13350:
  <https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=13350>
- Michigan Shopping Reform and Modernization Act, 2011 PA 15:
  <https://www.legislature.mi.gov/documents/mcl/pdf/mcl-Act-15-of-2011.pdf>
- Michigan Attorney General Scanner Law guidance:
  <https://www.michigan.gov/consumerprotection/protect-yourself/consumer-alerts/shopping/michigans-scanner-law>
- D.C. Code § 28-3904:
  <https://code.dccouncil.gov/us/dc/council/code/sections/28-3904>
- D.C. Code § 28-5207:
  <https://code.dccouncil.gov/us/dc/council/code/sections/28-5207>
- New York Agriculture and Markets Law § 197-b:
  <https://www.nysenate.gov/legislation/laws/AGM/197-B>
- Massachusetts 202 CMR 7.00:
  <https://www.mass.gov/regulations/202-CMR-700-price-disclosure>
- Connecticut General Statutes, Chapter 417:
  <https://www.cga.ct.gov/current/pub/chap_417.htm>
- Arizona Revised Statutes § 3-3431(C), current sale-of-commodities price
  provision: <https://www.azleg.gov/ars/3/03431.htm>. The Arizona Legislative
  Council's official table records the 2016 transfer from former § 41-2081 to
  § 3-3431:
  <https://www.azleg.gov/alisPDFs/council/TOSA_52nd_1st_Regular_and_1st_Special.pdf>.
- Arkansas Department of Agriculture, current Bureau of Standards page:
  <https://agriculture.arkansas.gov/crops-industry/bureau-of-standards/>. That
  page links the state's weights-and-measures compilation, including
  § 4-18-316, from the official Arkansas media host:
  <https://media.ark.org/agri/Weights_and_Measures.pdf>.

## Fifty-state-plus-D.C. authority map

`jurisdiction-research-v2.json` now maps one specific statute, regulation, or
official enforcement program for every state and D.C. The national index is
NIST's current state-by-state page, updated April 7, 2025:
<https://www.nist.gov/pml/owm/us-retail-pricing-laws-and-regulations-state>.
The map records the exact citation, source URL, source type, authority focus,
and a common operational baseline. Eight rows use an official NIST compilation
of state text because a stable current state deep-link was not established;
that provenance is stated rather than presented as direct state-code review.

An outbound availability probe on August 22, 2026 followed redirects for all
51 mapped URLs: 48 returned HTTP 200. Massachusetts and New York returned HTTP
403 to the automated client while remaining publicly indexed, and Tennessee
reset the automated connection while its current agency page remained publicly
indexed with the cited statute and UPC-verification program. URL availability
is recorded as research evidence, not made a deterministic CI gate: state sites
can apply bot controls or change transport behavior without changing the legal
source. Arkansas's retired path was replaced with the live compilation linked
by its current Bureau of Standards page, and Arizona's transferred citation was
updated to current § 3-3431(C).

The v2 map deliberately does **not** alter the frozen v20 legal-rule table.
V21 projects each exact citation and official URL into the executable
`rc_jurisdiction_rules` issue-spotting table without promoting the 45 research
rows into legal rules or remedies. All 51 map rows keep these gates:

- `substantive_legal_opinion: false`;
- `private_remedy_encoded: false`;
- `current_text_and_local_overlays_validated: false`; and
- `attorney_validation_required: true`.

The original six-jurisdiction triage remains the only subset with benchmark
rule fields. The other 45 rows have advanced from portal-only research queues
to specific authority maps, but not to deployment-ready legal conclusions.
The generated v2 workbook and 51 new structure-matched evidence packs preserve
that distinction. Counsel still must validate current text, scope, local
overlays, remedies, effective dates, and procedural requirements.
