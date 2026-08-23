# World-Creation Playbook

> **Scope:** the “Lawfirm status” snapshots below describe the lightweight
> product-only v16 reference world and its 91-tool vendor baseline. The current
> v21 Harbor release is a larger 23,310-task, 1,100-visible-tool superset; see
> [the v21 release audit](V21-RELEASE-AUDIT.md).

The canonical pipeline for building an executable agent world in any vertical
(next up: sales). Each stage lists what the lawfirm-qwen build already
implements (with the script/evidence that proves it) and what is new work.
The law world is the reference implementation of this playbook; the sales
world should reuse the machinery and close the gaps marked **NEW**.

## Stage 0 — Question-driven research (never one-shot)

Start from the user's prompt and interrogate the domain until the world is
understood, not just described. The research must produce a stored corpus,
not a summary:

- **Question ledger first.** Before searching, write the questions: What is
  the domain? Who are the stakeholders in each workflow? What is the business
  value? What tasks do they actually do all day? What counts as *done* for
  each task? What are the failure/chaos scenarios of the business? Which
  tools touch which steps?
- **Multi-angle sweep** for the answers: GitHub workflows in the domain,
  every agent arena/eval that touches it, practitioner articles, product
  docs of the tools in the workflow. One agent per angle; every claim keeps
  its link.
- **Everything lands in `data/research/`** as documents + a structured
  registry, so later stages cite evidence instead of memory.

*Lawfirm status:* implemented — 29-benchmark inventory
(`data/research/legal-eval-inventory.md`), 101-item domain registry with
4-angle GitHub/workflow sweep (`data/research/domain-registry.json`),
AA-leaderboard reference. **NEW for sales:** make the question ledger an
explicit first artifact (`data/research/questions.md`) and iterate the sweep
until every question has a cited answer — the law build asked its questions
implicitly.

## Stage 1 — Thesis

