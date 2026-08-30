# CounselBench-100 source

This directory contains the deterministic generator, multi-provider sandbox
MCP, qualification suite, and release tooling for CounselBench-100.

CounselBench-100 v3.2.3 contains 100 original synthetic legal matters across
ten practice workflows. Each employee request is a high-level workplace
question, not a prescribed tool recipe. Solving it requires the agent to find
and correlate raw records before deciding what is supported, what remains an
evidence hold, and what state may safely change.

Every task includes:

- 97 inspectable assets in nine native formats and twelve matter folders;
- 58–86 material records, explicitly separated from supporting references;
- evidence distributed across Clio Manage, Gmail, Google Drive, and Slack;
- source-byte-bound evidence receipts that accept equivalent optional provider
  projections while rejecting metadata-only and neighboring-object reads;
- natural employee requests that authorize ordinary task-scoped closeout without
  prescribing provider operations or a tool-call recipe;
- twelve portfolio decisions derived from immutable identity, operative
  authority/revision, current operations, and effective approval/capacity;
- three graded operating alternatives with exact outcomes, incremental cost,
  authority status, and signed timing variance against the matter control date;
- 5–9 supported actions and 3–7 evidence holds;
- a distinct 69–97-call reference trajectory;
- an exact Clio matter-register patch, a Clio decision note, and a task-native
  Gmail, Drive, or Slack completion update;
- native provider readback after each committed mutation; and
- fourteen task-specific semantic milestones totaling 100 CounselScore points.

The sandbox exposes 18 allowlisted resource operations that map to documented
Clio Manage v4, Gmail v1, Drive v3, and Slack Web API methods. It deliberately
does not expose business-level pseudo-tools such as `approve_finding` or
`resolve_matter`.

The v3.2.3 qualification contract runs 1,500 local executions:

- 100 oracle executions;
- 100 exact deterministic replays; and
- 1,300 adversarial executions covering no-op and copied-gold shortcuts, missing
  state, incomplete or late evidence, premature notification, missing readback,
  duplicate and rejected mutations, wrong values, wrong options, wrong branches,
  and substituted evidence.

Public artifacts:

- Harbor: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Hugging Face: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark page: <https://blobfish.ai/benchmarks/counselbench-100>
- Source: <https://github.com/blobfishai/legal-agent-simulation>

```bash
python3 benchmark/counselbench100/builder.py
python3 -m unittest discover -s benchmark/counselbench100/tests -p 'test_*.py' -v
python3 benchmark/counselbench100/run_suite.py
python3 benchmark/counselbench100/tests/conformance.py \
  --report dist/counselbench-100/reports/provider-contract-audit.json
```

Reference trajectories prove solvability and are excluded from model ranking.
A leaderboard row is eligible only after one model executes all 100 tasks
against the exact cryptographically identified release. Older, partial, or
cross-version scores are not inherited.

Generated files are written to `dist/counselbench-100` and ignored by Git. The
committed catalog and decision-rule table contain 100 authored matter spines
and 100 authored causal decisions. Generation and grading make no model or
external-network calls.

The canonical explorer lives in the Blobfish website repository. The page
under `site/` is retained only as a historical launch artifact.
