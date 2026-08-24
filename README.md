# legal-agent-simulation

> **Simulation only.** Every matter, client, document, attorney, and figure in
> this repository is synthetic test data.

`legal-agent-simulation` is an executable law-firm environment for evaluating
and training tool-using agents. It models matter intake, conflicts, research,
document management, docketing, discovery, deadlines, hearings, billing, and
document review/drafting across product-shaped MCP servers. Every task ships
with a deterministic verifier, so a rollout produces a reproducible reward and
an attributable pass/fail result.

The repository runs locally and offline except for the model endpoint used to
generate agent actions.

## What is included

- A stateful law-firm world backed by private per-session SQLite state.
- Product-shaped MCP tools for Clio, CourtListener, iManage, Relativity, LEDES,
  Google Workspace, ECF, deadline rules, and e-signature workflows.
- Deterministic task verifiers with partial credit and anti-hack vetoes.
- Single-episode and multi-model rollout runners.
- Full episode traces, aggregate benchmark results, and failure-mode reports.
- Harbor task export for container-isolated evaluation and training systems.

## Benchmark releases

| Release | Purpose | Scale |
|---|---|---|
| `world/blobfish/world-v21.json` | Current production-scale release | 23,310 tasks, 32 systems, 254 tables, 1,100 agent-visible tools, and 351 synthetic DOCX/XLSX/PDF inputs |
| `world/blobfish/world-v16.json` | Lightweight local benchmark and default simulation target | 291 tasks, 47 product-system tables, 2,767 seeded rows, and 91 agent-visible tools |

The v21 release is documented in [docs/V21-10X-WORLD.md](docs/V21-10X-WORLD.md).
The v16 admission evidence records 291/291 successful reference executions,
174 content-discriminating tasks, 117 tasks without determinate answer keys,
and zero broken keys, guards, or harness executions; see
[docs/DISCRIMINATION-v16.md](docs/DISCRIMINATION-v16.md).

## Where the tasks are

| Path | Contents |
|---|---|
| `world/blobfish/world-v21.json` | All current v21 task definitions, state, reference walks, and verifier programs |
| `world/blobfish/world-v16.json` | The 291-task world used by the local simulation and leaderboard runners by default |
| `tasks/task_NNN/` | Human-browsable, materialized v16 task bundles |
| `world/expansion/packs/*.json` | Source packs for the answer-keyed v16 expansions |
| `dist/harbor-v21-prod/tasks/` | Generated v21 Harbor task directories; this path appears after export and is intentionally gitignored |

Each materialized v16 task has this shape:

```text
tasks/task_NNN/
  task.json                 prompt, reference walk, provenance, and labels
  verifier.py               deterministic verifier
  seed/
    documents/*.md          task inputs and distractors
    input-documents.json    documents that must be read in full
    core-data.json          referenced or mutable entity rows
    mcp.json                system ownership for seeded data
```

The `tasks/` catalog is generated from the world document; do not edit those
bundles directly. To inspect task IDs and prompts in the default world:

```bash
jq -r '(.world // .).tasks[] | [.task_id, (.prompt // .instruction // .goal)] | @tsv' \
  world/blobfish/world-v16.json
```

The rollout runner accepts these task selectors:

| Selector | Meaning |
|---|---|
| `scored` | Default set: every v16 task except the explicit quarantine |
| `all` | Every task in the selected world |
| `law-native` | Scored tasks excluding the documented domain-fidelity exclusions |
| `expansion` | Tasks generated from the answer-keyed expansion packs |
| `flaky` | The 21-task reliability boundary set |
| `boundary` | Flaky tasks plus tasks labeled `in_band` or `too_hard` |
| `task_127,task_174` | An explicit comma-separated task list |

## Quick start

Requirements: Node.js 18 or newer and Python 3. The local world runtime itself
uses no model API key.

```bash
# Terminal 1: serve the default v16 world on http://127.0.0.1:8971
npm run world:serve

# Terminal 2: prove that all 291 reference executions pass
npm run oracle

# Check deterministic rejection behavior and the API-conformance contract
python3 world/local/discriminate.py --base http://127.0.0.1:8971 --report-only
python3 tools/conformance/run.py --check
```

To serve the production-scale world instead:

```bash
npm run v21:serve
```

Pass `--world-file world/blobfish/world-v21.json` to a simulation runner when
the server is using v21. A full v21 sweep is large and should be deliberately
scoped before model calls are enabled.

## Run RL rollouts and collect rewards

This repository provides the environment, rollout collector, deterministic
reward function, and task exports. It does **not** implement optimizer updates
such as PPO or GRPO. Connect the runner to the model server for the policy being
trained, collect episode JSON, update the policy in your trainer, and repeat
with a new run label.

### 1. Configure a model endpoint

Models are registered in `config/world.config.json`. The target-policy entry
expects an OpenAI-compatible endpoint:

```bash
export QWEN_BASE_URL=http://127.0.0.1:8000/v1
export QWEN_API_KEY=local-training-key
```

For a different model, add an entry under `models` with its endpoint, API-key
environment variable, model ID, context window, completion limit, and pricing.
The committed registry also includes DeepSeek, Anthropic, and xAI examples.

### 2. Start the environment

```bash
npm run world:serve
```

### 3. Run one rollout

```bash
node sim/run-simulation.mjs \
  --task task_127 \
  --engine qwen3-8b \
  --episode-out /tmp/task_127-qwen3-8b.json
```

The episode record contains task and model identifiers, the tool-call trace,
verifier conditions, scalar reward, pass/fail result, token usage, and cost
metadata.

### 4. Collect a resumable rollout batch

Start with the boundary set before paying for a full sweep:

