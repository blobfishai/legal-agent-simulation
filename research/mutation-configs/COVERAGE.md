# Seeded entity-variant coverage (`research/lab_mutate.py`)

Status of the committed seed plan (`seed-plan.json`) against the pinned Harvey
mirror `harveyai/harvey-labs@7be41d57fd5a`. Outputs land under
`research/mutations/<area>/<task>__seed-NNN/` and are gitignored: each variant
is fully reproducible from the pinned commit, the committed `entities.json`,
and the integer seed. Validation = `python3 research/lab_mutate.py --check-plan
research/mutation-configs/seed-plan.json`, which independently re-derives every
task.json and every document byte and fails closed on residual source
entities, drift, or orphaned outputs.

`candidate-status.json` classifies every committed `entities.json` as either
planned or blocked, and `tools/check_harvey_mutation_inventory.py` rejects any
missing, overlapping, or silently unclassified map before the expensive byte
reproduction check runs.

| # | Source task | Docs | Formats | Entities mapped | Seeds | Validation |
|---|---|---|---|---|---|---|
| 1 | banking-finance/identify-issues-in-compliance-certificate (pilot) | 4 | docx, xlsx, eml | 16 | 1, 2, 3 | pass |
| 2 | banking-finance/compare-borrower-covenant-compliance-analysis | 5 | 2 docx, 2 xlsx, eml | 11 | 1, 2, 3 | pass |
| 3 | banking-finance/compare-credit-agreement-against-term-sheet | 3 | 2 docx, eml | 14 | 1, 2, 3 | pass |
| 4 | corporate-ma/analyze-counterparty-spa-markup | 6 | 4 docx, xlsx, eml | 22 | 1, 2 | pass |
| 5 | employment-labor/analyze-counterparty-markup-of-executive-employment-agreement | 5 | 3 docx, xlsx, eml | 14 | 1, 2 | pass |
| 6 | real-estate/analyze-counterparty-markup-of-commercial-lease-agreement | 5 | 3 docx, xlsx, eml | 17 | 1, 2 | pass |
| 7 | tax/analyze-counterparty-markup-of-tax-closing-agreement | 6 | 4 docx, xlsx, eml | 11 | 1, 2 | pass |
| 8 | funds-asset-management/analyze-counterparty-markup-of-limited-partnership-agreement | 5 | 4 docx, eml | 14 | 1, 2 | pass |
| 9 | intellectual-property/analyze-counterparty-markup-of-ip-assignment-agreement | 6 | 4 docx, xlsx, eml | 19 | 1, 2 | pass |
| 10 | capital-markets/analyze-counterparty-markup-of-underwriting-agreement | 5 | 4 docx, eml | 15 | 1, 2 | pass |
| 11 | bankruptcy-restructuring/analyze-counterparty-markup-of-restructuring-support-agreement | 6 | 4 docx, xlsx, eml | 25 | 1, 2 | pass |
| 12 | data-privacy-cybersecurity/analyze-counterparty-markup-of-data-processing-agreement | 5 | 4 docx, eml | 18 | 1, 2 | pass |
| 13 | emerging-companies-venture-capital/analyze-counterparty-markup-of-stock-purchase-agreement | 6 | 4 docx, xlsx, eml | 23 | 1, 2 | pass |
| 14 | insurance/analyze-counterparty-markup-of-reinsurance-treaty | 6 | 3 docx, xlsx, 2 eml | 15 | 1, 2 | pass |
| 15 | litigation-dispute-resolution/analyze-counterparty-motion-to-dismiss | 6 | 4 docx, 2 eml | 16 | 1, 2 | pass |
| 16 | white-collar-defense-investigations/analyze-counterparty-markup-of-deferred-prosecution-agreement | 6 | 5 docx, eml | 16 | 1, 2 | pass |

Totals: 16 source tasks, 14 practice areas, 35 seeded variants (32 beyond the
pilot), 85 task-relative source document occurrences, and 182 generated
document instances. `--check-plan` verdict: **35/35 valid** at source
`7be41d57fd5a`.

Rows 15 and 16 were initially blocked by two newly identified upstream source
defects (each reproduced on the unmodified source, so entity-independent) and
were unblocked on 2026-08-23 by extending the tool — see the 2026-08-23
capability note below. The defect records and their resolutions are kept in
`candidate-status.json` under `resolved`.

Known tool limitation recorded during row 9: `.eml` headers that carry raw
UTF-8 (not RFC-2047 encoded-words) are surrogate-escaped by Python's header
parser, so non-ASCII names there ("Derek Muñoz") cannot be substituted; the
residual scan correctly flags them, and such names are left unmapped with the
choice documented.

Admission status: these thirty-five outputs are reproducible mutation and
regression fixtures, not thirty-five independently graded v21 tasks. See
[`../harvey-augmentation/ADMISSION.md`](../harvey-augmentation/ADMISSION.md) for
the release boundary. The canonical v21 scale claim instead counts 117 admitted
packs, 351 documents, and 94 mutations that are referenced by stable tasks and
native Harbor packages.

## Tool capability note (2026-08-23)

Rows 15 and 16 failed closed against two upstream source defects that were
entity-independent (each reproduced on unmodified source). The tool was again
extended rather than weakened. These changes advance generated provenance to
`research/lab_mutate.py v3`:

