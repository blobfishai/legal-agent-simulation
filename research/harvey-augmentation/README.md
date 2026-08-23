# Harvey LAB augmentation lane

This lane creates additional benchmark tasks without editing the pinned Harvey
mirror. It supports two distinct forms of expansion:

1. **Alternate tasks over unchanged evidence.** The same source documents can
   support a different party posture, deliverable, workflow stage, or prior-state
   requirement. This adds genuinely different work without manufacturing facts.
2. **Structure-preserving synthetic variants.** Declarative equal-length text
   substitutions alter entities, thresholds, dates, or terms inside raw OOXML
   parts. The generator does not parse and reserialize the package, so styles,
   runs, formulas, worksheet topology, relationships, sections, headers, and
   drawings remain untouched outside the matched bytes.

Every generated task includes:

- the Harvey source commit and source task path;
- source and output SHA-256 values for every input;
- exact task/document replacement counts;
- changed OOXML part names and a package-topology equality check;
- a copied recipe and mutation manifest;
- fail-closed task/rubric and ZIP/XML validation.

The source material is MIT-licensed. The required Harvey notice is retained in
[`LICENSE.harvey-labs`](LICENSE.harvey-labs); strict and broad generated
manifests both bind the source license by SHA-256 and bind the checked-out source
to the commit in `research/repos-commits.json`.

## Generate the pilots

```bash
for recipe in research/harvey-augmentation/recipes/*.json; do
  python3 tools/mutate_harvey_task.py --recipe "$recipe"
done
```

Generated tasks are written below `research/harvey-augmentation/generated/tasks/`.
The original `research/repos/harveyai@harvey-labs` tree remains clean.
Generation deliberately refuses to overwrite an existing variant.
Pass `--replace-generated` only to atomically refresh a directory whose existing
manifest identifies the same source task, output task, and variant.

Validate committed variants against the current pinned source with:

```bash
python3 tools/mutate_harvey_task.py \
  --check-root research/harvey-augmentation/generated \
  --recipes-dir research/harvey-augmentation/recipes
```

This tree-wide check rejects missing recipes, missing generated tasks, orphaned
tasks, extra files, source drift, residual source terms, and non-recipe changes.

The initial recipe set exercises four distinct benchmark designs: borrower-side
waiver drafting, lender-side reservation-of-rights drafting, a corrected
DOCX/XLSX compliance package, and a structure-preserving threshold-edge
mutation. See `ONLINE_SOURCES.md` for the rights-aware external source survey.

## Relationship to the broad seeded mutator

The repository also includes `research/lab_mutate.py`. The two tools serve
different quality envelopes:

- Use `research/lab_mutate.py` for high-volume, seed-driven entity variants. It
  can find names split across Word runs — including deleted runs inside tracked
  changes — and rewrites tracked-change author metadata, reviewer rosters, and
  docProps via a boundary-guarded pass over every serialized XML part, so
  redlined counterparty markups mutate cleanly. It generates coherent companies,
  people, domains, acronyms, and places from synthetic name banks, preserves
  OOXML member order and metadata, mutates spreadsheets without reserialization,
  retains every Word text-run node during cross-run replacement, stages and
  validates before publication, and refuses implicit overwrite. Unequal-length
  substitutions can still reflow text, so its DOCX outputs require
  template-family render testing.
- Use `tools/mutate_harvey_task.py` for benchmark-ready task derivatives and
  layout-sensitive seeds. Its equal-length raw-XML substitutions preserve every
  package part and byte outside the declared replacements. Its checker
  independently re-derives the task and every document from the pinned source
  plus recipe, rejecting any unrecorded change.

Both lanes leave the Harvey mirror immutable and record mutation provenance.
The broad lane copies its exact entity config into each seed and provides a
`--check` mode that independently re-derives every output byte.

These strict and broad outputs are generator regression assets, not silently
counted production tasks. The release-admission boundary and exact counts are
recorded in [`ADMISSION.md`](ADMISSION.md); v21 task counts include only fixtures
with stable task IDs, acceptance contracts, and Harbor packages.

The committed seed plan reproduces the local high-volume variants:

```bash
python3 research/lab_mutate.py \
  --plan research/mutation-configs/seed-plan.json
python3 research/lab_mutate.py \
  --check-plan research/mutation-configs/seed-plan.json
```

Seed outputs remain ignored because they are fully reproducible from the pinned
Harvey commit, the committed entity config, and the integer seed. The plan makes
the intended seed set explicit and rejects missing or orphaned variants.

The committed plan currently covers fourteen source tasks across twelve
practice areas for thirty-one seeded variants; per-task entity maps, seed
counts, formats, and validation status are tabulated in
[`../mutation-configs/COVERAGE.md`](../mutation-configs/COVERAGE.md).

## Pinned upstream source defects

The deep input audit parses every `.xml` and `.rels` member, not just each ZIP
CRC. At commit `7be41d57fd5a`, nine tracked Office packages contain raw,
unescaped ampersands in an XML text node. The mirror is intentionally not
rewritten: byte identity and Git cleanliness are part of the provenance model.
[`upstream-ooxml-defects.json`](upstream-ooxml-defects.json) records each exact
path, package part, occurrence count, and source SHA-256. The audit succeeds only
while the observed defects match that exact-hash inventory; any new, missing, or
changed defect fails validation. Generated mutation lanes still reject malformed
source packages rather than silently normalizing them.

## Guardrails for scaling

- Prefer alternate-task variants before document mutation.
- Keep source and generated lanes separate; never overwrite a Harvey input.
- Use equal-length substitutions by default to minimize pagination drift.
- Update rubric facts whenever a mutation changes the right answer.
- Require exact minimum replacement counts so stale recipes fail closed.
- Do not mutate arbitrary PDFs in place. Use fillable fields, a properly
  redacted/overlaid derivative with visual review, or a synthetic companion
  document instead.
- Label synthetic variants and retain attribution/license metadata.
- Run structural checks for every output and visual render checks for a
  representative sample of each template family before a large batch.
