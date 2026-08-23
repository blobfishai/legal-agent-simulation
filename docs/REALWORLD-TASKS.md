# v20 draft — real-world task additions (23 tasks)

> **Simulation only.** Every company, person, court, statute, deadline, and
> figure in these tasks is synthetic test data. Real matters supplied task
> *shapes*; the in-world "law" is a seeded memo corpus the verifiers pin
> against, so grading never depends on live law or an LLM judge.

`world/blobfish/world-v20-draft.json` (**2,347 tasks**, world_id
`legal-agent-simulation-world-v20-draft`) is the single merged v20 draft line,
built by `world/v20/build.py` on the frozen `world-v19.json` base. It adds
three things:

1. **16 real-world consumer-protection tasks** (two families, 54 seeded
   documents, 6 new matters) — this document's main subject;
2. **6 RetailGuard retail price-accuracy tasks** riding a draft-lane product
   addition (9 `rc_*` tables, 19 `retail_*` tools from
   `mcp/v4/contracts/retail-compliance.json`);
3. **1 recovered Harvey LAB practice task** (`labp_b50165c2a9cd39db`), taking
   LAB hosting to **2,010/2,010**.

All tasks ride the native v18/v19 lane: each carries a `walk` plus
`reference_args` the oracle replays verbatim, and verifiers are compiled by
the generic declarative VCode compiler (`world/v19/verifiers.compile_vcode`,
re-exported by `world/v20/verifiers.py`). The realworld pack sources of record
are emitted to
`world/expansion/packs-realworld/consumer-protection-{compliance,privacy}.json`;
the retail/recovery lane's task and verifier dicts live in
`world/v20/retail_lane.json` (extracted from the superseded single-lane
`world-v20.json` before its deletion), with tables regenerated at build time
from the RetailGuard contract plus
`research/retail-price-accuracy/seed-data.json`.

## Provenance — real anchor → synthetic transform

Research provenance with citations: `research/realworld-tasks/RESEARCH.md`;
machine-readable designs: `research/realworld-tasks/task-designs.json`.

| Real anchor | Synthetic matter | Tasks |
|---|---|---|
| *Kukorinis v. Walmart*, No. 8:22-cv-02402 (M.D. Fla.) ($45M weighted-goods and bagged-citrus settlement) + MI Scanner Law / MA item pricing / CT free-item rule / NIST HB130 EPPV | *Delgado v. Halvorsen Market Group, Inc.* — $42.5M settlement; §7.3 51-jurisdiction survey; §7.4 receipt footer; §7.5 T&C/receipt/signage remediation | cp_001–cp_005, cp_008, cp_009 |
| People v. Walmart CA weights-and-measures consent judgments (quarterly audits, $3-or-free guarantee; penalties count overcharges only) | Halvorsen San Bernal County stipulated judgment CIVSB-2024-118822 — Q3 audit scorecard, rider matrix | cp_006, cp_007 |
| FTC v. Amazon (Prime) $2.5B negative-option settlement + 8th Cir. click-to-cancel vacatur (7/8/2025) + CA/NY/VT/IL/DC ARL variance | Cobalt Peak Media / PeakStream+ FCB consent order — 51-jurisdiction ARL matrix + enrollment/cancel remediation | cp_010, cp_011 |
| FTC Fees Rule 16 CFR 464 (in effect 5/12/2025) + CA SB 478/SB 1524 + MN + MA 940 CMR 38 + Marriott PA AVC | Bluewater Lodge & Resorts AG CID — all-in pricing exhibit + drip-pricing matrix | cp_012 |
| *Cothron v. White Castle* per-scan accrual + SB 2979 single-accrual amendment + BIPA §15(a) 3-year destruction | Prairie Grill *Suarez* settlement — destruction schedule, exposure math, §6 package | pp_001, pp_002 |
| Equifax multistate settlement + real 51-jurisdiction breach-notification variance (30/45/60-day, AG thresholds, MA content bar, CT monitoring, encryption safe harbors) | Harborline Outfitters credential-stuffing breach — notification grid + state-variant letters | pp_003, pp_004 |

The Walmart shape the program asked for — "settled in California, review all
other jurisdictions' law, implement changes across receipt, contract, wording"
— is exactly cp_001 (51-row survey matrix), cp_002 (remediation rollout +
deadline), cp_004 (T&C redline), cp_005 (receipt spec), and cp_007
(guarantee-conflict riders). That prompt conflates separate matters: the
`Kukorinis` settlement was a Florida federal weighted-goods case, while
California separately brought checkout-price and price/weight enforcement
actions. The benchmark preserves the operational pattern without presenting a
California accidental-double-scan class settlement as a verified fact.