Compress the research into the world's thesis: domain, company archetype,
stakeholders/roles, core workflows, entities, and the *definition of done*
per workflow. The thesis is the framing every later stage must be consistent
with. (The blobfish world document carries this as `thesis`; fill it from
Stage 0's ledger, not from vibes.)

## Stage 2 — Tool census and multi-system mocking

Enumerate the real tool landscape of the domain, then mock **all of it**:

- List the systems practitioners actually use — for sales: Salesforce CRM,
  HubSpot, Apollo, Outreach, Gong, plain Excel/Sheets, a local SQLite/ERP,
  email. For each: pull its MCP server docs, public API reference, and
  GitHub examples of people driving its CLI/API — that's the ground truth
  for the mock's surface.
- Mock each system as its own tool namespace with its own storage:
  some records live in the mock-Salesforce tables, some in mock-HubSpot,
  some in a spreadsheet file, some in a local DB. **The fragmentation is the
  realism**: "what's total sales this week?" must require joining
  spreadsheet + CRM + local DB, with the systems disagreeing in the ways the
  Stage 0 articles say they disagree.
- Data chaos is *designed from evidence*: every chaos pattern (duplicate
  leads, stale sync, currency mismatches, superseded quotes) traces to an
  eval, article, or reading collected in Stage 0.

*Lawfirm status:* implemented — 91 agent-visible product tools over one session-private SQLite
world with chaos-lite (distractor documents, superseded drafts, ambiguous
acks, injected API friction; `world/local/server.py`), now fronted by **9
per-system MCP servers** (practice management, court records, e-filing,
deadline rules, DMS, discovery, Workspace, e-billing, and e-signature — `mcp/systems.json`,
`mcp/serve-system.mjs`, topology-proven by `npm run mcp:test`). **NEW for sales (the
headline gap):** multi-system fragmentation — several mock services with
separate namespaces/storage and cross-system reconciliation tasks. The local
runtime already supports the mechanics (tool namespaces, per-table state,
seeded friction); what's new is generating N systems with overlapping,
deliberately inconsistent data.

## Stage 3 — Tables and core-service mocks

From the scenarios + tool census, design the tables per system and the
MCP-tool ↔ table contracts (which tools read/write which tables, what an
audit trail looks like, which fields are load-bearing for verification).
Depth target: every workflow from the thesis has the tables it mutates, and
every graded outcome is a row a verifier can pin.

*Lawfirm status:* implemented — 47 product-state tables,
vendor-shaped tool contracts, and verifier-pinnable outcomes (`world/expansion/assemble.mjs` generates
verifiers with pinned answer keys; `world/local/oracle.py` is the admission
gate: a task ships only if its reference walk executes and passes).

## Stage 4 — Task seeding from evals, arenas, and articles

Start from the tasks the field already measures: every eval/arena task shape
found in Stage 0, plus scenarios described in practitioner articles. Port
each with the answer-key discipline: prompt states the output vocabulary,
the answer comes only from the seeded data, the verifier pins it
(exact values, required reads, forbidden fabrications).

*Lawfirm status:* implemented — eval-anchored packs plus native product workflows,
291 tasks, 291/291
oracle-verified; coverage proof with per-item verdicts
(`docs/COVERAGE.md`).

## Stage 5 — Triage loop: run, classify, and grow to the boundary

Run the target model 1–3 episodes per task and triage:

| Outcome | Label | Action |
|---|---|---|
| Fails 3/3 | **too hard** | Stop escalating. First rule out harness fault (see below) — then keep the task labeled, and mine it for failure modes. |
| Mixed (1/3, 2/3) | **flaky — the gold** | Keep. These sit at the capability boundary; diff the passing vs failing runs to name the failure mode (why sometimes-pass/sometimes-fail). |
| Passes 1st try | **too easy** | **Grow it**: spawn harder variants of the same task — more steps, more depth, more ambiguity in the prompt, longer required walks (3 tools → 10), withheld titles, more distractors, superseding instructions. Re-run. Repeat until the lineage produces a flaky or too-hard descendant. |

**The growth loop is the point**: every too-easy task is a seed for a longer-
horizon descendant; the world keeps deepening until the model fails, so the
task set always hugs the current model's boundary.

**Harness-fault discipline (non-negotiable):** before believing any failure,
audit it. The lawfirm build found three harness bugs masquerading as model
failures — output-cap truncation reading as "emission collapse",
shared-seed contamination reading as off-task damage (202 verdicts flipped),
and one prompt/verifier drift task — all documented with quantified impact
in `docs/AUDIT.md`. Every new world inherits that audit checklist:
truncation markers (`finish_reason`, arg-parse failures at the token cap),
state isolation between servers, prompt↔verifier consistency probes, and
whole-family zero-scores treated as bug-suspects first.

*Lawfirm status:* triage + classification implemented
(`sim/run-leaderboard.mjs` 3-episode protocol, `sim/lib/classify-failure.mjs`
10-mode taxonomy, per-model reports, all-failed-traces evidence page).
**Growth loop v1 implemented** (`sim/grow-tasks.mjs`): picks families the
engine passed 3/3, emits depth-6/8/10 variants (interleaved audit reads +
pinned writes) as growth packs → `assemble --packs-dir … --out world-grown` →
oracle-admit → measure. **Round-1 finding (deepseek-chat, 9 grown tasks,
27/27 episodes passed):** raw depth with an explicitly stated chain does NOT
move the boundary — long-horizon execution of a spelled-out plan is easy;
the discriminating levers are the hosted pushes' tier-3+ ones: withheld
ids/titles (agent must find the record), unstated chains (derive the
procedure from a policy memo), and derived values (compute, don't copy).
Growth round 2 should escalate ambiguity, not length. That is exactly the
"grow until failure" loop doing its job: r1 proved the mechanism and
eliminated one hypothesis.

**Round-2 result (measured, deepseek-chat, 15 v3 workflow tasks × 3 eps,
$1.07):** ambiguity escalation works — the pack scores **95.6** with **2
flaky boundary tasks and 0 too-hard**, versus r1's 27/27 clean sweep. The two
boundary tasks name their failure modes precisely: (a) **silent scan
truncation** — the all-matters trust sweep called the list tool with its
default limit (25 of 36 rows), computed balances from a partial set, and
filed 2 of the 4 required overdraft alerts; (b) **friction non-recovery** —
an injected error hit one required checkpoint of the LEDES gate and the run
moved on instead of retrying. Both are exactly the operational failure modes
this world exists to catch. Round 3 should push the same levers harder
(larger scan sets that force explicit pagination; multi-hop derived values).

**Audit discipline held here too:** the round's third failure (0/3 on the
docket-alert task) was traced to an authoring bug — the prompt said
"new-entry alert" while the enum value is `entry`, and the required walk gave
the agent no way to discover the vocabulary. Fixed by making discovery part
of the task (list existing alerts first, then create with the observed
value); it now passes 3/3 with the model sending `"entry"`. A task is not
allowed to grade a guess.

## Packaging — Harbor

The finished world exports as a self-contained Harbor package (task.yaml,
Dockerfile, environment DB + server, tasks.jsonl, integrity manifest) so any
harness can run it without this repo: `python3 world/local/export_harbor.py`.

## The invariants (any vertical)

1. Research is stored, question-driven, and multi-angle — never one-shot.
2. Every tool mocked from its real docs; every chaos pattern from evidence.
3. Data fragmented across systems the way the domain actually fragments it.
   **Domain-fidelity gate:** every table, column, and tool justifies itself
   against the thesis — a two-tier vocabulary lint (foreign-anywhere infra
   terms; foreign-in-firm-systems business terms, with client documents
   exempt) runs at generation time (`world/expansion/domain-lint.mjs`; law
   run: docs/DOMAIN-AUDIT.md found the ERP invoices/employees remnants).
4. A task is admitted only if its reference walk executes and its verifier
   passes (oracle gate); verifiers pin answers deterministically.
5. Failures are audited for harness fault before they are believed.
6. Flaky tasks are the product; too-easy tasks are seeds for growth;
   too-hard tasks stop growing and feed the failure-mode report.
