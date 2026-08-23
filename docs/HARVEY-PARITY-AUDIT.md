# Harvey LAB parity and repository gap audit

Audit date: 2026-08-23

Harvey upstream: `harveyai/harvey-labs@7be41d57fd5a6e97b5f246a029e810f83d09cd96`

Harbor upstream checked: `harbor-framework/harbor@b37833221e27435a18d7acdd41d875cdc2831893` (`v0.22.0-2-gb3783322`)

## Executive answer

The Harvey repository is copied completely at
`research/repos/harveyai@harvey-labs`. It is a clean, byte-exact nested Git
checkout at the pinned `main` commit audited on the date above, with all **63,074
tracked paths**, all **2,010 task configurations**, and
all **60,971 physical inputs** (3,206,739,638
bytes). Harvey has **zero PDF input files**; claiming that Harvey PDFs were
copied would be false. Every upstream DOCX, XLSX, PPTX, EML, TXT, and JSON input
is present.

The Harbor repository is likewise copied as a clean exact checkout at
`research/repos/harbor-framework@harbor`. Its commit is pinned in
`research/repos-commits.json`, and `research/clone-repos.sh` hydrates that
framework source alongside the Harvey and legal-research corpus.

The executable v21 world has **23,310 tasks**,
**23,310 deterministic verifiers**, **1,100
agent-visible tools**, **11 internal operations**,
**254 state tables**, and **351 new matched
DOCX/XLSX/PDF inputs**. All 2,010 Harvey tasks are hosted inside that world.

The format answer is precise:

- The nested Harvey mirror has the same folder structure and bytes as Harvey.
- The repository root adds `world/`, `mcp/`, `harbor/`, deterministic verifiers,
  research, and release architecture; it is not a renamed upstream clone.
- `world-v21.json` is a canonical state model, not a Harbor task directory.
- `dist/harbor-v21-prod/tasks/*` is native Harbor schema 1.4.
- Harbor 0.22.0 is a local framework. No Harbor API,
  account, OAuth login, or hosted Hub is required.

## Folder and format topology

```text
legal-agent-simulation/
├── research/repos/harveyai@harvey-labs/  # exact Harvey tree
├── research/repos/harbor-framework@harbor/ # exact Harbor framework tree
├── world/blobfish/world-v21.json          # canonical stateful world (not Harbor)
├── mcp/v5/contracts/                      # 1,100 visible product tools
├── research/v21-seeded-documents/         # 117 packs / 351 matched inputs
├── harbor/                                # exporter, images, locked Harbor runner
└── dist/harbor-v21-prod/
    ├── dataset/dataset.toml                # Harbor dataset manifest
    └── tasks/<task-id>/                    # native Harbor task packages
```

The full Harvey binary corpus is intentionally gitignored because it is 3.207
GB of input payload (about 5.46 GiB with Git metadata). A clean checkout uses
`research/clone-repos.sh`, then the strict audit verifies commit, paths, bytes,
formats, LFS/zero-byte absence, OOXML CRCs, and known-defect hashes. This is a
complete local copy with deterministic hydration, not an ordinary-Git bundle.

## Measured inventory

