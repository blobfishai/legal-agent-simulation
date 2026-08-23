# V21: 10x executable legal-work world

World v21 expands the 2,331-task canonical v20 world to exactly 23,310 tasks
without replacing its Harvey LAB, retail, capstone, or product-workflow lanes.
It also merges the 16 separately researched consumer-protection/privacy tasks
from `world-v20-draft.json`.

## Shipped surface

| Dimension | V20 canonical | V21 | Added |
|---|---:|---:|---:|
| Tasks | 2,331 | 23,310 | 20,979 (16 researched + 20,963 generated) |
| Deterministic verifiers | 2,331 | 23,310 | 20,979 |
| Agent-visible tools | 110 | 1,100 | 990 |
| Total operations | 121 | 1,111 | 990 |
| Contracts/systems | 10 | 32 | 22 |
| Tables | 56 | 254 | 198 |
| New evidence packs | 0 | 117 | 117 |
| New DOCX/XLSX/PDF inputs | 0 | 351 | 351 |

The 22 added CounselOps contracts cover litigation, corporate, contracts,
employment, privacy, cybersecurity, intellectual property, real estate, tax,
bankruptcy, antitrust, healthcare, environmental, financial services,
investment funds, insurance, immigration, trusts and estates, nonprofit,
government contracts, product safety, and investigations. Each domain has nine
resource types with list/get/search/create/update operations: 45 tools per
domain, 990 total.

## Task and verifier construction

Each generated task is grounded in one of the 117 mounted evidence packs, reads
two exact records, creates one record, and updates one record. Focus assignments
cover every added tool; 36 inherited v4 tools that previously lacked task
coverage receive explicit compatibility calls. Pack usage is balanced at
179–180 tasks per pack. Sixty-six packs span the 22 CounselOps practice
domains; 51 additional packs map one retail price-accuracy authority for every
state and D.C. while preserving the attorney-validation boundary. V21 also
projects all 51 exact citations and official URLs into the executable
`rc_jurisdiction_rules` table and migrates the six retail task/verifier pairs
through the authority-map gate. The two pairs that used generic portal-only
vocabulary are rewritten, and four top-level/phase VCode programs require all
51 rows through an unfiltered `count=51`/`total=51` tool result. Separate
build and scale gates bind each executable row to its exact citation and
official URL; the frozen v20 snapshot is unchanged.

The v21 VCode compiler emits a unique integrity-bound verifier configuration
for every generated task. Compact per-task stubs import one shared deterministic
runtime, keeping the canonical JSON at 263,108,165 bytes instead of duplicating
the evaluator 20,963 times. Gates include ordered calls, exact arguments,
observation anchors, exact created state, before/after update state, row-count
deltas, no deletes, forbidden-text vetoes, and no collateral mutation. The
scale checker executes every generated positive path and four negative modes
for every added tool: omitted final call, trap phrase, collateral write, and
deletion.

These 20,963 entries are deterministic matrix variants, not a claim of 20,963
independently lawyer-authored matters. They test stateful tool execution and
evidence handling; they do not grade open-ended legal prose or replace attorney
review. All entities and documents are synthetic.

## Rebuild and verify

```bash
npm run v20:build                 # rebuild canonical v20 from frozen v19 + overlay
npm run v21:build                 # contracts, 351 documents, and world
npm run v21:check                 # document hashes + full positive/adversarial gate
npm run v21:document-render-check # render all 585 pages and inspect geometry/text
npm run v21:serve                 # local MCP/runtime; v5 contracts auto-selected
npm run v21:harbor -- --tasks <comma-separated-task-ids>
```

Generated artifacts and their manifests:

- `mcp/v5/build-report.json` — contract/table/tool totals;
- `research/v21-seeded-documents/build-report.json` — evidence-pack totals and
  structure signature;
- `world/v21/build-report.json` — task/verifier coverage and world SHA-256;
- `world/v20/retail-overlay.json` — checked-in reconstruction delta for the
  otherwise gitignored canonical v20 snapshot.

`tools/check_v21_scale.py --sample N` is a faster development smoke test. A
release claim must use the default exhaustive mode.
The document-render command uses host LibreOffice when available and otherwise
runs through the local locked LAB renderer image with networking disabled.

## Release evidence

The 2026-08-22 release gate produced SHA-256
`76364790d9a548f01af25337a170c49269cbfeaf3f3b667db9460c29bdb2f5ab`
for `world-v21.json`; a second clean-process rebuild matched byte-for-byte. The exhaustive
checker executed all 20,963 generated positive paths plus four adversarial
modes for each of the 990 added tools. A live HTTP oracle independently passed
990/990 added-tool focus tasks.

All generated source documents are rendered with LibreOffice and inspected by
the release gate: 117 one-page DOCX briefs, 351 one-page spreadsheet
worksheets, and 117 one-page PDF extracts (585 rendered pages across 351
files). The gate also binds each rendered source to the catalog byte count and
SHA-256, rejects symlinks and traversal, and tests full-bleed PDF bodies for
clipping independently of their edge-to-edge headers. This review originally caught and
closed an original DOCX orphan-page defect and pinned both DOCX and spreadsheet
layout contracts in the deterministic structure signature.
