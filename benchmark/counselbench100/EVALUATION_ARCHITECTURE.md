# CounselBench evaluation architecture

CounselBench uses the same functional loop as enterprise agent benchmarks:
isolated task state, an agent process, captured trajectories, and an independent
grading step. Harbor provides orchestration; a pinned filesystem MCP provides
the sandbox; a deterministic legal verifier grades investigation, decision,
state, and answer.

## Runtime flow

```text
high-level employee request + 96 immutable source records
                         |
                         v
              filesystem MCP sandbox
                         |
                         v
  identity -> authority -> operations -> approval/revision
                         |
              +----------+----------+
              |                     |
       supported action        evidence hold
              +----------+----------+
                         |
        decision + matter-register state + advice
                         |
             exact post-write readback
                         |
                         v
             hidden deterministic verifier
```

The agent receives neither the gold output nor the verifier token. It can reach
only `/workspace/documents` and `/workspace/output` through six tool
contracts pinned to the official MCP filesystem server. Hidden world
specification files are outside the allowlisted roots.

Each task has twelve portfolio items, 96 records in twelve folders and seven
text-native formats, 55–65 required evidence reads, 3–8 custody checks,
task-specific searches, three writes, and three readbacks. Reference
trajectories range from 68 to 85 successful calls. The verifier checks causal
prerequisites and outcomes, not one exact call order.

## Archipelago/APEX mapping

| Layer | CounselBench / Blobfish | Archipelago / APEX analogue |
|---|---|---|
| Task state | Immutable source room, writable output state, per-trial trace | Environment image plus initial snapshot |
| Tool gateway | Pinned official filesystem MCP contract with closed offline implementation | Environment-server APIs and task-specific tools |
| Agent execution | Harbor agent container | Agent service and selectable implementation |
| Trajectory | Complete MCP trace plus agent and verifier artifacts | Trajectory, final snapshot, prompts, and agent logs |
| Grading | Deterministic causal, branch, state-diff, containment, and readback criteria | Independent grading service with composable graders |
| Reproducibility | 100 oracle trials, 1,000 negative controls, 100 exact replays, contract conformance | Containerized reruns against frozen environment and grader |

The similarity is functional, not a claim that implementations are
interchangeable. Archipelago separates environment, agents, and grading into
services. CounselBench delegates orchestration to Harbor, embeds the MCP world
inside every task pack, and keeps verification behind a capability token.

## Why deterministic grading works here

The generator creates raw facts and independently recomputes every branch from
four controls. The evidence does not carry the computed disposition. The
verifier can therefore check exact IDs, revisions, values, source paths,
owners, deadlines, state rows, and trace ordering without a model judge.

This design intentionally limits the scored claim. Open-ended legal
persuasiveness is not graded. Whether the agent found the right records,
applied the released decision rule, changed only the task-scoped state, and
reported the exact supported result is graded.

## Public references

- [Mercor Archipelago source](https://github.com/Mercor-Intelligence/archipelago)
- [APEX Accounting benchmark](https://www.mercor.com/apex/apex-accounting-leaderboard/)
- [APEX Agents leaderboard](https://www.mercor.com/apex/apex-agents-leaderboard/)
- [Harbor Framework](https://harborframework.com/)
- [Model Context Protocol servers](https://github.com/modelcontextprotocol/servers)
