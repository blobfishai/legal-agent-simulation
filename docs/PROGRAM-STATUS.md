# LAB-Superset program status

Program exit: **BLOCKED EXTERNAL**.

Local implementation: **complete**. Milestones passed: **8/9**.

This is generated from the committed gate artifacts. A milestone is green only when every listed binary check is green; CI executes the corresponding commands and rejects stale output.

## Milestone gates

| Milestone | Status | Checks | Evidence summary |
|---|---|---:|---|
| M0 · Safety nets | `passed` | 3/3 | 2324/2324 current-world task fixture bundles; 6/6 known-bad tasks represented; CI contains fixtures, badbank, and public-claim gates |
| M1 · Product-surface migration | `passed` | 4/4 | 99 Gen-1 tools retired after 276 migrated + 15 native tasks; 291/291 reference walks pass; 0 broken keys, 0 broken guards, 0 harness errors; 117 content gaps explicitly classified; 21/21 boundary tasks remeasured; 5 observed class changes explained |
| M2 · Vendor contract fidelity | `passed` | 6/6 | 91/91 task-used product-contract tools registered; 0 harness/extension gaps; all 2324 admitted task walks close over the 91 agent-visible tools; no unused endpoints were added to chase the planning estimate; 53/53 published input schemas and 85/85 publicly verifiable vendor targets pass; 91/91 success-wire calls and 19/19 vendor behavior fixtures pass; 13/13 CourtListener tools pass against pinned live-source serializers; iManage partner-gated ceiling is public |
| M3 · Court filing, deadline, and e-signature mocks | `passed` | 3/3 | 5 e-filing + 5 deadline + 5 e-signature tasks admitted; 15/15 new workflow reference walks pass; 0 broken guards/keys or harness errors; 5 e-filing wrong-value mutations explicitly tool-rejected |
| M4 · Evidence and grounded grading | `passed` | 3/3 | 51,683/51,683 LAB documents text-parsed; 9 exact-hash OOXML recoveries recorded; source bytes preserved; build-time proposal/validation; grade time is pure code with 0 judge calls; 110/117 source-grounded text keys + 7 exact-state keys; 0 exceptions |
| M5 · Harvey LAB deterministic import | `passed` | 6/6 | 2,009/2,010 LAB tasks hosted; 1 quarantined with a published reason; 65,614/111,814 criteria (58.7%) clear the executable 55% admission floor; the earlier ~60% was an estimate; 2274/2274 oracle; 0 broken guards/keys; Harbor file/state oracle=1.0 and no-op=0.0; 250 firm-knowledge tasks use F-beta with P/R/over-inclusion channels; 11/11 unique LAB diligence VDRs carry P/R/F-beta/over-inclusion grading (15 executable tasks because one source seeds five migrated tasks) |
| M6 · Long-horizon and multi-turn task families | `passed` | 6/6 | 5 capstones, each with a 50-call reference walk; 30 multi-turn tasks; 35 load-bearing corrections; 35/35 new tasks pass oracle and reject adversarial modes; 5 capstones pass 3/3 with bit-identical state digests; 35/35 pre-correction walks rejected; Harbor capstone and multi-turn cumulative rewards both equal 1.0 |
| M7 · Calibration, canaries, leaderboard, and public claim | `blocked_external` | 5/6 | clean canary passes; seeded defect halts before model spend; 10-family fixed-50/all-tools protocol proof accepted; 856 graded records reconcile; 32 infrastructure outcomes excluded; 0 canary/verifier failures; friction=3.58% (configured 3.00%, alert=true); 856/6972 valid episodes; 6116 remain; leaderboard is derivable for all 2324 tasks and honestly marks 856 partial observations; suspect-audit decision boundary is complete with 0 unresolved rows |
| M8 · Legal eval, skill, and MCP ecosystem adapters | `passed` | 3/3 | 175/175 legal skills pinned; 100 candidates; 0 unsafe auto-admissions; 27 production-MCP tools classified without false exactness; 1 adapter; legal-mcp base-URL swap passes with external network disabled |

## Open gate

- `M7/three_episode_calibration`: 856/6972 valid episodes; 6116 remain.
  External blocker: DeepSeek API account reports Insufficient Balance (HTTP 402). Recommended top-up: **$1150**.

## Denominators that must not be conflated

- `milestone_numbering`: the source plan says eight milestones but enumerates M0 through M8; this audit covers all nine labels.
- `lab_task_hosting`: 2,009/2,010 source tasks (99.95%).
- `lab_practice_criteria`: 65,614/111,814 criteria (58.7%); passes the executable 55% M5 admission floor; the earlier ~60% figure was an estimate, not a hidden pass.
- `tool_surface`: the charter's ~150-170 end-state count was a planning estimate, not an acceptance threshold; the shipped task-driven T1 surface is 91 agent-visible tools plus 11 non-discoverable simulator/migration operations. All 2,324 admitted task walks close over that surface, while the plan's own T2 rule forbids adding endpoints no task exercises.
- `calibration`: 856/6972 valid single-model episodes under one frozen protocol.
- `friction_schedule`: world-v19 freezes the legacy deterministic (tool, call-index) schedule; the production sweep observed 3.58% against the configured 3.00% and keeps the drift alert public. Changing schedule scope requires a new world/protocol namespace, never a mid-denominator runtime edit.

## Exact resume handoff

Start or retain the pinned world server:

```bash
python3 world/local/server.py --port 8988 --world world/blobfish/world-v19.json --v2-contracts mcp/v3/contracts
```

After the provider balance is available, resume the same model/protocol denominator:

```bash
node sim/run-leaderboard.mjs --engines deepseek-chat --tasks all --episodes 3 --concurrency 32 --world-file world/blobfish/world-v19.json --local-base http://127.0.0.1:8988 --label v19-triage --episode-namespace v19-triage --resume --retry-ungraded --compress-episodes --tool-scope all --max-cost-usd 1500 --max-episode-cost-usd 5 --min-free-disk-mb 1024 --canary-every 25
```

Do not mix another engine into the 856 committed DeepSeek episodes. A provider switch requires a fresh 6,972-episode namespace.

## Rebuild and verify

```bash
python3 tools/build_program_exit_audit.py --check
python3 tools/check_program_exit_audit.py
```
