# Seeded entity-variant coverage (`research/lab_mutate.py`)

Status of the committed seed plan (`seed-plan.json`) against the pinned Harvey
mirror `harveyai/harvey-labs@7be41d57fd5a`. Outputs land under
`research/mutations/<area>/<task>__seed-NNN/` and are gitignored: each variant
is fully reproducible from the pinned commit, the committed `entities.json`,
and the integer seed. Validation = `python3 research/lab_mutate.py --check-plan
research/mutation-configs/seed-plan.json`, which independently re-derives every
task.json and every document byte and fails closed on residual source
entities, drift, or orphaned outputs.

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

Totals: 8 source tasks, 6 practice areas, 19 seeded variants (16 beyond the
pilot), 39 source documents mutated per seed set, `--check-plan` verdict:
**19/19 valid** at source `7be41d57fd5a`. No candidate task was dropped.

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
