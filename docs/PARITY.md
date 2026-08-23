# Parity audit — how much of the downloaded corpus do we host?

> Historical v19 admission record retained for lineage. It does not describe
> the current release denominator. See
> [`HARVEY-PARITY-AUDIT.md`](HARVEY-PARITY-AUDIT.md) for the v21 audit:
> 2,010/2,010 Harvey tasks inside 23,310 total tasks, 1,100 visible tools,
> 23,310 deterministic verifiers, and 351 new seeded Office/PDF inputs.

`HOSTED` means we read the benchmark's own task definitions and/or documents out of
`research/repos/` and run them: their data, their ground truth. `INSPIRED` means we wrote
tasks in that benchmark's shape from our own knowledge — defensible content, but **not**
coverage of that benchmark, and it is not counted as such here.
For Harvey practice, hosting and criterion coverage are separate: a hosted task has a
deterministic file/state contract, while only mechanically validated criteria contribute
to the headline determinate score.

| Benchmark | Task definitions available | Hosted | Parity |
|---|---|---|---|
| harvey-labs (practice + contracts) | 1,760 | 1,759 | 99.9% |
| harvey-labs firm-knowledge (C&H) | 250 | 250 | 100.0% |
| LegalBench | 162 | 160 | 98.8% |
| MAUD | 92 | 92 | 100.0% |
| CUAD | 41 | 41 | 100.0% |
| ACORD | 1 | 0 | 0.0% |
| ObliQA | 1 | 0 | 0.0% |
| LawFlow | 1 | 0 | 0.0% |
| LawBench | 1 | 0 | 0.0% |
| lex-glue | 1 | 0 | 0.0% |
| **total** | **2,310** | **2,302** | **99.7%** |

## Our own tasks, by provenance

| Source | Tasks |
|---|---|
| hosted (generator reads research/repos/) | 2097 |
| inspired (authored from knowledge) | 155 |
| original world / graph-walk | 72 |
| **world total** | **2324** |

World artifact audited: `world/blobfish/world-v19.json`.

## Upstream release audit (harvey-labs v1.0)

Upstream tagged a public **v1.0** release (`1da4750`, 2026-07-24) on a squash-rooted
lineage disjoint from the pinned `main` history. The tree-level audit
([`docs/AUDIT-V1.0.md`](AUDIT-V1.0.md), `research/harvey-v1.0-delta.json`) proves the
pin `7be41d5` is a **strict content superset** of v1.0: 0 task definitions exist at
v1.0 that the pin lacks, the pin additionally carries the 250-task firm-knowledge lane
(9,538 files) plus 6 rubric fixes and 44 document fixes newer than the release, and
v1.0's only unique file is a zero-byte stray artifact. The parity table above is
therefore unaffected by the release; v1.0 is the public compatibility point, not a
content source.

## Harvey LAB deterministic coverage (world-v19)

- Practice source tasks accounted for: **1,760 / 1,760**
- Practice tasks quarantined with a published reason: **1**
- Criteria compiled to source-grounded assertions: **65,614 / 111,814 (58.7%)**
- Residual prose criteria are dropped and counted; no LLM judge contributes to the deterministic score.

## What this corrects

`docs/COVERAGE.md` reports 24 covered / 17 partial / 0 hostable-gap against a registry of
101 items. That registry is a list of URLs and descriptions; the verdicts were reached by
reading abstracts, not by running the benchmarks' own tasks. It measures *whether the world
could express a shape*, which is a real question, but it is not parity and should never
have been read as parity. This file measures parity.