| Measure | Harvey LAB | Local v21 |
| --- | ---: | ---: |
| Task configs / hosted Harvey tasks | 2,010 | 2,010/2,010 |
| Task-path manifest SHA-256 | `ff9b848518885cfc8e9714c4cd637a1f852c51c5608cb05f439d241c1e7a0f14` | `ff9b848518885cfc8e9714c4cd637a1f852c51c5608cb05f439d241c1e7a0f14` |
| Broad mutation candidates | — | 35 variants across 16 tasks / 14 practice areas; 0 blocked and 2 resolved upstream-defect candidates; plan `45b2a1d8b24bc9384e47857529132c80cc26043b2d977d36e2d14ba48fc46917` |
| Total executable tasks | — | 23,310 |
| Physical upstream inputs | 60,971 | 60,971 exact local copies |
| Input bytes | 3,206,739,638 | same exact bytes |
| Generic / visible product tools | 6 | 1,100 + 11 internal |
| Per-task deterministic verifier programs | 0 | 23,310 |
| Practice criteria determinized | — | 65,614/111,814 |
| New structure-matched packs / inputs | — | 117 / 351 |
| New DOCX / XLSX / PDF | — | 117 / 117 / 117 |
| Rendered fixture pages passing automated QA | — | 585/585 |
| Retail scenario inputs | — | 18 across 3 matched scenarios |
| Specific state-plus-D.C. authority maps | — | 51/51 |
| Authority maps represented as legal opinions/remedies | — | 0 / 0 |
| Retail authority packs / admitted tasks | — | 51 / 9,129 |
| Harbor packages / unique content digests | — | 23,310 / 23,310 |
| Harbor package files / exact topology hash | — | 343,517 / `46fc43bcd3e104921f14d7e0af46bbec0dd3d3964b440b5ef97d8382d98fb519` |
| Harbor file lanes / staged document instances | — | 22,813 / 126,598 |
| Harbor multi-step tasks / phases | — | 36 / 89 |
| Anonymous production image pulls | — | 0/2 exact digests |

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
| Repository bytes and Harvey folder tree | 63,074 tracked paths at 7be41d57fd5a | Exact clean nested Git mirror; repository root intentionally adds runtime architecture | `exact_nested_copy` |
| Task configurations | 2,010 task.json files | All 2,010 hosted inside 23,310 total executable tasks | `exact_plus_executable` |
| Physical input documents | 60,971 files / 3,206,739,638 bytes | All exact bytes present in the nested mirror; full mirror is gitignored and deterministically hydrated | `exact_local_copy_hydratable_distribution` |
| DOCX/XLSX/PDF requested by audit | 42,009 DOCX, 11,148 XLSX, 0 PDF | Every upstream DOCX/XLSX copied; 351 new synthetic inputs include 117 PDFs | `exact_copy_plus_labeled_extension` |
| Generic agent tools | bash, read, write, edit, glob, grep | Exact harness copied; file lanes retain shell/document tooling and state lanes expose 1,100 executable product tools | `exact_copy_plus_realistic_state_tools` |
| Document skills and sandbox | DOCX/XLSX/PPTX skills and LibreOffice/pandoc/parsers sandbox | Exact sources copied and staged into applicable Harbor file lanes; locked derivative image used for execution | `exact_and_operational` |
| Evaluation and graders | Criterion-level LLM judge, all-pass scoring, one gold rubric; no per-task deterministic programs | Exact judge copied; 23,310 task-specific deterministic verifiers added as a separate lane | `exact_copy_plus_deterministic_lane` |
| Firm-knowledge tasks | 250 tasks over one shared 9,288-file DMS | 250/250 hosted against pinned evidence indexes | `operational_parity` |
| Practice tasks | 1,760 task-local assignments | 1,760/1,760 hosted; one disclosed response.md adapter repairs a missing upstream output filename | `operational_parity_with_adapter` |
| Mutated and seeded documents | No repository-wide deterministic mutation program | 117 structure-matched packs / 351 DOCX-XLSX-PDF inputs, including 51 jurisdiction packs | `local_extension` |
| 51-jurisdiction retail authority reachability | No retail-compliance world or jurisdiction authority map | 51/51 exact citations and official URLs are exposed by executable tools; all remain attorney-gated | `executable_issue_spotting_map` |
| Harbor task format | Harvey LAB uses its own filesystem harness, not Harbor | 23,310 native Harbor schema-1.4 packages with instruction.md, task.toml, environment, solution, and tests | `native_harbor_export` |
| Canonical world format | No stateful world model | world-v21.json is the canonical runtime model; generated dist packages are Harbor format | `canonical_not_harbor_export_is_harbor` |
| Harbor framework dependency | Not applicable | Local runner pins Harbor 0.22.0; no Harbor API, OAuth, account, or hosted Hub is required | `local_framework_only` |
| Production image reachability | Not applicable | 0/2 immutable production images anonymously pullable | `external_registry_visibility_pending` |

## What “copy all tasks, tools, and verifiers” means

Every Harvey source file—including tasks, six generic filesystem tools,
judge/scoring code, skills, sandbox, tests, utilities, and the single gold
rubric—is in the exact mirror. Harvey does **not** ship 2,010 deterministic
verifier programs or 1,100 legal-product APIs. Those are local additions.

All 1,760 practice tasks and 250 firm-knowledge tasks are hosted. One practice
task omitted an output filename upstream; the port adds a disclosed
`response.md` adapter without editing the source. The LAB judge remains a
separate semantic lane because exact state checks cannot grade every criterion.

## Seeded documents and task generation

The seed catalog has **117 packs / 351
documents**. Every pack contains one DOCX matter brief, one XLSX evidence and
computation register, and one PDF source extract. All packs share the same
heading, table, worksheet, formula, print, page-size, and PDF structure
signature. Content, jurisdiction, dates, amounts, anchors, risk, and issue facts
change. Every file is synthetic, hashed, manifested, reproducible, and
attorney-gated.

All **585 rendered pages** pass expected-pagination,
extractable-text, nonblank-raster, geometry, and safe-edge-treatment checks. The
machine report distinguishes automated raster evidence from contact-sheet human
review instead of treating structural validation as visual proof.

