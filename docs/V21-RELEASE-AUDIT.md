# V21 release and gap audit

Audit date: 2026-08-23
Scope: Harvey LAB parity, v21 scale, documents, deterministic verification,
Harbor packaging/runtime, clean rebuilds, and production image publication.

## Release conclusion

V21 is a reproducible executable extension of the canonical v20 world. The
release contains 23,310 tasks, 23,310 deterministic verifiers, 1,100
agent-visible tools, 11 internal operations, 32 contracts, 254 tables, and 351
new synthetic source documents. The canonical world is 263,127,521 bytes with
SHA-256 `7cb5f9ccb36ea1e3ce27bf86554550ba73a01b1e04be35ca6a3e6e15a38702c6`.
A second clean-process rebuild produced the same bytes.

This audit found and closed twenty-four release-blocking or publication-integrity
defects:

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
4. A clean production runner lacked the ignored multi-gigabyte evidence
   indexes. The release now hydrates checksum-pinned compressed assets and
   verifies their expanded bytes, SQLite integrity, row counts, and source
   metadata before building.
5. Harbor file lanes depended on an ignored 3.2 GB Harvey checkout. The exact
   release-critical inputs, sandbox, authoring skills, and MIT license are now
   narrowly vendored and fingerprinted while the complete mirror remains
   reproducibly hydratable at its pinned commit.
6. The file-lane base default still referenced v17. All v21 generation,
   checking, release, and full-export paths now route both v21 images
   explicitly.
7. Independently generated full exports and release images used different
   hidden oracle credentials. The encrypted Actions credential, retained local
   export credential, exhaustive solution check, and image proof hash now form
   one fail-closed chain.
8. Buildx could wrap a validated single-manifest candidate in a new production
   index while the workflow asserted digest identity. Promotion now uses
   unique per-run candidates and carbon-copies the validated manifest before
   comparing candidate and production digests.
9. The copied Harvey Dockerfile, document build dependencies, npm libraries,
   and Harbor runner had mutable transitive resolution. The upstream copy
   remains byte-exact, while production uses a digest-pinned Python base, a
   dated Debian snapshot, hash/integrity locks, pinned Python/uv versions, and
   a committed 91-package Harbor runner lock.
10. The full production export used mutable `:v21` image references and its
    dataset manifest was not part of the exhaustive gate. Production commands
    now reject non-digest or cross-repository images and recompute all 23,310
    Harbor package hashes, names, symlink constraints, and dataset entries.
11. A successful GHCR push did not prove that first-published container
    packages were public. Release and full-export checks now obtain anonymous
    pull tokens, require exact production manifest digests, and reject private
    packages even when the operator has local registry credentials.
12. The document renderer trusted catalog paths and could treat a full-bleed
    header as permission for clipped body content. It now rejects traversal and
    symlinked path components, binds the exact filename/byte/SHA-256 inventory,
    and independently checks body geometry below the header. Four adversarial
    renderer tests prove those failure paths.
13. The parity audit compared Harvey's tracked `tasks/<id>/task.json` paths to
    practice-task directory IDs without normalizing their intentionally
    different representations. Traversal-safe normalization now proves exact
    set and manifest-hash equality for all 1,760 practice and 250 firm tasks.
14. A private-registry image-inspection failure and a readable-image oracle
    mismatch shared one `matched: false` state. Reports now preserve a typed
    failure class, and registry privacy can excuse only remote inspection
    unavailability, never missing or mismatched proof metadata.
15. Multi-step file tasks exposed final deliverable requirements and graded
    files before closeout. Prompts and verifiers now request and score those
    artifacts only in the final phase.
16. Harbor validation trusted summaries of generated packages. It now compares
    exact task text, README bytes, source inputs, skills, test and solution
    programs, file modes, and the complete root/task/dataset topology.
17. Generation accepted unsafe identifiers and could follow staged source
    links. Every generated path is now confined below the output root;
    traversal, symlink, special-file, duplicate-ID, duplicate-phase, and
    duplicate-skill inputs fail closed.
18. Re-generation could retain stale dataset or root files. The generator now
    replaces confined trees transactionally, and validation rejects every
    unexpected published entry rather than silently ignoring it.
19. Dataset verification trusted declared task digests. It now hashes the exact
    publishable file set and proves every ordered name, digest, and package
    count against the full 23,310-package export.
