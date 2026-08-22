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

## Generate the pilots

```bash
for recipe in research/harvey-augmentation/recipes/*.json; do
  python3 tools/mutate_harvey_task.py --recipe "$recipe"
done
```

Generated tasks are written below `research/harvey-augmentation/generated/tasks/`.
The original `research/repos/harveyai@harvey-labs` tree remains clean.
Generation deliberately refuses to overwrite an existing variant.

Validate committed variants against the current pinned source with:

```bash
while IFS= read -r manifest; do
  python3 tools/mutate_harvey_task.py --check "$(dirname "$manifest")"
done < <(rg --files research/harvey-augmentation/generated \
  -g mutation-manifest.json)
```

The initial recipe set exercises four distinct benchmark designs: borrower-side
waiver drafting, lender-side reservation-of-rights drafting, a corrected
DOCX/XLSX compliance package, and a structure-preserving threshold-edge
mutation. See `ONLINE_SOURCES.md` for the rights-aware external source survey.

## Relationship to the broad seeded mutator

The repository also includes `research/lab_mutate.py`. The two tools serve
different quality envelopes:

- Use `research/lab_mutate.py` for high-volume, seed-driven entity variants. It
  can find names split across Word runs and generates coherent companies,
  people, domains, acronyms, and places from synthetic name banks. Because it
  may merge affected Word runs and reserialize workbooks, its outputs require
  template-family render testing.
- Use `tools/mutate_harvey_task.py` for benchmark-ready task derivatives and
  layout-sensitive seeds. Its equal-length raw-XML substitutions preserve every
  package part and byte outside the declared replacements. Its checker
  independently re-derives the task and every document from the pinned source
  plus recipe, rejecting any unrecorded change.

Both lanes leave the Harvey mirror immutable and record mutation provenance.

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