The 51 retail packs add one authority-mapped evidence set for every state and
D.C. All are referenced by admitted v21 tasks. Workbooks carry citation,
official URL, source type, common controls, and fields rejecting legal-opinion
or private-remedy encoding. They do not overwrite Harvey inputs or the frozen
v20 snapshot. In v21, the same 51 citations and official URLs are projected
into the executable `rc_jurisdiction_rules` table. All six legacy retail
task/verifier pairs pass the migration audit; the two authority-dependent pairs
are rewritten away from the generic-portal vocabulary. Four top-level/phase
VCode programs require an unfiltered list observation with both `count=51` and
`total=51`; separate fail-closed build and checker gates prove that those 51
executable rows exactly match the mapped citations and official URLs.
Both authority-dependent workflows also pass the live local HTTP oracle
(2/2).

## Walmart example and 51-jurisdiction research

The request's example conflates distinct matters. `Rector v. Walmart` alleges
shelf/register mismatches in D.C.; the cited opinion concerns a first-filed
stay, not a merits settlement. `Kahn v. Walmart` addresses alleged scanner
discrepancies. The $45 million `Kukorinis` settlement concerned weighted goods
and bagged citrus in Florida, not a California self-checkout double-charge
settlement. California separately reported checkout and price/weight cases.

The executable work covers preservation, transaction reconstruction, exposure,
authority mapping, remedy gating, receipt/policy redlines, duplicate-scan and
price-sync controls, weights, retesting, and national closeout. Common wording
corrects verified overcharges promptly and preserves statutory rights; it never
promises litigation immunity.

The v2 map advances all 51 jurisdictions from a portal list to a specific
statute, regulation, or official enforcement-program map. Every row still sets
`substantive_legal_opinion=false`, `private_remedy_encoded=false`,
`current_text_and_local_overlays_validated=false`, and
`attorney_validation_required=true`.

## Harbor executable evidence

The export contains **23,310/23,310 tasks**,
**23,310 unique package digests**,
**343,517 byte-checked package files**,
**22,813 file lanes**, **126,598 staged
document instances**, and **zero agent-side world leaks or package symlinks**.
Package topology SHA-256: `46fc43bcd3e104921f14d7e0af46bbec0dd3d3964b440b5ef97d8382d98fb519`. Dataset
task-digest manifest SHA-256: `7112905a61d6b0404b2d4a6379fef9a5a1d5272444ac349915b7dcd8d236d023`. Dataset
SHA-256: `7f5eb4cf057e741b3195314631c59a02a395e4f917d67d4e408374fc3595dc49`. The locked runner uses Harbor
0.22.0 with a 91-package graph. The export is bound to
`ghcr.io/blobfishai/legal-agent-sim-world@sha256:8ff066a70e0d3d6ea6e7c705bd14948d663daadfed64e5fcbbf5e4b265557524` and `ghcr.io/blobfishai/legal-agent-sim-agent-lab@sha256:1664abf1b6f3e0571d9cc071a26a89dee0c1f978db0197f2a649c9cba46849f0`; the independent
anonymous registry audit passes 0/2 exact digests.
Local remote-metadata comparison of the export oracle proof is
`false` with failure
class `remote_image_inspection_unavailable`. Registry privacy can
excuse remote inspection unavailability, but never an oracle-integrity failure;
the release workflow's successful oracle canaries remain the independent
production proof. Harbor Hub is optional.

## Closed repository-controlled gaps

- All 2,010 Harvey task configurations are hosted path-for-path with a matching provenance-manifest hash; all 60,971 upstream inputs are present in the exact pinned mirror.
- The v21 world contains 23,310 tasks, 23,310 deterministic verifiers, 1,100 visible tools, and 254 tables.
- All 23,310 tasks have native Harbor packages whose generated text bytes, staged inputs, skills, world-image context, root topology, and publishable Harbor dataset file sets are checked exactly; package and digest manifests are recorded.
- Fifty-one specific retail authorities now drive 51 matched seed packs and admitted document-grounded tasks without encoding legal opinions or remedies.
- All 351 admitted seed documents render into the expected 585 pages and pass pagination, text, raster, geometry, and safe-edge-treatment checks.
- The four strict and 35 broad Harvey mutation experiments are explicitly lifecycle-labeled as regression candidates and are not double-counted; 94 release-admitted mutations have stable task references and Harbor packages.
- Harbor runner is upgraded to v0.22.0 and remains a local framework with no Harbor API dependency.
- The exact Harbor framework checkout is clean, pinned in the research lock, recorded in the local corpus manifest, and reproducibly hydrated by research/clone-repos.sh.
- Validation scripts that retain assertions fail closed under python -O, and the regression suite enforces that invariant for every tracked production Python file.

## Intentional differences, not hidden parity claims

