# Rights-aware online legal-document sources

Research date: 2026-08-22. This inventory was rechecked against primary
publisher, government, and licensing pages on that date. Where a collection's
rights statement is ambiguous or more restrictive than an open derivative-work
licence, the policy fails closed.

Public access is not the same thing as permission to redistribute or mutate a
document. The recommended seed policy below is intentionally conservative.

| Source | Useful material | Seed policy | Rights and ingestion notes |
| --- | --- | --- | --- |
| [Atticus Project datasets](https://www.atticusprojectai.org/datasets/) | CUAD commercial contracts, MAUD merger agreements, and ACORD query-clause pairs | Mutation eligible | The publisher states that all datasets are CC BY 4.0. Preserve attribution, source URL, license, original hash, and a change log. |
| [Common Paper standards](https://commonpaper.com/standards/) | NDAs, cloud service agreements, terms of service, design-partner agreements, and other standard contracts | Mutation eligible | The standards page states that the agreements are released under CC BY 4.0. Attribute and identify changes. |
| [Bonterms Download Center](https://bonterms.com/download-center/) | NDAs, cloud/software terms, AI addenda, SLAs, BAAs, DPAs, and PSAs | Per-document license gate | The catalog says CC BY 4.0 unless otherwise noted, but some individual standards, including the [Standard End User Agreement](https://bonterms.com/standard/end-user-agreement-v1), are CC BY-ND 4.0. Mutate only an exact version expressly marked CC BY 4.0; keep BY-ND documents unmodified. |
| [UK Cabinet Office standard contracts](https://www.gov.uk/government/collections/government-standard-contracts-for-procurement) | Model Services Contract, Mid-Tier Contract, Short Form Contract, guidance, front sheets, core terms, and schedules in Word/PDF/ODT | Mutation eligible after file-level notice check | The current Model Services Contract states that its information may be used and reused, commercially or non-commercially, under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Preserve the required attribution and source/version; exclude any file or embedded third-party material carrying a different notice. |
| [Acquisition.gov FAR and DFARS](https://www.acquisition.gov/browse/index/far?frame=0) | Current and archived acquisition rules, provisions, clauses, and forms in HTML, DITA, PDF, Word, and e-book formats | Mutation eligible after government-authorship check | Official U.S. government works are generally outside U.S. copyright under [17 U.S.C. 105](https://www.copyright.gov/title17/92chap1.html#105), but the rule is authorship-specific. Admit only text verified as an official-duty government work; exclude contractor-supplied data, trademarks, seals, and third-party material. Pin the FAC/change number and effective date. |
| [EUR-Lex](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html?locale=en) | EU legislation, consolidated texts, summaries, metadata, HTML/XML/PDF renditions | Mutation eligible with exclusions | Legal documents are generally reusable unless otherwise specified; EU-owned editorial content is CC BY 4.0 and metadata is CC0. Exclude third-party works, special-condition documents, personal-data risks, logos, and industrial-property material. |
| [oneNDA](https://www.onenda.org/how-we-did-it) | A standardized NDA in Word format | Variables or unmodified copy only | oneNDA instructs users not to alter the body or branding and says changed documents may not be called oneNDA. Do not use it for free-text mutation; use only allowed variables or a separately branded synthetic agreement after a manual rights review. |
| [U.S. Courts forms](https://www.uscourts.gov/forms-rules/forms) | National federal forms, including downloadable PDFs and some Word templates | Fill-only pilot after provenance review | This is an official source, but the forms page does not itself state a blanket reuse license. Preserve the official form, fill only intended fields, record the revision/effective date, and confirm form-specific restrictions before redistribution. |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filing histories, XBRL facts, exhibits, HTML/XML/JSON, and nightly bulk archives | Retrieval and analysis; no automatic mutation | The data APIs require no authentication or key. Access does not make every privately authored filing exhibit public domain. Apply SEC fair-access rules and perform per-document copyright, privacy, and redistribution review. |
| [CourtListener / RECAP](https://wiki.free.law/c/courtlistener/help/data-coverage/federal-cases-and-filings) | Federal dockets and filing PDFs exposed through APIs | Retrieval and analysis; no automatic mutation | The archive contains mixed-authorship filings and exhibits, potentially with personal data. Prefer judicial opinions and clearly public-domain government material; scrub PII and review rights for briefs and exhibits. |
| [Public.Resource.Org legal materials](https://law.resource.org/pub/us/) | Bulk primary legal material and verified works of the U.S. government | Verified government works only | Federal works created within official duties and government edicts can be seeded after provenance checks. Do not infer that privately authored briefs or third-party material in the same tree are public domain. |
| [New Zealand Government Procurement templates](https://www.procurement.govt.nz/templates/) | Government model contracts, RFx documents, evaluation forms, due-diligence checklists, and variation templates in DOCX/PDF | Research only by default | The site's default licence is CC BY-NC 4.0 and it excludes third-party material, logos, and restricted content. Its procurement guidance also says approved templates should not be changed. Keep it out of commercial/distributable mutation corpora unless counsel approves a specifically non-commercial use and the exact file has no different notice. |
| [Australian Commonwealth Contracting Suite](https://www.finance.gov.au/government/procurement/commonwealth-contracting-suite-ccs) | Approach-to-market and contract terms, change records, smart forms, and sample contract PDFs | No mutation | The official copyright page applies CC BY-NC-ND 4.0, and the samples say they are informational rather than templates. They can inform task taxonomy and comparative research, but derivatives must not be generated or redistributed from them. |

## Best first ingestion wave

1. Start with CC BY 4.0 Atticus, Common Paper, and individually verified
   Bonterms documents. These support clause extraction, issue spotting,
   playbook comparison, redlining, diligence summaries, and alternate-party
   drafting tasks.
2. Add the UK Cabinet Office contract suites under OGL v3.0. Their multi-file
   Word structures support schedule reconciliation, precedence, change-order,
   service-level, procurement-risk, and cross-document consistency tasks.
3. Add EUR-Lex and verified government-authored FAR/DFARS material with
   attribution, version pins, and exclusion filters. These support authority
   timelines, applicability matrices, clause-selection tasks, and
   regulatory-change tasks.
4. Pilot fillable U.S. Courts forms without altering their fixed text. Pair
   them with wholly synthetic fact patterns, then verify every filled PDF
   visually and structurally.
5. Use EDGAR and RECAP as retrieval sources until a per-document provenance,
   privacy, and rights gate is in place. Keep New Zealand and Australian
   procurement documents out of the mutation corpus under their current
   restrictive licences.

## Task blueprints enabled by the first wave

| Input family | New task | Deliverable and deterministic anchors |
| --- | --- | --- |
| Atticus CUAD/MAUD | Build a contract diligence exception report from a selected agreement set | DOCX memo plus XLSX issue matrix; verify source contract IDs, clause labels, quoted anchors, row coverage, and formula-driven counts. |
| Common Paper and CC BY Bonterms | Compare a counterparty form against a stated playbook and prepare a narrow redline | DOCX redline plus negotiation summary; verify exact target clauses, required fallbacks, OOXML revision markup, attribution, and absence of edits outside the allowed sections. |
| UK Model Services Contract | Reconcile front sheet, core terms, and schedules for conflicts and missing elections | XLSX precedence/issue log plus DOCX amendment; verify schedule references, selected options, dates, amounts, cross-document anchors, and workbook formulas. |
| UK Model Services Contract | Prepare a change-control and service-level response from a synthetic performance record | DOCX notice plus XLSX credit calculation; verify notice prerequisites, timetable, service-level inputs, capped calculations, and preserved source citations. |
| FAR/DFARS | Select and flow down clauses for a synthetic procurement profile | XLSX clause matrix plus short memo; verify pinned FAC/change number, exact clause identifiers, prescription conditions, alternates, and flow-down decisions. |
| EUR-Lex | Compare two pinned versions of a legal instrument and prepare an applicability timeline | DOCX impact memo plus XLSX timeline; verify CELEX identifiers, effective dates, article references, jurisdiction/entity conditions, and chronology. |
| U.S. Courts forms | Complete an official fillable form from a wholly synthetic case file | Filled PDF plus filing checklist; verify field values, form/revision identifier, fixed-text hash, required attachments, and visual bounds without changing official language. |
| EDGAR or RECAP retrieval lane | Assemble a provenance-first evidence packet without mutating source filings | Markdown or DOCX memo plus citation index; verify accession/docket identifiers, complete pagination, retrieval timestamps, source URLs, and zero inclusion of nonresponsive documents. |

## Seed admission gate

A URL in this table is a research lead, not an approved seed. Before download or
mutation, require all of the following:

1. Resolve and record the canonical file URL, publisher, document version/date,
   retrieval time, media type, byte length, and SHA-256.
2. Save the exact licence text or public-domain basis that applies to that exact
   file. A collection-level statement is insufficient when the publisher says
   "unless otherwise noted."
3. Reject non-commercial and no-derivatives material for the distributable
   mutation corpus; reject files with an unknown author, embedded third-party
   works, PII, signatures, account details, or privileged/confidential content.
4. Record the allowed transformations and required attribution. Keep the
   untouched original immutable and generate derivatives into a separate tree.
5. Run the existing structure, residual-entity, re-derivation, schema, rubric,
   application-open, and visual checks before promoting a seed.

Every downloaded source should carry a sidecar with its canonical URL,
retrieval timestamp, publisher, exact license or rights basis, original hash,
document date/version, PII review status, allowed transformations, attribution
text, and generated-derivative lineage.