## Task inventory

| Task | Slug | Capability | Difficulty | Assertions | Built-in traps |
|---|---|---|---|---|---|
| task_v20_cp_001 | delgado-51-jurisdiction-survey-matrix | rule_application | high | 23 | superseded draft matrix (MI $10, MA all-retail, WY YES); never-enacted-statute memo; NY sunset |
| task_v20_cp_002 | delgado-remediation-rollout-and-deadline | computation | medium | 12 | Puerto Rico row in footprint (must exclude); off-by-one date |
| task_v20_cp_003 | delgado-puerto-rico-scope-escalation | abstention_and_escalation | medium | 7 | correct outcome is NO determination; fabricated PR row is vetoed |
| task_v20_cp_004 | delgado-terms-of-sale-redline | grounded_drafting_and_redlining | high | 7 | REJECTED v8 draft must not be the base |
| task_v20_cp_005 | delgado-receipt-spec-and-rolled-deadline | computation | medium | 7 | raw deadline is a Sunday; calendaring it fails |
| task_v20_cp_006 | consent-judgment-q3-audit-scorecard | computation | high | 16 | superseded 95%/undercharge template; boundary store 0233; undercharge-only store 0522 |
| task_v20_cp_007 | consent-judgment-guarantee-rider-matrix | rule_application | high | 11 | stale $2.00 signage; over-riding CA |
| task_v20_cp_008 | delgado-claims-administration-calendar | computation | high | 10 | opt-out lands on a Sunday; unrolled date fails |
| task_v20_cp_009 | delgado-claims-adjudication | computation | high | 16 | superseded flat-$15 Exhibit C; late claim; rolled opt-out timeliness |
| task_v20_cp_010 | peakstream-arl-51-jurisdiction-matrix | rule_application | high | 22 | vacated-federal-rule-as-effective; FL misclassification; 48-row undercount |
| task_v20_cp_011 | peakstream-arl-remediation-spec | grounded_drafting_and_redlining | medium | 12 | "call us to confirm" step must not survive |
| task_v20_cp_012 | bluewater-drip-pricing-remediation | computation | high | 18 | vacated-vs-in-effect federal rule confusion; abolish-the-service-charge recommendation |
| task_v20_pp_001 | prairie-grill-destruction-schedule-and-exposure | computation | high | 14 | NULL-template employee gets no date; already-overdue deadline; per-scan vs per-person scale |
| task_v20_pp_002 | prairie-grill-section6-remediation-package | grounded_drafting_and_redlining | medium | 13 | vendor "mathematical representations" position must be rejected |
| task_v20_pp_003 | harborline-51-jurisdiction-breach-grid | rule_application | high | 21 | encryption safe harbor; AG threshold (OR at 214); retired 45-days-everywhere playbook; mailing math |
| task_v20_pp_004 | harborline-state-variant-letters | grounded_drafting_and_redlining | high | 11 | MA content bar (attack method and count are absent-checked on the MA letter) |

Every task also carries per-document read-evidence assertions
(`tool_observation_contains` on `documents_download`), a required-path check,
a minimum-successful-calls floor, and a no-collateral-damage table guard.
Eight seeded trap documents ship across the families:
`draft-compliance-matrix-v1-SUPERSEDED`, `terms-of-sale-v8-draft-REJECTED`,
`superseded-2024-report-template`, `exhibit-c-draft-SUPERSEDED`,
`draft-arl-matrix-v0-STALE`, `draft-matrix-and-memo-v0-TRAP`,
`vendor-position-letter`, `legacy-ir-playbook-2019-RETIRED`.

## RetailGuard retail lane (6 tasks) — draft-lane product addition

RetailGuard (SIMULATED) is a retail price-accuracy compliance system added to
the **draft world only** — the v19 surface and its 91-tool contract set are
untouched; the v20 draft is served with `mcp/v4/contracts` (the frozen v3
system contracts plus `retail-compliance.json`: 9 `rc_*` tables, 19
`retail_*` tools, 110 agent-visible MCP tools total). This is consistent with
the T2 rule: the product ships **because** six admitted tasks exercise it —
`tools/check_v20_retail.py` asserts the union of the six tasks'
`retail_*` required tools equals the full 19-tool surface, so no endpoint
exists without an exercising task.