```bash
node sim/run-leaderboard.mjs \
  --engines qwen3-8b \
  --tasks boundary \
  --episodes 3 \
  --concurrency 2 \
  --label qwen-rl-001 \
  --episode-namespace qwen-rl-001 \
  --resume \
  --compress-episodes
```

Use `--tasks scored` for the full default benchmark, or pass explicit task IDs
for a curriculum slice. Paid runs can be bounded with `--max-cost-usd` and
`--max-episode-cost-usd`.

Outputs are written to:

```text
data/leaderboard/episodes/<engine>/<namespace>/   full rollout records
data/leaderboard/results/<engine>@*.json          aggregate scores
```

The failure-report builder does not consume the labeled, namespaced, compressed
episode layout above. For a separate canonical sweep written in the
unnamespaced, uncompressed layout, refresh the selected model report with the
first command below. The leaderboard builder reads aggregate result JSON and
can be refreshed independently with the second command, but it does not create
or reconcile failure-mode data for a labeled run.

```bash
node sim/build-failure-report.mjs --engine qwen3-8b
node docs/leaderboard/build-page.mjs
```

The training loop outside this repository should consume the episode reward
and verifier diagnostics, update the model checkpoint, serve that checkpoint at
the configured endpoint, and rerun with a new label. Keeping namespaces unique
prevents new rollouts from overwriting frozen comparison evidence.

### 5. Use container-isolated tasks

For trainers or agent harnesses that consume Harbor tasks, generate one
directory per world task and run a smoke episode:

```bash
python3 harbor/generate.py --build-image
uv run --project harbor/runner --locked harbor run \
  -p "dist/harbor/tasks/task_005" -a oracle
```

Production v21 export uses digest-pinned images and writes 23,310 task packages
to `dist/harbor-v21-prod`; see [harbor/README.md](harbor/README.md) for the image,
memory, and release requirements.

## Committed benchmark results

The repository contains scored aggregate runs for three models. Each run targeted
the same 155-task scored set with three episodes per task (465 target episodes),
and every recorded episode was scored by deterministic verification. DeepSeek
recorded all 465 episodes across 155 tasks. Grok recorded 177 episodes across 60
tasks, leaving 95 tasks unmeasured; Claude recorded 388 episodes across 130 tasks,
leaving 25 unmeasured. The score and reliability counts include only tasks with
at least one recorded episode. “All passed,” “mixed,” and “none passed” describe
the recorded episodes for each measured task.

| Model | Measured tasks | Recorded episodes | Score | All passed | Mixed | None passed | High-level result |
|---|---:|---:|---:|---:|---:|---:|---|
| [Grok 4.5](data/leaderboard/results/grok-4-5.json) | 60 | 177 | **90.0%** | 51 | 5 | 4 | Strongest score on the smallest measured subset; its recorded failures were off-task state changes, and diligence was the main weak area. |
| [DeepSeek V3.2 (chat)](data/leaderboard/results/deepseek-chat.json) | 155 | 465 | **88.2%** | 118 | 32 | 5 | Strong on drafting and workflow tasks; weakest on records research. Most failures were off-task changes or skipped workflow checkpoints. |
| [Claude Haiku 4.5](data/leaderboard/results/claude-haiku-4-5.json) | 130 | 388 | **60.3%** | 63 | 33 | 34 | Strong on short workflow chains, weaker on drafting and records research. The main failures were skipped checkpoints and leaving the deliverable in chat instead of writing it to the system of record. |

These are frozen historical measurements from August 10, 2026, and the task
denominators differ, so they are not a controlled head-to-head ranking. Compare
models directly only after rerunning them on the same world, task selector,
episode count, tool scope, and measurement protocol. Also use the model label
stored in each result artifact: registry entries can change after a run without
rewriting historical evidence.

Per-model failure reports are available in
[reports/](reports/README.md), and every aggregate traces back to episode records
under `data/leaderboard/episodes/`.

## Architecture

```text
OpenAI-compatible model endpoint
              |
              v
sim/run-simulation.mjs        one task rollout
sim/run-leaderboard.mjs       models × tasks × episodes
              |
              v
MCP bridge or per-system MCP servers
              |
              v
world/local/server.py         session state, tool execution, friction
              |
              v
task verifier                 partial reward + strict pass/fail + diagnostics
```

The runtime injects seeded, deterministic operational friction, including rate
limits, stale references, ambiguous write acknowledgements, and session write
caps. Each episode gets private state, so concurrent runs do not share changes.

## Repository layout

```text
config/world.config.json        model registry, world paths, task sets, flake data
mcp/                            MCP bridge, per-system servers, and contracts
world/local/server.py           local world runtime
world/local/oracle.py           reference-execution prover
world/blobfish/world-v16.json   default 291-task benchmark
world/blobfish/world-v21.json   current 23,310-task release
world/expansion/packs/          answer-keyed expansion sources
tasks/                          materialized v16 task bundles
harbor/                         container-isolated task exporter and runner lock
sim/run-simulation.mjs          one rollout
sim/run-leaderboard.mjs         batch rollout and aggregation
sim/build-failure-report.mjs    failure-mode classifier and report builder
data/leaderboard/episodes/      full episode evidence
data/leaderboard/results/       per-model aggregate results
reports/                        per-model failure-mode reports
docs/leaderboard/               static leaderboard builder and page
```

API fidelity is measured separately from task solvability. The current product
contract and known conformance gaps are documented in
[docs/CONFORMANCE.md](docs/CONFORMANCE.md) and
[docs/MCP-JUSTIFICATION.md](docs/MCP-JUSTIFICATION.md).

Third-party source and license information is preserved in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
