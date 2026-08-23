# v17A — Harvey LAB evidence and isolated file lane

Status: **built and mechanically verified** against
`harveyai/harvey-labs@7be41d57fd5a`.

This milestone imports the evidence and execution contract without pretending
that a copied prose rubric is a deterministic answer key. The source-native
task bank is evidence-ready; tasks enter the headline benchmark only in v17B
after compiled assertions pass oracle and discrimination.

## Measured inventory

| Measure | Result |
|---|---:|
| LAB tasks | 2,010 |
| Rubric criteria | 114,437 |
| Task-local document occurrences | 51,683 |
| Unique task-local binaries | 51,253 |
| Shared firm-knowledge DMS files | 9,288 |
| Total physical inputs | 60,971 |
| Total source bytes | 3,206,739,638 |
| Parsed task-local occurrences | 51,683 / 51,683 (100%) |
| Shared DMS parse failures | 0 |

Every task-local binary is preserved byte-for-byte in a content-addressed
store. The committed source lock covers the evidence tree, shared DMS tree,
MIT license, LAB parser, system prompt, and three document skills. The SQLite
index retains every occurrence-to-blob provenance edge and a full-text row for
every successfully parsed unique blob.

Nine task-local DOCX/XLSX packages contain raw ampersands in XML text nodes and
also fail through LAB's own pinned `parse-doc` implementation. The v5 indexer
recovers those exact packages by escaping only the otherwise-invalid
ampersands in a temporary derivative. The committed report records every
source SHA-256, package part, and occurrence count; exact binaries remain
unchanged in the content-addressed store.

## Extractor parity

The derivative indexer was compared document-by-document with LAB's own
containerized parser on a fixed, format-stratified sample:

| Format | Sample | Mean token recall | Worst document | Errors |
|---|---:|---:|---:|---:|
| DOCX | 32 | 98.4134% | 96.3086% | 0 |
| XLSX | 16 | 99.1639% | 92.6546% | 0 |
| PPTX | 16 | 100.0000% | 100.0000% | 0 |

DOCX uses safe direct OOXML text extraction and XLSX uses read-only openpyxl
for indexing throughput. PPTX stays on LAB's MarkItDown path because measured
notes/structure loss made the shortcut unacceptable. Exact input binaries are
never transformed.

## Two isolated lanes

For every task-local LAB task, Harbor can now stage:

- `/workspace/documents` as a read-only task-specific evidence mount;
- `/workspace/output` as the writable deliverable contract;
- the exact LAB `docx`, `xlsx`, and `pptx` skills;
- a separate heavy agent image based on LAB's pinned sandbox;
- output artifacts under `/logs/artifacts` after the trial.

`reward.json` reports `file_passed`, `state_passed`, and `lane_split`. At v17A,
`file_passed` is explicitly `grade_kind=output_contract_only`: it proves that
the exact non-empty filename exists and is not a symlink; it does not claim
that the document's prose is correct. The deterministic world reward is not
blended with this diagnostic. v17B adds source-grounded content assertions
before the split is eligible for the headline benchmark.

## Reproduce the gate

```bash
python3 world/ingest/lab_ingest.py --check
python3 tools/check_lab_ingest.py
python3 tools/check_lab_extractor_parity.py --check
python3 tools/check_lab_port.py
python3 tools/check_harbor_file_lane.py
```

Expected reconciliation:

```text
LAB port: 2,010/2,010 tasks, 114,437 criteria, 60,971 input files,
          1,758 exact output contracts
```

The two missing filename contracts are source omissions and are recorded by
stable task ID in `harvey-practice.json`; the importer does not invent them.
