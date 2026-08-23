# Results Audit — is it the model, or is it a bug?

Every failure cluster in the measured runs was treated as a suspected harness
bug until proven otherwise. The defects below record their measured blast
radius, remediation, and whether historical scores changed. Everything
reported in `reports/` is post-audit unless a section says otherwise.

## Bug 1 — output-cap truncation masquerading as "emission collapse" (FIXED)

**Symptom:** the classic doom loop — `draft_matter_document({})` →
"missing 3 required positional arguments" → identical retry — the same mode
the original hosted failure report called the dominant boundary behavior.

**Diagnosis:** draft tool calls that failed JSON parsing clustered at
**p50 = 21,131 / p90 = 21,807 bytes** of arguments — the byte-size of exactly
~4,096 tokens, which was `maxCompletionTokens`. The completion was truncated
mid-JSON by the harness, parsed as `{}`, and executed as an empty call. The
model never emitted an empty call.

**Impact:** 172 of 547 DeepSeek draft calls truncated; 12 failed episodes
attributable; the *shipped hosted report's* "emission collapse" mode carries
the same signature and the same 4096 cap and should be read as a harness
artifact (addendum added to `docs/FAILURE-REPORT.md`).

**Fix:** cap raised to 8192 (deliverable bodies observed ≤ ~23KB fit);
`finish_reason` now logged; the 12 tainted episodes re-run. Post-fix parse
errors: zero; emission collapse: zero.

## Bug 2 — shared-seed contamination poisoning guard assertions (FIXED)

**Symptom:** an off-task-damage tsunami: `no_offtask_table_changes` +
`no_undeclared_rows_created` failing together on 135 DeepSeek / 115 Haiku
episodes, always naming `matter_documents` with "130 → 205 rows, new ids
131+".

**Diagnosis:** the original-world server (:8971) and the expanded-world
server (:8972) shared `world/local/state/seed.db`. Starting the expanded
server rebuilt the shared seed with the 75 expansion documents; every later
session on :8971 began with 205 documents against a verifier baseline of 130.
The "damage" was my expansion pack, not the model.

