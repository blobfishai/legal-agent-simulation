# Harbor format (harbor-framework/harbor)

Converts the canonical world into real [Harbor](https://github.com/harbor-framework/harbor)
tasks — one Harbor task directory per world task, runnable with `harbor run`.
(For the older blobfish-style single bundle, see `world/local/export_harbor.py`,
which now writes to `dist/harbor-legacy`.)

> Simulation only — every matter, client, document, attorney, and figure is
> synthetic test data.

## Generate + build

```bash
npm run v21:harbor-prod   # 23,310 tasks -> dist/harbor-v21-prod/tasks
npm run v21:harbor-check  # exact manifests, inputs, skills, images, steps, corpus
```

The structural gate checks all 23,310 task directories against the canonical
world, including 22,813 file lanes, 126,592 staged document instances, 5,544
skill trees, 36 multi-step tasks/89 phases, both evidence-index hashes, and zero
agent-side `world.json` copies.

LAB-imported tasks carry a `file_lane` block. For those tasks the generator
also stages the exact commit-pinned input tree at `/workspace/documents`
(read-only), creates `/workspace/output`, copies Harvey's docx/xlsx/pptx skill
manuals, and uses the heavier LibreOffice+pandoc agent base:

```bash
python3 harbor/generate.py --build-lab-agent-image \
  --lab-agent-image ghcr.io/blobfishai/legal-agent-sim-agent-lab:v21
```

The verifier copies non-symlink output files to `/logs/artifacts` and emits
`file-lane.json`. Determinate file tasks check source-grounded anchor groups
inside DOCX, XLSX, PPTX, PDF, Markdown, JSON, and text outputs; thin upstream
tasks remain explicitly labeled `output_contract_only`. `reward.json` retains
the deterministic state reward and adds separate file/state diagnostics; the
lanes are never averaged. `python3 tools/check_harbor_file_lane.py` gates path
confinement and this contract.

V21's 198 seeded DOCX/XLSX/PDF fixtures are input-only file lanes: they stage
the evidence read-only but intentionally request no authoring skills or fake
deliverable path. Their stateful MCP workflow is the graded output. The
generator preserves an explicit empty `skills` list, so these lanes do not
silently inherit the legacy authoring defaults.

`dist/` is gitignored; the generated tree is a build artifact. Regeneration is
deterministic (the `/solve` token persists in
`dist/harbor/world-image/solve-token.txt`).

## Run

```bash
uvx harbor run -p "dist/harbor/tasks/task_v21_lt_matters_00001" -a oracle
uvx harbor run -p "dist/harbor/tasks/task_v21_lt_matters_00001" -a claude-code -m anthropic/claude-sonnet-5
uvx harbor run -p "dist/harbor/tasks" -a oracle -n 1                     # safe on a 2 GiB local VM
```

Multi-container tasks need Harbor's **docker** environment provider (compose
networking); cloud providers (Daytona/Modal/E2B) are not supported for these.
Each concurrent v21 trial starts a world container, so increase Docker/runner
memory before increasing `-n`; the release smoke is deliberately serial on a
2 GiB Colima VM.

## Ship

Tasks reference the world image as `ghcr.io/blobfishai/legal-agent-sim-world:v21`,
so a published image makes every task dir self-sufficient (no local build).
File-lane tasks likewise reference
`ghcr.io/blobfishai/legal-agent-sim-agent-lab:v21`. The GitHub Actions release
workflow rebuilds and publishes both images; Harbor registry publication still
needs its own interactive OAuth token:

The 4.7 GB materialized LAB/C&H search indexes are intentionally outside
ordinary Git history. `world/corpus/v21-production-evidence.json` pins their
release assets by compressed and uncompressed SHA-256, byte count, SQLite
integrity, table counts, and source metadata. A clean release runner hydrates
them with `python3 tools/hydrate_v21_evidence.py` before building the world
image; `--check` verifies a materialized copy without downloading it.

The full export and production world image must also share the same hidden
oracle credential. Local regeneration retains it only in the ignored
`world-image/solve-token.txt`; CI receives the same value through the encrypted
`V21_HARBOR_SOLVE_TOKEN` Actions secret. `v21:harbor-check` verifies that every
top-level and multistep oracle solution carries the export token without
printing it, while the production Harbor oracle gate proves the image carries
the corresponding hash.

```bash
# Optional manual image push (the release workflow normally performs this)
gh auth refresh -h github.com -s write:packages
gh auth token | docker login ghcr.io -u <github-user> --password-stdin
docker push ghcr.io/blobfishai/legal-agent-sim-world:v21
docker push ghcr.io/blobfishai/legal-agent-sim-agent-lab:v21
# then make the package public: https://github.com/orgs/blobfishai/packages

# Publish tasks to the Harbor registry (hub.harborframework.com)
uvx harbor auth login          # GitHub sign-in flow
uvx harbor publish "dist/harbor-v21-prod/tasks"
```

## Architecture

Two containers per trial (compose merge, like Harbor's `hello-mcp` example):

```
main (agent)                          world (shared image, TASK_ID env)
  python + curl + `tool` CLI    ──►     shim.py :8972
  no world doc, no verifiers            ├─ POST /mcp     JSON-RPC proxy + trace
  MCP config: lawfirm →                 ├─ POST /verify  VCode verdict
    http://world:8972/mcp               └─ POST /solve   oracle walk (token-gated)
                                        server.py :8971 (world runtime,
                                        SQLite session, seeded friction,
                                        product contracts)
```

- The **shim** creates the trial's session (per-task seeded baseline), records
  every `tools/call` into the trace exactly as `sim/run-simulation.mjs` does,
  and runs verification server-side — so the agent container never contains
  `world.json` (tasks, walks, verifier code, answer keys). The canonical source
  is `world/blobfish/world-v21.json`; historical worlds automatically retain
  their matching contract suite. The co-resident shim fetches only its task
  context from a loopback-only endpoint, avoiding a second parse of the large
  world document without exposing answer keys to the agent network.
- `tests/test.sh` writes `reward.json` with `reward` (the
  verifier's graded fraction, anti-hack vetoes to 0) and `passed` (strict
  pass/fail — the world's headline metric). File-lane tasks add separate
  diagnostic fields and preserve every produced artifact under
  `/logs/artifacts`.
- `solution/solve.sh` triggers the same reference walk that
  `world/local/oracle.py` proves against the selected task; the solve endpoint is gated by a
  token that exists only in the world image and in `solution/` (which Harbor
  copies in only for Oracle-agent runs).
- Native multi-step tasks use Harbor schema 1.4 `[[steps]]` and checkpoint
  VCodes. Older scripted-turn tasks retain their follow-up-message adapter for
  single-instruction harnesses.

## Files

```
harbor/generate.py           the exporter (stdlib only)
harbor/world-image/          shared image source: Dockerfile, start.sh, shim.py
harbor/agent-image/tool      firm-systems CLI baked into every agent container
```

## Validation performed

- `harbor run -a oracle` (real harbor CLI, v0.21.0): passed, reward 1.0.
- Manual compose smoke tests across task families (legacy walk, v3 product
  tools, hallucination trap, grounded drafting, session-script): oracle solve
  → `passed 1.0`; no-op agent → `passed 0.0` with the expected
  `failed_conditions` (discrimination preserved).
