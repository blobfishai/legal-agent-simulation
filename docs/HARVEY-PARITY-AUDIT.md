# Harvey LAB parity and gap audit

Audit date: 2026-08-22  
Upstream: `harveyai/harvey-labs@7be41d57fd5a6e97b5f246a029e810f83d09cd96`

## Executive answer

The exact Harvey repository is copied at
`research/repos/harveyai@harvey-labs`: it is a clean nested Git checkout at the
pinned commit with all **63,074 tracked paths**, all
**2,010 task configurations**, and all
**60,971 physical input files**
(3,206,739,638 bytes). The upstream corpus contains **zero PDF
inputs**; the audit therefore does not make the false claim that Harvey PDFs
were copied.

World v20 operationally hosts **2,010/2,010 Harvey tasks**. The only prior miss
had 15 intact inputs and 74 criteria but no output filename; v20 adds the
disclosed `response.md` adapter without editing the upstream task. World v20
then adds six executable retail-compliance tasks, producing **2,347
tasks and 2,347 deterministic verifiers** over
110 visible tools, 11
internal operations, 10 systems, and
56 state tables.

The folder-format answer has two parts:

- **Exact folder parity:** yes, inside the nested Harvey mirror.
- **Repository-root parity:** no, intentionally; this project adds
  `world/`, `mcp/`, `harbor/`, research, and verifier architecture.
- **Harbor:** Harvey LAB itself is not Harbor. The canonical world JSON is not
  Harbor either. `harbor/generate.py` exports real Harbor schema 1.4 task
  directories with isolated agent/world containers, MCP, `tests/test.sh`,
  `solution/solve.sh`, mounted inputs, artifacts, and native multi-step tasks.

## Measured inventory

| Measure | Harvey LAB | Local v20 |
| --- | ---: | ---: |
| Task configs / hosted Harvey tasks | 2,010 | 2,010/2,010 |
| Total executable tasks | — | 2,347 |
| Physical upstream inputs | 60,971 | 60,971 exact-mirror copies |
| Input bytes | 3,206,739,638 | same exact bytes |
| Generic / visible product tools | 6 | 110 + 11 internal |
| Per-task deterministic verifiers | 0 | 2,347 |
| Practice criteria determinized | — | 65,614/111,814 |
| Retail scenarios / inputs | — | 3 / 15 |
| Strict Harvey derivative tasks | — | 4 from 4 recipes |
| Broad seeded Harvey variants | — | 19 across 8 task families |
| 50 states + D.C. rows | — | 51 |
| Primary-source-triaged / research queue | — | 6 / 45 |
| Retail oracle | — | 6/6 |
| Retail bad-path leaks | — | 0 across no-op/text-only/blind-write/wrong-value |
| Recovered Harvey task oracle / bad-path leaks | — | 1/1 / 0 |

Upstream input format counts:

| Extension | Files | Bytes |
| --- | ---: | ---: |
| `.docx` | 42,009 | 2,712,418,686 |
| `.eml` | 5,784 | 53,139,322 |
| `.json` | 5 | 133,617 |
| `.pptx` | 1,136 | 103,547,720 |
| `.txt` | 889 | 55,575,066 |
| `.xlsx` | 11,148 | 281,925,227 |

## Exact copy versus executable implementation

| Area | Harvey LAB | This repository | Status |
| --- | --- | --- | --- |
| Repository bytes and folder tree | 63,074 tracked paths | Exact nested Git mirror at the pinned commit | `exact_copy` |
| Task configurations | 2,010 task.json files | All task configs remain byte-identical in the mirror; all 2,010 have an executable world-v20-draft adapter | `exact_plus_executable` |
| Input documents | 60,971 physical inputs / 3.207 GB | Every physical input is present in the exact mirror; 51,683 task-local documents are indexed for executable retrieval | `exact_copy_and_index` |
| Office/PDF formats | DOCX/XLSX/PPTX/EML/TXT/JSON; zero PDFs | All upstream formats copied; synthetic retail extension adds 3 PDF receipts and 4 immutable primary-source PDFs | `exact_plus_extension` |
| Generic agent tools | bash, read, write, edit, glob, grep | Exact harness/tools.py is copied; Harbor file-lane agents retain a shell and document stack, while state work uses 110 visible product tools | `exact_copy_different_operational_surface` |
| Document skills | docx, xlsx, pptx skill trees | Exact skill trees are copied and staged into each file-lane Harbor task | `exact_and_operational` |
| Sandbox | LibreOffice/pandoc/parsers image | Exact sandbox source copied; used as the file-lane agent-image base | `exact_and_operational` |
| Evaluation | Criterion-by-criterion LLM judge; all-pass task scoring | Exact evaluation code copied; operational headline uses deterministic VCode and separate file/state lanes | `exact_copy_alternative_default` |
| Gold graders/verifiers | One grader/gold/rubric.json; no per-task deterministic verifier programs | The one gold file is copied; world v20 ships 2,331 deterministic verifier programs | `exact_plus_extension` |
| Firm knowledge | 250 tasks over one shared 9,288-file DMS | All 250 hosted through the indexed shared corpus | `operational_parity` |
| Practice tasks | 1,760 task-local assignments | All 1,760 hosted; one task receives the explicit response.md adapter because upstream omitted a filename | `operational_parity_with_disclosed_adapter` |
| Harbor format | Not Harbor; custom filesystem harness | Schema 1.4 task.toml, isolated agent/world containers, MCP, tests/test.sh, solution/solve.sh, and native multi-step [[steps]] | `local_extension` |
| Canonical world format | No world/ state model | Canonical world-v20-draft.json is the runtime source format; harbor/generate.py exports it to Harbor | `local_extension` |