**Impact:** 126 DeepSeek / 114 Haiku episodes contaminated; **106 / 96
verdicts flipped** after exact offline rescoring
(`sim/rescore-contaminated.mjs` — strips only the matter_documents component
with the 130→ baseline signature, then recomputes pass/reward with the
verifier's own aggregation; originals preserved under `preRescore`).
DeepSeek 65.4 → **88.2**; Haiku 35.6 → **60.3**.

**Fix:** per-world state directories in `server.py`. Caveat noted in
methodology: contaminated sessions also *showed* the extra 75 documents to
the agent (marginally more distractors in queries); verdict-level rescoring
corrects the grading, not that second-order exposure.

## Bug 3 — prompt/verifier drift in one shipped task (QUARANTINED)

`task_016`'s prompt names invoice INV-1CU8DF9 (row id 9); its shipped
verifier pins row id 1. A correct agent fails; a wrong one passes. Kept
runnable, excluded from scored sets (`config.scoring.quarantinedTasks`).

## Bug 4 — verification baseline captured before per-task seeding (FIXED; 107 archived verdicts quarantined)

Per-task seed bundles are upserted into a session at creation. Before the fix
the verifier's `initial_state` was the **base-world** snapshot, taken before
that seeding — so rows the seed bundle inserted were credited to the agent.
`state_changed` and `rows_inserted_into_<table>` then passed on work no agent
did.

Found by reading traces rather than by a test: `task_098-t1` (Haiku) is
recorded as **passed with reward 1.0** having called only
`query_matter_documents` and `read_matter_document` — it never filed the
deliverable. Its own verdict gives it away, `reads_before_writes` reporting
`writes=0` beside `rows_inserted_into_matter_documents: 130 -> 205 rows`.
That self-contradiction is the detector (`sim/lib/quarantine.mjs`) — it needs
no tool-type table and no name regex, both of which mislabel delegation
surfaces like `operations_records_agent` (declared `read`, inserts rows).

*Fix:* `baseline_for()` snapshots the session database **after** seeding.
*Verified:* an empty episode on `task_038` now fails `state_changed`
("NO state change — agent did nothing") and `rows_inserted_into_matter_documents`
(`267 -> 267 rows`).

*Impact on archived evidence:* 107 verdicts (101 Haiku, 4 DeepSeek, 2
dual-surface), **34 of them recorded as passes**. Traces store steps and
verdicts but not world state, so they cannot be re-scored offline — a valid
verdict requires re-running. Until then they are excluded from every rate and
listed in `reports/QUARANTINE.md`. Excluding them moves Haiku from 60.1 over
388 episodes to **69.3 over the 287 self-consistent ones** — the direction is
up, because most contaminated verdicts failed the workflow-path check anyway;
the honest statement is that Haiku's true rate is unmeasured until a re-run.

## Bug 5 — `required_workflow_path` graded the reference solution's browsing order (FIXED; 9 verdicts corrected)

The check matched the declared checkpoint list as a strictly ordered
subsequence, which enforced ordering among the **read** checkpoints. That
ordering carries no legal or procedural meaning. A path of

    legal_matters_list -> legal_matters_get -> legal_matters_evidence_create

failed an agent that already had the matter id, fetched it directly, then
listed for context: identical evidence, identical write, zero reward. Eight
archived episodes fail on exactly that pattern, and a ninth
(`task_v3_006-t3`) only because seeded rate-limiting threw a 429 and its
successful retry landed after the next read — the world punishing correct
friction recovery.

*Fix* (`world/expansion/fix-path-ordering.mjs`, 217 + 15 verifiers rewritten):
every checkpoint must still succeed, declared repeats still require that many
successful calls, writes must occur in declared relative order, and every read
must occur before the write it justifies. Reads are unordered among themselves.
`reads_before_writes` and `no_shortcut_direct_update` are untouched and carry
the read-then-write discipline independently.

*Verified* three ways: the oracle still admits **270/270**; probes on both
verifier shapes behave correctly — reads in any order pass, write-before-reads
fails, write-without-reads fails, a missing read fails, and 2-of-3 required
writes fails (repeat counting intact); and an offline replay over all 296
archived failures flips exactly the 9 read-ordering artifacts, leaving 145 path
failures standing — including `task_086-t3`, whose delegation ran *after* its
write.

Unlike Bug 4, this one is exactly recomputable: the path assertion is a pure
function of the trace's tool sequence, no world state. The 9 corrections are in
`reports/PATH-RULE-RESCORE.md` and applied in the tasks-and-traces browser.
DeepSeek moves 88.1 → 89.3 on self-consistent verdicts.

## Bug 6 — the assembler allocated task ids by COUNT, not by maximum (FIXED before shipping)

`assemble.mjs` numbered appended tasks `task_${originalTaskCount + n}`. That is
correct only while no task has ever been retired. Retiring the 38 recipe tasks
left the surviving ids scattered — the world still contained `task_233`
through `task_270` — so the next assembly minted `task_233…task_270` a second
time and shipped **38 duplicate ids**.

Nothing crashed. The oracle simply ran `task_246` twice (`[1/2] fail`,
`[2/2] PASS`), the verifier lookup resolved whichever entry came first, and the
run reported 245/270 with failures attributed to innocent pre-existing tasks.
The tell was the oracle's own progress counter printing the same id twice — a
250-line report where the only wrong thing was a bracket.

*Fix:* allocate from `1 + max(existing numeric id)`. Retired ids are never
reused, so archived traces referencing them stay interpretable. New tasks land
at `task_271…task_308`; re-assembled world proves **270/270**.

## Bug 7 — a generated scenario that contradicted its own prompt (CAUGHT PRE-SHIP)

The covenant pack computes which financial covenant a borrower breached and
assigns the remediation owner from that. One generated borrower
(Cedarline Manufacturing, leverage 2.65x against a 3.50x maximum, coverage
3.06x against a 2.75x minimum) breached **neither** — but the branch fell
through to "coverage", so the task would have ordered the agent to open a
remediation while its own prompt said *"Do not open a remediation for a
covenant that is not breached."* Exactly the incoherent-task shape that
produced the `task_251` refusal earlier in this project.

*Fix:* the generator now **throws** rather than emitting a scenario with no
breach, so the defect cannot be reintroduced by editing the figures. This is
the general lesson from `task_251`: an answer key computed from data is safe;
an answer key computed from data with a silent fallback is not.

## Bug 8 — an answer key that contradicted the world, caught by a MODEL (FIXED)

`async-screen-coverage` asked for the number of documents the privilege screen
scanned and pinned **9**, the size of the review set. The runtime computes
coverage by `related_shape`, which is the whole matter folder — the review set
*and* the protocol document beside it — so the job reports **10**.

DeepSeek recorded 10 in three episodes out of three and was right every time.
The task was wrong.

The reason this survived the oracle is structural and worth stating: **the
oracle writes the pinned value; it never reads the job result.** A key that
disagrees with what the world actually returns is invisible to a reference walk
that never asks the world. The discrimination sweep could not see it either —
it perturbs the answer and checks for rejection, which a wrong-but-consistent
key passes.

Only measurement caught it, and only because the model disagreed. That is the
argument for measuring even when a task is oracle- and discrimination-proven:
those two prove the task is *satisfiable* and *bound*, not that it is *correct*.

*Fix:* coverage is derived from the document list (`REVIEW_SET.length + 1`)
rather than asserted, so it cannot drift from what the runtime counts. Re-run
after the fix: 3/3.

## Bug 12 — a third of `structural` is keyed off filenames, and its headline score measures that, not the model (FOUND; NOT YET FIXED)

*Defects 9–11 are described in `HANDOFF.md` but were never written up here; this
keeps their numbering rather than renumbering around the gap.*

`structural` was reported as the hardest generated family by a distance — 13%
recall, 5% precision. It is two families wearing one label.

Its 32 tasks were generated by two different code paths. The generator
originally matched folder names against the *flattened filenames* in
`world/corpus/ch/text/`, which drop the folder path; it was later fixed to read
the `folder` column of `index.sqlite`. Waves 1–16 (**11 tasks**) were frozen
into the bank under the old path, waves 20–23 (**21 tasks**) under the new one.
Five tasks name folders — `Disclosure Schedules`, `Signature Pages` — that do
not appear anywhere in the index, and in three the absent folder is the
*positive* term, so no answer can score above zero.

Do **not** try to tell the two apart by the `computed` field. Every structural
task says `"filename evidence of X without Y"` because that string is
hard-coded in the generator's `add()` call and was never updated when the
derivation changed. It describes the old path, is emitted by the new one, and
is the sort of stale provenance label that makes an audit trail worse than
none. The reliable discriminator is reconstruction: recompute the key from the
index and see whether it reproduces.

Simulating a perfect agent against each key, with no model in the loop:

| | recall | precision | exactly right |
|---|---|---|---|
| waves 20–23, exact top-level reconstruction | 100.0 | 100.0 | **21/21** |
| waves 1–16, same perfect reconstruction | 38.2 | 8.8 | **0/11** |

The modern tasks are perfectly answerable — median **3** tool calls, max 12,
against a 40-turn budget. The legacy ones are unreachable by any strategy,
because the key describes a corpus layout that the index does not have.

Then the sampling: of the four `structural` tasks in the 15-task pilot, **three
were legacy** (waves 16, 2, 2). The 13%/5% line is mostly a measurement of
broken answer keys.

There is a real difficulty underneath, and it should be kept. `corpus_files_list`
filters `folder LIKE '%X%'` while the gold uses the top-level folder, and the
corpus contains `Engagement` alongside `Engagement & Administration`,
`Correspondence` alongside `Correspondence/Client`. An agent that trusts the
filter's membership gets 88.8 recall / 57.3 precision and **0/21 exact**; one
that re-filters on the exact `folder` string the tool already returns in every
row gets 100/100. That is a genuine trap about believing a query's semantics
over its output, and it is worth measuring.

*Fix, applied:* the 11 non-reproducing tasks carry `quarantined: true` and a
reason in `world/blobfish/corpus-wave-tasks.json`, and
`sim/run-firm-knowledge.mjs` skips quarantined tasks by default (`--all` to
include them, for anyone re-checking the keys). They were selected by
reconstruction — recompute the key from the index, quarantine what does not
reproduce — not by the `computed` label, which is wrong for all 32. The
generator's hard-coded label is corrected so new waves describe their real
derivation. `structural` is 21 runnable tasks; the family has **not** been
re-measured, so its difficulty is still unknown and the 13%/5% figure should
not be cited.

*Scope — the other families were checked and are clean.* `conjunction`,
`exclusion` and `client_roll` derive their keys from document bodies, and
`corpus_search` reads those same files with the same lowercased-substring
semantics. Reproducing 9 sampled keys from the tool's semantics returned the
gold set element-for-element, 9 of 9. The index also matches the corpus on
disk exactly — 9,288 files each way, no rows with `chars = 0`, no
`parse_error` — so nothing the generator saw is hidden from the tool.
`superlative` is **unchecked**: its key rests on per-file hit counts rather
than set membership, and that needs its own pass. Structural was the only
family whose key was computed from a source the agent cannot query.

## Bug 13 — no verifier read a deliverable's text, so 119 tasks cannot tell right from wrong (PARTLY FIXED)

Asked what checks the write quality of a drafting task, the answer was: nothing.
`task_003` commissions an antitrust risk memo. Its only content-bearing
assertion is

```python
chk("rows_inserted_into_matter_documents", after_n > before_n, ...)
```

Live against the world, a document titled `asdf` with body `asdf` returned
`passed: True, reward: 1.0`.

It generalises. Across the 288 verifiers of world-v14, **none** referenced a
document body and none did any text inspection; 121 decided correctness on row
counts alone and 167 pinned only metadata (`doc_type`, a status, a role). Split
by method the line is clean: **0 of 117 `graph_walk` tasks pinned any field
value**, while all 156 `eval_anchored_expansion` tasks did.

The discrimination gate had been reporting this the whole time and it was read
as noise: **119 of 291 tasks fail `wrong_value` discrimination** — a perturbed,
wrong answer still scores reward 1.0. 117 of the 119 are `graph_walk`. That is
not a model result and never was; those tasks measure workflow compliance
(read-before-write, no off-task damage, audit log intact), which is worth
measuring and is not drafting.

The material for a fix was already in the repo. The packs ship a complete gold
deliverable body — `deep-drafting`'s `msa-counter-redline-cover-note` carries a
full counter-turn cover note — and the assembler used it only as the oracle's
reference answer, never as an assertion.

*Partly fixed:* `assemble.mjs` takes a `grounded` block on a create and emits
two core assertions over the written text — `<field>_grounded_in_sources` (every
required anchor present, body over a minimum length) and
`<field>_no_unsupported_claims` (no value the sources contradict). Anchors are
strings a correct deliverable must carry verbatim: ratios, dollar figures,
section numbers, a counterparty's name. `world/expansion/packs-grounded/` uses
it for three covenant-compliance tasks (`task_327`–`task_329`) seeded with a
superseded amendment carrying plausible wrong figures, so the check fails a
confidently wrong memo as well as an empty one:

| deliverable | verdict |
|---|---|
| reference body | PASS (oracle, 3/3) |
| `asdf` | FAIL — 7 anchors missing, 4 chars |
| fluent prose, no figures | FAIL — 7 anchors missing |
| cites the superseded amendment | FAIL — both checks, naming `4.25:1.00`, `$10,000,000`, `60 days` |

All three discriminate correctly under the gate. **The other 117 do not, and
are unchanged** — this adds a family that works rather than repairing the ones
that do not. Converting them is next, and cheap where a pack already ships a
gold body.

Two known limits. Substring anchors only bind facts a correct answer must state
verbatim, so this raises the floor on grounding and says nothing about the
quality of an argument. And reward is the fraction of core assertions passed, so
`asdf` still scores **0.8** while failing — for anything consuming reward as a
training signal that is too generous, and grounding probably belongs with the
guards that veto to 0.

## Bug 14 — same-world server startup could publish a partial SQLite seed (FIXED)

**Symptom:** the M0.3 sustained replay first produced an intermittent
`oracle_error` on `task_314`; later in the same process, fixture sessions began
failing with `database disk image is malformed` and then connection refusals.
The abandoned session database was 167,936 bytes while the complete seed was
2,129,920 bytes. A fresh server passed `task_314` three of three times and the
full fixture bank, excluding a task/verifier defect.

**Diagnosis:** Bug 2 namespaced state by world, but two processes serving the
*same* world still shared one `seed.db`. Startup removed and rebuilt that file
in place. A concurrent session `shutil.copyfile` could therefore observe the
database between schema creation and completion. Per-world namespacing stopped
cross-version contamination; it did not make same-version publication atomic.

**Fix:** `build_seed_db` now creates a private
`seed.db.<pid>.<uuid>.tmp`, adds both Gen-1 and contract tables, runs
`PRAGMA integrity_check`, and atomically publishes it with `os.replace`.
Session construction removes its destination if copying or task seeding fails.
`tools/check_atomic_seed.py` blocks a writer before publication and proves a
reader sees the complete old seed followed by the complete new seed—never the
intermediate database. Post-fix sustained replay: oracle 291/291,
discrimination 291/291 with zero harness errors, fixtures 1,455/1,455
byte-identical, badbank 6/6 rejected.

**Blast radius:** infrastructure availability only; the malformed session never
produced a task verdict. The new classifier treats any missing/malformed episode
as `HARNESS-ERROR`, so this class can no longer be misreported as model failure.

## Bug 15 — multi-row verifiers allowed pins to come from different rows (FIXED)

**Symptom:** after the M0 classifier switched from stale assertion metadata to
the assertions actually executed by VCode, `task_v3_013` and `task_v3_015`
became `BROKEN-KEY`: a corrupted terminal note still passed.

**Diagnosis:** `build-v3-tasks.mjs` generated one independent search across all
new rows for each pinned field. On a three-note task, an earlier correct row
could satisfy `subject=EXPENSE POLICY REVIEW` while a different row satisfied
`matter_id=19`; no single row had to satisfy the declared insert. The world
document's `assertions` arrays also omitted these generated pin checks, so the
old report classified both tasks as having no answer key instead of exposing
the defect.

**Fix:** every declared insert now compiles to one same-row predicate containing
all of its pins; each diagnostic check evaluates that predicate. The v3 builder
has `--refresh-only`, can update the 15 generated verifiers in the canonical
world without altering tasks or seeds, and emits complete assertion manifests.
The discrimination classifier derives assertion names from executable VCode,
reports metadata drift separately, and exits non-zero on broken keys. The two
fixed tasks pass their oracle and reject no-op, text-only, blind-write, and
wrong-value episodes. Full post-fix result: **174 discriminating, 117 declared
no-answer-key, 0 broken keys, 0 broken guards, 0 harness errors**.

**Historical measurement impact:** task_v3_013's three recorded model passes
contain the correct three matter/subject pairs and remain passes. The archived
task_v3_015 result used an older four-matter key and is already represented by
its saved per-episode assertions; it is not silently regraded under the current
two-matter world. Any cross-version comparison must use the task/world version
recorded with the episode.

## Bug 16 — top-level JSON-RPC errors looked like successful oracle calls (FIXED)

**Symptom:** an oracle reference step that named an unknown or unavailable tool
could receive a valid JSON-RPC `error` envelope, yet the trace recorded
`ok: true` with an empty observation. The Harbor solve shim had the same
interpretation. A verifier that did not independently require that step could
therefore let an unsolvable reference walk appear healthy.

**Diagnosis:** both clients inspected only `result.isError`. JSON-RPC protocol
errors live in the mutually exclusive top-level `error` member, so an absent
`result` was coerced to `{}` and then treated as success.

**Fix:** `OracleSession.call`, Harbor trace forwarding, and the Harbor reference
solver now fail any top-level `error` and preserve its body in the trace. The
M7.1 gate calls a deliberately nonexistent tool and asserts failure. It also
runs the leaderboard canary against a clean world and a copy with a seeded
failing verifier: the clean probe exits 0; the corrupted probe exits 3 after
**zero model episodes**. Pure fixtures cover refusal/zero-call/infra
classification, friction rate, verifier crashes, and wall-clock percentiles.
The committed proof is `data/leaderboard/canary-proof-v19.json`.

**Blast radius:** reference/admission confidence, not previously saved model
verdicts. No shipped reference walk names an unknown tool, so the M0 golden
fixtures remain byte-identical; the defect mattered when evolving or partially
migrating a world.

## What survived the audit (real model behavior, with evidence)

1. **Side-copy writes (DeepSeek, 34 episodes).** The model files the
   deliverable correctly, then *also* writes a duplicate via
   `document_agent` / notes via `save_memory` into assistant tables —
   undeclared record creation the world's guards veto. Evidence it is not a
   lure of the local runtime: the hosted trajectories show the hosted model
   never touched those write surfaces, and the guard contract is identical.
   Real enterprise-relevant behavior: agents scribbling into side systems.
2. **Deliverable left in chat (Haiku, 36 episodes).** Researches correctly,
   then writes the memo into its final chat message and never calls
   `draft_matter_document`. Zero argument-parse errors and zero missing-arg
   errors across all 110 Haiku draft calls — when it drafts, it drafts
   cleanly — so this is instruction-following, not emission capability.
3. **Checkpoint/order adherence (both; Haiku 108 vs DeepSeek 21 episodes).**
   The world's ordered-playbook contract requires declared checkpoints in
   order (e.g. `list → get → create`, or an `operations_records_agent`
   review step the prompt only implies). Models complete the outcome but
   skip/reorder checkpoints. Strict — the records-research family (0–22%
   scores) is best read as "implicit-checkpoint adherence", not research
   incapacity; both flagged as contract-strict in the reports.
4. **The flaky-21 boundary set** remains discriminative post-fix: DeepSeek
   87.3, Haiku 56.9 — with per-episode traces on disk.

## Residual caveats

- Haiku's row is **partial** (388/465 episodes; its lane was stopped
  mid-run to cap spend) and its contaminated episodes were rescored, not
  re-run.
