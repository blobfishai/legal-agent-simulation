# CounselBench-100 source

This directory contains the deterministic source generator, MCP world,
qualification suite, and release tooling for CounselBench-100.

The v2.0.0 release contains 100 original synthetic matters, 9,600 seeded source
documents, high-level employee requests, 100 distinct 46-call accepted MCP
trajectories, three decision alternatives per matter, and a deterministic
182-criterion verifier with partial-credit rewards and strict full-task pass.
The release completed 600 local qualification executions with 100/100 oracle
passes, 100/100 exact replays, and zero false accepts across 400 adversarial
controls. A model leaderboard row is published only after all 100 tasks have run
on this exact release; the prior ten-task v1.1 sample is not inherited.

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
  benchmark.counselbench100.tests.test_scoring -v
python3 benchmark/counselbench100/run_suite.py
python3 benchmark/counselbench100/tests/conformance.py \
  --report dist/counselbench-100/reports/mcp-conformance.json
```

Reference trajectories prove solvability and are excluded from model ranking.
Any future model publication must cover all 100 v2.0 tasks exactly once.

Generated release files are written to `dist/counselbench-100` and are intentionally ignored by Git. The committed catalog contains 100 hand-authored matter spines; generation makes no network calls.

The canonical benchmark explorer lives in the Blobfish website repository and
is deployed at the public URL above. The page under `site/` is retained only as
the historical v1.0 launch artifact.
