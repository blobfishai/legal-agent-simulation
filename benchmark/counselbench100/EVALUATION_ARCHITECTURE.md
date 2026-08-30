# CounselBench evaluation architecture

CounselBench uses the same functional loop as enterprise agent benchmarks:
isolated provider state, an agent process, captured trajectories, and an
independent deterministic grader. Harbor provides orchestration; the task pack
serves a closed multi-provider MCP; CounselScore grades investigation,
reasoning, provider state, communication, readback, and containment.

## Runtime flow

```text
high-level employee question + 97 provider-bound assets
                           |
                           v
          Clio Manage | Gmail | Drive | Slack sandbox MCP
                           |
                           v
     identity -> authority -> current fact -> approval/capacity
                           |
                +----------+----------+
                |                     |
         supported action        evidence hold
                +----------+----------+
                           |
       Clio register + Clio note + task-native communication
                           |
              native provider readback after each write
                           |
                           v
              hidden deterministic CounselScore verifier
```

The agent receives neither gold state nor the verifier capability token.
Provider tools expose only task-scoped synthetic resources. Hidden world specs,
expected values, and reference trajectories stay outside the agent boundary.

## Provider fidelity

Each public tool maps to one documented operation:

- Clio Manage v4 matters and notes (`GET`, `POST`, and `PATCH`);
- Gmail v1 messages (`list`, `get`, and `send`);
- Google Drive v3 files and comments (`list`, `get`, and `create`); and
- Slack Web API search, conversation, and post operations.

The sandbox owns deterministic implementation and synthetic state. It does not
rename a business outcome into a fake API. Request nesting, identifiers,
resource paths, methods, read/write annotations, and provider response shapes
remain provider-shaped. A release-time contract audit rejects pseudo-tools,
missing upstream metadata, permissive schemas, and incorrect mutation flags.

## Evidence and state model

Every task has twelve portfolio items, 97 assets in twelve folders and nine
native formats, and 58–86 material reads. Each asset has an immutable evidence
ID, provider record ID, digest, revision timestamp, source role, and material
flag. The remaining assets are inspectable supporting references rather than
secretly mandatory padding.

Reference trajectories contain 69–97 successful calls. All 100 raw tool-name
sequences and semantic action graphs are distinct. The verifier checks causal
prerequisites and resulting provider state; it does not require one arbitrary
global order among independent evidence reads.

## Archipelago/APEX mapping

| Layer | CounselBench / Blobfish | Archipelago / APEX analogue |
|---|---|---|
| Task state | Immutable provider records plus isolated mutable Clio/collaboration state | Environment image plus initial snapshot |
| Tool gateway | Documented provider operations over a closed sandbox MCP | Environment-server APIs and task-specific tools |
| Agent execution | Harbor agent container | Agent service and selectable implementation |
| Trajectory | Full MCP call/result digest trace plus agent and verifier artifacts | Trajectory, final snapshot, prompts, and agent logs |
| Grading | CounselScore semantic milestones backed by atomic evidence, state, containment, and readback checks | Independent grading service with composable graders |
| Reproducibility | 100 oracle trials, 1,500 negative controls, 100 exact replays, provider contract audit | Containerized reruns against frozen environment and grader |

The similarity is functional, not a claim that the implementations are
interchangeable. Archipelago separates environment, agents, and grading into
services. CounselBench delegates orchestration to Harbor, embeds its MCP world
inside each task pack, and protects verification with a capability token.

## Why deterministic grading works

The generator creates raw facts and independently recomputes every branch from
four controls. Evidence does not carry the computed disposition. The verifier
can therefore check exact IDs, revisions, values, source roles, owners,
deadlines, task-scoped state, and trace ordering without a model judge.

The scored claim is intentionally bounded. Open-ended legal persuasiveness is
not graded. Whether the agent found the right records, applied the authored
decision rule, changed only authorized provider state, communicated the exact
supported result, and verified committed state is graded.

## Public references

- [Mercor Archipelago source](https://github.com/Mercor-Intelligence/archipelago)
- [APEX Accounting benchmark](https://www.mercor.com/apex/apex-accounting-leaderboard/)
- [APEX Agents leaderboard](https://www.mercor.com/apex/apex-agents-leaderboard/)
- [Harbor Framework](https://harborframework.com/)
- [Clio Manage API](https://docs.developers.clio.com/api-docs/clio-manage/)
- [Gmail API](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users)
- [Google Drive API](https://developers.google.com/drive/api/reference/rest/v3)
- [Slack Web API](https://api.slack.com/methods)