- `document_agent`/`sheet_agent`/`calendar_agent` semantics are synthesized
  (hosted implementations are lost); their write-through behavior matches the
  hosted tool contract (write-type tools with agent-table targets) but was
  not byte-verified against hosted code.
- All scores are world-specific; absolute numbers are not comparable to any
  other harness (see `docs/WHY-BEYOND-HARVEY-LAB.md` §2).

*Measurement spend: DeepSeek ≈ $50 (465 episodes + re-runs), Haiku ≈ $45
(388 episodes, stopped). No further model spend without explicit go-ahead.*

## Bug 17 — the public LAB comparison overstated scope after the judge-lane amendment (FIXED)

**Symptom:** `WHY-BEYOND-HARVEY-LAB.md` still described a 156-task, Gen-1 world and
could be read as claiming parity with LAB's complete rubric judgment. That was no
longer the implemented architecture: world-v19 hosts 2,009 of 2,010 LAB tasks,
determinizes 65,614 of 111,814 practice criteria, and deliberately does not run a
prose-quality judge.

**Diagnosis:** the narrative was handwritten before the v16–v19 migration and had no
executable dependency on the import, ingest, oracle, discrimination, file-lane, or
triage reports. The §0G amendment removed the judge lane from the headline, but no
gate forced the claim language to change with it.

