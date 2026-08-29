# CounselBench-100 source

This directory contains the deterministic source generator, pinned MCP world,
qualification suite, and release tooling for CounselBench-100.

The v3.1.0 release contains 100 original synthetic legal matters and 9,700
agent-visible files across ten practice workflows, including a native PDF and
parser-validated XLSX evidence source in every task. Each employee request asks for a
decision in ordinary workplace language. The task-specific investigation is
discovered from the records: twelve portfolio items must be joined across
immutable identity, operative authority, current operations, and effective
approval/revision evidence.

Every task has a real mix of 5–9 supported actions and 3–7 evidence holds. It
requires 56–67 full evidence reads and a distinct 76–93-call MCP trajectory,
including three state-changing deliverables and exact post-write readback. All
100 raw tool sequences and all 100 semantic action graphs are distinct.

The v3 qualification ran 1,200 local executions:

- 100/100 oracle passes
- 100/100 exact deterministic replays
- 0 false accepts in each of ten adversarial controls (1,000/1,000 rejected)
- copied-gold, no-op, state-only, incomplete-read, write-before-read,
  missing-readback, unauthorized-write, wrong-value, wrong-decision, and
  wrong-evidence trajectories all fail

Public artifacts:

- Harbor: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Hugging Face: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark page: <https://blobfish.ai/benchmarks/counselbench-100>
- Source: <https://github.com/blobfishai/legal-agent-simulation>

```bash
python3 benchmark/counselbench100/builder.py
python3 -m unittest \
  benchmark.counselbench100.tests.test_builder \
  benchmark.counselbench100.tests.test_generation \
  benchmark.counselbench100.tests.test_scoring
python3 benchmark/counselbench100/run_suite.py
python3 benchmark/counselbench100/tests/conformance.py \
  --report dist/counselbench-100/reports/mcp-conformance.json
```

Reference trajectories prove solvability and are excluded from model ranking.
A leaderboard row is eligible only after one model has executed all 100 tasks
against the exact v3.1.0 release. Older or partial scores are not inherited.

Generated files are written to `dist/counselbench-100` and are ignored by Git.
The committed catalog and decision-rule table contain 100 authored matter
spines and 100 authored causal decisions. Generation and grading make no model
or network calls.

The canonical explorer lives in the Blobfish website repository. The page under
`site/` is retained only as a historical launch artifact.
