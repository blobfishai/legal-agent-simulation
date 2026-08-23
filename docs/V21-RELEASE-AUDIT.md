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

This audit found and closed eleven release-blocking or publication-integrity
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
| Unit suites | 43/43 passed (manifest, port, local runtime, anonymous GHCR) |
| Seed reproducibility | 198/198 files byte-identical in isolated rebuild |
| Visual document audit | 330/330 rendered pages inspected: 66 DOCX, 198 worksheet pages, 66 PDF |
| Harbor structural export | executable gate passed 23,310 manifests, 22,813 file lanes, 126,592 staged document instances, 5,544 skill trees, and zero agent-side `world.json` copies |
| Harvey runtime recovery | 34/34 files, 113,081 bytes, tree SHA-256 `bbdcf02717bf2ad491bf5ebbe028ebd5d69f5427609fddb0aaca3ad8d4e88d5a` |
| Locked LAB image context | 10/10 source/lock files, tree SHA-256 `de22a672df02ecfcac25087c236f5733bf0121a4f937da3c40a508bccb59f512` |
| Locked release dependencies | 9-package seeded-document closure, 48-package LAB Python closure, npm integrity lock, and 91-package Harbor runner graph |
| Harbor schema 1.4 steps | 36 multi-step tasks, 89 step test/solution fixtures |
| Harbor oracle canary | 5/5 representative tasks reward 1.0; zero exceptions |
| Harbor discrimination | no-op task reward 0.0; zero harness exceptions |
| Production image release | workflow `32614596061` passed; exact candidate-to-production manifest equality |
| Digest-pinned dataset | 23,310/23,310 package hashes; 23,310 unique digests; manifest SHA-256 `6493cf4864d33730d9968e4c09d5c3d170317ba6e62595e93f35bc4def255271` |

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
binary SHA-256 enforcement, materializes Harbor 0.21.0 from `uv.lock`, and
builds the LAB derivative from the pinned base, dated Debian snapshot, pip
hashes, and npm integrity lock. Before push it imports every document library
and parses real DOCX/XLSX/PDF fixtures with networking disabled. Candidate tags
include commit, run ID, and attempt; only candidates that pass five oracle and
five no-op trials are carbon-copied to production with exact digest equality.
The validated production workflow is
[`32614596061`](https://github.com/blobfishai/legal-agent-simulation/actions/runs/32614596061)
at runtime source commit `b4473f12a1d27db6be4b7bc1fc899f6778412a3d`.
It promoted these exact single-manifest images:

- world: `ghcr.io/blobfishai/legal-agent-sim-world@sha256:1608f5df62775d6c7c0eb1341d26ee8dfef9fc5c5ae1ce4aaf1abfa63aa77155`
- LAB agent: `ghcr.io/blobfishai/legal-agent-sim-agent-lab@sha256:3898548e7cfa3fd4853b820d92fd8fb04f42b645794f9211ca25fd5839f7ad80`

Post-release hardening is green in
[`32616206854`](https://github.com/blobfishai/legal-agent-simulation/actions/runs/32616206854):
the deterministic trust chain, exhaustive v21 gate, and Harbor oracle/no-op
smoke all passed with the anonymous-access checker included.

The full generated Harbor release is `dist/harbor-v21-prod`: 23,310 task
packages plus the `legal-agent-simulation/v21` dataset. Its production wrapper
accepts only the two promoted `@sha256` image references. The export checker
then recomputes every Harbor package content hash and compares all 23,310
unique names/digests with `dataset/dataset.toml` before registry publication.
Authenticated publication and public download/runtime checks are documented in
`harbor/README.md`.

At this audit checkpoint, the promoted GHCR manifests still return HTTP 401 to
an anonymous token request because GitHub initializes new container packages
as private. The Harbor CLI also has neither a stored credential nor a
`HARBOR_API_KEY`. Public visibility requires the package administrator's
one-time settings confirmation; Harbor publication requires the user's OAuth
callback code or API key. These external states are deliberately reported as
pending, and the active release goal must not be closed until both public
pullability and public Harbor registry download/runtime trials pass.

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