**Fix:** `tools/build_superset_matrix.py` now derives both the machine-readable matrix
and the public write-up from committed proof artifacts. The checker fails if the
dropped 46,200 criteria, absent judge lane, exact-hash recovery accounting, contamination boundary,
iManage ceiling, or incomplete calibration disappears. The claim is narrowed to a
strict operational superset of the deterministically admitted LAB subset—not a
superset of LAB's prose-quality judgment.

**Blast radius:** documentation and external claims only; task rewards and prior model
episodes are unchanged. M7 remains open until the three-episode world-v19 calibration
report is complete.

## Bug 18 — calibration resent multi-megabyte schemas for unbounded turns (FIXED)

**Symptom:** the first world-v19 calibration pilot spent $189.68 on only 31
episodes. A five-call task consumed roughly 4.5 million prompt tokens; several
short failing tasks consumed 30–40 million each.

**Diagnosis:** the model request published all 91 vendor schemas on every turn.
The list serialized to 2,989,272 bytes because two self-contained DocuSign
request schemas alone contributed 2,770,307 bytes. Independently,
`maxAgentTurns` was implemented as a floor (`Math.max`), despite its name and
comment describing a cap. Ordinary tasks therefore received at least 50 turns,
while one pilot task received a 1,551-turn allowance. The 31 quarantined
episodes accumulated 700,704,206 prompt tokens and 1,324 tool calls.