20. Oracle evidence could repeat caller-supplied success fields. Reports now
    derive match state from observed image proofs, bind the production runner
    hash, and preserve typed failure classes.
21. Runtime validation relied on Python `assert`, which disappears under
    optimized execution. Production guards are explicit exceptions and the
    test suite executes them under `python -O`.
22. Existing generated files could be hard-linked to source files, and source
    mode drift was not attested. Atomic replacement now breaks aliases safely;
    deterministic `0644`/`0755` modes are generated and checked end to end.
23. Harvey mutations did not fully preserve ZIP member metadata, could lose
    duplicate-member order, treated `FAIL only if` as malformed, and allowed
    concurrent plans to race. Mutation engine v3 preserves archive structure,
    rejects unsupported data-descriptor changes, and serializes output through
    a hardened owner-only lock.
24. Oregon, Tennessee, and Washington retail rows contained mismatched or weak
    top-level anchors. The corpus now maps OAR 603-027-0180 with Oregon
    statutes, Tenn. Code Ann. § 47-26-913 with the official 2026 rule-review
    packet, and Wash. Rev. Code § 19.94.390; regenerated DOCX/PDF/XLSX evidence
    and all 15 changed render pages were revalidated. A deterministic gate now
    freezes those reviewed anchors together with the prior Arkansas and Arizona
    corrections so a byte-reproducible rebuild cannot normalize a future legal
    citation regression into a passing artifact.

## Measured inventory

| Measure | Harvey LAB at pinned commit | Local v21 |
| --- | ---: | ---: |
| Task configurations / hosted tasks | 2,010 | 2,010/2,010 preserved inside 23,310 total tasks |
| Tracked upstream paths | 63,074 | exact local nested mirror, plus local extensions |
| Physical upstream inputs | 60,971 / 3,206,739,638 bytes | exact local mirror; 15 release-critical inputs narrowly vendored for clean rebuilds |
| Upstream PDFs | 0 | 117 new synthetic evidence PDFs plus provenance-tracked research PDFs |
| Deterministic per-task verifiers | 0 | 23,310 |
| Generic / product tools | 6 generic shell/file tools | 1,100 visible + 11 internal operations |
| Product contracts / tables | none | 32 / 254 |
| New structured evidence | none | 117 packs: 117 DOCX, 117 XLSX, 117 PDF |

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
| V21 second-process rebuild | byte-identical world SHA-256 |
| Generated positive paths | 20,963/20,963 passed |
| Added-tool adversarial modes | omitted call, forbidden text, collateral write, and deletion all rejected for every one of 990 tools |
| Live HTTP oracle | 990/990 added-tool focus tasks passed |
| Tool coverage | 1,100/1,100 visible tools exercised |
| Unit suites | 99/99 passed (manifest, port, local runtime, assertion guards, Harbor byte/topology and dataset integrity, Harvey mutation v3, anonymous GHCR, production-wrapper trust boundary) |
| Document-render adversarial suite | 4/4 passed: full-bleed header accepted, clipped body rejected, catalog hash substitution rejected, traversal rejected |
| Seed reproducibility | 351/351 files byte-identical in isolated rebuild |
| Retail authority reachability | 51/51 citations and official URLs projected into executable state; 6 retail task/verifier pairs checked, 2 authority-dependent pairs rewritten, 4 VCode programs require an unfiltered `count=51`/`total=51` authority-list result; both authority workflows passed the local HTTP oracle; 45 research rows remain attorney-gated |
| Visual document audit | 351/351 source files and 585/585 rendered pages: 117 DOCX, 351 worksheet pages, 117 PDF; exact catalog bytes/hashes and safe body geometry verified |
| Harvey mutation inventory | 35 byte-reproducible variants across 16 source tasks and 14 practice areas; 85 task-relative source-document occurrences produce 182 generated document instances; 0 blocked and 2 resolved source-defect candidates classified |
| Harbor structural export | executable gate passed 23,310 manifests, 22,813 file lanes, 126,598 staged document instances, 5,544 skill trees, and zero agent-side `world.json` copies or package symlinks |
| Harvey runtime recovery | 34/34 files, 113,081 bytes, tree SHA-256 `bbdcf02717bf2ad491bf5ebbe028ebd5d69f5427609fddb0aaca3ad8d4e88d5a` |
| Locked LAB image context | 10/10 source/lock files, tree SHA-256 `de22a672df02ecfcac25087c236f5733bf0121a4f937da3c40a508bccb59f512` |
| Locked release dependencies | 9-package seeded-document closure, 48-package LAB Python closure, npm integrity lock, and 91-package Harbor runner graph |
| Harbor schema 1.4 steps | 36 multi-step tasks, 89 step test/solution fixtures |
| Core Harbor execution model | Local task paths and Docker runtime; no Harbor API, account, OAuth, or hosted publication required |
| Harbor oracle canary | 5/5 representative tasks reward 1.0; zero exceptions |
| Harbor discrimination | no-op task reward 0.0; zero harness exceptions |
| Production image release | workflow `32624207755`: rebuild, candidate build/push, Harbor oracle/no-op validation, and exact candidate-to-production promotion passed; final anonymous-pull gate failed 0/2 |
| Digest-pinned dataset | 23,310/23,310 package hashes; 23,310 unique digests; manifest SHA-256 `9a30f15ba76e15eb45dc6c5dc4adf66516927b8e28dd565c2c8ebd8362e31b3d` |

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