| Task | What it grades |
|---|---|
| task_v20_retail_incident_audit | incident findings recorded + audit filed from the checkout evidence |
| task_v20_retail_refund_exposure | Michigan bounty refund approved; incident exposure updated; analysis filed |
| task_v20_retail_51_jurisdiction_triage | 51-row `rc_jurisdiction_rules` triage (6 primary-source-triaged, 45 flagged pending substantive validation, attorney validation required on all rows) |
| task_v20_retail_receipt_redline | receipt template redline with statutory-rights savings language |
| task_v20_retail_control_remediation | POS control remediation (duplicate-scan threshold) |
| task_v20_retail_national_closeout | 4-phase checkpointed national remediation (26-call walk; per-phase vcodes) |

Provenance: `research/retail-price-accuracy/` — NIST HB130-shaped scenario
documents (docx/xlsx/pdf) built reproducibly by
`tools/build_retail_price_accuracy_pack.py` (byte-identical `--check` gate),
structure-preserving jurisdiction mutations (CA/MI/DC scenario triplet with a
shared structure signature), and a sources manifest of sha256-pinned reference
PDFs. The 51-jurisdiction register is honest about research depth: only 6
jurisdictions are primary-source triaged; the other 45 are marked
`official_portal_identified_not_substantively_validated` and every row carries
`attorney_validation_required`.

That paragraph describes the frozen v20 lane. V21 preserves the six benchmark
rules but replaces the 45 portal-only executable rows with exact issue-spotting
citations and official URLs from `jurisdiction-research-v2.json`; their status
is `specific_authority_mapped_attorney_validation_required`, and no new remedy,
deadline, applicability conclusion, or local overlay is encoded.

## Recovered Harvey LAB task (1)