- `validate_task` accepts the explicit "FAIL only if" trigger alongside
  "FAIL if" (`FAIL_CLAUSE_RE`). The upstream litigation criterion C-021 is
  written "PASS if … FAIL only if …", which is fail-closed in the same sense;
  a rubric with no FAIL clause is still rejected (probe-tested).
- The OOXML writers snapshot each source member's ZIP metadata before writing
  and restore what Python's `zipfile` normalizes (`flag_bits` reset to 0,
  zero `external_attr` promoted to `0o600 << 16`): `external_attr` via the
  central directory, `flag_bits` by patching the already-written local header
  so the archive stays internally consistent. The white-collar
  `negotiation-strategy-memo.docx` (flag_bits `0x802`, external_attr 0,
  authored by a different upstream pipeline than its siblings) now
  round-trips byte-faithfully; a data-descriptor flag mismatch still fails
  closed. Metadata is retained in archive order, so duplicate ZIP member names
  cannot collapse into one dictionary entry. Members whose metadata already
  matches are untouched, so every
  previously passing document re-derives byte-identically — verified by the
  full 35-variant `--check-plan` re-derivation.
- CLI generation and checking now share an ownership-checked, non-symlink,
  mode-0600 advisory lock keyed to the resolved output tree. Concurrent plan
  generation/check invocations can no longer observe or publish a partially
  replaced variant; each individual variant still uses its validated sibling
  staging directory and atomic directory replacement.
- Plan execution captures one clean, pinned source attestation and rechecks it
  at closeout while retaining per-task, per-document, license, entity-map, and
  generated-byte validation. It no longer runs a full 60,971-file Git status
  scan for every generated or re-derived variant (up to 210 scans for the
  35-variant generate-and-check CLI path); a regression freezes the
  source-cleanliness scan count at two per complete plan operation.
- DOCX verification processes paragraph runs together exactly once and limits
  the isolated-run fallback to XML outside those paragraphs. Boundary
  substitutions use literal search instead of recompiling and applying one
  regular expression per entity/run, and the residual verifier case-folds a
  document once before native literal searches. Regression tests preserve the
  boundary, split-run, metadata, and unscoped-run semantics.

## Tool capability note (2026-08-22)

The first generation attempt for the four counterparty-markup tasks (rows 4,
5, 7, 8) failed closed with residual source entities in the redlined
documents: tracked-change constructs carry entity names outside ordinary text
runs (`w:delText` deleted-run text, `w:author` revision metadata, reviewer
rosters in `word/people.xml`, and docProps text nodes), which the v2 mutator
never rewrote. `research/lab_mutate.py` was extended rather than weakened:

- `WT_RE` now covers `w:delText` alongside `w:t`, so deleted runs participate
  in the same cross-run paragraph replacement as live runs;
- a boundary-guarded, XML-escape-aware pass (`replace_escaped_xml_boundary`)
  runs over every serialized XML part of a DOCX, covering attribute values and
  metadata text nodes.

Both passes match exactly the byte forms the semantic residual scan reads and
apply the same alphanumeric boundary guards, so any document that previously
passed the residual scan re-derives byte-identically — verified against the
pilot and against a passing redline-bearing output before regeneration. All
validation (topology equality, OOXML parse, fail-closed residual scan,
byte-level re-derivation) is unchanged.

## Entity-mapping scope

Entity maps cover every transaction party, counsel firm (with domains), and
named person (with e-mail local parts and, where the text uses gendered
pronouns, matching replacement gender). Two deliberate scope choices:

- Deep comp-table filler names (e.g. the ~25 customer names inside
  `dataforge-financial-summary.xlsx`) are mapped only where they also appear
  in the negotiation documents; purely tabular one-off names are left as-is
  to stay within the deterministic name banks. The real-estate comp table
  (row 6) is fully mapped as a worked example of the opposite choice.
- Names that occur only as bare surnames with no recoverable first name
  ("Mr. Brennan" in row 8's precedent anecdote) or only as alternate
  short-form domains (`csmlaw.com`, `khdlaw.com`, `hpllaw.com`, `acwlaw.com`)
  are left unmapped; they never boundary-match a substitution source, so the
  fail-closed scan is unaffected.

Eponymous founder/firm tangles (Whitmore Capital + Marcus/Julian Whitmore;
Kessler Hahn & Devereaux + Thomas Kessler) are modeled as a company entity
without a bare-surname fragment plus a person entity that owns the standalone
surname; longest-match ordering keeps the compound and personal usages
disjoint. Comma-form firm names ("Hargrove, Pennington & Locke LLP"), which
cannot match a single entity name, are decomposed into a leading single-name
lawfirm entity (carrying the domain) plus an "X & Y" lawfirm entity.

## Adding a task

1. Pick a task whose `documents/` are OOXML/eml/plain only (no PDFs — the
   mutator refuses them by design).
2. Inventory entities: read `task.json` and the extracted document text
   (`extract_all_text` in the tool); capture companies with role + prefix
   fragments + domains, firms, and people (exactly "First Last"; add
   `pronouns` only when the text itself uses she/he for that person).
3. Write `research/mutation-configs/<area>/<slug>/entities.json`, append the
   task to `seed-plan.json` with unique seeds.
4. Generate each new seed via `--task <area>/<slug> --entities ... --seed N`
   (the plan runner refuses existing output dirs), then run `--check-plan`.
5. The residual scan names any term it could not eliminate; refine the entity
   map (fragments, decomposition) rather than relaxing validation.