The workflow fixes Python at 3.12.13, installs the seeded-document closure with
binary SHA-256 enforcement, materializes Harbor 0.22.0 from `uv.lock`, and
builds the LAB derivative from the pinned base, dated Debian snapshot, pip
hashes, and npm integrity lock. Before push it imports every document library
and parses real DOCX/XLSX/PDF fixtures with networking disabled. Candidate tags
include commit, run ID, and attempt; only candidates that pass five oracle and
five no-op trials are carbon-copied to production with exact digest equality.
The latest production promotion is workflow
[`32624207755`](https://github.com/blobfishai/legal-agent-simulation/actions/runs/32624207755)
at runtime source commit `b06e0f74bc3f22215f853af49bf4191ee99dd621`.
Steps 1–16 passed, including rebuild, exhaustive verification, evidence
hydration, candidate publication, real Harbor oracle/no-op validation, and
exact candidate-to-production promotion. Step 17 then failed the independent
anonymous-pull gate. The run promoted these exact single-manifest images:

- world: `ghcr.io/blobfishai/legal-agent-sim-world@sha256:9b1cb5669c72e433928253d6e9abb212193ef5ed67bb3eff24758151f00dc81f`
- LAB agent: `ghcr.io/blobfishai/legal-agent-sim-agent-lab@sha256:9105b0e44d4563cbb327cdecdd48b9d76d26a9d688ede4a35a2afc5ccbe19d5a`

The local full-export audit is bound to those exact digests. It passed all
23,310 task packages, all 23,310 unique dataset digests, and the canonical
world hash. Both anonymous token requests returned HTTP 401. Local image
metadata inspection is therefore recorded as
`remote_image_inspection_unavailable`; an oracle mismatch would instead be an
unacceptable `oracle_integrity_failure` and cannot be waived by package
privacy. The successful Harbor canaries in the release run remain the remote
execution proof for these promoted candidates.

The full generated Harbor release is `dist/harbor-v21-prod`: 23,310 task
packages plus the `legal-agent-simulation/v21` dataset. Its production wrapper
accepts only the two promoted `@sha256` image references. The export checker
then recomputes every Harbor package content hash and compares all 23,310
unique names/digests with `dataset/dataset.toml` before execution or
distribution. The task directories run directly through the local Harbor
framework; hosted Harbor Hub publication is optional and is not a production
dependency or release criterion.

At this audit checkpoint, the promoted GHCR manifests still return HTTP 401 to
an anonymous token request because GitHub initializes new container packages
as private. This is a container-image reachability issue, not a Harbor API
requirement: the task definitions point at immutable GHCR image digests, so a
clean unauthenticated runner cannot start them until the package administrator
makes those two images public. Core Harbor itself runs these local packages
without any Harbor credential. Anonymous GHCR pullability remains the only
external publication state pending for the configured public execution path.

## Explicit boundaries and remaining external work

These are not hidden or represented as completed legal conclusions:

- The retail v2 register maps a specific statute, regulation, or official
  enforcement program for all 50 states and D.C., and 51 matched evidence
  packs and executable authority rows are admitted into v21. Only CA, CT, DC,
  MA, MI, and NY have benchmark legal-rule fields. Every new map still rejects substantive-opinion and
  private-remedy encoding and requires current-law review by licensed counsel.
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
