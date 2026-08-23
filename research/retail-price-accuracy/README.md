# Retail price-accuracy evidence pack

This directory is a reproducible, synthetic evidence pack for legal-agent
tasks involving self-checkout duplicate scans, shelf/register price mismatch,
packaged-weight variance, customer remediation, receipt wording, legal triage,
and control implementation.

It contains one base scenario and two structurally identical mutations:

- `scenarios/ca-price-weight-duplicate-scan-v1`
- `mutations/mi-price-weight-duplicate-scan-v1`
- `mutations/dc-price-weight-duplicate-scan-v1`

Every scenario has the same six input filenames and internal structure:

- `incident-report.docx`
- `checkout-event-log.xlsx`
- `sample-receipts.pdf`
- `customer-price-accuracy-policy.docx`
- `jurisdiction-source-register.xlsx`
- `jurisdiction-authority-map-v2.xlsx`

Regenerate them with:

```bash
python3 tools/build_retail_price_accuracy_pack.py
python3 tools/build_retail_price_accuracy_pack.py --check  # isolated byte-for-byte rebuild
```

`seed-data.json` hydrates the executable RetailGuard product contract in world
v20. Every legal-rule row is marked `attorney_validation_required = 1`. Six
jurisdictions have benchmark-level primary-source triage; the other 45 rows
identify an official code portal and deliberately say that substantive review
is pending. NIST Handbook 130/EPPV is used only as an inspection-method
baseline, never as a substitute for governing law.

`jurisdiction-research-v2.json` layers two research passes on top of that
frozen fixture without changing it: a per-jurisdiction authority map (one
anchored citation per row, consumed by the generated
`jurisdiction-authority-map-v2.xlsx`), and — under each researched row's
`deep_triage` key — an AI-assisted primary-source triage of all 45
former research-queue jurisdictions: the located pricing/scanner/item-pricing
authority (or an explicit none-found finding), the UDAP statute, the
weights-and-measures chapter, an overcharge-remedy analysis, a proposed rule
tier, per-row confidence, residual attorney work, and source URLs. Notable
deep-triage findings: Wisconsin's Wis. Stat. § 98.08 statutory
refund-the-difference remedy, Oklahoma's lowest-price mandate
(Okla. Stat. tit. 2, § 2-14-38), Hawaii's charged-price-equals-displayed-price
rule (HRS § 486-116), and Virginia's per se VCPA treatment of item-pricing
violations (Va. Code §§ 3.2-5627, 3.2-5630). Deep triage is research staging,
not attorney validation: every row remains
`attorney_validation_required`, and none of it feeds the frozen
`rc_jurisdiction_rules` seed table.

All stores, customers, receipts, event logs, amounts, and product records are
synthetic. No receipt, contract clause, disclaimer, or control can ensure that
a retailer will not be sued.