`labp_b50165c2a9cd39db` recovers the one quarantined LAB practice task
(`contracts/commercial-vendor-customer/vendor-services-agreement-term-negotiation/scenario-03`).
The upstream task omitted only its output filename contract; the recovery
supplies a disclosed `response.md` adapter
(`provenance.adapter_output_contract = "response.md"`) while the pinned source
bytes stay untouched (`source_task_unchanged: true`; the file lane points at
the read-only mirror's 15 input documents). With it, practice hosting reaches
1,760/1,760 unique sources and total LAB hosting **2,010/2,010** — recorded in
the world's `lab_practice_recovery` key and asserted by both
`tools/check_v20_retail.py` and the build's own fail-closed hosting check.

## Admission evidence

- **Measured model baseline (single episode)**: `grok-4.5` on
  `task_v20_cp_001` against the served draft (2026-08-22): 12 tool calls,
  $0.099, verdict **NOT PASSED** — the verifier correctly withheld reward from
  an incomplete attempt while the oracle proves the same task solvable
  (16/16). Anthropic and DeepSeek keys were API-limit-blocked at measurement
  time (Anthropic resets 2026-09-01), so no multi-model baseline is claimed.
- **Content validators**: `world/v20/content.py::validate()` re-derives every
  pinned date (weekend rolls included), every sum (317 stores, 1,684 network,
  638,204 residents, 636,332 mailings, 27 AG jurisdictions, 30/21 ARL split),
  and every dollar figure ($698.85, $923.00, $350,398.00, $15.54B/$8.4M/$42M).
  The build additionally refuses to emit a world if any pinned assertion string
  is missing from the oracle reference output, any trap string is present in
  it, or any read anchor falls outside the 4,000-char observation window.
- **Oracle (all against the merged 2,347-task draft, served with
  `mcp/v4/contracts`)**: realworld 16/16 → `world/v20/oracle-realworld.json`;
  retail 6/6 → `data/oracle-v20-retail.json`; recovery 1/1 →
  `data/oracle-v20-harvey-recovery.json` — every report
  `{"passed": all, "pass_rate": 1.0}`.
- **Discrimination (four modes per task via
  `world/v20/discriminate_lane.py`: noop, text_only, blind_write,
  wrong_value)**: 16 realworld → `world/v20/discrimination-realworld.json`;
  6 retail → `data/discrimination-v20-retail.json`; 1 recovery →
  `data/discrimination-v20-harvey-recovery.json`. All 23 tasks × 4 modes fail
  as required: zero discrimination failures, zero inconclusive wrong-value
  probes, zero harness errors.
- **Gates**: `npm run retail:check` (pack byte-reproducibility +
  `tools/check_v20_retail.py`) and `npm run v20:check` both exit 0 against the
  merged draft; the retail gate additionally pins RetailGuard contract/seed
  equality, the 121/110/19-tool runtime surface, the 56-table world,
  scenario-manifest hashes, and the recovery task's adapter contract.
- **Parity audit**: `tools/build_harvey_parity_audit.py` regenerated
  `reports/harvey-parity-audit.json` + `docs/HARVEY-PARITY-AUDIT.md` from the
  merged draft (hosted 2,010/2,010; the G1–G11 open-gap ledger is preserved)
  and its `--check` mode verifies the artifacts are current.
- **Base integrity**: the build reads `world-v19.json` and writes only
  `world-v20-draft.json` (plus `world/v20/` artifacts and the emitted packs);
  the superseded single-lane `world/blobfish/world-v20.json` was deleted after
  its lane was extracted to `world/v20/retail_lane.json`.
- **Harbor**: task dirs for `task_v20_cp_001` and
  `task_v20_retail_national_closeout` regenerated from the merged draft under
  `dist/harbor-v20-smoke/` (image `legal-agent-sim-world:v20-draft`); oracle
  trial on cp_001 via the real harbor CLI → reward 1.0.

## Run one end-to-end

```bash
npm run v20:build     # = python3 world/v20/build.py (deterministic merged draft)
npm run v20:check     # = python3 tools/check_v20_retail.py (merged-draft gate)
npm run retail:check  # pack byte-reproducibility + the same gate

# serve the merged draft (v4 contracts = v3 systems + RetailGuard)
python3 world/local/server.py --port 8979 \
  --world world/blobfish/world-v20-draft.json --v2-contracts mcp/v4/contracts &

python3 world/local/oracle.py --base http://127.0.0.1:8979 \
  --world world/blobfish/world-v20-draft.json \
  --tasks task_v20_cp_001 --out /tmp/oracle-cp001.json      # expect 1/1

# four-mode discrimination for any task set
python3 world/v20/discriminate_lane.py --base http://127.0.0.1:8979 \
  --tasks task_v20_retail_national_closeout --out /tmp/disc.json

# a real model episode
node sim/run-simulation.mjs --task task_v20_cp_001 --engine deepseek-chat \
  --base http://127.0.0.1:8979

# harbor lane (separate out-dir; does not touch the v16 export)
python3 harbor/generate.py --world world/blobfish/world-v20-draft.json \
  --out dist/harbor-v20-smoke --tasks task_v20_cp_001 \
  --image-tag legal-agent-sim-world:v20-draft --build-image
uv run --project harbor/runner --locked harbor run \
  -p "dist/harbor-v20-smoke/tasks/task_v20_cp_001" -a oracle
```

## Design decisions and dropped elements (recorded honestly)

- **Spreadsheet deliverable → DMS matrix document.** The mirrored Sheets tool
  (`sheets_values_update`) persists one cell per call by vendor-faithful
  design, so a 51-row live sheet would cost 51 writes against the 50-write
  session cap. The matrix deliverables are therefore MatterVault documents
  with a canonical row grammar stated in each prompt (pins and traps check
  exact row strings), plus a summary note carrying the pinned aggregates.
- **Email sends dropped from graded walks.** `gmail_messages_send` takes a
  base64 RFC-822 body; grading its content would pin encoding rather than
  substance. The "email the partner/GC/insurer" steps in the original designs
  became pinned summary notes on the matter.
- **PDF/XLSX inputs are text-bodied DMS documents.** The in-world DMS stores
  full text bodies (`dm_documents.body`); filenames keep their design
  extensions (`.xlsx.txt` where the body is a data export) so provenance to
  the design specs stays legible. The binary file lane remains the LAB
  import's domain.
- **Puerto Rico abstention.** The designs' "51 jurisdictions, PR excluded"
  detail became a dedicated abstention task (cp_003) in the
  hallucination-trap tradition: the only passing behavior is an escalation
  note; any statute determination for PR is vetoed.
- The v19 world remains the frozen M7 calibration RC; `world-v20-draft.json`
  is a draft superset awaiting the usual promotion gates (fixtures, matrix,
  program-status regeneration) before any leaderboard use.
