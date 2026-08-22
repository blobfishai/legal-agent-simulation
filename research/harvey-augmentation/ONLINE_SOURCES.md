# Rights-aware online legal-document sources

Research date: 2026-08-22.

Public access is not the same thing as permission to redistribute or mutate a
document. The recommended seed policy below is intentionally conservative.

| Source | Useful material | Seed policy | Rights and ingestion notes |
| --- | --- | --- | --- |
| [Atticus Project datasets](https://www.atticusprojectai.org/datasets/) | CUAD commercial contracts, MAUD merger agreements, and ACORD query-clause pairs | Mutation eligible | The publisher states that all datasets are CC BY 4.0. Preserve attribution, source URL, license, original hash, and a change log. |
| [Common Paper standards](https://commonpaper.com/standards/) | NDAs, cloud service agreements, terms of service, design-partner agreements, and other standard contracts | Mutation eligible | The standards page states that the agreements are released under CC BY 4.0. Attribute and identify changes. |
| [Bonterms Download Center](https://bonterms.com/download-center/) | NDAs, cloud/software terms, AI addenda, SLAs, BAAs, DPAs, and PSAs | Per-document license gate | The catalog says CC BY 4.0 unless otherwise noted, but some individual standards are CC BY-ND 4.0. Mutate only an exact version expressly marked CC BY 4.0; keep BY-ND documents unmodified. |
| [EUR-Lex](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html?locale=en) | EU legislation, consolidated texts, summaries, metadata, HTML/XML/PDF renditions | Mutation eligible with exclusions | Legal documents are generally reusable unless otherwise specified; EU-owned editorial content is CC BY 4.0 and metadata is CC0. Exclude third-party works, special-condition documents, personal-data risks, logos, and industrial-property material. |
| [oneNDA](https://www.onenda.org/how-we-did-it) | A standardized NDA in Word format | Variables or unmodified copy only | oneNDA instructs users not to alter the body or branding and says changed documents may not be called oneNDA. Do not use it for free-text mutation; use only allowed variables or a separately branded synthetic agreement after a manual rights review. |
| [U.S. Courts forms](https://www.uscourts.gov/forms-rules/forms) | National federal forms, including downloadable PDFs and some Word templates | Fill-only pilot after provenance review | This is an official source, but the forms page does not itself state a blanket reuse license. Preserve the official form, fill only intended fields, record the revision/effective date, and confirm form-specific restrictions before redistribution. |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filing histories, XBRL facts, exhibits, HTML/XML/JSON, and nightly bulk archives | Retrieval and analysis; no automatic mutation | The data APIs require no authentication or key. Access does not make every privately authored filing exhibit public domain. Apply SEC fair-access rules and perform per-document copyright, privacy, and redistribution review. |
| [CourtListener / RECAP](https://wiki.free.law/c/courtlistener/help/data-coverage/federal-cases-and-filings) | Federal dockets and filing PDFs exposed through APIs | Retrieval and analysis; no automatic mutation | The archive contains mixed-authorship filings and exhibits, potentially with personal data. Prefer judicial opinions and clearly public-domain government material; scrub PII and review rights for briefs and exhibits. |
| [Public.Resource.Org legal materials](https://law.resource.org/pub/us/) | Bulk primary legal material and verified works of the U.S. government | Verified government works only | Federal works created within official duties and government edicts can be seeded after provenance checks. Do not infer that privately authored briefs or third-party material in the same tree are public domain. |

## Best first ingestion wave

1. Start with CC BY 4.0 Atticus, Common Paper, and individually verified
   Bonterms documents. These support clause extraction, issue spotting,
   playbook comparison, redlining, diligence summaries, and alternate-party
   drafting tasks.
2. Add EUR-Lex material with attribution and exclusion filters. This supports
   authority timelines, applicability matrices, multilingual comparison, and
   regulatory-change tasks.
3. Pilot fillable U.S. Courts forms without altering their fixed text. Pair
   them with wholly synthetic fact patterns, then verify every filled PDF
   visually and structurally.
4. Use EDGAR and RECAP as retrieval sources until a per-document provenance,
   privacy, and rights gate is in place.

Every downloaded source should carry a sidecar with its canonical URL,
retrieval timestamp, publisher, exact license or rights basis, original hash,
document date/version, PII review status, allowed transformations, attribution
text, and generated-derivative lineage.