## Retail case correction and task design

The prompt's Walmart example conflates multiple matters. `Rector v. Walmart`
alleges shelf/register mismatches in D.C.; `Kahn v. Walmart` concerns alleged
scanner-price discrepancies; the $45 million `Kukorinis` settlement concerned
weighted goods and bagged citrus in the Middle District of Florida—not a
California self-checkout double-charge settlement. California separately
reported checkout-price and price/weight enforcement resolutions.

The new environment therefore models the legal work without encoding the
conflation as fact:

1. evidence preservation and incident audit;
2. transaction-level exposure and jurisdiction-gated refunds;
3. a candid 50-state-plus-D.C. research matrix;
4. receipt and policy redlines with statutory-rights savings language;
5. duplicate-scan, price-sync, and weight-control implementation plus retest;
6. a four-checkpoint national closeout matter.

The three scenario packs (CA, MI, D.C.) have the same five filenames, DOCX
heading topology, XLSX sheet/column topology, and two-page receipt layout.
Facts and answers change, not the file-reading structure. All receipt pages
were rendered and visually inspected. Four immutable primary-source PDFs have
URL, retrieval date, and SHA-256 records in `sources/manifest.json`.

## All currently identified gaps

These are not hidden behind the word “parity.”

| ID | Severity | Gap | Required closure |
| --- | --- | --- | --- |
| G1 | high | 46,200 of 111,814 practice rubric criteria remain outside the deterministic assertion subset. | Run the copied LAB dual-judge lane as a separately reported semantic score, or add source-validated deterministic assertions with oracle and corruption gates. |
| G2 | high | The 45 baseline-only state rows are not a completed 51-jurisdiction legal opinion. | Qualified counsel must validate current primary text and applicability for each jurisdiction before deployment; encode each completed review with a version/effective-date pin. |
| G3 | high | No receipt, contract term, disclaimer, or control can ensure that the retailer will not be sued. | Use accurate-charge prevention, rapid detection/refund, nonwaiver wording, evidence preservation, audits, escalation, and current legal review. |
| G4 | high | Frozen v19 external reference-model calibration remains incomplete (856/6,972 episodes) because the pinned account lacked funds. | Fund and resume the exact frozen calibration denominator, or publish a separately versioned replacement protocol. |
| G5 | medium | RetailGuard is a synthetic documentation-fixture API, not a conformance-tested mirror of a real retail platform. | Choose a licensed/public retail API specification or partner sandbox, pin it, and add schema/error/pagination conformance tests. |
| G6 | medium | The seven new/adapted tasks were structurally exported to Harbor, but a full 2,331-task Docker/Harbor fleet run was not repeated in this audit. | Build/publish the v20 world and LAB agent images, run the seven-task Harbor oracle canary, then fan out the full task tree with recorded Harbor version and image digests. |
| G7 | medium | The exact upstream mirror contains nine known malformed OOXML XML parts. | Keep the immutable source, exact-hash allowlist, recovery copies, and separate normalized derivatives. Fail on any hash or defect-count drift. |
| G8 | medium | Deterministic anchors do not fully grade visual polish, tracked-change semantics, formula correctness after every application, or professional legal judgment. | Add OOXML semantic checks, formula recalculation, render comparisons, and the copied LAB judge as independent channels; never average away lane disagreement. |
| G9 | low | The repository root intentionally does not reproduce Harvey's top-level layout. | Use the nested mirror for byte/folder parity and the generated Harbor tree for runnable task parity; do not describe the repository root as an upstream clone. |
| G10 | low | Upstream contains no PDF inputs, so there is nothing upstream to copy in that format. | Keep the zero-PDF audit fact. Add only clearly labeled synthetic or provenance-tracked public reference PDFs in separate extension lanes. |
| G11 | medium | Four strict Harvey derivative tasks and 19 broad seeded variants are generator/harness assets, not separately admitted v20 state workflows. | Index each derivative evidence set, compile its changed rubric facts, then require world admission, file/state lane agreement, oracle, corruption probes, and Harbor canary before counting it in the 2,331-task world total. |

## What “copy all tools and verifiers” means here

Every upstream tool, judge, scoring, sandbox, skill, test, and utility source
file is present in the exact mirror. Harvey has six generic filesystem tools
and LLM-judge scoring; it does **not** provide 2,010 deterministic verifier
programs to copy. The local product tools and VCodes are additions. Describing
them as verbatim Harvey tools or verifiers would be inaccurate.

## Reproduction and gates

```bash
python3 tools/audit_harvey_inputs.py --check
python3 world/port/lab_determinize.py --check
python3 tools/build_retail_price_accuracy_pack.py
python3 tools/build_retail_price_accuracy_pack.py --check
python3 world/v20/build.py
python3 tools/check_v20_retail.py
python3 tools/check_harbor_file_lane.py
python3 tools/build_harvey_parity_audit.py --check
```

The machine-readable companion is `reports/harvey-parity-audit.json`.
