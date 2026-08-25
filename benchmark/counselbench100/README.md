# CounselBench-100 source

This directory contains the deterministic source generator, MCP world,
qualification suite, and public benchmark page for CounselBench-100.

The v1.0.0 release contains 100 original synthetic matters, 9,600 seeded source
documents, 109-call accepted MCP trajectories, and a deterministic verifier.
The release completed 600 local qualification executions, 100/100 Dockerized
Harbor oracle trials, a clean-room run from the public Harbor download, and ten
valid stratified model trials that produced substantive (non-infrastructure)
failures.

Public artifacts:

- Harbor: <https://hub.harborframework.com/datasets/blobfishai/counselbench-100>
- Hugging Face: <https://huggingface.co/datasets/SamuelChien821/counselbench-100>
- Benchmark page: <https://counselbench-100.samuelchien821.chatgpt.site>
- Source: <https://github.com/blobfishai/legal-agent-simulation>

```bash
python3 benchmark/counselbench100/builder.py
python3 benchmark/counselbench100/run_suite.py
python3 benchmark/counselbench100/tests/conformance.py
```

Generated release files are written to `dist/counselbench-100` and are intentionally ignored by Git. The committed catalog contains 100 hand-authored matter spines; generation makes no network calls.

The page under `site/` is independently validated with `npm run lint && npm
test` and deployed through OpenAI Sites.