**Fix:** measured sweeps now support a recorded `systems` protocol: every
system needed by the workflow, one deterministic core-system distractor, and
one deterministic specialist distractor. Scoping remains at whole-system
granularity, so it never reveals the exact reference walk and it does not alter
any vendor schema. The turn allowance is now bounded by
`min(50, max(10, ceil(reference_calls * 1.25) + 5))`. Triage and leaderboard
builders reject records from a different scope or protocol version. Long episodes retain the 12
most recent tool results verbatim and deterministically compact older results
to 1,000 characters (six/300 under context pressure), while preserving every
assistant/tool protocol link and the full immutable episode trace. Episode records can be stored
as deterministic JSON.GZ with raw/compressed collision checks and byte-identical
rebuild tests. A v1 post-fix probe passed for $0.07966: 290,296 prompt
tokens, seven turns/eight calls, and a 138,293-byte three-system schema surface.

**Blast radius:** the pilot never entered a completed calibration report. Its
31 records are preserved under
`data/leaderboard/quarantine/deepseek-chat/v19-triage-oversized-schema/` and are
excluded from every denominator. No oracle, verifier, task, or product contract
changed; this was a model-runner protocol and spend-control defect.

## Bug 19 — a cost-safe turn floor truncated the calibration (FIXED)

**Symptom:** after Bug 18's schema fix, the first breadth-first calibration
slice produced 0 passes and 89 of 106 episodes ended on their exact turn
ceiling. The records were internally valid but could not distinguish model
difficulty from a harness timeout.