- Only research/repos/harveyai@harvey-labs reproduces Harvey's folder tree; repository root is a strict-superset implementation.
- The canonical world JSON is not Harbor format; the generated task directories and dataset are Harbor format.
- Harvey upstream has zero PDF inputs; local PDFs are labeled synthetic fixtures or provenance-tracked public references.
- Deterministic verifiers supplement rather than impersonate Harvey's LLM judge.
- Research-only mutation candidates remain reproducible but are excluded from production task counts until they satisfy the documented admission gate.
- The 2 upstream-defect mutation candidates are explicitly classified as resolved in the 35-variant broad plan; immutable Harvey source bytes remain untouched.

## All remaining gaps and external boundaries

| ID | Severity | Gap | Required closure |
| --- | --- | --- | --- |
| G1 | high | 46,200 of 111,814 practice criteria remain outside the deterministic assertion subset. | Report the copied LAB judge independently or add source-grounded assertions with oracle and corruption gates; never infer semantic quality from deterministic state success. |
| G2 | high | All 51 jurisdictions have a specific authority map, but none of the new v2 rows is represented as a deployment-ready 51-jurisdiction legal opinion. | Counsel validates and signs a versioned jurisdiction memorandum; only then may a row become an executable legal rule or remedy. |
| G3 | high | No receipt, contract term, disclaimer, refund policy, software control, or benchmark can ensure that a retailer will not be sued. | Use prevention, rapid correction, nonwaiver language, evidence preservation, audits, escalation, and current legal review; describe residual risk candidly. |
| G4 | high | Frozen v19 external reference-model calibration remains incomplete at 856/6,972 episodes because the pinned account lacked funds. | Fund and resume the exact frozen denominator or publish a separately versioned replacement protocol. |
| G5 | medium | The 1,100 product tools are executable synthetic legal-operations contracts, not certified mirrors of proprietary vendor APIs. | Pin a licensed or public partner specification and add schema, error, authentication, pagination, and rate-limit conformance tests. |
| G6 | medium | The full export is structurally and deterministically checked, but a 23,310-trial external model fleet run is not part of this repository audit. | Run the frozen dataset at an explicitly sized concurrency and publish agent/model, Harbor version, image digests, costs, failures, and denominator. |
| G7 | medium | The exact upstream mirror contains 9 known malformed OOXML XML parts. | Keep the immutable source, exact-hash allowlist, recovery copies, and separate normalized derivatives; fail on hash or defect-count drift. |
| G8 | medium | Deterministic anchors do not completely grade visual polish, tracked-change semantics, recalculated formulas in every office application, or professional legal judgment. | Keep render, OOXML semantic, formula-recalculation, file/state, and semantic-judge channels separate and expose disagreement. |
| G9 | high | Only 0/2 digest-bound GHCR production images are anonymously pullable. | A package administrator must change both GHCR container packages to Public; rerun the digest-bound anonymous gate afterward. |
| G10 | low | The 3.207-GB Harvey input payload is present locally but intentionally excluded from ordinary Git history. | Run research/clone-repos.sh and the strict input audit, or publish a license-compatible content-addressed corpus artifact with hash verification. |

No open item is a repository-controlled implementation omission. The remaining
items are semantic or legal-review boundaries, external calibration and fleet
measurement, proprietary-spec access, immutable upstream defects, or corpus
distribution constraints. Research-only mutation candidates are explicitly
lifecycle-labeled and are not double-counted as graded tasks.

## Reproduction and gates

```bash
npm run harvey:input-audit-check
npm run harvey:parity-audit-check
python3 tools/build_retail_price_accuracy_pack.py --check
python3 tools/build_v21_seed_documents.py --check
npm run v21:check
npm run v21:document-render-check
python3 tools/run_harbor_production.py generate   --world-image ghcr.io/blobfishai/legal-agent-sim-world@sha256:8ff066a70e0d3d6ea6e7c705bd14948d663daadfed64e5fcbbf5e4b265557524   --lab-image ghcr.io/blobfishai/legal-agent-sim-agent-lab@sha256:1664abf1b6f3e0571d9cc071a26a89dee0c1f978db0197f2a649c9cba46849f0
# This exits 1 while G9 remains; structural and dataset reports are still written first.
python3 tools/run_harbor_production.py check   --world-image ghcr.io/blobfishai/legal-agent-sim-world@sha256:8ff066a70e0d3d6ea6e7c705bd14948d663daadfed64e5fcbbf5e4b265557524   --lab-image ghcr.io/blobfishai/legal-agent-sim-agent-lab@sha256:1664abf1b6f3e0571d9cc071a26a89dee0c1f978db0197f2a649c9cba46849f0
uv run --project harbor/runner --locked harbor --version
```

Machine-readable evidence: `reports/harvey-parity-audit.json`,
`reports/v21-harbor-export-audit.json`,
`reports/v21-harbor-dataset-audit.json`,
`reports/v21-ghcr-public-audit.json`,
`reports/v21-oracle-proof-audit.json`,
`reports/v21-document-render-audit.json`, and
`reports/v21-document-visual-review.json`.
