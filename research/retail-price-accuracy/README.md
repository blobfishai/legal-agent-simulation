# Retail price-accuracy evidence pack

This directory is a reproducible, synthetic evidence pack for legal-agent
tasks involving self-checkout duplicate scans, shelf/register price mismatch,
packaged-weight variance, customer remediation, receipt wording, legal triage,
and control implementation.

It contains one base scenario and two structurally identical mutations:

- `scenarios/ca-price-weight-duplicate-scan-v1`
- `mutations/mi-price-weight-duplicate-scan-v1`
- `mutations/dc-price-weight-duplicate-scan-v1`

Every scenario has the same five input filenames and internal structure:

- `incident-report.docx`
- `checkout-event-log.xlsx`
- `sample-receipts.pdf`
- `customer-price-accuracy-policy.docx`
- `jurisdiction-source-register.xlsx`

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

All stores, customers, receipts, event logs, amounts, and product records are
synthetic. No receipt, contract clause, disclaimer, or control can ensure that
a retailer will not be sued.