**Diagnosis:** protocol v1 used a 10-turn minimum. The 106-task slice averaged
15.4 turns and 32.6 tool calls, but 84% exhausted the allowance. This was not an
API or verifier failure; the model was still actively using tools when the
runner stopped it. A ceiling that binds most episodes is part of the task, not
an incidental resource guard, and therefore must be calibrated and versioned.

**Fix:** protocol v2 raises the minimum to 20 turns while retaining the hard
50-turn cap: `min(50, max(20, ceil(reference_calls * 1.25) + 5))`. The observed
v1 cost/turn curve projects v2 at roughly $1.7K for 6,972 episodes, within the
$2K program envelope and behind both $10/episode and $1,700/sweep circuit
breakers. An explicit `--max-turns` override now clears the canonical protocol
identifier, so probes can never enter the production denominator. Pure gates
pin that behavior.

**Blast radius:** all 106 v1 episodes are preserved under
`data/leaderboard/quarantine/deepseek-chat/v19-triage-turn-budget-v1/` and are
excluded by the protocol-version gate. The episode-major schedule made the
sample broad, but no v1 result is reused. Tasks, verifiers, world state, and
vendor contracts are unchanged.

## Bug 20 — flat-rate accounting hid cache economics and justified a leaky scope (FIXED)

**Symptom:** the runner reported $189.68 for the 31-episode all-tools pilot and
projected that an unrestricted world sweep would exceed the approved $2K envelope.
That projection forced protocol v2 to expose only systems inferred from each task's
reference walk. Even with two distractors, the scope leaked task relevance and made
the benchmark easier than the nine-system world it claimed to measure.

**Diagnosis:** DeepSeek returned `prompt_cache_hit_tokens` and
`prompt_cache_miss_tokens` on every completion, but the runner discarded both and
charged all input at the uncached V3 rate. The API was in fact serving
`deepseek-v4-flash` behind the stale `deepseek-chat` alias. Replaying the immutable
pilot logs at DeepSeek's 2026-08-12 published V4 Flash rates ($0.0028/M cache-hit,
$0.14/M cache-miss, $0.28/M output) yields **$4.18**, with a **97.9% input cache-hit
rate**. The original estimate was 45.4× too high.

