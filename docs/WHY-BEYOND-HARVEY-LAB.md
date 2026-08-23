# What world-v19 proves beyond Harvey LAB

> **Precise claim:** this world is a strict operational superset of the source-grounded LAB subset that is mechanically determinized here. It is **not** a superset of LAB's prose-quality judgment, and it does not call an LLM judge at grade time.

Program exit status: **NOT YET READY**.

Open gate(s): M7/three_episode_calibration: 856/6972 valid episodes; 6116 remain.

## Imported LAB surface

| Measure | Result | Proof |
|---|---:|---|
| LAB tasks hosted | 2,009/2,010 (99.95%) | `docs/PARITY.md`, `world/v17/build-report.json` |
| LAB documents preserved as source bytes | 51,683 | `world/corpus/lab/ingest-report.json` |
| Documents text-parsed | 51,683/51,683 | same report; 0 failures and 9 exact-hash recoveries |
| Practice criteria compiled to assertions | 65,614/111,814 (58.7%) | `world/port/determinate/lab-report.json` |
| Residual practice criteria dropped and counted | 46,200 | never judged or silently passed |
| LAB prose-quality judge | excluded | this benchmark's headline is judge-free |

Hosting and deterministic criterion coverage are different denominators. A task can preserve LAB's inputs and instruction while only its mechanically validated determinations contribute reward.

## Eight additional instruments

| Instrument | Status | Evidence |
|---|---|---|
| System-of-record state verification | `proven` | 2324/2324 reference walks persist the required final state — `data/oracle-v18.json`, `data/oracle-v19-m6.json` |
| Independent file/state lanes | `proven_harness_model_measurement_pending` | file-only fixture produces lane_split=true and reward=0; oracle and no-op Harbor trials preserve both channels — `tools/check_harbor_file_lane.py`, `data/harbor-v17-file-lane-smoke.json` |
| Bit-identical deterministic replay | `proven` | 2324/2324 task verdict fixtures recorded — `tools/fixtures/verdicts`, `tools/check_fixtures.py` |
| Repeated-trial pass^k and empirical difficulty | `implemented_calibration_pending` | 0/2324 tasks have three usable world-v19 model episodes — `data/triage/world-v19.json`, `docs/TRIAGE-v19.md`, `docs/leaderboard/index.html` |
| Seeded fault injection on vendor-shaped errors | `proven` | deterministic 429/stale-reference/auth/async schedules; infrastructure errors have a separate signature — `tools/check_auth_errors.py`, `tools/check_sweep_health.py`, `data/leaderboard/canary-proof-v19.json` |
| Per-step failure attribution | `proven` | every episode records ordered tool, arguments, observation, outcome, and verifier conditions — `sim/run-simulation.mjs`, `docs/evidence/traces.html` |
| Adversarial admission gates | `proven` | 2324/2324 tasks tested; 0 broken guards/keys, 0 harness errors, 5 explicitly inconclusive wrong-value probes — `data/discrimination-v18.json`, `data/discrimination-v19-m6.json`, `tools/check_gates.py` |
| Retrieval precision/recall and paging discipline | `proven_harness_model_measurement_pending` | gold-set F-beta, over-inclusion, and page-completion channels are separate verdict fields — `tools/check_retrieval_grading.py`, `tools/check_pagination.py`, `sim/build-leaderboard-v2.mjs` |

## What the executable world adds

The released world contains **2,324 tasks** across all **10 capability types**, **91 agent-visible tools** plus **11 non-discoverable simulator/migration operations** over **9 mirrored systems**, **5** 50-call capstones, and **30** load-bearing interruption tasks. Its reference proof is 2,324/2,324; adversarial probes cover 2,324/2,324.

LAB asks whether a file satisfies expert-written criteria. This world additionally asks whether the agent read the right evidence, paged through all qualifying records, handled real-shaped failures, changed the correct system state, avoided collateral writes, filed the same grounded deliverable it produced, and retained corrections over a multi-phase matter.

## Deterministic grading boundary

The compiler validates money, dates, numbers, named entities, section references, planted issue sets, retrieval gold sets, redline diffs, and grounded anchors against the task's own evidence. Oracle and discrimination gates then prove the assertion accepts the constructed solution and rejects no-op, text-only, blind-write, and corrupted-value behavior. LLMs may propose build-time interpretations; only code can admit or grade them.

This deliberately gives up argument elegance, tone, persuasion, and open-ended synthesis quality. Those are not approximated with an unreliable automatic judge.

## Caveats that travel with every score

- No prose style, persuasion, or legal-writing-quality score is produced.
- The 46,200 residual practice criteria are not silently treated as passing.
- Verbatim public LAB tasks are contamination-caveated and reported separately.
- iManage fidelity is capped by the public connector specification; the full API is partner-gated.
- Conformance applies to task-used endpoints, not every endpoint in each vendor product.
- The original 291 tasks include synthetic evidence; hosted LAB provenance applies only where recorded.
- 0 LAB files failed text extraction; 9 malformed upstream OOXML packages were recovered only in temporary parser derivatives, with exact paths and hashes published and source bytes preserved.
- The file/state split is proven by Harbor fixtures and an oracle/no-op smoke; model-level lane-split coverage remains null until Harbor model episodes are imported.
- Difficulty labels and the world-v19 pass³ headline remain provisional until `data/triage/world-v19.json` says `complete: true`.

## Rebuild the claim

```bash
python3 tools/build_superset_matrix.py --check
python3 tools/check_superset_matrix.py
```

Every claim above is also available in `data/superset-matrix-v19.json`; no value is maintained separately in prose.
