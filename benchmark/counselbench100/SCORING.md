# CounselBench-100 scoring contract

CounselBench-100 v2.0 reports continuous, deterministic criterion credit and a
separate strict pass. The grader makes no model, network, clock, locale, or
random call.

## Why v2.0 keeps the corrected metric

The v1.0 baseline contained ten substantive GPT-5.6-sol executions. Every run
read all 96 documents and completed 109–117 successful MCP calls, yet all ten
received zero because the verifier required full JSON equality and a single
all-or-nothing memo grounding gate. Some expected issue labels and remediation
owners were assigned by generator order but were not recoverable from the
records. That made the binary display invalid as a diagnostic model metric.

v1.1 exposed stable finding IDs, issue labels, severity, owner, and response
deadline in realistic record-control metadata. The verifier scores those
recoverable values individually while retaining a strict all-criteria pass.

v2.0 keeps those 182 checks but moves the solve procedure and output schema out
of the user request and into a discoverable work-product control in the evidence
room. The accepted walk inventories all 96 records, then reads the 32 controlling
and corroborating records plus that control. Sixty-four context records remain as
realistic distractors. Every matter has its own reference sequence and three
explicitly explained decision alternatives; no exact call order is graded.

## Criteria per task

| Category | Criteria | Weight |
|---|---:|---:|
| Review procedure | 8 | 25% |
| Structured findings | 152 | 55% |
| Counsel memo | 22 | 20% |
| Total | 182 | 100% |

The findings category has eight document-level criteria plus nine criteria for
each of 16 findings: presence, five exact identity/evidence fields, required
fact anchors, source-bounded controlled facts, and required action anchors. The
memo category checks five sections, one complete grounding criterion per
finding, and absence of forbidden claims.

## Caps and strict pass

- Missing deliverables or outputs not written through MCP cap reward at 0.20.
- Any other incomplete review-procedure criterion caps reward at 0.49.
- Strict pass requires every procedure, finding, and memo criterion.
- Exact equality with the reference answer remains a diagnostic only.

All criterion outcomes and category scores are included in the verifier report,
so a leaderboard value can be reproduced without an external judge.