**Fix:** provider cache fields are now accumulated per turn, unclassified tokens are
conservatively billed at the uncached rate, and every episode records the full cost
breakdown, served model, pricing date, and official source URL. Protocol v3 exposes
all 91 tools across all nine systems and uses one uniform 50-turn ceiling; deterministic
context compaction remains. `systems` scoping remains available only for diagnostic
probes and cannot receive the canonical protocol id. A pure CI gate pins cache,
fallback, model-alias, and provenance behavior.

**Blast radius:** all v1/v2 measurements and cost projections are quarantined by
protocol id; no task, verifier, world state, or vendor contract changed. The paid
world-v19 denominator starts empty under `v19-all-tools-fixed50-context-v4`.

## Bug 21 — wall-clock allowance still leaked oracle walk length (FIXED)

**Symptom:** an all-tools v3 acceptance probe completed eight of ten representative
episodes, including the 125-call capstone, but `task_003` and one LAB extraction task
were killed twice before they could write terminal records. Their model action budget
was the same 50 turns as every other task; their process budget was not.

**Diagnosis:** `run-leaderboard.mjs` still calculated child timeout from the reference
walk: `max(12, min(45, 5 + reference_calls * 0.35))` minutes. This both leaked oracle
complexity and gave a short-reference task less wall-clock opportunity to use the same
published 91-tool surface. The eight terminal v3 records took 1.1–13.2 minutes; two
valid 50-turn records ended at the action ceiling, while the missing cases were killed
at the unrelated 12-minute process ceiling.

**Fix:** protocol v4 pins one 30-minute wall-clock ceiling for every task, independent
of reference data, alongside the uniform 50-turn action ceiling. A timeout remains an
infrastructure classification and is never scored as model failure. The v3 probe is
preserved in its own namespace and excluded by protocol id; CI pins the v4 timeout.
The replacement ten-family proof produced 10/10 graded records, zero infrastructure
errors, three passing oracle canaries, $1.03420 total billed cost, and a 22.20-minute
maximum (`data/leaderboard/protocol-proof/deepseek-chat/v19-all-tools-fixed50-context-v4/manifest.json`).

**Blast radius:** eight valid but provisional v3 records and two missing records; none
entered the production namespace or any leaderboard denominator.

## Bug 22 — terminal provider billing errors fanned out as generic infrastructure retries (FIXED)

**Symptom:** the production v4 sweep reached 327 valid records, then the graded
denominator stopped while the scheduler advanced from 327 to 400 jobs in seconds.
Every new DeepSeek request was failing with HTTP 402 `Insufficient Balance`, but child
stdout/stderr were discarded and the parent treated every missing episode record as a
generic retryable infrastructure failure.

**Diagnosis:** `run-leaderboard.mjs` ignored child diagnostics, retried all
infrastructure failures once, and had no terminal-provider error class. Concurrency
therefore amplified one external account-state change into dozens of redundant calls.
No failed child wrote an episode, so none entered a model denominator or incurred a
reported token charge; 327 previously completed records remain valid and immutable.

**Fix:** child stdout/stderr now feed a bounded 4KB diagnostic tail. HTTP
400/401/402/403/404/422 failures are terminal; the first one halts the sweep without a
retry, writes the reason to sweep health, and exits with code 5. Timeouts and 5xx errors
retain one retry. A live proof against the exhausted account records one passing oracle
canary, one infrastructure classification, HTTP 402, zero model-failure credit, and
zero reported spend in `data/leaderboard/provider-halt-proof-v19.json`; the pure CI gate
also pins transient and timeout branches.

**Checkpoint:** `data/leaderboard/calibration-checkpoint-v19.json` hashes all 327 v4
episodes: 13 passes, $30.14736 actual spend, 99.11% cache-hit rate, $612.63 empirically
projected remaining spend, and 6,645 missing episode slots. It also reports the 141
turn-ceiling outcomes separately from infrastructure (61 were error-heavy in their last
ten calls). M7.2 remains open until the same DeepSeek denominator reaches 6,972/6,972;
switching engines would require a clean restart, never score mixing.

## Bug 23 — the public exit flag did not aggregate every milestone gate (FIXED)

**Symptom:** `data/superset-matrix-v19.json` correctly remained not-ready while
calibration was incomplete, but its readiness calculation inspected only oracle,
discrimination, fixture-count, and triage signals. If conformance, one of the three
new product workflows, the capstone replay, or an ecosystem adapter later regressed
while those four signals stayed green, the matrix could have declared the whole
program ready.

**Diagnosis:** M0–M8 had strong individual checkers but no single executable exit
ledger. The public matrix was therefore a partial aggregate rather than the source of
truth implied by `program_exit_ready`.

**Fix:** `tools/build_program_exit_audit.py` now derives
`data/program-exit-v19.json` and `docs/PROGRAM-STATUS.md` from every milestone's
committed proof. Each check has a proof pointer and verification command;
`tools/check_program_exit_audit.py` requires exact M0–M8 coverage, rejects missing
proofs, and reconciles all failed checks with the top-level open-gate list. The
superset matrix consumes this audit and cannot disagree with it. CI executes all
upstream checks before rebuilding both aggregates.

