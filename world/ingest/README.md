# Harvey LAB evidence ingest

This directory is the reproducible boundary between the public Harvey LAB
snapshot and the simulation world. The source itself is intentionally ignored
because it is 3.2 GB; its revision and byte identity are committed here.

Measured at `harveyai/harvey-labs@7be41d57fd5a`:

- 2,010 tasks and 114,437 criteria;
- 51,683 task-local documents (51,253 unique blobs, 2,686,142,369 bytes);
- one shared 9,288-file firm-knowledge DMS used by 250 tasks (the existing
  `world/corpus/ch` store);
- 60,971 physical input files and 3,206,739,638 bytes in total.

`lab-source-lock.json` records the exact evidence-tree SHA-256, the shared DMS
tree SHA-256, the MIT license hash, and the LAB parser/skills harness hash.
Source drift is a hard error.

## Build and verify

```bash
# Recompute identity only; does not parse files.
python3 world/ingest/lab_ingest.py --inventory-only

# Build Harvey's sandbox/parser image from the pinned source, then ingest.
docker build -t legal-agent-lab-parser:7be41d57fd5a \
  research/repos/harveyai@harvey-labs/sandbox
python3 world/ingest/lab_ingest.py

# Verify metadata and materialized paths; --deep re-hashes all source blobs.
python3 world/ingest/lab_ingest.py --check
python3 world/ingest/lab_ingest.py --check --deep

# Fast hermetic regression gate used in CI.
python3 tools/check_lab_ingest.py
python3 tools/check_lab_extractor_parity.py --check
```

The host only enumerates, hashes, and hard-links opaque source bytes. Office
parsing runs once inside the network-disabled LAB sandbox. The resulting
`world/corpus/lab` directory is regenerable and ignored; the compact measured
`lab-ingest-report.json` is committed. A run exits nonzero below 99% parsed and
lists every failed occurrence by task and source path.

Nine pinned upstream packages contain raw ampersands in OOXML text nodes. The
v5 extractor first attempts normal parsing, then narrowly escapes only those
otherwise-invalid ampersands in an in-memory/temporary derivative. Exact source
blobs remain untouched. Every recovery is recorded by source SHA-256, package
part, and occurrence count in the ingest report and must match the separately
audited upstream-defect inventory.

For indexing speed, the derivative extractor reads OOXML text nodes directly
for DOCX and openpyxl cell values for XLSX; PPTX stays on Harvey's own
MarkItDown path because measurement showed its notes/structure were material.
`lab-extractor-parity.json` is a format-stratified comparison against
Harvey's own parser; CI requires its mean and worst-document token-recall
thresholds. This optimization never touches the exact binary evidence.

## Index contract

`index.sqlite` contains:

- `tasks`: source instructions, full canonical `task.json`, evidence-set
  pointer, deliverable contract, and criterion count;
- `files`: stable per-task occurrence IDs and full provenance;
- `blobs`: one content-addressed binary/text record per SHA-256;
- `blobs_fts`: one full-text index row per unique parsed blob.

The shared firm-knowledge corpus is referenced, not expanded 250 times. Its
9,288 files are already indexed at `world/corpus/ch` with zero parse failures.
