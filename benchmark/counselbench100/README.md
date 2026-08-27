# CounselBench-100 source

This directory contains the deterministic source generator, MCP world,
qualification suite, and release tooling for CounselBench-100.

The v1.2.0 generator produces 100 original synthetic matters, 9,600 seeded source
documents, 109-call accepted MCP trajectories, and a deterministic
criterion-level verifier with partial-credit rewards and strict full-task pass.
Since v1.2 the `md` and `txt` evidence records are composed onto the structure of
real legal documents (title block, recitals, articles, tables, signature page)
from vendored Harvey LAB exemplar skeletons (`document_seeds/`, MIT) around the
record-control block the verifier grades; exemplar facts are re-drawn and every
seeded finding literal is scrubbed from the borrowed prose. The published v1.1.0
artifacts predate the structured records; republish after qualification to ship
them.
The release completed 600 local qualification executions, 100/100 Dockerized
Harbor oracle trials, a clean-room run from the public Harbor download, and ten
valid stratified model trials that produced substantive (non-infrastructure)
failures.

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
uv run --project harbor/runner --locked harbor run \
  --config benchmark/counselbench100/oracle-all-v1.1.json --yes
CODEX_FORCE_AUTH_JSON=1 uv run --project harbor/runner --locked harbor run \
  --config benchmark/counselbench100/real-agent-stratified-v1.1.json --yes
```

The Codex command deliberately opts into the authenticated local
`~/.codex/auth.json`; without that flag Harbor 0.22 defaults to an
`OPENAI_API_KEY` connection.

Generated release files are written to `dist/counselbench-100` and are intentionally ignored by Git. The committed catalog contains 100 hand-authored matter spines; generation makes no network calls (the unit tests need `PYTHONPATH=benchmark/counselbench100`).

The canonical benchmark explorer lives in the Blobfish website repository and
is deployed at the public URL above. The page under `site/` is retained only as
the historical v1.0 launch artifact.