**Blast radius:** public readiness and release bookkeeping only. No task, verifier,
model episode, or score changed. The stronger aggregate reports 8/9 numbered
milestones green and exactly one external gate: M7.2 calibration.

## Bug 24 — the calibration checkpoint's resume command targeted the wrong server (FIXED)

**Symptom:** the committed checkpoint advertised a resume command without
`--local-base`. In a clean shell, the runner falls back to
`config/world.config.json` at port 8971, while the frozen world-v19 calibration
server and handoff use port 8988. The command was descriptive but not directly
runnable.

**Diagnosis:** the first calibration process supplied its local base outside the
command recorded by `tools/build_calibration_checkpoint.py`. That ambient setting was
not present in `.env` and therefore was not reproducible from the checkpoint alone.

**Fix:** the generated resume command now pins
`--local-base http://127.0.0.1:8988`. The program-status artifact publishes both the
matching server command and the exact resume command; its checker rejects a handoff
that loses the explicit base URL.

**Blast radius:** handoff metadata only. The 327 committed episodes, provider-halt
proof, measurement protocol, and projected remaining spend are unchanged.

## Program variance 1 — task-driven T1 is 91 tools, not the charter's estimated 150–170 (ACCEPTED)

**Observed variance:** the charter estimated a nine-system end state of roughly
150–170 tools. The conformance registry and agent surface contain 91 discoverable
tools, with 11 additional non-discoverable simulator/migration operations.

**Resolution:** the count was a planning estimate, while the same charter makes
task demand the endpoint-admission rule and explicitly defers T2 endpoints that no
task uses. The complete 2,324-task bank closes over the 91-tool surface: the full
v18 oracle proves 2,289 tasks and the v19 M6 oracle proves the 35 additions. Every
discoverable tool is conformance-registered and there are zero simulator-extension
gaps. Adding dozens of uncalled endpoints would weaken, not strengthen, that rule.

**Guard:** M2's `task_used_surface_closure` check now fails if the admitted task
denominator no longer equals the union of the proven v18 and v19 reference walks.
`PROGRAM-STATUS.md` publishes the variance beside the other denominators so the
smaller surface cannot be mistaken for the original estimate or for full-product
API coverage.

**Blast radius:** scope accounting only. No task, endpoint, verifier, or score was
changed. This does not broaden the fidelity claim: conformance remains per exposed,
task-used endpoint, and full vendor surfaces remain out of scope.

## Bug 25 — paid sweep could start without enough disk to checkpoint health (FIXED)

**Symptom:** the first funded resume crossed the 327-record cache and then crashed
with `ENOSPC` while writing `deepseek-chat@v19-triage.sweep-health.json`. The data
volume had only 179 MiB free. The crash occurred before any new graded episode was
committed, so the canonical denominator remained exactly 327.

**Diagnosis:** episode writes were atomic and resumable, but the scheduler had no
storage preflight. A full volume could therefore consume model time before discovering
that the final health/checkpoint artifact could not be written.

**Fix:** 24+ GiB was recovered by clearing only the re-downloadable `uv` package
cache; source, LAB evidence, Docker volumes, and episode data were untouched.
`sim/lib/storage-headroom.mjs` now provides a deterministic storage gate, and every
paid leaderboard run requires at least 1,024 MiB free before its first model call
(configurable with `--min-free-disk-mb`). Low storage exits as infrastructure code 6.
The pure unit gate runs in CI and the exact resume command pins the threshold.

**Blast radius:** no task, verifier, or model score changed. No newly paid episode was
lost. The subsequent exact resume advanced the same namespace from 327 to 856 valid
records before the provider's HTTP-402 guard stopped it.

## Audit finding 1 — v19 friction is deterministic but correlated by tool/call index (OPEN CAVEAT)

**Finding:** production sweep health reports 2,207 friction-shaped observations over
61,586 tool calls: 3.58% versus the configured 3.00%, crossing the 0.5-point alert
threshold. Canaries and verifiers remained clean; the sweep stopped on HTTP 402, not
on the advisory drift alert.

**Cause:** the frozen v19 runtime hashes `(seed, tool, call_index)`. Sessions reset the
call index but do not contribute a deterministic episode key, so agents that repeat a
tool sequence repeat the same scheduled failures. The configured 3% is a hash
threshold, not an independently sampled per-call aggregate, and repeated sequences
can therefore produce a correlated realized rate.

**Disposition:** do not silently change the schedule during the paid v19 denominator;
that would mix two environments under one protocol id and invalidate all 856 records.
The production sweep-health artifact and M7 exit ledger keep the alert visible. A
future schedule-scope change must introduce a deterministic task/episode key, bump the
world/measurement protocol, and start a fresh namespace. This is a comparability
caveat, not permission to relabel the partial sweep as complete.
