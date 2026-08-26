# CounselBench evaluation architecture

CounselBench has the same core evaluation loop as Mercor's public Archipelago
runner—isolated task state, an agent process, captured trajectories, and a
separate grading step—but it uses Harbor packaging and a deterministic legal
verifier rather than reproducing Archipelago's three-service topology.

## Runtime flow

```text
task prompt + 96 immutable records
               |
               v
Harbor trial container -> filesystem MCP world -> append-only tool trace
               |                    |
               |                    v
               +-----------> exactly two output files
                                      |
                                      v
                         hidden deterministic verifier
                                      |
                                      v
                    criteria + category scores + strict pass
```

The agent never receives the gold output or verifier token. The world exposes
six allowlisted filesystem tools over Streamable HTTP MCP. Every full task
requires 96 separate document reads, eight custody checks, inventory and search
calls, and two MCP writes: at least 109 successful calls.

## Archipelago/APEX mapping

| Layer | CounselBench / Blobfish | Archipelago / APEX analogue |
|---|---|---|
| Task state | Immutable `/workspace/documents`, writable `/workspace/output`, per-trial world state | Environment image plus initial snapshot |
| Tool gateway | Pinned filesystem MCP contract with offline implementation | Environment-server APIs and task-specific tools |
| Agent execution | Harbor agent container (`codex` for the measured run, `oracle` for qualification) | Agent service and selectable agent implementations |
| Trajectory | Harbor result, complete Codex transcript, MCP trace, token/cost data | Trajectory, final snapshot, prompts, and agent logs |
| Grading | 182 Boolean criteria, weighted category score, deterministic caps, separate strict pass | Grading service with composable rubric graders; public APEX methodology commonly uses criterion-level model judging |
| Reproducibility | 100 oracle trials, 400 negative controls, 100 exact replays, MCP contract conformance, public-download smoke | Containerized reruns against stored environment and grading configuration |

The architectural similarity is therefore functional, not a claim that the
implementations are interchangeable. Archipelago separates environment,
agents, and grading into services. CounselBench delegates orchestration to
Harbor, embeds the MCP world in each task package, and keeps grading local to a
hidden verifier process.

## Why the grader differs

Legal findings in this benchmark have recoverable record-control fields and
controlled fact anchors. That permits exact criterion checks without a model
judge. The verifier performs no model, network, clock, locale, or random call.
It reports continuous credit for diagnostic value while strict pass still
requires every criterion.

This design avoids evaluator-model drift and makes a score reproducible from
the public verifier report. It also deliberately limits what can be graded:
criteria must be represented by exact fields, trace events, or source-bounded
tokens. Open-ended legal persuasiveness is outside this release's score.

## Public references

- [Mercor Archipelago source](https://github.com/Mercor-Intelligence/archipelago)
- [APEX Accounting benchmark](https://www.mercor.com/apex/apex-accounting-leaderboard/)
- [APEX Agents leaderboard](https://www.mercor.com/apex/apex-agents-leaderboard/)
- [Harbor Framework](https://harborframework.com/)
- [Model Context Protocol servers](https://github.com/modelcontextprotocol/servers)

