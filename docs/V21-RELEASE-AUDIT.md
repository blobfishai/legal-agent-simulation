# V21 release and gap audit

Audit date: 2026-08-22  
Scope: Harvey LAB parity, v21 scale, documents, deterministic verification,
Harbor packaging/runtime, clean rebuilds, and production publication.

## Release conclusion

V21 is a reproducible executable extension of the canonical v20 world. The
release contains 23,310 tasks, 23,310 deterministic verifiers, 1,100
agent-visible tools, 11 internal operations, 32 contracts, 254 tables, and 198
new synthetic source documents. The canonical world is 255,222,487 bytes with
SHA-256 `55dea9469163b3d0a78594bcb8808cecfd202f01f1f446723cce3470f49d9394`.
An isolated rebuild produced the same bytes.

This audit found and closed three release-blocking implementation defects:

1. Generated DOCX briefs could orphan the validation boundary on a second
   page. The shared layout is now one page and its margins/body style are part
   of the structure contract.
2. The first expanded VCode representation duplicated the evaluator in every
   task and exceeded a 2 GiB Docker VM. Each task now carries only an
   integrity-bound configuration stub and imports a shared deterministic
   runtime.
3. The Harbor shim parsed a second copy of the large world document. It now
   receives only its exact task context from a loopback-only endpoint inside
   the world container; the agent container cannot reach that endpoint or
   read `world.json`.

## Measured inventory

| Measure | Harvey LAB at pinned commit | Local v21 |
| --- | ---: | ---: |
| Task configurations / hosted tasks | 2,010 | 2,010/2,010 preserved inside 23,310 total tasks |
| Tracked upstream paths | 63,074 | exact local nested mirror, plus local extensions |
| Physical upstream inputs | 60,971 / 3,206,739,638 bytes | exact local mirror; 15 release-critical inputs narrowly vendored for clean rebuilds |
| Upstream PDFs | 0 | 66 new synthetic evidence PDFs plus provenance-tracked research PDFs |
| Deterministic per-task verifiers | 0 | 23,310 |
| Generic / product tools | 6 generic shell/file tools | 1,100 visible + 11 internal operations |
| Product contracts / tables | none | 32 / 254 |
| New structured evidence | none | 66 packs: 66 DOCX, 66 XLSX, 66 PDF |

The exact Harvey tree remains at the pinned commit
`7be41d57fd5a6e97b5f246a029e810f83d09cd96` under the gitignored local research
corpus. `research/clone-repos.sh` hydrates the pinned tree. The Git repository
does not pretend that a 3.2 GB nested checkout is stored in normal Git history;
the exact 15 files required by the recovered canonical task and the small
upstream sandbox/skill sources required by Harbor are tracked under
`research/harvey-recovery/` with the upstream MIT license.

## Validation evidence

| Gate | Result |
| --- | --- |
| V20 canonical rebuild | 2,331 tasks/verifiers; deterministic report |
| V21 isolated rebuild | byte-identical world SHA-256 |
| Generated positive paths | 20,963/20,963 passed |
| Added-tool adversarial modes | omitted call, forbidden text, collateral write, and deletion all rejected for every one of 990 tools |
| Live HTTP oracle | 990/990 added-tool focus tasks passed |
| Tool coverage | 1,100/1,100 visible tools exercised |
| Unit suites | 39/39 passed (manifest, port, local runtime) |
| Seed reproducibility | 198/198 files byte-identical in isolated rebuild |
| Visual document audit | 330/330 rendered pages inspected: 66 DOCX, 198 worksheet pages, 66 PDF |
| Harbor structural export | executable gate passed 23,310 manifests, 22,813 file lanes, 126,592 staged document instances, 5,544 skill trees, and zero agent-side `world.json` copies |
| Harbor schema 1.4 steps | 36 multi-step tasks, 89 step test/solution fixtures |
| Harbor oracle canary | 5/5 representative tasks reward 1.0; zero exceptions |
| Harbor discrimination | no-op task reward 0.0; zero harness exceptions |

The five-task Harbor canary spans the legacy scripted-turn, v20 researched
consumer-protection, v20 retail multi-step, v21 generated state, and v21 seeded
document lanes. The exhaustive in-process checker covers every generated task;
`npm run v21:harbor-check` separately proves exact source/export file trees,
schema 1.4 topology, executable test/solution programs, image routing,
contracts, and packaged corpus hashes across the complete export. The container
canary proves the shared Docker/Harbor integration rather than repeating 23,310
equivalent image starts on a 2 GiB development VM.

## Production path

`.github/workflows/v21-release.yml` rebuilds the release from tracked inputs,
runs the exhaustive checker, asserts the world hash above, builds the isolated
world and file-lane agent images, and publishes
`ghcr.io/blobfishai/legal-agent-sim-world:v21` and
`ghcr.io/blobfishai/legal-agent-sim-agent-lab:v21` using the
repository-scoped GitHub Actions token. The build hydrates the complete LAB and
C&H FTS indexes from the `v21-production-evidence` release. Their 1.49 GB of
compressed assets expand to 4,738,142,208 exact SQLite bytes and are gated by
compressed/uncompressed SHA-256, SQLite quick-check, semantic table counts, and
pinned Harvey source metadata in `world/corpus/v21-production-evidence.json`.
The ignored full-export oracle token is mirrored only into the encrypted
`V21_HARBOR_SOLVE_TOKEN` Actions secret; the export gate checks every solution
against it, and candidate promotion requires live oracle success against the
image's corresponding token hash.
The full generated Harbor dataset is `dist/harbor-v21-prod/tasks` (23,310
tasks); Harbor registry publication is a separate authenticated operation
documented in `harbor/README.md`.

## Explicit boundaries and remaining external work

These are not hidden or represented as completed legal conclusions:

- The retail register has official portals for all 50 states and D.C., but
  only CA, CT, DC, MA, MI, and NY have benchmark-level primary-source triage.
  The other 45 rows explicitly require substantive review by licensed counsel.
- No receipt wording, contract term, refund policy, software control, or
  benchmark can guarantee that a retailer will not be sued. The synthetic
  scenarios test evidence preservation, correction, escalation, and controlled
  wording; they are not a 51-jurisdiction legal opinion.
- Harvey's semantic judge covers prose quality and legal nuance that cannot be
  reduced safely to exact assertions. Of 111,814 imported practice criteria,
  65,614 have a determinate assertion subset and 46,200 remain in the separate
  semantic-evaluation boundary.
- Newly added CounselOps systems are realistic synthetic product contracts,
  not claims of byte-for-byte parity with proprietary vendor APIs. Historical
  partner-gated vendor conformance ceilings remain documented separately.
- A full 23,310-trial Harbor fleet run is an infrastructure/cost measurement,
  not additional verifier logic. Release confidence comes from exhaustive
  task/verifier execution, structural export checks, and representative real
  Harbor trials; production operators should size concurrency to runner memory.

Within the repository-controlled v21 build, verifier, document, export, and
container surfaces, this audit has no unresolved implementation defect. The
items above require legal judgment, third-party credentials, proprietary
access, or fleet capacity and must not be relabeled as code-complete facts.
